"""Bluesky の返信・メンションを集めて下書きを作り、確かめたものだけ返す。

  python3 scripts/bsky_notifications.py fetch --go
  python3 scripts/bsky_notifications.py send          # 見るだけ
  python3 scripts/bsky_notifications.py send --go     # approve=true だけ返す（1回20件まで）
"""
from __future__ import annotations

import os as _ng_os, sys as _ng_sys  # N-Hack 専用の門（下の3行を消すとこのキットは動きません）
_ng_sys.path.insert(0, _ng_os.path.dirname(_ng_os.path.abspath(__file__)))
import nhack_gate as _nhack_gate  # noqa: E402,F401


import argparse
import json

import bsky
from _common import DATA, append_log, read_log

DRAFTS = DATA / "bsky-reply-drafts.json"


def load():
    return json.loads(DRAFTS.read_text(encoding="utf-8")) if DRAFTS.exists() else []


def store(rows):
    DATA.mkdir(exist_ok=True)
    DRAFTS.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch(go: bool) -> None:
    s = bsky.session(go)
    r = bsky.get(s, "app.bsky.notification.listNotifications", {"limit": "50", "reasons": "reply"}, go)
    r2 = bsky.get(s, "app.bsky.notification.listNotifications", {"limit": "50", "reasons": "mention"}, go)
    if not go:
        print("\n（dry-run でした）")
        return
    done = {x["uri"] for x in read_log("bsky-replied.jsonl")}
    rows = load()
    known = {x["uri"] for x in rows}
    added = 0
    for n in (r or {}).get("notifications", []) + (r2 or {}).get("notifications", []):
        if n["uri"] in done or n["uri"] in known:
            continue
        rows.append({"uri": n["uri"], "reason": n.get("reason"), "from": n.get("author", {}).get("handle"),
                     "text": (n.get("record") or {}).get("text"), "at": n.get("indexedAt"),
                     "reply": "", "approve": False})
        known.add(n["uri"])
        added += 1
    store(rows)
    print(f"新しい返信・メンション {added} 件")


def send(go: bool) -> None:
    from bsky_post import post
    rows = load()
    todo = [x for x in rows if x.get("approve") and x.get("reply") and not x.get("sent")][:20]
    for x in todo:
        post([x["reply"]], go, reply_to=x["uri"])
        if go:
            x["sent"] = True
            append_log("bsky-replied.jsonl", {"uri": x["uri"]})
    if go:
        store(rows)
    print(f"返信 {len(todo)} 件" + ("" if go else "（dry-run）"))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["fetch", "send"])
    p.add_argument("--go", action="store_true")
    a = p.parse_args()
    fetch(a.go) if a.action == "fetch" else send(a.go)
