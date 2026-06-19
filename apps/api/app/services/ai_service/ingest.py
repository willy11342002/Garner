"""Content ingestion — analysis, tagging, title, vision, video, location extraction."""
import asyncio
import io
import logging

import google.genai as genai
from google.genai import types

from app.core.config import settings
from app.core.tracing import traced

from ._client import _gemini_call, _get_client, _llm_call, _parse_json, _video_llm

logger = logging.getLogger(__name__)

_NOTES_PROMPT = """\
You are a knowledge base assistant. Read the following content and produce structured notes in Traditional Chinese Markdown.

Start with this FIXED section (always first, exactly this header):

## 核心主題
One or two paragraphs explaining what this content is about and why it matters.

Then organize the rest of the notes into 2–5 sections using `## ` headers that YOU choose, picked to fit THIS content's type and structure. Do NOT reuse a generic template — the headers should reflect what this specific content actually is. For example:
- A tutorial / how-to → e.g. 前置知識 / 步驟拆解 / 常見坑
- A news / report → e.g. 發生什麼 / 背景脈絡 / 影響與後續
- An opinion / essay → e.g. 核心論點 / 論證與證據 / 反方觀點
- A recipe / itinerary → e.g. 食材清單 / 製作步驟 / 小提示
- A concept / explainer → e.g. 關鍵概念 / 運作原理 / 應用場景
These are only illustrations — invent whatever headers best capture this content. Use bullet lists or paragraphs within each section as appropriate, and `### ` sub-headers only if a section genuinely needs them.

Rules:
- Write entirely in Traditional Chinese
- The `## 核心主題` section is mandatory and must come first; all other section headers are your choice
- Pick 2–5 body sections — fewer for short/simple content, more for rich content
- Be thorough but organized — capture ALL meaningful ideas and details from the source; organized knowledge, not a transcript. Omit only filler and repetition
- Do NOT include the video/article title as a heading
- Return ONLY the Markdown, no extra commentary, no code fences

Content:
"""

_TAGS_PROMPT = """\
Analyze the following content and return ONLY a JSON object:
{
  "embed_text": "用繁體中文(zh-TW)寫一段 2-3 句、精煉描述主題的句子，供語意搜尋使用（必須是繁體中文，不要用英文）",
  "tags": {
    "zh-TW": ["標籤1", "標籤2", "標籤3"],
    "en": ["tag1", "tag2", "tag3"]
  },
  "locations": [
    {"name": "地點名稱", "order": 0}
  ]
}

Rules for tags:
- 3–7 short labels (1–3 words each)
- BROAD, REUSABLE categories — themes, domains, concepts that apply across many items
- AVOID specific proper nouns or one-off details
- Tags must be conceptually paired (same index = same concept across languages)

Rules for locations:
- Extract ONLY specific, real-world places that are actually visited or featured in the content (e.g. restaurants, landmarks, cities, neighborhoods)
- EXCLUDE places merely mentioned in passing or unrelated to the content's subject matter
- Use the most recognizable name for the place (prefer official or well-known names)
- order starts at 0 and reflects the sequence in which places appear
- Return [] if no concrete locations are identifiable
- Return ONLY the JSON object, no markdown fences, no extra text

Content:
"""

_TAGS_WITH_CANDIDATES_PROMPT = """\
Analyze the following content and return ONLY a JSON object.

The user already has these existing tags (zh-TW names):
{candidates}

Rules for tags:
- Choose 3–7 short labels (1–3 words each)
- PREFER existing tags from the list above when they fit — this keeps the user's tag space clean
- Only create NEW tags when no existing tag adequately covers the concept (max 2 new tags)
- BROAD, REUSABLE categories — themes, domains, concepts that apply across many items
- AVOID specific proper nouns or one-off details
- For existing tags: use the exact zh-TW name from the list; derive the English equivalent yourself
- Tags must be conceptually paired (same index = same concept across languages)

Rules for locations:
- Extract ONLY specific, real-world places that are actually visited or featured in the content (e.g. restaurants, landmarks, cities, neighborhoods)
- EXCLUDE places merely mentioned in passing or unrelated to the content's subject matter
- Use the most recognizable name for the place (prefer official or well-known names)
- order starts at 0 and reflects the sequence in which places appear
- Return [] if no concrete locations are identifiable
- Return ONLY the JSON object, no markdown fences, no extra text

Output format:
{{
  "embed_text": "用繁體中文(zh-TW)寫一段 2-3 句、精煉描述主題的句子，供語意搜尋使用（必須是繁體中文，不要用英文）",
  "tags": {{
    "zh-TW": ["標籤1", "標籤2", "標籤3"],
    "en": ["tag1", "tag2", "tag3"]
  }},
  "locations": [
    {{"name": "地點名稱", "order": 0}}
  ]
}}

Content:
"""

_TITLE_PROMPT = """\
你的任務是產生或清理一個繁體中文標題（不超過 20 字）。

規則：
- 只輸出標題本身，不要加引號、標點或任何額外說明
- 若提供了「原始標題」：只移除 hashtag（如 #Shorts、#viral、#台灣 等 # 開頭的詞），其餘文字一字不改，直接回傳清理後的結果；禁止改寫、翻譯或重新措辭
- 若原始標題移除 hashtag 後不足 3 字，或未提供原始標題，才根據下方摘要重新產生標題
"""

