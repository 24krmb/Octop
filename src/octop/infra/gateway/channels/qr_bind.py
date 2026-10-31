"""WeCom / WeChat QR bind helpers (shared by API and CLI)."""

from __future__ import annotations

import asyncio
import platform
from typing import Any

import httpx

_qq_qr_sessions: dict[str, tuple[Any, str]] = {}





async def qq_qr_generate(session_id: str) -> dict[str, str]:
    """Create a QQ Bot QR task, replacing any pending task for this session."""
    try:
        from octop_gateway.channels.qq import QQBotQRLogin
    except ImportError as exc:
        raise RuntimeError("QQ QR login requires a recent octop-gateway installation.") from exc

    previous = _qq_qr_sessions.pop(session_id, None)
    if previous is not None:
        previous[0].cancel(previous[1])

    login = QQBotQRLogin(source="octop")
    result = await login.fetch_qr_code()
    _qq_qr_sessions[session_id] = (login, result.task_id)
    return {"qrcode_token": result.task_id, "qrcode_url": result.qrcode_url}


async def qq_qr_poll(session_id: str, qrcode_token: str) -> dict[str, Any]:
    """Poll the active QQ Bot QR task for an Octop API or CLI session."""
    session = _qq_qr_sessions.get(session_id)
    if session is None or session[1] != qrcode_token:
        return {"status": "error", "message": "QQ QR session is missing or expired"}

    login, task_id = session
    result = await login.poll(task_id)
    if result.status == "pending":
        return {"status": "pending"}

    _qq_qr_sessions.pop(session_id, None)
    if result.status == "expired":
        return {"status": "expired", "message": "QQ QR code expired"}
    if not result.credentials:
        return {"status": "error", "message": "QQ QR binding returned no credentials"}

    credentials = result.credentials[0]
    return {
        "status": "success",
        "app_id": credentials.app_id,
        "secret": credentials.app_secret,
        "user_openid": credentials.user_openid,
    }


async def weixin_qr_generate() -> dict[str, str]:
    try:
        from octop_gateway.channels.weixin.login_qr import WeixinQRLogin
    except ImportError as exc:
        raise RuntimeError(
            "WeChat QR login requires octop-gateway with weixin channel support."
        ) from exc
    login = WeixinQRLogin()
    result = await login.fetch_qr_code()
    return {
        "qrcode_token": str(result.qrcode),
        "qrcode_url": str(result.qrcode_img_content),
    }


async def weixin_qr_poll(qrcode_token: str) -> dict[str, Any]:
    try:
        from octop_gateway.channels.weixin.login_qr import WeixinQRLogin
    except ImportError as exc:
        raise RuntimeError(
            "WeChat QR login requires octop-gateway with weixin channel support."
        ) from exc
    login = WeixinQRLogin()
    try:
        result = await asyncio.wait_for(login.wait_for_login(qrcode_token), timeout=60.0)
    except TimeoutError:
        return {"status": "wait"}
    if not result.connected:
        return {"status": "error", "message": result.message}
    return {
        "status": "success",
        "account_id": result.account_id,
        "token": result.bot_token,
        "base_url": result.base_url,
    }
