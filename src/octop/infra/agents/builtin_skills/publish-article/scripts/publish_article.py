#!/usr/bin/env python3
"""24KRMB 门户文章发布工具 — 基于 Discuz 根目录 post_article_api.php。

用法:
  publish_article.py check                                  探活（密码鉴权验证）
  publish_article.py post --catid CID --title T --content-file FILE
       [--username NAME] [--summary S] [--from-url U] [--from-name N]
  publish_article.py post --catid CID --title T --content "<p>HTML正文</p>" ...

说明:
  - 正文为 HTML（门户文章是富文本），禁止 <script>/javascript:/onerror 等危险标签（服务端会拦截）。
  - 成功返回 {"ok": true, "aid": 文章ID, "url": 门户文章链接}。
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(os.path.dirname(HERE), "config.json")
UA = "24K-Claw-Octop/1.0"


def load_cfg():
    with open(CFG_PATH, encoding="utf-8") as f:
        return json.load(f)


def call_api(cfg, fields, timeout=30):
    data = dict(fields)
    data["DISCUZ_POST_PASSWORD"] = cfg["password"]
    body = urllib.parse.urlencode(data, encoding="utf-8").encode()
    req = urllib.request.Request(
        cfg["api_url"], data=body,
        headers={"User-Agent": UA,
                 "Content-Type": "application/x-www-form-urlencoded; charset=utf-8"})
    try:
        raw = urllib.request.urlopen(req, timeout=timeout).read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
    except (urllib.error.URLError, OSError) as e:
        return {"ok": False, "error": "network", "detail": str(e)}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"ok": False, "error": "bad_json", "raw": raw[:300]}


def cmd_check(cfg, a):
    """探活：发送最小参数，白名单外/密码错会明确返回。"""
    r = call_api(cfg, {"catid": "0", "title": "connectivity-check", "content": "ping"})
    if r.get("code") == 200:
        out = {"ok": True, "note": "意外发布了探活文，请删除", "aid": r.get("aid")}
    elif r.get("code") == 400:
        out = {"ok": True, "note": "API 可达且鉴权通过（400 为探活参数预期的缺失响应）"}
    elif r.get("code") == 403:
        out = {"ok": False, "error": "auth", "msg": r.get("msg"), "hint": "密码错误或 IP 不在白名单"}
    else:
        out = {"ok": False, "error": "unknown", "detail": r}
    print(json.dumps(out, ensure_ascii=False, indent=1))


def cmd_post(cfg, a):
    content = a.content
    if a.content_file:
        with open(a.content_file, encoding="utf-8") as f:
            content = f.read()
    if not content:
        print(json.dumps({"ok": False, "error": "empty_content"}, ensure_ascii=False))
        sys.exit(2)
    fields = {
        "catid": str(a.catid or cfg.get("default_catid") or ""),
        "title": a.title,
        "content": content,
        "username": a.username or cfg.get("default_username") or "财锋派",
        "summary": a.summary or "",
        "from_url": a.from_url or cfg.get("default_from_url") or "",
        "from_name": a.from_name or cfg.get("default_from_name") or "",
    }
    r = call_api(cfg, fields)
    out = dict(r)
    if r.get("code") == 200 and r.get("aid"):
        out["ok"] = True
        out["url"] = f"{cfg['site']}/portal.php?mod=view&aid={r['aid']}"
    elif r.get("code") == 200:
        out["ok"] = True
    else:
        out["ok"] = False
    print(json.dumps(out, ensure_ascii=False, indent=1))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    sp = sub.add_parser("post")
    sp.add_argument("--catid"), sp.add_argument("--title", required=True)
    sp.add_argument("--content"), sp.add_argument("--content-file")
    sp.add_argument("--username"), sp.add_argument("--summary")
    sp.add_argument("--from-url"), sp.add_argument("--from-name")
    a = p.parse_args()
    cfg = load_cfg()
    {"check": cmd_check, "post": cmd_post}[a.cmd](cfg, a)


if __name__ == "__main__":
    main()
