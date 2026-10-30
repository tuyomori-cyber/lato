#!/usr/bin/env python3
"""Read-only Native Messaging Host for LATO."""
import json
import os
import struct
import sys
from pathlib import Path

MAX_REQUEST_BYTES = 64 * 1024
MAX_MARKDOWN_BYTES = 512 * 1024
MAX_DIRECTORY_ENTRIES = 1000


class HostError(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message


def config_path():
    return Path.home() / ".config" / "lato" / "config.json"


def load_root():
    path = config_path()
    try:
        stat = path.stat()
        if stat.st_mode & 0o022:
            raise HostError("READ_FAILED", "Host configuration must not be group/world writable")
        data = json.loads(path.read_text(encoding="utf-8"))
        root = Path(data["root_path"])
        if not root.is_absolute() or not root.is_dir():
            raise ValueError("root_path must be an existing absolute directory")
        return root.resolve(strict=True)
    except HostError:
        raise
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        raise HostError("READ_FAILED", f"Invalid Host configuration: {error}") from error


def relative_path(value, allow_root=False):
    if not isinstance(value, str) or "\0" in value or "\\" in value:
        raise HostError("INVALID_PATH", "relative_path is invalid")
    if value == "" and allow_root:
        return []
    parts = value.split("/")
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise HostError("INVALID_PATH", "relative_path must be a normal relative path")
    return parts


def target_path(root, value, allow_root=False):
    parts = relative_path(value, allow_root)
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise HostError("SYMLINK_NOT_ALLOWED", "Symbolic links are not supported")
    try:
        resolved = current.resolve(strict=True)
    except FileNotFoundError as error:
        raise HostError("NOT_FOUND", "Path does not exist") from error
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise HostError("OUTSIDE_ROOT", "Path is outside the configured root") from error
    return resolved


def list_directory(root, value):
    directory = target_path(root, value, allow_root=True)
    if not directory.is_dir():
        raise HostError("NOT_A_DIRECTORY", "Path is not a directory")
    entries = []
    try:
        for entry in directory.iterdir():
            if entry.name.startswith(".") or entry.is_symlink():
                continue
            if entry.is_dir():
                entries.append({"name": entry.name, "kind": "directory"})
            elif entry.is_file() and entry.suffix == ".md":
                entries.append({"name": entry.name, "kind": "markdown"})
    except OSError as error:
        raise HostError("READ_FAILED", str(error)) from error
    if len(entries) > MAX_DIRECTORY_ENTRIES:
        raise HostError("DIRECTORY_TOO_LARGE", "Directory has too many visible entries")
    entries.sort(key=lambda item: (item["kind"] != "directory", item["name"].casefold()))
    return {"relative_path": value, "entries": entries}


def read_markdown(root, value):
    path = target_path(root, value)
    if not path.is_file():
        raise HostError("NOT_A_MARKDOWN_FILE", "Path is not a file")
    if path.suffix != ".md":
        raise HostError("NOT_A_MARKDOWN_FILE", "Only .md files can be read")
    try:
        content = path.read_bytes()
    except OSError as error:
        raise HostError("READ_FAILED", str(error)) from error
    if len(content) > MAX_MARKDOWN_BYTES:
        raise HostError("FILE_TOO_LARGE", "Markdown exceeds 512 KiB")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise HostError("INVALID_ENCODING", "Markdown must be UTF-8") from error
    return {"relative_path": value, "content": text, "path_info": {
        "absolute_path": str(path), "parent_absolute_path": str(path.parent), "file_name": path.name,
    }}


def process(request):
    if not isinstance(request, dict) or request.get("version") != 1:
        raise HostError("INVALID_REQUEST", "Unsupported request")
    request_id = request.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        raise HostError("INVALID_REQUEST", "request_id is required")
    root = load_root()
    operation, value = request.get("operation"), request.get("relative_path")
    if operation == "list_directory":
        result = list_directory(root, value)
    elif operation == "read_markdown":
        result = read_markdown(root, value)
    else:
        raise HostError("INVALID_REQUEST", "Unsupported operation")
    return {"ok": True, "request_id": request_id, "result": result}


def read_message():
    length_data = sys.stdin.buffer.read(4)
    if len(length_data) != 4:
        return None
    length = struct.unpack("<I", length_data)[0]
    if length > MAX_REQUEST_BYTES:
        raise HostError("INVALID_REQUEST", "Request exceeds size limit")
    payload = sys.stdin.buffer.read(length)
    if len(payload) != length:
        raise HostError("INVALID_REQUEST", "Incomplete request")
    return json.loads(payload.decode("utf-8"))


def write_message(message):
    payload = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(payload)) + payload)
    sys.stdout.buffer.flush()


def main():
    request_id = None
    try:
        request = read_message()
        if request is None:
            return
        request_id = request.get("request_id") if isinstance(request, dict) else None
        write_message(process(request))
    except HostError as error:
        write_message({"ok": False, "request_id": request_id, "error": {"code": error.code, "message": error.message}})
    except Exception as error:  # Keep protocol failures structured.
        print(f"Unexpected LATO Host error: {error}", file=sys.stderr)
        write_message({"ok": False, "request_id": request_id, "error": {"code": "READ_FAILED", "message": "Unexpected Host error"}})


if __name__ == "__main__":
    main()
