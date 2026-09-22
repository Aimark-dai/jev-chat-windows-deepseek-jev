# 当前项目边界与开发约定

本文描述 `Aimark-dai/jev-chat-windows-deepseek-jev` 当前版本，不代表上游 `jev-chat/jev-chat-windows` 的原始规划。

## 产品目标

在用户自己的 Windows 电脑上读取当前微信聊天画面，给出可核对的 JEV 判断和三条候选回复。候选由 DeepSeek 官方接口生成；启用 TypeSafe 后，JEV 负责生成前的结构化预判和生成后的质量复审、排序。

## 固定边界

1. 只处理用户自己设备上有权查看的聊天。
2. 只使用窗口级截图和本地 OCR，不注入微信、不读取或解密微信数据库、不读取微信进程内存。
3. 捕获帧在内存中处理，不把聊天截图作为文件保存。
4. API Key 仅保存在 Windows 当前用户环境变量，不进入 `config.json`、日志、源码或发布包。
5. 自动发送默认关闭。只有用户在主界面明确打开后，才允许填入并启动 3 秒倒计时。
6. 切换会话、出现新消息、微信不在前台、关闭开关或 JEV 复审未通过，都必须取消自动发送。
7. 起草规则禁止生成转账、红包、收款相关操作建议。
8. 正式版本号必须与 Git 标签一致；发布包必须同时提供 SHA256 校验文件。

## 当前链路

```text
微信窗口 → WGC 截图 → RapidOCR → 最近聊天状态
  → TypeSafe JEV 预判（可选）
  → DeepSeek 生成三条候选
  → TypeSafe JEV 质量复审与排序（可选）
  → 不合格时重写一次
  → 悬浮窗展示 → 用户填入或显式授权后倒计时发送
```

关闭 TypeSafe 时，`core/jev_client.py` 使用 DeepSeek 完成基础判断与排序。

## 关键模块

| 文件 | 责任 |
| --- | --- |
| `core/engine.py` | 全链路编排、复审、限次重写与结果汇总 |
| `core/typesafe_client.py` | TypeSafe 官方 System One 请求、返回校验和错误处理 |
| `core/jev_client.py` | 关闭 TypeSafe 时的 DeepSeek 判断实现 |
| `core/questions.py` | JEV 预判、复审和排序问题定义 |
| `core/draft.py` | DeepSeek 候选生成与输出清洗 |
| `app/capture.py` | Windows 微信窗口捕获 |
| `app/ocr.py` | 本地 OCR、说话人和会话识别 |
| `app/fill.py` | 填入微信及自动发送门禁 |
| `app/overlay.py` | 主界面、设置、判断卡片和倒计时状态 |
| `app/update.py` | 查询本仓库 GitHub Release 的新版本 |

## 来源说明

Windows 截图、OCR 和悬浮窗基础来自 MIT 项目 [jev-chat/jev-chat-windows](https://github.com/jev-chat/jev-chat-windows)。本仓库的模型链路、TypeSafe 官方直连、自动发送门禁、版本发布和后续界面调整属于本仓库的二次开发。完整说明见根目录 [NOTICE.md](../NOTICE.md)。
