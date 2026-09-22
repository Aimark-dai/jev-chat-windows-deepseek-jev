# -*- coding: utf-8 -*-
"""版本号。源码读取最近 Git tag；正式发布时 CI 会用当前 tag 覆盖本文件。"""
from pathlib import Path
import subprocess


def _source_version() -> str:
    """源码运行显示最近发布版本 + dev，避免冒充正式 Release。"""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        tag = result.stdout.strip()
        tag = tag[1:] if tag.startswith("v") else tag
        if tag and all(part.isdigit() for part in tag.split(".")):
            return f"{tag}-dev"
    except (OSError, subprocess.SubprocessError):
        pass
    return "0.0.0-dev"


VERSION = _source_version()
