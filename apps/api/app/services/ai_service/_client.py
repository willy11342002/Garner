"""Gemini client primitives shared across all ai_service modules."""
import asyncio
import json
import logging

import httpx

from app.core.config import settings
from app.core.tracing import traced

logger = logging.getLogger("garner.chat")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

_model_cache: dict[str, str] = {
    "llm": "gemini-2.5-flash",
    "video_llm": "google/gemini-2.5-flash",
    "embedding": "openai/text-embedding-3-small",
}


async def load_model_configs() -> None:
    """Load model config from app_settings (keys prefixed with 'model.') into the in-memory cache."""
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
    """Convert OpenRouter-style names (provider/model) to bare Gemini model IDs.

    google/gemini-2.5-flash → gemini-2.5-flash
    anthropic/claude-3-haiku → gemini-2.5-flash  (non-Gemini fallback)
    gemini-2.5-flash → gemini-2.5-flash
    """
    if name.startswith("google/"):
        return name[len("google/"):]
    if "/" in name:
        # Non-Gemini OpenRouter model (e.g. anthropic/...) — use default
        return "gemini-2.5-flash"
    return name


def _llm() -> str:
    return _normalize_gemini_model(_model_cache["llm"])


def _video_llm() -> str:
    return _normalize_gemini_model(_model_cache.get("video_llm", "gemini-2.0-flash"))


def _emb() -> str:
    return _model_cache["embedding"]


def _gemini_headers() -> dict:
    return {"X-Goog-Api-Key": settings.google_ai_api_key}


def _gemini_url(stream: bool = False) -> str:
    action = "streamGenerateContent" if stream else "generateContent"
    url = f"{_GEMINI_BASE}/{_llm()}:{action}"
    if stream:
        url += "?alt=sse"
    return url


def _to_gemini_body(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """Convert OpenAI-format messages to Gemini native request body.

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

    body: dict = {"contents": contents}
    if system_text:
        body["systemInstruction"] = {"parts": [{"text": system_text}]}
    if tools:
        body["tools"] = [{"functionDeclarations": [
            {
                "name": t["function"]["name"],
                "description": t["function"].get("description", ""),
                "parameters": t["function"].get("parameters", {}),
            }
            for t in tools
        ]}]
    return body


async def _gemini_call(messages: list[dict], *, timeout: int = 90, tools: list[dict] | None = None) -> str:
    body = _to_gemini_body(messages, tools=tools)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _gemini_url(),
            headers=_gemini_headers(),
            json=body,
            timeout=timeout,
        )
        if resp.status_code == 401:
            raise RuntimeError("Gemini service unavailable")
        resp.raise_for_status()
    parts = resp.json()["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts).strip()


async def _llm_call(prompt: str, timeout: int = 90) -> str:
    return await _gemini_call([{"role": "user", "content": prompt}], timeout=timeout)


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
