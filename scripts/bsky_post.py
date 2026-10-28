"""Bluesky に投稿する（1本・スレッド・返信）。

  python3 scripts/bsky_post.py --file drafts/bsky-2026-11-01.md          # 見るだけ
  python3 scripts/bsky_post.py --file drafts/bsky-2026-11-01.md --go     # 投稿
  python3 scripts/bsky_post.py --text "ひとこと" --reply-to at://... --go

md の形は Threads と同じ（## 1投稿目 / ## 2投稿目 …）。1投稿は300字（書記素）まで。
URL は自動でリンクにします（facets・位置はバイトで数える公式の決まり）。
"""
from __future__ import annotations

import os as _ng_os, sys as _ng_sys  # N-Hack 専用の門（下の3行を消すとこのキットは動きません）
_ng_sys.path.insert(0, _ng_os.path.dirname(_ng_os.path.abspath(__file__)))
import nhack_gate as _nhack_gate  # noqa: E402,F401


import argparse
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone

import bsky
from _common import append_log, read_text_arg

URL = re.compile(rb"https?://[^\s\)\]\}>\"']+")


def graphemes(t: str) -> int:
    """書記素のおおよその数（結合文字・異体字セレクタ・ZWJ を前の字にまとめる）。"""
    n = 0
    prev_zwj = False
    for c in t:
        if unicodedata.combining(c) or c in ("️", "︎") or 0x1F3FB <= ord(c) <= 0x1F3FF:
            continue
        if c == "‍":
            prev_zwj = True
            continue
        if prev_zwj:
            prev_zwj = False
            continue
        n += 1
    return n


def facets(text: str) -> list[dict]:
    b = text.encode("utf-8")
    return [{"index": {"byteStart": m.start(), "byteEnd": m.end()},
             "features": [{"$type": "app.bsky.richtext.facet#link", "uri": m.group().decode()}]}
            for m in URL.finditer(b)]


def parse_md(md: str) -> list[str]:
    parts = re.split(r"^## \d+投稿目\s*$", md, flags=re.M)[1:]
    return [re.sub(r"^<!--.*?-->$", "", x, flags=re.M).strip() for x in parts if x.strip()] or [md.strip()]


def strong_ref(uri: str, cid: str) -> dict:
    return {"uri": uri, "cid": cid}


def post(parts: list[str], go: bool, reply_to: str | None = None, langs=("ja",)) -> list[str]:
    for i, t in enumerate(parts, 1):
        if graphemes(t) > 300:
            sys.exit(f"[止めました] {i}投稿目が {graphemes(t)} 字（上限300）")
    s = bsky.session(go)
    root = parent = None
    if reply_to:
        r = bsky.get(s, "app.bsky.feed.getPosts", {"uris": reply_to}, go)
        p0 = ((r or {}).get("posts") or [{"uri": reply_to, "cid": "<cid>", "record": {}}])[0]
        parent = strong_ref(p0["uri"], p0["cid"])
        root = (p0.get("record", {}).get("reply") or {}).get("root") or parent
    uris = []
    for t in parts:
        rec = {"$type": "app.bsky.feed.post", "text": t, "langs": list(langs),
               "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
        f = facets(t)
        if f:
            rec["facets"] = f
        if parent:
            rec["reply"] = {"root": root, "parent": parent}
        r = bsky.post(s, "com.atproto.repo.createRecord", {"repo": s["did"], "collection": "app.bsky.feed.post",
                                                           "record": rec}, go) or {"uri": "<uri>", "cid": "<cid>"}
        uris.append(r["uri"])
        parent = strong_ref(r["uri"], r["cid"])
        root = root or parent
        if go:
            time.sleep(2)
    if go:
        append_log("bsky-published.jsonl", {"uris": uris, "head": parts[0][:40]})
        print("投稿しました:", uris[0])
    else:
        print("\n（dry-run でした）")
    return uris


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--text")
    p.add_argument("--file")
    p.add_argument("--reply-to", help="返信先の at:// URI")
    p.add_argument("--go", action="store_true")
    a = p.parse_args()
    parts = parse_md(read_text_arg(None, a.file)) if a.file else [read_text_arg(a.text, None)]
    post(parts, a.go, a.reply_to)
