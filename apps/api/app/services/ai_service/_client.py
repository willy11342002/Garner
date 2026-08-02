"""Gemini client primitives — uses google-genai SDK, native types throughout.

對話內容一律用 `google.genai.types.Content` / `types.Part` 表示，不再經過
OpenAI 格式的 dict 中介。呼叫端用下面的 builder 直接組：

    user_turn("台北有什麼好吃的")
    model_turn(text="我查一下", calls=[("search", {"query": "台北美食"})])
    tool_results(("search", {"count": 3}))

這樣工具參數不用「dumps 成字串再 loads 回來」，也不用維護 tool_call_id → name
的對照表（Gemini 的 functionResponse 直接帶 name）。
"""
import asyncio
import json
import logging
from collections.abc import Sequence
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


# ── Content builders ───────────────────────────────────────────────────────────
#
# 呼叫端用這些組對話，不要自己手刻 types.Content —— 集中在這裡才能保證
# 「相鄰同 role 要合併」「空 parts 要丟掉」這類 Gemini 的硬性要求只實作一次。


def text_part(text: str) -> types.Part:
    return types.Part(text=text)


def image_part(data: bytes, mime_type: str = "image/jpeg") -> types.Part:
    """圖片 part。直接吃 bytes，SDK 內部處理 base64，不用先組 data: URL 再拆回來。"""
    return types.Part.from_bytes(data=data, mime_type=mime_type)


def user_turn(*parts: str | types.Part) -> types.Content:
    """使用者這一輪。字串會自動包成 text part，方便最常見的純文字情況。

    空字串不會產生 part（否則會送出一個空的 text part，Gemini 視為無效內容）。
    """
    return types.Content(
        role="user",
        parts=[text_part(p) if isinstance(p, str) else p for p in parts if p],
    )


def model_turn(
    text: str | None = None,
    calls: Sequence[tuple[str, dict]] = (),
) -> types.Content:
    """模型這一輪：可帶文字、可帶 function call，兩者可並存。

    calls 是 (工具名, 參數 dict) 的序列 —— 參數保持 dict，不再序列化成 JSON 字串。
    """
    parts = ([text_part(text)] if text else []) + [
        types.Part.from_function_call(name=name, args=args or {}) for name, args in calls
    ]
    return types.Content(role="model", parts=parts)


def _json_safe(value: object) -> dict:
    """把工具結果轉成純 JSON 型別的 dict。

    工具結果常常夾帶 UUID、datetime、Decimal 這類 SDK 序列化不了的值（例如 crud 直接
    回傳的 ORM 衍生 dict）。舊的 OpenAI-dict 路徑是靠 json.dumps(..., default=str) 順手
    擋掉的；改成原生 types 後那層網不見了，所以在這裡明確補回來 —— 少了它，一個
    datetime 就會讓整條串流在送出前炸掉。
    """
    if not isinstance(value, dict):
        value = {"result": value}
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def tool_results(*results: tuple[str, object]) -> types.Content:
    """工具執行結果。Gemini 把 functionResponse 歸在 user 這一側。

    response 必須是 dict；非 dict 的結果（例如工具回了 list 或純字串）包成 {"result": ...}。
    """
    return types.Content(
        role="user",
        parts=[
            types.Part.from_function_response(name=name, response=_json_safe(response))
            for name, response in results
        ],
    )


def _prepare(contents: Sequence[types.Content]) -> list[types.Content]:
    """送出前的正規化：丟掉空 parts 的 content，合併相鄰同 role 的 content。

    Gemini 不接受連續兩個同 role 的 content，也不接受 parts 為空的 content。
    """
    out: list[types.Content] = []
    for c in contents:
        if not c.parts:
            continue
        if out and out[-1].role == c.role:
            out[-1].parts.extend(c.parts)
        else:
            out.append(types.Content(role=c.role, parts=list(c.parts)))
    return out


def _config(
    system: str | None,
    tools: Sequence[types.FunctionDeclaration] | None,
) -> types.GenerateContentConfig | None:
    kwargs: dict = {}
    if system:
        kwargs["system_instruction"] = system
    if tools:
        kwargs["tools"] = [types.Tool(function_declarations=list(tools))]
    return types.GenerateContentConfig(**kwargs) if kwargs else None


def _unavailable_if_auth_error(e: genai.errors.ClientError):
    """401/403 代表服務端拒絕，不是使用者的 auth 問題 —— 轉成 503 讓前端別誤判。"""
    if getattr(e, "status_code", None) in (401, 403):
        raise RuntimeError("Gemini service unavailable")
    raise e


async def generate(
    contents: Sequence[types.Content],
    *,
    system: str | None = None,
    tools: Sequence[types.FunctionDeclaration] | None = None,
    model: str | None = None,
) -> str:
    """非串流呼叫，回傳文字。"""
    try:
        response = await _get_client().aio.models.generate_content(
            model=model or _llm(),
            contents=_prepare(contents),
            config=_config(system, tools),
        )
        return response.text or ""
    except genai.errors.ClientError as e:
        _unavailable_if_auth_error(e)


async def _llm_call(prompt: str) -> str:
    """單一 prompt 的便利包裝（ingest / report / chain 的多數呼叫都是這種）。"""
    return await generate([user_turn(prompt)])


async def generate_stream(
    contents: Sequence[types.Content],
    *,
    system: str | None = None,
    tools: Sequence[types.FunctionDeclaration] | None = None,
    model: str | None = None,
) -> AsyncIterator:
    """串流呼叫，yield 原始 SDK chunk。

    每個 chunk 是 .candidates[0].content.parts —— 可能是 text、也可能是 functionCall。
    一律用 _chunk_parts(chunk) 讀，parts 可能是 None 而不只是缺席。
    """
    try:
        stream = await _get_client().aio.models.generate_content_stream(
            model=model or _llm(),
            contents=_prepare(contents),
            config=_config(system, tools),
        )
        async for chunk in stream:
            yield chunk
    except genai.errors.ClientError as e:
        _unavailable_if_auth_error(e)


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
