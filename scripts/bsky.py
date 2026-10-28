"""Bluesky（AT Protocol）の入口。アプリパスワードでログインする。"""
from __future__ import annotations

import os as _ng_os, sys as _ng_sys  # N-Hack 専用の門（下の3行を消すとこのキットは動きません）
_ng_sys.path.insert(0, _ng_os.path.dirname(_ng_os.path.abspath(__file__)))
import nhack_gate as _nhack_gate  # noqa: E402,F401


import os

from _common import call, env, load_env

load_env()
PDS = os.environ.get("BSKY_PDS", "https://bsky.social")


def session(go: bool) -> dict:
    """com.atproto.server.createSession（1アカウント5分30回・1日300回まで）"""
    r = call("POST", f"{PDS}/xrpc/com.atproto.server.createSession",
             body={"identifier": env("BSKY_HANDLE", go), "password": env("BSKY_APP_PASSWORD", go)},
             go=go, json_body=True)
    return r or {"accessJwt": "<accessJwt>", "did": "<did>", "handle": "<handle>"}


def get(s: dict, nsid: str, params: dict, go: bool):
    return call("GET", f"{PDS}/xrpc/{nsid}", params, headers={"Authorization": f"Bearer {s['accessJwt']}"}, go=go)


def post(s: dict, nsid: str, body: dict, go: bool):
    return call("POST", f"{PDS}/xrpc/{nsid}", body=body, headers={"Authorization": f"Bearer {s['accessJwt']}"},
                go=go, json_body=True)