_TITLE_WITH_RAW_TEMPLATE = """\
原始標題：{raw_title}

摘要：
{summary}
"""

_TITLE_FROM_SUMMARY_TEMPLATE = """\
摘要：
{summary}
"""

_VIDEO_ANALYSIS_PROMPT = """\
請分析這段影片的內容，以繁體中文輸出以下資訊：

1. **畫面文字**：逐字轉錄影片畫面中所有可見文字（字幕、壓字、標題、品牌名稱等），若無文字則略過。
2. **視覺內容**：描述影片的主要視覺場景與主題。
3. **口語內容**：轉錄影片中人物的說話或旁白。若聲音是背景音樂或歌曲，標記為「[背景音樂]」並略過歌詞，不轉錄。

請盡可能完整，確保畫面壓字被完整擷取。
"""

_VISION_PROMPT = """\
以下是一篇 Instagram 貼文的圖片（按順序排列）。
請仔細辨識並轉錄每張圖片中的所有文字，同時描述視覺內容。
若圖片中有資訊圖表、列表、時間表等結構化內容，請保留其結構。

輸出格式（每張圖片一段）：
[圖片 N]
文字：（逐字轉錄圖中所有可見文字）
描述：（簡短描述圖片視覺內容）

請用繁體中文輸出，確保文字轉錄完整準確。
"""

_EXTRACT_LOCATIONS_PROMPT = """\
Read the following content and extract ONLY specific, real-world places that are actually visited or featured (e.g. restaurants, landmarks, cities, neighborhoods, scenic spots).

Rules:
- EXCLUDE places merely mentioned in passing or unrelated to the content's subject matter
- Use the most recognizable name for each place (official or well-known name)
- order starts at 0 and reflects the sequence places appear in the content
- Return [] if no concrete locations are identifiable
- Return ONLY a JSON array, no markdown fences, no extra text

Output format:
[{"name": "地點名稱", "order": 0}]

Content:
"""

MAX_VIDEO_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB — Google File API limit


async def suggest_tags(content: str, candidate_tags: list[str] | None = None) -> dict:
    """Returns {"zh-TW": [...], "en": [...]}"""
    truncated = content[:32000]
    if candidate_tags:
        candidates_str = "、".join(candidate_tags)
        prompt = _TAGS_WITH_CANDIDATES_PROMPT.format(candidates=candidates_str) + truncated
    else:
        prompt = _TAGS_PROMPT + truncated
    raw = await _llm_call(prompt)
    data = _parse_json(raw)
    return data.get("tags", {"zh-TW": [], "en": []})


@traced(op="ai", name="analyze_content")
async def analyze_content(content: str, candidate_tags: list[str] | None = None) -> dict:
    """Returns {summary_md: {zh-TW: <markdown>}, embed_text: str, tags: {zh-TW, en}}."""
    truncated = content[:32000]

    if candidate_tags:
        candidates_str = "、".join(candidate_tags)
        tags_prompt = _TAGS_WITH_CANDIDATES_PROMPT.format(candidates=candidates_str) + truncated
    else:
        tags_prompt = _TAGS_PROMPT + truncated

    notes_task = asyncio.create_task(_llm_call(_NOTES_PROMPT + truncated))
    tags_task = asyncio.create_task(_llm_call(tags_prompt))

    zh_md, tags_raw = await asyncio.gather(notes_task, tags_task)
    tags_data = _parse_json(tags_raw)

    return {
        "summary_md": {"zh-TW": zh_md},
        "embed_text": tags_data.get("embed_text", ""),
        "tags": tags_data.get("tags", {"zh-TW": [], "en": []}),
        "locations": tags_data.get("locations", []),
    }


async def generate_title(summary_md: str, raw_title: str | None = None) -> str:
    """Derive a concise zh-TW title from a Markdown summary, optionally cleaning an existing raw title."""
    if raw_title:
        body = _TITLE_WITH_RAW_TEMPLATE.format(raw_title=raw_title, summary=summary_md[:2000])
    else:
        body = _TITLE_FROM_SUMMARY_TEMPLATE.format(summary=summary_md[:2000])
    return await _llm_call(_TITLE_PROMPT + "\n" + body)


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    """依 token 估算切割文字。用空白估算（1 token ≈ 4 chars）。"""
    char_size = chunk_size * 4
    char_overlap = overlap * 4
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + char_size
        chunks.append(text[start:end].strip())
        start += char_size - char_overlap
    return [c for c in chunks if c]


async def extract_locations(text: str) -> list[dict]:
    """Extract location names from existing notes_md using AI. Returns [{name, order}]."""
    truncated = text[:16000]
    raw = await _llm_call(_EXTRACT_LOCATIONS_PROMPT + truncated)
    try:
        data = _parse_json(raw)
        if isinstance(data, list):
            return [loc for loc in data if isinstance(loc, dict) and loc.get("name")]
    except Exception:
        pass
    return []


