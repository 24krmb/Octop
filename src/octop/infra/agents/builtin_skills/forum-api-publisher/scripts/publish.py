#!/usr/bin/env python3
"""24KRMB 社区发布工具 — 供 AI 调用（封装全部连接与认证细节）。

用法:
  publish.py check                                   连通性检查
  publish.py forums                                  列出版块(fid/名称)
  publish.py post    --fid FID --title T --content C [--confirm]
  publish.py reply   --tid TID --fid FID --content C [--confirm]
  publish.py article --catid CID --title T --content C
"""
import argparse
import base64
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(os.path.dirname(HERE), "config.json")
UA = "24K-Claw-Octop/1.0"


def load_cfg():
    with open(CFG_PATH, encoding="utf-8") as f:
        return json.load(f)


def headers(cfg, token=None, uniqueid=None):
    appid, secret = cfg["app"]["appid"], cfg["app"]["secret"]
    nonce, t = str(uuid.uuid4()).replace("-", "")[:20], str(int(time.time()))
    sign = base64.b64encode(
        hashlib.sha256((nonce + t + secret).encode()).hexdigest().encode()
    ).decode()
    h = {"appid": appid, "nonce": nonce, "t": t, "sign": sign, "User-Agent": UA}
    if token:
        h["token"] = token
    if uniqueid:
        h["uniqueid"] = uniqueid
    return h


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


_opener = urllib.request.build_opener(NoRedirect)


def call(cfg, path, payload=None, token=None, uniqueid=None):
    """调用社区接口。返回 (json, http_status)。301 的 Body 也正确读取。"""
    url = f"{cfg['site']}/api/restful/?/{path}"
    body = urllib.parse.urlencode(
        {"_REQUEST": json.dumps(payload or {}, ensure_ascii=False)}
    ).encode()
    req = urllib.request.Request(url, data=body, headers=headers(cfg, token, uniqueid))
    try:
        resp = _opener.open(req, timeout=30)
        status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
        resp = e
    raw = resp.read().decode(errors="replace")
    try:
        return json.loads(raw), status
    except json.JSONDecodeError:
        return {"ret": None, "raw": raw}, status


def ensure_token(cfg):
    cached_tok = cfg.get("token")
    exp = cfg.get("expires_in") or 0
    if cached_tok and time.time() < exp - 60:
        return cached_tok
    r, _ = call(cfg, "token")
    if r.get("ret") != 0:
        print(json.dumps({"ok": False, "error": "token_failed", "detail": r}, ensure_ascii=False))
        sys.exit(2)
    tok = r["token"]
    cfg["token"], cfg["expires_in"] = tok, r.get("expires_in", 0)
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return tok


def get_credentials():
    """社区账号凭据三级来源：环境变量 → 实例私有文件 → 缺失（需向用户询问）。"""
    u = os.environ.get("COMMUNITY_USERNAME")
    p = os.environ.get("COMMUNITY_PASSWORD")
    if u and p:
        return u, p, "env"
    cred_file = os.environ.get("COMMUNITY_CRED_FILE",
                               os.path.join(os.path.dirname(HERE), "..", "..", "..", "..", ".discuz_credentials.json"))
    cred_file = os.path.abspath(cred_file)
    if os.path.isfile(cred_file):
        c = json.load(open(cred_file, encoding="utf-8"))
        u, p = c.get("username"), c.get("password")
        if u and p:
            return u, p, "file"
    return None, None, "missing"


def login(cfg, tok):
    user, pwd, src = get_credentials()
    if not user:
        return tok, {"ok": False, "error": "need_credentials",
                     "hint": "首次使用需社区账号：请向用户询问账号与密码，写入环境变量 COMMUNITY_USERNAME/COMMUNITY_PASSWORD 或实例凭据文件（chmod 600），然后重试。"}
    r, _ = call(cfg, "member/login", {
        "GET": {"mod": "logging", "action": "login", "loginsubmit": "yes"},
        "POST": {"fastloginfield": "username", "username": user, "password": pwd,
                 "cookietime": "2592000"}}, token=tok)
    msg = (r.get("data", {}).get("msg") or {}).get("message", "")
    ok = "succeed" in msg          # login_succeed / location_login_succeed 均算成功
    return tok, {"ok": ok, "message": msg, "user": (r.get("data") or {}).get("user"), "source": src}


def with_retry(cfg, fn):
    """提交类重试：仅网络层异常时指数退避，业务响应不重发。"""
    delays = (2, 4, 8)
    last_err = None
    for i, d in enumerate((0,) + delays):
        if d:
            time.sleep(d)
        try:
            return fn()
        except (urllib.error.URLError, OSError) as e:
            last_err = str(e)
    return {"ret": None, "error": "network", "detail": last_err}


