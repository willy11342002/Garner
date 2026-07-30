"""ai_service package — public API re-exports.

All callers that do `from app.services import ai_service` continue to work
without modification; symbols are resolved through this __init__.

Symbols are resolved lazily via module __getattr__ (PEP 562): importing this
package no longer eagerly imports every submodule (and therefore doesn't
eagerly pull in google-genai / langgraph / langchain at process start —
those only load on first actual use of a symbol that needs them). Keep new
public symbols listed in _LAZY_ATTRS instead of adding top-level imports.
"""
import importlib

_LAZY_ATTRS = {
    # _client
    "OPENROUTER_URL": "._client",
    "load_model_configs": "._client",
    "with_heartbeat": "._client",
    # chain
    "analyze_chain_hop": ".chain",
    "analyze_full_chain": ".chain",
    # chat
    "compress_memory": ".chat",
    # embed
    "embed": ".embed",
    "embed_many": ".embed",
    # ingest
    "analyze_content": ".ingest",
    "chunk_text": ".ingest",
    "describe_images": ".ingest",
    "describe_video": ".ingest",
    "extract_locations": ".ingest",
    "generate_title": ".ingest",
    "suggest_tags": ".ingest",
    "understand": ".ingest",
    # report
    "generate_report_body": ".report",
    "revise_text": ".report",
    # rerank
    "rerank": ".rerank",
    "preload_rerank": ".rerank",
    # segment
    "segment": ".segment",
    "preload_segment": ".segment",
}

__all__ = list(_LAZY_ATTRS)


def __getattr__(name: str):
    try:
        module_name = _LAZY_ATTRS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    module = importlib.import_module(module_name, __name__)
    # Importing a submodule (e.g. ".segment") makes Python's import system
    # bind it onto this package under its own short name — globals()["segment"]
    # = <module> — as an unavoidable side effect, regardless of which symbol
    # we actually asked for. When a submodule's filename collides with one of
    # its own exported public symbols (segment.py exports segment(), rerank.py
    # exports rerank()), that side effect silently overwrites the callable
    # with the raw module, and __getattr__ never runs again for that name
    # since the attribute now exists. Fixing only globals()[name] isn't
    # enough — e.g. resolving "preload_segment" first still clobbers
    # "segment" via the same import. Restore every symbol backed by this
    # submodule, not just the one requested, so the collision can't survive.
    for sym, mod_name in _LAZY_ATTRS.items():
        if mod_name == module_name:
            globals()[sym] = getattr(module, sym)
    return globals()[name]
