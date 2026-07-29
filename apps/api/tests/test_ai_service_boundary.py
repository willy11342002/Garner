"""ai_service package 邊界測試。

ai_service/__init__.py 用 PEP 562 的 module __getattr__ 做 lazy import，只認得
_LAZY_ATTRS 裡列出的 symbol。任何 `ai_service.X` 若 X 不在表裡，會在「執行到那一行」
才拋 AttributeError —— 對只在錯誤路徑上的呼叫（例如 trip not found）等於是個
永遠不會被一般測試踩到的地雷。這裡用靜態掃描把整個類別的問題一次擋住。
"""
import ast
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

APP_DIR = Path(__file__).resolve().parent.parent / "app"
AI_SERVICE_MODULE = "app.services.ai_service"


def _aliases_bound_to_ai_service(tree: ast.AST) -> set[str]:
    """找出這個檔案裡有哪些名字綁到 ai_service package 本身。

    涵蓋 `from app.services import ai_service`、`... as _ai`、
    `import app.services.ai_service as x`。不涵蓋 `from ...ai_service._client import _sse`
    —— 那是直接匯入子模組的 symbol，繞過 package __getattr__，本來就安全。
    """
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "app.services":
                for a in node.names:
                    if a.name == "ai_service":
                        aliases.add(a.asname or a.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name == AI_SERVICE_MODULE and a.asname:
                    aliases.add(a.asname)
    return aliases


def _collect_attribute_accesses() -> list[tuple[str, int, str]]:
    """回傳 [(檔案相對路徑, 行號, 屬性名)]，涵蓋 app/ 底下所有對 ai_service 的屬性存取。"""
    found: list[tuple[str, int, str]] = []
    for path in APP_DIR.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - 語法錯誤自有其他測試會抓
            continue
        aliases = _aliases_bound_to_ai_service(tree)
        if not aliases:
            continue
        rel = str(path.relative_to(APP_DIR.parent))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id in aliases
            ):
                found.append((rel, node.lineno, node.attr))
    return found


def test_every_ai_service_attribute_access_is_resolvable():
    """所有 `ai_service.X` 的 X 都必須在 _LAZY_ATTRS 裡。

    這條測試存在的原因：trip_service 曾經呼叫 ai_service._sse()，而 _sse 是 _client
    的私有 symbol、不在 _LAZY_ATTRS 裡，於是「行程不存在」這條錯誤路徑一踩就整串
    SSE 炸掉，而不是回一個 error 事件。
    """
    from app.services.ai_service import _LAZY_ATTRS

    accesses = _collect_attribute_accesses()
    assert accesses, "掃不到任何 ai_service 屬性存取，掃描器可能壞了"

    unresolvable = [
        (path, lineno, attr)
        for path, lineno, attr in accesses
        if attr not in _LAZY_ATTRS and not attr.startswith("__")
    ]
    assert not unresolvable, (
        "以下 ai_service 屬性存取無法被 __getattr__ 解析，執行到就會 AttributeError：\n"
        + "\n".join(f"  {p}:{n} → ai_service.{a}" for p, n, a in unresolvable)
        + "\n修法：改成 from app.services.ai_service.<submodule> import <symbol>，"
        "或把該 symbol 加進 _LAZY_ATTRS（僅限公開 API）。"
    )


def test_lazy_attrs_all_actually_exist():
    """_LAZY_ATTRS 表裡的每個 symbol 都要真的能被解析出來（防表本身寫錯／子模組改名）。"""
    import app.services.ai_service as ai_service
    from app.services.ai_service import _LAZY_ATTRS

    missing = []
    for name in _LAZY_ATTRS:
        try:
            getattr(ai_service, name)
        except AttributeError as e:
            missing.append(f"{name}: {e}")
    assert not missing, "_LAZY_ATTRS 有解析不出來的 symbol：\n" + "\n".join(missing)


async def test_ai_edit_trip_stream_yields_error_when_trip_not_found():
    """行程不存在時要 yield 一個 SSE error 事件，而不是拋例外。

    這是 _sse bug 原本會炸掉的那條路徑。
    """
    from app.services import trip_service

    with patch.object(
        trip_service, "_get_accessible_trip", new=AsyncMock(return_value=None)
    ):
        events = [
            ev
            async for ev in trip_service.ai_edit_trip_stream(
                db=AsyncMock(),
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                trip_id=UUID("00000000-0000-0000-0000-0000000000ff"),
                instruction="把第一天改短一點",
            )
        ]

    assert events == ['event: error\ndata: {"message": "trip not found"}\n\n']
