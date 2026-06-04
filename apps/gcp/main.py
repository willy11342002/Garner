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


@app.get("/health")
async def health():
    return {"status": "ok"}


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