async def _upload_video_via_sdk(client: genai.Client, video_bytes: bytes, mime_type: str) -> str:
    """Upload video bytes via google-genai SDK File API. Returns the file URI."""
    file_ref = await client.aio.files.upload(
        file=io.BytesIO(video_bytes),
        config=types.UploadFileConfig(mime_type=mime_type, display_name="garner_video"),
    )
    for _ in range(60):
        if str(file_ref.state) in ("FileState.ACTIVE", "ACTIVE"):
            return file_ref.uri
        if str(file_ref.state) in ("FileState.FAILED", "FAILED"):
            raise RuntimeError(f"Google File API processing failed for {file_ref.name}")
        await asyncio.sleep(1)
        file_ref = await client.aio.files.get(name=file_ref.name)
    raise RuntimeError(f"Google File API did not become ACTIVE in time: {file_ref.name}")


async def describe_video(video_bytes: bytes, mime_type: str = "video/mp4") -> str:
    """Analyse a video via Google File API + Gemini SDK.

    Returns "" on any failure so callers can continue gracefully.
    """
    if not video_bytes:
        return ""

    if not settings.google_ai_api_key:
        logger.warning("describe_video: GOOGLE_AI_API_KEY not set, skipping")
        return ""

    if len(video_bytes) > MAX_VIDEO_BYTES:
        logger.warning("describe_video: video too large (%d bytes), skipping", len(video_bytes))
        return ""

    client = _get_client()

    try:
        file_uri = await _upload_video_via_sdk(client, video_bytes, mime_type)
        logger.info("describe_video: uploaded to Google File API → %s", file_uri)
    except Exception:
        logger.exception("describe_video: File API upload failed")
        return ""

    try:
        response = await client.aio.models.generate_content(
            model=_video_llm(),
            contents=[types.Content(parts=[
                types.Part(file_data=types.FileData(file_uri=file_uri, mime_type=mime_type)),
                types.Part(text=_VIDEO_ANALYSIS_PROMPT),
            ])],
        )
        return (response.text or "").strip()
    except Exception:
        logger.exception("describe_video: Gemini call failed")
        return ""


async def describe_images(images: list[bytes]) -> str:
    """Run vision AI on a list of image bytes, return combined text description."""
    import base64

    _IMAGE_MAGIC = (
        b"\xff\xd8\xff",        # JPEG
        b"\x89PNG\r\n\x1a\n",  # PNG
        b"RIFF",                # WebP (RIFF....WEBP)
        b"GIF8",                # GIF
    )
    images = [b for b in images if any(b.startswith(m) for m in _IMAGE_MAGIC)]
    if not images:
        return ""

    MAX_PER_IMAGE = 1 * 1024 * 1024
    MAX_TOTAL = 4 * 1024 * 1024

    def _resize(data: bytes) -> bytes:
        import io
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        img.thumbnail((1024, 1024), Image.LANCZOS)
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=85)
        return buf.getvalue()

    content: list[dict] = []
    total = 0
    for img_bytes in images[:10]:
        if len(img_bytes) > MAX_PER_IMAGE:
            try:
                img_bytes = _resize(img_bytes)
                logger.info("describe_images: resized image to %d bytes", len(img_bytes))
            except Exception:
                logger.warning("describe_images: resize failed, skipping image", exc_info=True)
                continue
        if total + len(img_bytes) > MAX_TOTAL:
            logger.warning("describe_images: reached total size cap, stopping at %d images", len(content))
            break
        b64 = base64.b64encode(img_bytes).decode()
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })
        total += len(img_bytes)

    if not content:
        return ""

    content.append({"type": "text", "text": _VISION_PROMPT})

    try:
        return await _gemini_call([{"role": "user", "content": content}], timeout=120)
    except Exception:
        logger.exception("describe_images: Gemini call failed")
        return ""


async def understand(
    video_bytes_list: list[bytes] | bytes | None = None,
    image_bytes_list: list[bytes] | None = None,
    mime_type: str = "video/mp4",
    title: str | None = None,
    description: str | None = None,
) -> str | None:
    """Combine any mix of videos, images, title and description into raw_content."""
    parts: list[str] = []

    if title:
        parts.append(f"[標題]\n{str(title)[:3000]}")
    if description:
        parts.append(f"[說明]\n{str(description)[:3000]}")

    videos: list[bytes] = []
    if video_bytes_list is not None:
        videos = video_bytes_list if isinstance(video_bytes_list, list) else [video_bytes_list]
    images: list[bytes] = image_bytes_list or []

    tasks: list[tuple[str, object]] = []
    if images:
        tasks.append(("images", describe_images(images)))
    for i, vb in enumerate(videos):
        tasks.append((f"video_{i}", describe_video(vb, mime_type)))

    if tasks:
        results = await asyncio.gather(*[t for _, t in tasks])
        for (label, _), text in zip(tasks, results):
            if not text:
                continue
            if label == "images":
                parts.append(f"[圖片內容]\n{text}")
            else:
                idx = int(label.split("_")[1]) + 1
                parts.append(f"[影片 {idx} 內容分析]\n{text}")

    return "\n\n".join(parts) if parts else None
