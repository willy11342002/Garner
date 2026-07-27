"""ai_service package — public API re-exports.

All callers that do `from app.services import ai_service` continue to work
without modification; symbols are resolved through this __init__.
"""
from ._client import (
    OPENROUTER_URL,
    load_model_configs,
    with_heartbeat,
)
from .chain import analyze_chain_hop, analyze_full_chain
from .chat import (
    agentic_chat_stream,
    chat_stream,
    compress_memory,
    synthesize_custom,
    synthesize_focus,
)
from .embed import embed, embed_many
from .ingest import (
    analyze_content,
    chunk_text,
    describe_images,
    describe_video,
    extract_locations,
    generate_title,
    suggest_tags,
    understand,
)
from .report import generate_report_body, revise_text
from .rerank import rerank
from .segment import segment
from .tools import stream_tool_loop

__all__ = [
    # _client
    "OPENROUTER_URL",
    "load_model_configs",
    "with_heartbeat",
    # chain
    "analyze_chain_hop",
    "analyze_full_chain",
    # chat
    "agentic_chat_stream",
    "chat_stream",
    "compress_memory",
    "synthesize_custom",
    "synthesize_focus",
    # embed
    "embed",
    "embed_many",
    # ingest
    "analyze_content",
    "chunk_text",
    "describe_images",
    "describe_video",
    "extract_locations",
    "generate_title",
    "suggest_tags",
    "understand",
    # report
    "generate_report_body",
    "revise_text",
    # rerank
    "rerank",
    # segment
    "segment",
    # tools
    "stream_tool_loop",
]
