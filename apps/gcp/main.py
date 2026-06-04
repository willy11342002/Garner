import asyncio
import logging
import os
import shutil
import tempfile

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Vela Transcriber")

API_SECRET = os.environ.get("API_SECRET", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")


class TranscribeRequest(BaseModel):
    url: str


class TranscribeResponse(BaseModel):
    text: str | None
    duration: int | None


class SubtitlesRequest(BaseModel):
    video_id: str
    cookies: str | None = None  # cookies.txt content


class SubtitlesResponse(BaseModel):
    text: str | None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/subtitles", response_model=SubtitlesResponse)
async def get_subtitles(req: SubtitlesRequest, x_api_key: str = Header(...)):
    if API_SECRET and x_api_key != API_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    text = await _fetch_subtitles(req.video_id, req.cookies)
    return SubtitlesResponse(text=text)


async def _fetch_subtitles(video_id: str, cookies: str | None) -> str | None:
    import json
    import yt_dlp

    def _run():
        with tempfile.TemporaryDirectory() as tmpdir:
            cookies_path = None
            if cookies and cookies.strip():
                cookies_path = os.path.join(tmpdir, "cookies.txt")
                with open(cookies_path, "w", encoding="utf-8") as f:
                    f.write(cookies)

            ydl_opts = {
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["zh-Hant", "zh-TW", "zh-Hans", "zh-CN", "en"],
                "subtitlesformat": "json3",
                "outtmpl": os.path.join(tmpdir, "%(id)s"),
                "quiet": True,
                "no_warnings": True,
            }
            if cookies_path:
                ydl_opts["cookiefile"] = cookies_path

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

            files = os.listdir(tmpdir)
            for lang in ["zh-Hant", "zh-TW", "zh-Hans", "zh-CN", "en"]:
                for fname in files:
                    if f".{lang}." in fname and fname.endswith(".json3"):
                        return _parse_json3(os.path.join(tmpdir, fname))
            for fname in files:
                if fname.endswith(".json3"):
                    return _parse_json3(os.path.join(tmpdir, fname))
        return None

    def _parse_json3(path: str) -> str | None:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        texts = [
            seg.get("utf8", "").strip()
            for event in data.get("events", [])
            for seg in event.get("segs", [])
            if seg.get("utf8", "").strip() not in ("", "\n")
        ]
        return " ".join(texts) or None

    try:
        return await asyncio.to_thread(_run)
    except Exception:
        logger.exception("Subtitle fetch failed for video_id=%s", video_id)
        return None


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(req: TranscribeRequest, x_api_key: str = Header(...)):
    if API_SECRET and x_api_key != API_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY not configured")

    text, duration = await _download_and_transcribe(req.url)
    return TranscribeResponse(text=text, duration=duration)


async def _download_and_transcribe(url: str) -> tuple[str | None, int | None]:
    import yt_dlp
    from groq import AsyncGroq

    tmpdir = tempfile.mkdtemp()
    audio_base = os.path.join(tmpdir, "audio")
    duration: int | None = None

    def _download():
        nonlocal duration
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": audio_base,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "32",
            }],
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                duration = info.get("duration")

    try:
        await asyncio.to_thread(_download)

        audio_path = audio_base + ".mp3"
        if not os.path.exists(audio_path):
            logger.warning("Audio file not found after download: %s", audio_path)
            return None, duration

        client = AsyncGroq(api_key=GROQ_API_KEY)
        with open(audio_path, "rb") as f:
            result = await client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=f,
            )
        return result.text, duration

    except Exception:
        logger.exception("Transcription failed for url=%s", url)
        return None, duration
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
