#!/usr/bin/env python3
"""Install LATO's per-user Native Messaging Host and fixed root configuration."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HOST_NAME = "org.foxbook.lato"
EXTENSION_ID = "lato@foxbook.local"
SOURCE_HOST = Path(__file__).resolve().parents[1] / "native-host" / "lato_host.py"


def checked_file(path: Path) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"更新先が通常のファイルではありません: {path}")


def staged_file(directory: Path, content: bytes, mode: int) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".lato.", suffix=".tmp", dir=directory)
    path = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path


def validate_firefox(path: Path) -> Path:
    if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError("--firefox には実行可能なFirefoxの絶対パスを指定してください。")
    try:
        result = subprocess.run([str(path), "--version"], text=True, capture_output=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError("Firefoxのバージョンを確認できません。") from error
    if result.returncode != 0 or "Firefox" not in result.stdout + result.stderr:
        raise ValueError("指定された実行ファイルがFirefoxではありません。")
    return path.resolve(strict=True)


def install(root: Path, firefox: Path, home: Path) -> None:
    if not SOURCE_HOST.is_file():
        raise ValueError("インストール元のNative Hostが見つかりません。")
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("--root は既存ディレクトリである必要があります。")
    validate_firefox(firefox)
    host_target = home / ".local" / "share" / "lato" / "lato_host.py"
    config_target = home / ".config" / "lato" / "config.json"
    manifest_target = home / ".mozilla" / "native-messaging-hosts" / f"{HOST_NAME}.json"
    for target in (host_target, config_target, manifest_target):
        checked_file(target)
    compile(SOURCE_HOST.read_bytes(), str(SOURCE_HOST), "exec")
    manifest = {"name": HOST_NAME, "description": "LATO read-only local Markdown host", "path": str(host_target), "type": "stdio", "allowed_extensions": [EXTENSION_ID]}
    config = {"version": 1, "root_path": str(root)}
    staged = []
    try:
        staged.append(staged_file(host_target.parent, SOURCE_HOST.read_bytes(), 0o700))
        staged.append(staged_file(config_target.parent, (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode(), 0o600))
        staged.append(staged_file(manifest_target.parent, (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode(), 0o600))
        for source, target in zip(staged, (host_target, config_target, manifest_target)):
            os.replace(source, target)
    finally:
        for path in staged:
            path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="LATO Native Messaging Hostをユーザー単位で導入します。")
    parser.add_argument("--root", required=True, type=Path, help="LATOで閲覧を許可する既存ディレクトリの絶対パス")
    parser.add_argument("--firefox", required=True, type=Path, help="Firefox実行ファイルの絶対パス")
    args = parser.parse_args()
    try:
        install(args.root, args.firefox, Path.home())
    except (OSError, ValueError) as error:
        print(f"インストール失敗: {error}", file=sys.stderr)
        return 1
    print(f"LATO Native Hostを導入しました。固定ルート: {args.root.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