def interpret(result):
    """把调用结果翻译为统一判定。"""
    if result.get("error") == "network":
        return {"ok": False, "kind": "network", "detail": result.get("detail")}
    ret = result.get("ret")
    msg = (result.get("data", {}) or {}).get("msg") or {}
    if isinstance(msg, dict) and msg.get("message"):
        m = msg["message"]
        if m in ("post_newthread_succeed", "post_reply_succeed", "article_publish_succeed"):
            return {"ok": True, "kind": "published",
                    "tid": result.get("data", {}).get("tid"),
                    "url_forward": msg.get("url_forward")}
        if "audit" in m or "审核" in (msg.get("show_message") or ""):
            return {"ok": True, "kind": "audit", "message": msg.get("show_message")}
        if ret == -109:
            return {"ok": False, "kind": "not_imported", "message": "接口未导入/未授权（站长后台处理）"}
        if ret == -110:
            return {"ok": False, "kind": "site_config", "message": "站点 Redis 未配置（站长处理）"}
        return {"ok": False, "kind": "api_error", "ret": ret, "message": m or result}
    return {"ok": ret == 0, "kind": "raw", "result": result}


def cmd_check(cfg, a=None):
    tok = ensure_token(cfg)
    r, status = call(cfg, "member/loginInfo", {"GET": {"mod": "logging", "action": "login"}}, token=tok)
    print(json.dumps({"ok": r.get("ret") == 0, "http": status}, ensure_ascii=False))


def cmd_forums(cfg, a=None):
    tok = ensure_token(cfg)
    r, _ = call(cfg, "index/forumlist", token=tok)
    out = []

    def walk(items):
        for f in items or []:
            out.append({"fid": f.get("fid"), "name": f.get("name"), "type": f.get("type")})
            sub = f.get("subforums")
            if sub:
                walk(json.loads(sub) if isinstance(sub, str) else sub)

    walk((r.get("data") or {}).get("forumlist") or [])
    print(json.dumps({"ok": r.get("ret") == 0, "forums": out}, ensure_ascii=False, indent=1))


def cmd_post(cfg, a):
    tok = ensure_token(cfg)
    tok, lg = login(cfg, tok)
    if not lg.get("ok"):
        print(json.dumps({"ok": False, "error": "login_failed", "detail": lg}, ensure_ascii=False))
        sys.exit(3)
    fid = a.fid or cfg.get("default_fid")
    if not fid:
        print(json.dumps({"ok": False, "error": "no_fid"}, ensure_ascii=False))
        sys.exit(4)
    result = with_retry(cfg, lambda: call(cfg, "newthread", {
        "POST": {"fid": str(fid), "subject": a.title, "message": a.content}},
        token=tok, uniqueid=str(uuid.uuid4()))[0])
    out = interpret(result)
    out["fid"] = str(fid)
    if out.get("ok") and out.get("tid"):
        out["url"] = f"{cfg['site']}/thread-{out['tid']}-1-1.html"
    print(json.dumps(out, ensure_ascii=False, indent=1))


def cmd_reply(cfg, a):
    tok = ensure_token(cfg)
    tok, lg = login(cfg, tok)
    if not lg.get("ok"):
        print(json.dumps({"ok": False, "error": "login_failed", "detail": lg}, ensure_ascii=False))
        sys.exit(3)
    result = with_retry(cfg, lambda: call(cfg, "forum/reply", {
        "POST": {"fid": str(a.fid or cfg.get("default_fid") or ""),
                 "tid": str(a.tid), "subject": "", "message": a.content,
                 "replysubmit": "yes"}},
        token=tok, uniqueid=str(uuid.uuid4()))[0])
    out = interpret(result)
    if out.get("ok") and out.get("tid"):
        out["url"] = f"{cfg['site']}/forum.php?mod=viewthread&tid={out['tid']}"
    print(json.dumps(out, ensure_ascii=False, indent=1))


def cmd_article(cfg, a):
    tok = ensure_token(cfg)
    tok, lg = login(cfg, tok)
    if not lg.get("ok"):
        print(json.dumps({"ok": False, "error": "login_failed", "detail": lg}, ensure_ascii=False))
        sys.exit(3)
    result = with_retry(cfg, lambda: call(cfg, "portal/publish", {
        "POST": {"catid": str(a.catid), "subject": a.title, "content": a.content}},
        token=tok)[0])
    print(json.dumps(interpret(result), ensure_ascii=False, indent=1))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    sub.add_parser("forums")
    sp = sub.add_parser("post")
    sp.add_argument("--fid"), sp.add_argument("--title", required=True), sp.add_argument("--content", required=True)
    sr = sub.add_parser("reply")
    sr.add_argument("--tid", required=True), sr.add_argument("--fid"), sr.add_argument("--content", required=True)
    sa = sub.add_parser("article")
    sa.add_argument("--catid", required=True), sa.add_argument("--title", required=True), sa.add_argument("--content", required=True)
    a = p.parse_args()
    cfg = load_cfg()
    {"check": cmd_check, "forums": cmd_forums, "post": cmd_post,
     "reply": cmd_reply, "article": cmd_article}[a.cmd](cfg, a)


if __name__ == "__main__":
    main()
