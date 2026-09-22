# -*- coding: utf-8 -*-
"""TypeSafe official System One API client for Jev decisions."""

from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.request

try:
    from .jev_client import JevError, redact_secrets
except ImportError:
    from jev_client import JevError, redact_secrets

API_URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
MAX_RETRIES = 3


def _api_key() -> str:
    key = (os.environ.get("TYPESAFE_API_KEY") or "").strip()
    if not key:
        raise JevError("TYPESAFE_API_KEY 未配置，请在设置中填写 TypeSafe 官方 API 密钥。")
    return key


def _error_body(exc: urllib.error.HTTPError) -> str:
    try:
        raw = exc.read().decode("utf-8", errors="replace")
    except Exception:
        raw = ""
    return redact_secrets(raw)[:800]


def ask(state: dict, questions: dict, timeout: float = 20) -> dict:
    """Send state and typed questions directly to TypeSafe Jev."""
    key = _api_key()
    payload = json.dumps(
        {"model": MODEL, "state": state, "questions": questions},
        ensure_ascii=False,
    ).encode("utf-8")

    for attempt in range(MAX_RETRIES + 1):
        req = urllib.request.Request(
            API_URL,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            if not isinstance(result.get("answers"), dict):
                raise JevError("TypeSafe JEV 返回结果缺少 answers 对象")
            return result
        except urllib.error.HTTPError as exc:
            detail = _error_body(exc)
            if exc.code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                time.sleep(2**attempt)
                continue
            readable = {
                401: "TypeSafe JEV HTTP 401：API 密钥无效。",
                402: "TypeSafe JEV HTTP 402：账户余额不足。",
                422: f"TypeSafe JEV HTTP 422：请求格式错误。{detail}",
                429: f"TypeSafe JEV HTTP 429：请求过快，重试 {MAX_RETRIES} 次后仍受限。{detail}",
            }.get(exc.code, f"TypeSafe JEV HTTP {exc.code}：{detail}")
            raise JevError(readable, exc.code) from None
        except (TimeoutError, socket.timeout) as exc:
            if attempt < MAX_RETRIES:
                time.sleep(2**attempt)
                continue
            raise JevError(f"TypeSafe JEV 请求超时 {timeout}s") from exc
        except urllib.error.URLError as exc:
            reason = redact_secrets(getattr(exc, "reason", exc))
            if attempt < MAX_RETRIES:
                time.sleep(2**attempt)
                continue
            raise JevError(f"TypeSafe JEV 请求失败：{reason}") from None
        except (KeyError, TypeError, ValueError) as exc:
            raise JevError(f"TypeSafe JEV 返回结果无法解析：{redact_secrets(exc)}") from None

    raise JevError("TypeSafe JEV：重试用尽")
