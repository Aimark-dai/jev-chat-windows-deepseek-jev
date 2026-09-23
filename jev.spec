# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包定义，CI（.github/workflows/release.yml）和 build.bat 共用这一份。
onedir 不是 onefile：PySide6 + onnxruntime 打出来 ~150MB，onefile 每次启动都要解压一遍，慢且占临时盘。
Windows 产出 onedir，macOS 产出 .app；两者都必须在各自平台打包。"""
from PyInstaller.utils.hooks import collect_all
from pathlib import Path
import os
import sys

IS_MAC = sys.platform == "darwin"
NAME = "jev-chat-macos" if IS_MAC else "jev-chat-windows"

hiddenimports = [
    # spawn 出来的采集子进程按名字 import app.worker，再顺着它拉 capture/ocr；
    # 父进程这边 engine 也是运行时才走到，一并钉死，别指望静态分析都能扫出来
    "app.worker", "app.capture", "app.capture_macos", "app.ocr", "app.fill",
    "app.fill_macos", "app.overlay", "app.settings",
    "app.version", "app.update",
    "core.engine", "core.draft", "core.jev_client", "core.typesafe_client", "core.questions",
]
datas, binaries = [], []
packages = [
    "rapidocr_onnxruntime",  # .onnx 模型 + config.yaml 是包数据，不收就是启动即炸
    "onnxruntime",           # capi 下面那堆 DLL
    "qfluentwidgets",        # qss / 图标资源
]
packages.append("keyring" if IS_MAC else "windows_capture")
for pkg in packages:
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

excludes = [
    # 确认没人用：rapidocr 只 import 了 cv2 / PIL / yaml / pyclipper / shapely（PIL 千万别排，读图要它）
    "tkinter", "matplotlib", "scipy", "pandas",
] + ["PySide6." + m for m in (
    # 留着 QtCore / QtGui / QtWidgets / QtSvg / QtSvgWidgets / QtXml —— import qfluentwidgets 实测就这六个
    "QtWebEngineCore", "QtWebEngineWidgets", "QtWebEngineQuick", "QtWebChannel",
    "QtMultimedia", "QtMultimediaWidgets", "QtCharts", "QtDataVisualization",
    "QtQuick", "QtQuick3D", "QtQuickControls2", "QtQuickWidgets", "QtQuickTest", "QtQml",
    "QtPdf", "QtPdfWidgets", "QtBluetooth", "QtNfc", "QtSensors", "QtSerialPort",
    "QtTest", "QtDesigner", "QtHelp", "QtRemoteObjects", "QtScxml", "QtStateMachine",
    "QtTextToSpeech", "QtPositioning", "QtLocation", "QtSql",
    "Qt3DCore", "Qt3DRender", "Qt3DInput", "Qt3DLogic", "Qt3DAnimation", "Qt3DExtras",
)]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

# Windows 的 Qt6Core 使用系统 ICU 的未加版本后缀的导出。构建机 PATH 中可能有
# Poppler 等工具自带的 icuuc.dll（导出带 _78 后缀）；PyInstaller 误收后启动即报
# “DLL load failed while importing QtCore”。只排除非 PySide6 自带的 ICU DLL。
def _foreign_icu(binary):
    destination, source, _ = binary
    name = Path(destination).name.lower()
    return (name.startswith(("icuuc", "icudt", "icuin")) and name.endswith(".dll")
            and "pyside6" not in {part.lower() for part in Path(source).parts})


a.binaries = [binary for binary in a.binaries if not _foreign_icu(binary)]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # runner 上本来就没 upx，而且压 Qt / onnxruntime 的 DLL 是出了名的能压坏
    console=False,  # 不要黑框；print 也就跟着没了，状态界面上都有，聊天内容本来就不许落日志
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None if IS_MAC else "docs/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=NAME,
)

if IS_MAC:
    app = BUNDLE(
        coll,
        name="JevChat.app",
        icon=None,
        bundle_identifier="com.aimarkdai.jevchat",
        version=os.environ.get("JEV_BUILD_VERSION", "0.0.0"),
        info_plist={
            "NSPrincipalClass": "NSApplication",
            "NSAppleEventsUsageDescription": "用于在你点击填入时将回复写入微信。",
        },
    )
