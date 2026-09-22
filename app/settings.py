# -*- coding: utf-8 -*-
"""设置持久化。key 硬约束（docs/KICKOFF.md #6）：只进环境变量，绝不落文件；relationship 不是密钥，落 config.json。

key 的持久化走 Windows 用户环境变量（注册表 HKCU\\Environment，跟 setx 写的是同一个地方）。
读的时候先看进程环境，没有就直接读注册表——IDE 启动时把环境快照拿走了，之后再 Run 继承的还是旧环境，
只靠 os.environ 会「保存了下次打开还是没有」。"""
from __future__ import annotations

import ctypes
import json
import os
import sys  # 只为下面这一处：打包后 __file__ 指向临时解包目录，config.json 得放在 exe 旁边才存得住

_ROOT = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
         else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG = os.path.join(_ROOT, "config.json")
_DEFAULT_RELATIONSHIP = "romantic partners"
_DEFAULT_CONTEXT = 10
_ENV = "DEEPSEEK_API_KEY"
_DEEPSEEK_ENV = _ENV  # 兼容旧调用名；定制版只使用 DeepSeek 官方服务
_TYPESAFE_ENV = "TYPESAFE_API_KEY"
_PROVIDERS = ("deepseek",)
_JUDGE_PROVIDERS = ("deepseek", "typesafe")

def relationship() -> str:
    """每次都重新读文件，改设置不用重启进程。"""
    try:
        with open(_CONFIG, encoding="utf-8") as f:
            return json.load(f).get("relationship") or _DEFAULT_RELATIONSHIP
    except (OSError, ValueError):
        return _DEFAULT_RELATIONSHIP

def context() -> int:
    """参考上下文条数：起草和判断各看最近多少条消息。3~30，缺失/脏数据一律退默认值。"""
    try:
        with open(_CONFIG, encoding="utf-8") as f:
            n = int(json.load(f).get("context", _DEFAULT_CONTEXT))
    except (OSError, ValueError, TypeError):
        return _DEFAULT_CONTEXT
    return max(3, min(30, n))

def style() -> str:
    """用户自己描述的说话风格（可选，自由文本），只喂给起草模型。默认空 = 只照着最近的消息模仿。"""
    try:
        with open(_CONFIG, encoding="utf-8") as f:
            return str(json.load(f).get("style") or "")
    except (OSError, ValueError):
        return ""

def draft_provider() -> str:
    """候选话术固定由 DeepSeek 官方接口起草。"""
    try:
        with open(_CONFIG, encoding="utf-8") as f:
            v = json.load(f).get("draft_provider")
    except (OSError, ValueError):
        return _PROVIDERS[0]
    return v if v in _PROVIDERS else _PROVIDERS[0]

def judge_provider() -> str:
    """判断与排序来源。缺失或脏数据安全回退到 DeepSeek。"""
    try:
        with open(_CONFIG, encoding="utf-8") as f:
            value = json.load(f).get("judge_provider")
    except (OSError, ValueError):
        return "deepseek"
    return value if value in _JUDGE_PROVIDERS else "deepseek"

def reply_target() -> bool:
    """群聊指定回复对象：开了才在界面上选回复给谁、才把对象喂给模型。默认关。"""
    try:
        with open(_CONFIG, encoding="utf-8") as f:
            return bool(json.load(f).get("reply_target", False))
    except (OSError, ValueError):
        return False

def auto_send() -> bool:
    """是否在倒计时后自动发送推荐回复。高风险动作，缺省必须关闭。"""
    try:
        with open(_CONFIG, encoding="utf-8") as f:
            return json.load(f).get("auto_send") is True
    except (OSError, ValueError):
        return False

def thinking() -> bool:
    """起草时是否开思考模式：慢且贵，默认关。"""
    try:
        with open(_CONFIG, encoding="utf-8") as f:
            return bool(json.load(f).get("thinking", False))
    except (OSError, ValueError):
        return False

def check_update() -> bool:
    """启动时要不要去 GitHub 查一次最新版本号：默认开，只出这一次网，设置里能关。"""
    try:
        with open(_CONFIG, encoding="utf-8") as f:
            return bool(json.load(f).get("check_update", True))
    except (OSError, ValueError):
        return True

def _get_key(env_name: str) -> str:
    """进程环境优先；没有就读注册表并带进进程环境，之后 core/ 里按 os.environ 读就有了。"""
    v = os.environ.get(env_name, "").strip()
    if not v:
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                v = str(winreg.QueryValueEx(k, env_name)[0]).strip()
        except Exception:  # 非 Windows / 没这个值
            v = ""
        if v:
            os.environ[env_name] = v
    return v

def _set_key(env_name: str, value: str) -> None:
    """只写进程环境 + HKCU\\Environment，不写任何文件。"""
    os.environ[env_name] = value
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, env_name, 0, winreg.REG_SZ, value)
        # 广播一下，之后新开的终端/进程就能看到；已经开着的 IDE 看不到也无所谓，启动时会读注册表
        ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x1A, 0, "Environment", 2, 5000, None)
    except Exception:
        pass  # 非 Windows（本机 Mac 开发）走不到，忽略

def key() -> str:
    return _get_key(_ENV)

def has_key() -> bool:
    return bool(key())

def deepseek_key() -> str:
    return key()

def has_deepseek_key() -> bool:
    return has_key()

def typesafe_key() -> str:
    return _get_key(_TYPESAFE_ENV)

def has_typesafe_key() -> bool:
    return bool(typesafe_key())

def save(key_text: str | None, relationship_text: str, context_n: int | None = None,
         deepseek_key_text: str | None = None, provider_text: str | None = None,
         reply_target_on: bool | None = None, style_text: str | None = None,
         thinking_on: bool | None = None, check_update_on: bool | None = None,
         auto_send_on: bool | None = None, typesafe_key_text: str | None = None,
         judge_provider_text: str | None = None) -> None:
    """每个参数为空/None = 保留当前值。key 只写进程环境 + HKCU\\Environment，不写文件。"""
    if key_text:
        _set_key(_ENV, key_text)
    if deepseek_key_text and not key_text:
        _set_key(_DEEPSEEK_ENV, deepseek_key_text)
    if typesafe_key_text:
        _set_key(_TYPESAFE_ENV, typesafe_key_text)
    n = context() if context_n is None else max(3, min(30, int(context_n)))
    provider = "deepseek"
    judge = judge_provider() if judge_provider_text is None else str(judge_provider_text)
    judge = judge if judge in _JUDGE_PROVIDERS else "deepseek"
    target = reply_target() if reply_target_on is None else bool(reply_target_on)
    style_v = style() if style_text is None else str(style_text).strip()  # 空串 = 清掉
    think = thinking() if thinking_on is None else bool(thinking_on)
    check = check_update() if check_update_on is None else bool(check_update_on)
    auto = auto_send() if auto_send_on is None else bool(auto_send_on)
    with open(_CONFIG, "w", encoding="utf-8") as f:
        json.dump({"relationship": relationship_text, "context": n, "draft_provider": provider,
                   "judge_provider": judge,
                   "reply_target": target, "style": style_v, "thinking": think,
                   "check_update": check, "auto_send": auto}, f, ensure_ascii=False)

def set_auto_send(enabled: bool) -> None:
    """主界面快捷开关：只更新自动发送，其他设置按当前值保留。"""
    save(None, relationship(), auto_send_on=bool(enabled))
