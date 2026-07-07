"""Almandoub conversation agent as a local HTTP service.

``POST /api/handle`` accepts ``{"message": "..."}`` and returns the decided
action (REPLY / ESCALATE / CREATE_OR_UPDATE_ORDER), intent, confidence and a
safe response. The intent model loads once at startup (``ALMANDOUB_MODEL``,
default ``<project>/models/almandoub_intent_model.json``).
"""

from __future__ import annotations

import os
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .agent import decide
from .config import PROJECT_ROOT
from .http_base import BaseServiceHandler, build_server
from .model import IntentModel

_MODEL: IntentModel | None = None


def model_path() -> Path:
    raw = os.environ.get("ALMANDOUB_MODEL", "").strip()
    return Path(raw) if raw else PROJECT_ROOT / "models" / "almandoub_intent_model.json"


def _handle_route(data: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    message = str(data.get("message") or "").strip()
    if not message:
        return 400, {"ok": False, "error": "missing 'message'"}
    if _MODEL is None:
        return 503, {"ok": False, "error": f"model not loaded: {model_path()}"}
    return 200, {"ok": True, **decide(message, _MODEL)}


class Handler(BaseServiceHandler):
    post_routes = {"/api/handle": staticmethod(_handle_route)}


def create_server(host: str | None = None, port: int | None = None) -> ThreadingHTTPServer:
    global _MODEL
    path = model_path()
    _MODEL = IntentModel.load(path) if path.exists() else None
    return build_server(Handler, host=host, port=port)


def run_server(host: str | None = None, port: int | None = None) -> None:
    from .version import __version__

    server = create_server(host=host, port=port)
    print(f"almandoub service v{__version__}: http://{server.server_address[0]}:{server.server_address[1]}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
