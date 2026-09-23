# -*- coding: utf-8 -*-
"""TypeSafe official System One API client for Jev decisions."""

from __future__ import annotations

import json
import math
import os
import re
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


class TypeSafeAccessDenied(JevError):
    """The service rejected access; a new chat message must not trigger a retry."""


def _access_denied_message(detail: str) -> str:
    try:
        error = json.loads(detail)
    except (TypeError, ValueError):
        error = {}
    if isinstance(error, dict) and error.get("error_code") == 1010:
        message = "TypeSafe JEV HTTP 403 / Cloudflare 1010：当前客户端请求被服务方拦截，请联系 TypeSafe 处理。"
        ray_id = str(error.get("ray_id") or "")
        if re.fullmatch(r"[0-9a-fA-F]{8,64}", ray_id):
            message += f" Ray ID：{ray_id}。"
        return message
    return "TypeSafe JEV HTTP 403：服务拒绝访问，请检查账号权限或联系 TypeSafe 处理。"


def _validate_answers(data: dict, questions: dict) -> dict:
    answers = data.get("answers") if isinstance(data, dict) else None
    if not isinstance(answers, dict):
        raise JevError("TypeSafe JEV 返回结果缺少 answers 对象")

    normalized = {}
    for name, spec in questions.items():
        item = answers.get(name)
        if not isinstance(item, dict):
            raise JevError(f"TypeSafe JEV 返回结果缺少 {name}")
        kind = spec.get("type")
        if kind == "score":
            score = item.get("score")
            if isinstance(score, bool) or not isinstance(score, (int, float)):
                raise JevError(f"TypeSafe JEV 返回结果 {name}.score 不是数字")
            highest = max(0, len(spec.get("criteria") or []) - 1)
            if not math.isfinite(float(score)) or not 0 <= float(score) <= highest:
                raise JevError(f"TypeSafe JEV 返回结果 {name}.score 超出 0-{highest}")
            normalized_item = {"type": "score", "score": float(score)}
            confidence = item.get("confidence")
            if confidence is not None:
                if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                    raise JevError(f"TypeSafe JEV 返回结果 {name}.confidence 不是概率")
                confidence = float(confidence)
                if not math.isfinite(confidence) or not 0 <= confidence <= 1:
                    raise JevError(f"TypeSafe JEV 返回结果 {name}.confidence 超出 0-1")
                normalized_item["confidence"] = confidence
            levels = {str(index) for index in range(highest + 1)}
            legend = item.get("legend")
            if legend is not None:
                if not isinstance(legend, dict) or any(str(key) not in levels for key in legend):
                    raise JevError(f"TypeSafe JEV 返回结果 {name}.legend 无效")
                normalized_item["legend"] = {str(key): value for key, value in legend.items()}
            probabilities = item.get("probabilities")
            if probabilities is not None:
                if not isinstance(probabilities, dict):
                    raise JevError(f"TypeSafe JEV 返回结果 {name}.probabilities 不是对象")
                clean_probabilities = {}
                for key, value in probabilities.items():
                    key = str(key)
                    if key not in levels or isinstance(value, bool) or not isinstance(value, (int, float)):
                        raise JevError(f"TypeSafe JEV 返回结果 {name}.probabilities 无效")
                    value = float(value)
                    if not math.isfinite(value) or not 0 <= value <= 1:
                        raise JevError(f"TypeSafe JEV 返回结果 {name}.probabilities 超出 0-1")
                    clean_probabilities[key] = value
                normalized_item["probabilities"] = clean_probabilities
            normalized[name] = normalized_item
            continue

        if kind == "noul":
            probability = item.get("noul")
            if isinstance(probability, bool) or not isinstance(probability, (int, float)):
                raise JevError(f"TypeSafe JEV 返回结果 {name}.noul 不是概率")
            probability = float(probability)
            if not math.isfinite(probability) or not 0 <= probability <= 1:
                raise JevError(f"TypeSafe JEV 返回结果 {name}.noul 超出 0-1")
            normalized[name] = {"type": "noul", "noul": probability}
            continue

        choice = item.get("choice")
        if isinstance(choice, bool):
            choice = "true" if choice else "false"
        choice = str(choice or "").strip()
        allowed = tuple((spec.get("criteria") or {}).keys())
        if choice not in allowed:
            raise JevError(f"TypeSafe JEV 返回结果 {name}.choice={choice!r} 不在允许值中")
        normalized_item = {"type": kind, "choice": choice}
        confidence = item.get("confidence")
        if confidence is not None:
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                raise JevError(f"TypeSafe JEV 返回结果 {name}.confidence 不是概率")
            confidence = float(confidence)
            if not math.isfinite(confidence) or not 0 <= confidence <= 1:
                raise JevError(f"TypeSafe JEV 返回结果 {name}.confidence 超出 0-1")
            normalized_item["confidence"] = confidence
        probabilities = item.get("probabilities")
        if probabilities is not None:
            if not isinstance(probabilities, dict):
                raise JevError(f"TypeSafe JEV 返回结果 {name}.probabilities 不是对象")
            clean_probabilities = {}
            for key, value in probabilities.items():
                if key not in allowed or isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise JevError(f"TypeSafe JEV 返回结果 {name}.probabilities 无效")
                value = float(value)
                if not math.isfinite(value) or not 0 <= value <= 1:
                    raise JevError(f"TypeSafe JEV 返回结果 {name}.probabilities 超出 0-1")
                clean_probabilities[key] = value
            normalized_item["probabilities"] = clean_probabilities
        normalized[name] = normalized_item
    return normalized


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
            return {**result, "answers": _validate_answers(result, questions)}
        except urllib.error.HTTPError as exc:
            detail = _error_body(exc)
            if exc.code == 403:
                raise TypeSafeAccessDenied(_access_denied_message(detail), 403) from None
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
