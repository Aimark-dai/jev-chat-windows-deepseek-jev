# 来源与修改说明

`Aimark-dai/jev-chat-windows-deepseek-jev` 是公开的二次开发项目，并非 `jev-chat` 或 `Finderchangchang` 官方发行版。

## 上游来源

- [jev-chat/jev-chat-windows](https://github.com/jev-chat/jev-chat-windows)
  - MIT License
  - Copyright (c) 2026 rezoch340
  - 本仓库沿用了其 Windows 窗口采集、本地 OCR、微信填入、悬浮窗和部分工程结构。
- [Finderchangchang/jev-chat-JARVIS](https://github.com/Finderchangchang/jev-chat-JARVIS)
  - 更早的 Android 项目及 JEV 聊天判断思路来源。

## 本仓库的主要修改

- 移除 OpenRouter 依赖，候选话术改为 DeepSeek 官方 API 生成。
- 增加 TypeSafe 官方 System One / JEV 直连客户端。
- 实现“JEV 预判 → DeepSeek 生成 → JEV 复审排序 → 限次重写”的链路。
- 增加默认关闭、带 3 秒可取消倒计时和多重门禁的自动发送功能。
- 增加 GitHub 项目入口、正式版本显示、启动更新检查和自动 Release 流水线。
- 调整设置页、判断卡片、演示数据、文档与公开发布内容。

这些修改由本仓库维护者完成，上游作者没有参与或背书这些定制功能。上游版权声明与 MIT 条款保留在 [LICENSE](LICENSE) 中。

第三方运行依赖仍分别遵循各自许可证；本文件不替代其许可证文本。
