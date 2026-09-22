# jev-chat-windows

> **本机官方直连定制版（2026-09-22）**：DeepSeek 官方接口负责生成候选话术；
> 开启 TypeSafe JEV 后，JEV 会先判断意图、风险和行动，再指导 DeepSeek 生成，最后复审排序；
> 候选全部不合格时只重写一次，第二次仍不合格会禁止自动发送并要求人工确认。
> JEV 使用 `TYPESAFE_API_KEY` 调用 `https://api.typesafe.ai/v1/systemone`，不经过 OpenRouter，
> 并显示 JEV 返回的候选概率。两种密钥都只保存在 Windows 当前用户环境变量。
> 主界面底部可选开启“3 秒自动发送”；默认关闭。开启后先替换填入微信输入框，
> 显示 3 秒可取消倒计时，然后按 Enter 发送。切换会话、来新消息或微信不在前台时会取消。

DeepSeek 接口依据：
[Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)、
[JSON Output](https://api-docs.deepseek.com/guides/json_mode/)、
[Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode/)。

微信（Windows 4.x）旁挂的回复辅助：本地 OCR 读屏上的对话 → TypeSafe JEV 预判 →
DeepSeek 按预判生成 3 条候选 → TypeSafe JEV 复审排序 → 一键填入微信输入框。默认手动发送；主界面开启“3秒自动发送”后，
会先填入并显示可取消倒计时，再按 Enter 发送。

判断内核来自安卓版 [Finderchangchang/jev-chat-JARVIS](https://github.com/Finderchangchang/jev-chat-JARVIS)，
这里把采集换成了 Windows 端的窗口截图 + 离线 OCR。

## 下载即用（推荐）

**普通使用直接下载，不用装 Python、不用碰源码。** 后面的「源码运行」是给开发者的。

👉 **[下载最新版](https://github.com/Aimark-dai/jev-chat-windows-deepseek-jev/releases/latest)**

1. 在 Releases 页下载 `jev-chat-windows-vX.Y.Z.zip`（约 146 MB）
2. 解压到一个固定目录（整个文件夹一起，exe 要用旁边那堆文件）
3. 双击 `jev-chat-windows.exe`

要求：Windows 10 1903+ / 11、微信 Windows 4.x、一个 DeepSeek 官方 API key；如需 JEV 全链路优化，
再准备一个 TypeSafe 官方 API key。

首次启动会弹设置页填写 DeepSeek key，并可开启 TypeSafe JEV。两个 key 都写进 Windows 用户环境变量（注册表 `HKCU\Environment`），
不落任何文件；其余设置写在 exe 旁边的 `config.json`，整个文件夹拷走设置也跟着走。

> exe 没签名，SmartScreen 会拦一下：「更多信息」→「仍要运行」。介意就往下看「自己打包」，自己打的更踏实。

## 使用说明

**第一次启动**

1. 填写 **DeepSeek 官方 API key**（[platform.deepseek.com](https://platform.deepseek.com/) 申请）。
2. 需要 JEV 全链路优化时，打开对应开关并填写 **TypeSafe 官方 API key**。
3. 选「你们的关系」（恋人 / 朋友 / 同事 / 家人 / 自定义），保存即可。

**日常怎么用**

- 微信开着、别最小化（用别的窗口盖住没事），把要聊的会话点开
- 对方来一条消息 → 悬浮窗几秒后给判断摘要 + 三条候选（带 Jev 给的胜出概率）
- 点「填入微信」→ 文字进微信输入框 → **你自己看一眼、改一改、按发送**。只有显式打开“3秒自动发送”才会代按 Enter
- 你在微信里切到哪个会话，悬浮窗就跟到哪个；群聊会带上发言人名，想指定回复给谁去设置里开「群聊指定回复对象」
- 暂时不想让它读微信：标题栏开关拨到「已暂停」

**花多少钱**

只有对方来新消息才调用服务。开启 JEV 时通常是一次 JEV 预判 + 一次 DeepSeek 起草 + 一次 JEV 复审；
复审不合格时再增加一次 DeepSeek 重写和一次 JEV 复审。十分钟没人说话就是十分钟零调用。
思考模式默认关，别开——起草三句话用不上，慢好几倍还贵。

## 截图

<table>
<tr>
<td width="33%"><img src="docs/ui_home.png" alt="回复建议"></td>
<td width="33%"><img src="docs/ui_settings.png" alt="设置"></td>
<td width="33%"><img src="docs/ui_toggle_off.png" alt="采集暂停"></td>
</tr>
<tr>
<td align="center">回复建议：「当前会话」跟随微信、群聊多一行「回复对象」，3 条候选带 Jev 概率百分比，推荐那条置顶</td>
<td align="center">设置：关系背景、说话风格、参考上下文条数、群聊指定回复对象（往下还有回复服务）</td>
<td align="center">采集暂停：不再读微信，已有候选照样能填入、能复制</td>
</tr>
</table>

## 功能

- **跟着微信当前会话走**：会话名从面板头部 OCR 出来，记录、上下文、候选都按会话分开存；也可以自己
  在下拉框里选另一个会话，翻它的记录和上次的建议（那会儿只能看不能填）。
- **群聊**：每条消息前面的发言人名会一起喂给模型，所以它知道哪句是谁说的；打开「群聊指定回复对象」
  还能选回复给谁，三条候选都按 TA 写，填入时可带「@名字 」前缀（纯文本）。
- **3 条候选**：每条带 Jev 给的胜出概率百分比，按概率排序，推荐那条置顶并标「推荐回复」；
  每条都有「填入微信」和复制按钮。
- **判断摘要**：建议动作、可能意图、对方可能需要、紧张度 0–9。
- **采集开关**：标题栏一拨就停，WGC 会话一起停掉（Win10 的黄框跟着消失），已有候选不受影响。
- **实时聊天记录**：底部展开，看 OCR 到底读出了什么，认错了一眼就能发现。
- **JEV 全链路优化**：先判断意图、风险和行动，再指导 DeepSeek 生成并复审；不合格最多重写一次。
- **思考模式开关**：默认关；开了模型先想再写，更斟酌但慢好几倍、贵一些。
- **参考上下文条数**：3~30，默认 10，起草和判断都按它取最近 N 条。
- **说话风格**：一句话描述自己的口吻，补在「照着你最近发的消息模仿」之上。
- **响应式悬浮窗**：置顶、可拖可缩，最小 320×360，窄于 400 进紧凑模式。
- **新版本提示**：启动时（可关）查一次 GitHub 最新版本号，有新版本会在标题栏下面出现一条提示，
  点「去下载」跳转 Release 页。

## 隐私与边界

这是个人自用工具，下面几条是硬约束，代码里就是这么写的：

- **只读自己电脑上、自己本来就有权查看的对话。** 不代替任何人查看别人的聊天。
- **只截自己的微信窗口 + 本地离线 OCR（RapidOCR）。** 不 hook、不注入、不读微信数据库、不解密、
  不碰微信进程内存。
- **截图只在内存里。** 捕获到的帧是 numpy 数组，全程不写磁盘、不进日志、不上传，程序里没有 `.save()`。
- **自动发送默认关闭。** 只有用户显式打开主界面开关才会在 3 秒倒计时后按 Enter；JEV 复审未通过时强制禁止自动发送。
- **不碰钱。** 转账、红包、收款相关的界面元素一律不碰，起草的 system prompt 里也禁了这几个话题。
- **只有对方的新消息到来（或你在群里换了回复对象）才调一次模型。** 静默期零调用——十分钟没人说话
  就是十分钟零 token。
- **API key 只进环境变量。** `DEEPSEEK_API_KEY` 和可选的 `TYPESAFE_API_KEY`
  都写进注册表 `HKCU\Environment`（跟 `setx` 同一个地方），任何文件里都不出现 key，也绝不进日志
  （报错文本一律脱敏）。
- **启动时查一次版本号（可关）。** 只向 GitHub Releases API 发一个 GET，带的只有 UA 和当前版本号，
  不夹带任何聊天内容；设置里「启动时检查更新」关掉就完全不发这个请求，源码直接跑（没有版本号）也
  不会发。

什么会出网：DeepSeek 起草、TypeSafe JEV 预判与复审，加上启动时（可关）一次到 GitHub 查版本号。
`core/` 送出去的是**最近 N 条对话文本**（N = 设置里的「参考上下文」，默认 10；群聊带发言人名）、
**关系设置**、**你自己最近 12 条 60 字以内的短消息**（当口吻样本，链接和长段不送）、**你填的说话
风格**，群聊指定了回复对象的话再加一个对象名。除此之外没有别的。OCR 全程离线。

## 工作原理

```
WGC 截微信窗口（GPU 合成窗口也能截，被遮挡也能截）
  → 像素锚点定位消息区（认底色和分隔线，不写死坐标，深浅主题通用）
  → OCR 面板头部的会话名当 key（头部像素没变就不重跑），记录、上下文、候选都按会话分开存
  → RapidOCR 只认消息区那一块
  → 按气泡颜色分 me / her，灰字（引用块、时间戳、群里的发言人名、链接卡片）过滤掉，
    发言人名摘出来挂到它下面那条消息上
  → 跟上一帧比，滚动翻出来的旧消息不重复上报
  → 冒出新的 her 消息才调 core.engine.analyze()
  → TypeSafe JEV 预判 → DeepSeek 按判断生成 → TypeSafe 复审排序
  → 全部不合格则重写一次；仍不合格只展示并禁止自动发送
  → 悬浮窗给判断摘要 + 3 条候选 → 点「填入微信」
```

截图和 OCR 跑在独立子进程里（一帧 OCR 250~800ms，放 Qt 主线程界面会僵），父进程只管界面和网络调用。

### 模型

| 环节 | 服务 | 模型 | key |
| --- | --- | --- | --- |
| 意图、风险、行动预判 | TypeSafe 官方 System One | `jev-latest` | `TYPESAFE_API_KEY` |
| 起草 3 条候选 | DeepSeek 官方 | `deepseek-flash` | `DEEPSEEK_API_KEY` |
| 质量复审 + 排序 | TypeSafe 官方 System One | `jev-latest` | `TYPESAFE_API_KEY` |

开启 JEV 后，第一次判断的结构化结果会直接交给 DeepSeek 约束生成；生成后再由 JEV 做质量门禁和排序。
全部候选不合格时按 JEV 给出的主要问题重写一次。温度 0.6，`max_tokens` 400；思考模式默认关，开了会带上思考开关、`max_tokens` 提到 4000（DeepSeek 把
思考过程也算进去，400 会把答案截断）。模型只给出 1~2 条时会带着它的回答追问一次补齐，还不够就按实际
条数走（少于 2 条就不排序）。

### 为什么走 OCR

微信 Windows 4.x（进程 `Weixin.exe`，窗口类 `Qt51514QWindowIcon`）界面自绘在一块 GPU 合成画布上
（`MMUIRenderSubWindowHW`）。UIA 树只有 2 个节点、**没有控件树**——`probe/probe_win.py`、
`probe/probe_win2.py` 实测证伪。

所以唯一干净的非侵入采集路 = 截自己的微信窗口 + 本地 OCR。离线、零 token。

### 为什么起草不那么像 AI

- system prompt 是中文写的反模板规则：不总结不复述、不解释自己为什么这么回、不用「首先/其次/总之」和
  「亲/您/加油哦」这类客套、不排比不凑三段式、句尾别习惯性加句号、允许不完整的句子和口头语、
  三条不是「温暖版/负责版/行动版」而是同一个人三个心情下随手打的（其中一条可以只有几个字）。
- 喂口吻样本：把你自己最近 12 条短消息原样给它，照着你的用词、句长、标点习惯写；设置里的
  「说话风格」再补一句你自己的描述。
- 收尾还做了清洗：剥掉编号、方括号、引号和照抄的「me:」前缀，去掉句尾句号（`？！～` 留着，那是语气）。

## 环境要求

下载 exe 的只看前三条；Python 只有源码运行 / 自己打包才需要。

- **Windows 10 1903+ 或 Windows 11**（Windows Graphics Capture 的最低要求）
- **Python 3.10+**（Releases 里的 exe 是 CI 用 3.11 打的；只想用 exe 的话不用装 Python）
- **微信 Windows 4.x**（`Weixin.exe`）
- **DeepSeek 官方 API key**（[platform.deepseek.com](https://platform.deepseek.com/)）
- **TypeSafe 官方 API key**（可选；开启 JEV 全链路优化时需要）

> Win10 上 WGC 会在微信窗口外画一圈黄框，系统不给关；Win11 才能关掉。
> 嫌碍眼就把标题栏的采集开关拨到「已暂停」，黄框立刻消失。

## 源码运行（开发者）

普通使用请直接用上面的[下载即用](#下载即用推荐)。想改代码、调 prompt、自己打包才需要这一节。

```bash
git clone https://github.com/Aimark-dai/jev-chat-windows-deepseek-jev.git
cd jev-chat-windows-deepseek-jev
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

PyCharm / VS Code 里直接 Run `main.py` 也行。

首次启动会自动弹出设置页：填 DeepSeek 官方 API key，可选开启 TypeSafe JEV，再选你们的关系。
key 写进注册表 `HKCU\Environment`，重启后依然有效，不落任何文件；其余设置写进项目根的 `config.json`
（已在 `.gitignore` 里）。

### 自己打包

双击 `build.bat`（没有 `.venv` 会自己建一个，装依赖、调 PyInstaller，一路到底），或者手动：

```bash
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean jev.spec
```

出来的是 `dist\jev-chat-windows\`，整个文件夹就是成品（onedir：onefile 有 150MB 要每次启动解压）。
推一个 `v*` tag，`.github/workflows/release.yml` 会在 `windows-latest` 上打好、压成 zip 挂到 Release 上；
手动触发（workflow_dispatch）只出 artifact，方便试打包。

## 设置说明

改完点「保存设置」，下一次生成立即生效，不用重启。

| 控件 | 作用 | 存在哪 |
| --- | --- | --- |
| 你们的关系 | 恋人/朋友/同事/家人/自定义，起草和判断都按它把握称呼和分寸 | `config.json` → `relationship`（默认 `romantic partners`） |
| 说话风格（可选） | 一句话描述自己的口吻，只喂给起草；留空就只靠最近消息模仿 | `config.json` → `style` |
| 参考上下文 | 起草和判断各看最近多少条消息，3~30 | `config.json` → `context`（默认 10） |
| 群聊指定回复对象 | 开了群聊里才有「回复对象」那一行，候选针对 TA 写 | `config.json` → `reply_target`（默认关） |
| DeepSeek API 密钥 | 生成 3 条候选；关闭 JEV 时也负责判断排序 | 注册表 `HKCU\Environment` → `DEEPSEEK_API_KEY` |
| TypeSafe JEV 全链路优化 | 先预判、再指导生成、最后复审排序 | `config.json` → `judge_provider`（默认 `deepseek`） |
| TypeSafe API 密钥 | 仅在开启 JEV 全链路优化时需要 | 注册表 `HKCU\Environment` → `TYPESAFE_API_KEY` |
| 起草时开启思考模式 | 开了模型先想再写，慢好几倍、贵一些 | `config.json` → `thinking`（默认关） |
| 3秒自动发送 | 显式开启后才自动发送；JEV 复审不通过时强制禁用 | `config.json` → `auto_send`（默认关） |
| 启动时检查更新 | 开了才在启动时查一次 GitHub 最新版本号，有新版本就在标题栏下面提示 | `config.json` → `check_update`（默认开） |

主界面上那几个（标题栏的采集开关、「当前会话」和「回复对象」下拉、「填入时带 @」勾选框）只在内存里，
不落盘，重启回默认。

## 界面说明

- **当前会话**：顶部下拉框，自动跟着微信走（右边标「跟随微信」）。聊天记录、喂给模型的上下文和候选
  都按会话分开，切来切去不串味。也可以自己选另一个会话翻它的记录和上次的建议（标「浏览中」）——
  那会儿只能看不能填，微信当前开着的不是它，填进去就串会话了；微信一切会话，界面自己跟回去。
- **回复对象（群聊，可选）**：设置里打开「群聊指定回复对象」，群聊的「当前会话」下面会多一行下拉框，
  选回复给谁，三条候选就都按 TA 来写（换一个人会立刻重生成）。旁边的「填入时带 @」默认勾着，填入时会
  在开头加「@名字 」——那只是普通文字，微信不会认成真正的 @（真 @ 得用微信自己的选人面板）。
  开关关着就是普通回复，没有这一行，也不加 @。
- **采集开关**：标题栏右上角。拨到「已暂停」就完全不读微信（WGC 会话一起停掉，黄框也没了），
  已经生成的候选照样能填入、能复制。
- **填入微信**：点候选卡片上的「填入微信」，文字进微信输入框，光标留在那儿，**发送你自己按**。
- **复制**：卡片右上角的复制按钮，想手动粘到别处就用它。
- **聊天记录**：底部按钮展开，看 OCR 到底读出了什么，认错了一眼就能发现。

几个注意：

- **微信别最小化。** Windows 不渲染最小化窗口，什么截图法都拿不到画面。程序发现被最小化会无激活还原
  再压到最底下（不抢焦点），但直接用别的窗口盖住微信是更省心的做法——被遮挡不影响 WGC。
- **群聊和单聊各算一个会话**（群名后面的成员数「(422)」会去掉，只拿名字当 key）。
- **判断题的口径是按一对一写的**，群里多人混说时结论会偏。

## 项目结构

```
main.py                 入口：父进程只管界面，子进程采集，队列传消息（IDE 直接 Run）
app/                    UI + 采集层
  capture.py            找微信窗口 + WGC 盯帧 + 像素锚点定位消息区；帧全程内存
  ocr.py                RapidOCR 读消息区 → 按颜色分 me/her/灰字 → 滚动去重；另读头部的会话名
  worker.py             采集子进程主循环（截图 → 定位 → OCR → 去重 → 丢队列）
  fill.py               填入与显式授权后的发送：写剪贴板 → 点输入框 → Ctrl+V；发送前有独立门禁
  overlay.py            置顶悬浮窗：会话/回复对象、判断摘要、3 条候选、聊天记录、设置页（PySide6 + Fluent）
  settings.py           两个 key 只进注册表，其余设置落 config.json
core/                   Jev 判断内核，平台无关，跟安卓原版同一套口径
  engine.py             唯一入口：JEV 预判 → DeepSeek 生成 → JEV 复审/限次重写
  jev_client.py         关闭 TypeSafe 时使用的 DeepSeek 判断客户端
  typesafe_client.py    TypeSafe 官方 System One / JEV 客户端
  questions.py          预判问题、质量门禁、排序问题与状态构造
  draft.py              DeepSeek 官方接口起草 3 条候选
tools/
  demo.py               端到端冒烟：拿一段写死的对话跑完整链（需 key + 联网）
  preview_ui.py         用合成数据预览界面，不采集不联网不碰微信；可 --screenshot 出图
  make_icon.py          生成 docs/icon.ico（打包图标），图标已提交，换颜色才用重跑
probe/                  一次性探针，结论已写进本文，留着是为了可复现
  probe_win.py          UIA 能不能读微信聊天文字 → 证伪（树是空的）
  probe_win2.py         UIA 证伪 v2：分清「树是空的」和「有树没文字」，顺带试 LegacyIAccessible
  probe_notify.py       微信来消息走不走 Windows 通知平台（能监听到就零 OCR）
  probe_ocr.py          OCR 读不读得准中文气泡、左右说话人分不分得开
  probe_ocr_speed.py    RapidOCR 一帧多久、裁小能快多少（结论：det_limit_type 必须 'max'）
  probe_ocr_live.py     WGC 持续盯窗口 + 变了就 OCR，新文字实时打控制台
  probe_printwindow.py  试 PrintWindow + PW_RENDERFULLCONTENT 能不能绕开 Win10 黄框（未验证）
jev.spec                PyInstaller 打包定义（onedir），build.bat 和 CI 共用这一份
build.bat               本地一键打包（双击就行）
.github/workflows/release.yml  推 v* tag → windows-latest 上打包 → zip 挂到 Release
requirements.txt        依赖（纯 ASCII 注释：中文 Windows 上 pip 按 GBK 读会炸）
docs/KICKOFF.md         最初的需求和硬约束说明
docs/icon.ico           程序图标，tools/make_icon.py 生成
docs/ui_*.png           README 里那三张截图，tools/preview_ui.py --screenshot 出的
config.json             你自己的设置，不进仓库（在 .gitignore 里）
```

`tools/` 和 `probe/` 里的脚本都按「项目根在 `PYTHONPATH` 里」写（PyCharm 默认会把内容根加进去）。
命令行跑 `tools/demo.py` 得自己带上：`set PYTHONPATH=. && python tools/demo.py`。
代码里没有 `sys.path` 补丁。

## 已知限制 / 路线图

- **Win10 黄框**：WGC 的采集提示框，系统不给关，Win11 才行。`probe/probe_printwindow.py` 是
  PrintWindow + `PW_RENDERFULLCONTENT` 的替代方案探针，**还没在微信 4.x 上验证过**，能出图就能换掉 WGC。
- **输入框拉高超过面板一半会认错消息区**：消息区靠「面板 45% 高度以下第一根分隔线」定位，
  输入框拉太高就会把它当成消息区底线。
- **OCR 的「文字必须落在平底色上」规则只对精确像素的帧成立**：框里众数颜色占比低于 45% 就当成图片里的
  字扔掉（头像、照片、表情包上的字）。缩放或压缩过的图（比如拿预览窗再截一次）底色会糊成几百种颜色，
  整屏都会被当成图片。
- **群聊里名字行被 OCR 漏识，这条消息会挂到上一个人头上**；「填入时带 @」加的 `@名字 ` 也只是纯文本，
  微信不会把它变成真正的 @ 提醒——真 @ 得走微信自己的选人面板，本工具不模拟那套按键。
- **会话靠头部标题认**：OCR 抖一个字会按相似度归到已知会话（不然一抖就多出一个会话），
  代价是名字只差一个字的两个会话会被并成一个。头部一直认不出就先挂在「当前会话」名下。
- **同一人连发两句一模一样的会吞一条**：去重按文本相似度做的。对「要不要触发分析」没影响。
- **`fill` 靠点击输入框坐标**：算的是消息区底线下方 40px、左边界右侧 60px，微信改布局就得跟着调。
- **没有托盘**：关窗口就是退出（标题栏的「最小化」是收到任务栏，不是后台常驻）。

## 更新记录

**v0.1.3**
- 起草去 AI 味：中文反模板 system prompt、拿自己最近的消息当口吻样本、可选「说话风格」设置、
  温度 1.2、去句尾句号、剥掉照抄的「me:」前缀
- 显式关掉 V4.1 Flash 默认开着的思考模式（`max_tokens` 400），设置里另给一个「起草时开启思考模式」
  开关，开了提到 4000
- OCR：文字必须落在平底色上，头像/照片/表情包里的字直接丢
- 候选解析修复：一行一个 `["…"]`、逗号连着的多个数组、带编号的 JSON 行都能剥干净

**v0.1.2**
- 按会话拆分：头部会话名当 key，每个会话独立去重/记录/上下文/候选；悬浮窗「当前会话」跟随微信、
  也能浏览其他会话
- 群聊：发言人名进模型上下文；可选「群聊指定回复对象」——选回复给谁、候选针对 TA、填入可带 @
- 悬浮窗响应式：最小 320×360，窄于 400 进紧凑模式
- 起草模型升到 DeepSeek V4.1 Flash；模型只给 1~2 条时追问补齐，仍不足按实际条数走

**v0.1.1**
- 起草可选 DeepSeek 直连，设置页加「起草模型来源」和 DeepSeek key（同样只进注册表）
- Jev 判断和排序仍旧只走 OpenRouter

**v0.1.0**
- 首个发布版：窗口截图 + 本地 OCR + Jev 判断 + 悬浮窗 3 条候选 + 填入不发送
- 候选卡片显示 Jev 概率百分比并按概率排序
- 设置里加「参考上下文」条数（3~30，默认 10）；key 直接读写注册表 `HKCU\Environment`
- PyInstaller onedir 打包（`jev.spec` + `build.bat`）+ 推 `v*` tag 自动出 Release

## 致谢

- [Finderchangchang/jev-chat-JARVIS](https://github.com/Finderchangchang/jev-chat-JARVIS) — 安卓原版，
  Jev 判断内核和题目口径都来自这里
- [RapidOCR](https://github.com/RapidAI/RapidOCR) — 离线中文 OCR
- [windows-capture](https://github.com/NiiightmareXD/windows-capture) — Windows Graphics Capture 的 Python 绑定
- [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) — 界面组件

## License

MIT，见 [LICENSE](LICENSE)。
