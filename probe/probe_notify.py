# -*- coding: utf-8 -*-
"""
P2 门禁探针（方案②）：微信桌面来消息，UserNotificationListener 能不能拿到？

UserNotificationListener 是微软官方 API，读 Windows 通知中心里的 toast。
要用户授权，只读通知，不碰微信进程、不读数据库、不注入。回答唯一那个问题：
    微信 4.x 发消息时，是走 Windows 通知平台（能监听到），
    还是自己画弹窗（一条也看不到）？

用法（Windows，Python 3.9~3.12）:
    pip install winsdk
    python probe/probe_notify.py

跑起来后：把微信切到后台，用手机/别人给你发条消息，看终端有没有冒出来。Ctrl+C 停。

判定:
    冒出 app='微信'/'Weixin' 且带正文  -> ② 可行，通知即触发点，零 OCR
    授权 OK 但发消息啥也不冒            -> 微信自绘弹窗，不走通知平台，②否决
    授权拿不到(Denied)                 -> 去 设置>隐私>通知，允许 python.exe
"""
import asyncio
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    from winsdk.windows.ui.notifications.management import UserNotificationListener
    from winsdk.windows.ui.notifications import NotificationKinds
except ImportError:
    try:
        from winrt.windows.ui.notifications.management import UserNotificationListener
        from winrt.windows.ui.notifications import NotificationKinds
    except ImportError:
        sys.exit("缺依赖：pip install winsdk\n"
                 "（若 winsdk 装不上：pip install winrt-Windows.UI.Notifications.Management "
                 "winrt-Windows.UI.Notifications winrt-Windows.Foundation）")


def to_list(vec):
    """WinRT 集合转 list，兼容不同 projection。"""
    try:
        return list(vec)
    except TypeError:
        return [vec.get_at(i) for i in range(vec.size)]


def app_name(n):
    try:
        return n.app_info.display_info.display_name
    except Exception:
        return "?"


def texts_of(n):
    out = []
    try:
        for b in to_list(n.notification.visual.bindings):
            for el in to_list(b.get_text_elements()):
                if el.text:
                    out.append(el.text)
    except Exception as e:
        out.append(f"<读正文失败: {e}>")
    return out


def is_wechat(app):
    a = (app or "").lower()
    return "微信" in (app or "") or "weixin" in a or "wechat" in a


async def main():
    listener = UserNotificationListener.get_current()
    status = await listener.request_access_async()
    print(f"授权状态: {status.name if hasattr(status, 'name') else status} (1=Allowed 2=Denied)")
    if getattr(status, "value", status) != 1:
        print("未获授权。去 设置 > 隐私和安全性 > 通知，把 python.exe 打开后重跑。")
        return

    # 先把通知中心里现有的都 dump 一遍
    notes = to_list(await listener.get_notifications_async(NotificationKinds.TOAST))
    print(f"\n通知中心当前有 {len(notes)} 条 toast:")
    for n in notes:
        app = app_name(n)
        mark = " ★微信" if is_wechat(app) else ""
        print(f"  [id={n.id}] {app!r}{mark}  {' | '.join(texts_of(n))[:60]}")

    print("\n" + "=" * 60)
    print("开始监听。现在把微信切到后台，让别人/用手机给你发条消息。")
    print("确认：微信设置里消息通知已开、Windows 专注助手/勿扰已关。Ctrl+C 停。")
    print("=" * 60 + "\n")

    seen = {n.id for n in notes}
    saw_wechat = False
    try:
        while True:
            cur = to_list(await listener.get_notifications_async(NotificationKinds.TOAST))
            for n in cur:
                if n.id in seen:
                    continue
                seen.add(n.id)
                app = app_name(n)
                wx = is_wechat(app)
                saw_wechat = saw_wechat or wx
                print(f"[+ id={n.id}] app={app!r}{' ★微信' if wx else ''}")
                for t in texts_of(n):
                    print(f"      {t}")
            await asyncio.sleep(2)
    except KeyboardInterrupt:
        print("\n\n>>> 判定:", "★ 监听到微信通知 → ② 可行" if saw_wechat
              else "没监听到微信通知 → 微信可能自绘弹窗，② 否决，回退方案①/剪贴板")


if __name__ == "__main__":
    asyncio.run(main())
