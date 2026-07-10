"""Gemini client primitives — uses google-genai SDK."""
import asyncio
import json
import logging
from typing import AsyncIterator

import google.genai as genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger("garner.chat")

# OpenRouter is still used for embeddings
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_model_cache: dict[str, str] = {
    "llm": "gemini-2.5-flash",
    "video_llm": "google/gemini-2.5-flash",
    "embedding": "openai/text-embedding-3-small",
}

_gemini_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=settings.google_ai_api_key)
    return _gemini_client


async def load_model_configs() -> None:
    """Load model config from app_settings (keys prefixed with 'model.') into cache."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.app_setting import AppSetting

    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(AppSetting).where(AppSetting.key.like("model.%"))
        )).scalars().all()
        for row in rows:
            _model_cache[row.key[len("model."):]] = row.value


def _normalize_gemini_model(name: str) -> str:
    """Convert OpenRouter-style names to bare Gemini model IDs.

    google/gemini-2.5-flash → gemini-2.5-flash
    anthropic/claude-3-haiku → gemini-2.5-flash  (non-Gemini fallback)
    gemini-2.5-flash → gemini-2.5-flash
    """
    if name.startswith("google/"):
        return name[len("google/"):]
    if "/" in name:
        return "gemini-2.5-flash"
    return name


def _llm() -> str:
    return _normalize_gemini_model(_model_cache["llm"])


def _video_llm() -> str:
    return _normalize_gemini_model(_model_cache.get("video_llm", "gemini-2.0-flash"))


def _emb() -> str:
    return _model_cache["embedding"]


def _to_gemini_contents(messages: list[dict]) -> tuple[str | None, list[dict]]:
    """Convert OpenAI-format messages → (system_instruction, gemini_contents).

    Handles: system → systemInstruction, user/assistant/tool roles,
    multimodal image_url → inlineData, tool_calls → functionCall,
    tool results → functionResponse.
    """
    system_text: str | None = None
    contents: list[dict] = []
    tc_id_to_name: dict[str, str] = {}

    for msg in messages:
        role = msg["role"]

        if role == "system":
            system_text = (system_text + "\n\n" + msg["content"]) if system_text else msg["content"]

        elif role == "user":
            raw = msg.get("content") or ""
            if isinstance(raw, str):
                parts: list[dict] = [{"text": raw}] if raw else []
            else:
                parts = []
                for item in raw:
                    if item.get("type") == "text":
                        parts.append({"text": item["text"]})
                    elif item.get("type") == "image_url":
                        url = item["image_url"]["url"]
                        if url.startswith("data:"):
                            mime, b64 = url[5:].split(";base64,", 1)
                            parts.append({"inlineData": {"mimeType": mime, "data": b64}})
            if contents and contents[-1]["role"] == "user":
                contents[-1]["parts"].extend(parts)
            elif parts:
                contents.append({"role": "user", "parts": parts})

        elif role == "assistant":
            parts = []
            if msg.get("content"):
                parts.append({"text": msg["content"]})
            for tc in msg.get("tool_calls", []):
                fn = tc["function"]
                name = fn["name"]
                args_raw = fn.get("arguments", "{}")
                try:
                    args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                except Exception:
                    args = {}
                parts.append({"functionCall": {"name": name, "args": args}})
                tc_id_to_name[tc["id"]] = name
            if parts:
                contents.append({"role": "model", "parts": parts})

        elif role == "tool":
            tc_id = msg.get("tool_call_id", "")
            name = tc_id_to_name.get(tc_id, "unknown")
            raw_content = msg.get("content", "{}")
            try:
                response_data = json.loads(raw_content) if isinstance(raw_content, str) else raw_content
            except Exception:
                response_data = {"result": raw_content}
            fr_part = {"functionResponse": {"name": name, "response": response_data}}
            if contents and contents[-1]["role"] == "user":
                contents[-1]["parts"].append(fr_part)
            else:
                contents.append({"role": "user", "parts": [fr_part]})

    return system_text, contents


def _oi_tools_to_sdk(tools: list[dict]) -> types.Tool:
    """Convert OpenAI-format tool list to SDK types.Tool."""
    declarations = []
    for t in tools:
        fn = t["function"]
        declarations.append(types.FunctionDeclaration(
            name=fn["name"],
            description=fn.get("description", ""),
            parameters=fn.get("parameters", {}),
        ))
    return types.Tool(function_declarations=declarations)


def _make_config(
    system_instr: str | None,
    tools: list[dict] | None = None,
) -> types.GenerateContentConfig | None:
    kwargs: dict = {}
    if system_instr:
        kwargs["system_instruction"] = system_instr
    if tools:
        kwargs["tools"] = [_oi_tools_to_sdk(tools)]
    return types.GenerateContentConfig(**kwargs) if kwargs else None


async def _gemini_call(
    messages: list[dict], *, timeout: int = 90, tools: list[dict] | None = None
) -> str:
    """Non-streaming Gemini call. Returns text."""
    client = _get_client()
    system_instr, contents = _to_gemini_contents(messages)
    config = _make_config(system_instr, tools)
    try:
        response = await client.aio.models.generate_content(
            model=_llm(),
            contents=contents,
            config=config,
        )
        return response.text or ""
    except genai.errors.ClientError as e:
        if getattr(e, "status_code", None) in (401, 403):
            raise RuntimeError("Gemini service unavailable")
        raise


async def _llm_call(prompt: str, timeout: int = 90) -> str:
    return await _gemini_call([{"role": "user", "content": prompt}], timeout=timeout)


async def _gemini_generate_stream(
    messages: list[dict],
    tools: list[dict] | None = None,
) -> AsyncIterator:
    """Yield raw SDK chunks from a Gemini streaming call.

    Each chunk has .candidates[0].content.parts — text parts and/or functionCall parts.
    Use _chunk_parts(chunk) to read them safely (parts can be None, not just absent).
    """
    client = _get_client()
    system_instr, contents = _to_gemini_contents(messages)
    config = _make_config(system_instr, tools)
    try:
        stream = await client.aio.models.generate_content_stream(
            model=_llm(),
            contents=contents,
            config=config,
        )
        async for chunk in stream:
            yield chunk
    except genai.errors.ClientError as e:
        if getattr(e, "status_code", None) in (401, 403):
            raise RuntimeError("Gemini service unavailable")
        raise


def _chunk_parts(chunk) -> list:
    """安全取出串流 chunk 的 parts。

    Gemini 串流最後一個 chunk（finish_reason=STOP 等）常常 candidates[0].content.parts
    直接是 None（不是空 list、也不是 candidates 本身為空），只檢查 `if chunk.candidates`
    會漏掉這個情況，導致 `for part in None` 炸掉。這裡把 candidates/content/parts
    每一層都當作可能是 None 來檢查。
    """
    if not chunk.candidates:
        return []
    content = chunk.candidates[0].content
    if not content or not content.parts:
        return []
    return content.parts


def _parse_json(raw: str) -> dict:
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    return json.loads(raw, strict=False)


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def with_heartbeat(agen, interval: float = 15.0):
    """SSE keepalive wrapper: sends `: ping` comment if stream is silent for `interval` seconds."""
    queue: asyncio.Queue = asyncio.Queue()
    _END = object()

    async def _pump():
        try:
            async for ev in agen:
                await queue.put(ev)
        except asyncio.CancelledError:
            raise
        except BaseException as e:
            await queue.put(e)
        else:
            await queue.put(_END)

    pump_task = asyncio.create_task(_pump())
    get_task: asyncio.Task | None = None
    try:
        while True:
            if get_task is None:
                get_task = asyncio.create_task(queue.get())
            done, _ = await asyncio.wait({get_task}, timeout=interval)
            if not done:
                yield ": ping\n\n"
                continue
            item = get_task.result()
            get_task = None
            if item is _END:
                break
            if isinstance(item, BaseException):
                raise item
            yield item
    finally:
        if get_task is not None:
            get_task.cancel()
        if not pump_task.done():
            pump_task.cancel()
        try:
            await pump_task
        except BaseException:
            pass
