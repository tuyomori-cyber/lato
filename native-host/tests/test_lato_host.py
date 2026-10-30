import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "lato_host.py"
SPEC = importlib.util.spec_from_file_location("lato_host", MODULE_PATH)
lato_host = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lato_host)


class LatoHostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "root"
        self.root.mkdir()
        (self.root / "docs").mkdir()
        (self.root / "docs" / "note.md").write_text("# note\n", encoding="utf-8")
        self.config = Path(self.temp.name) / "config.json"
        self.config.write_text(json.dumps({"version": 1, "root_path": str(self.root)}), encoding="utf-8")
        self.config.chmod(0o600)
        self.original_config_path = lato_host.config_path
        lato_host.config_path = lambda: self.config

    def tearDown(self):
        lato_host.config_path = self.original_config_path
        self.temp.cleanup()

    def test_lists_directories_and_markdown_only(self):
        (self.root / "ignore.txt").write_text("ignore", encoding="utf-8")
        result = lato_host.process({"version": 1, "request_id": "1", "operation": "list_directory", "relative_path": ""})
        self.assertEqual(result["result"]["entries"], [{"name": "docs", "kind": "directory"}])

    def test_reads_utf8_markdown_and_returns_paths(self):
        result = lato_host.process({"version": 1, "request_id": "2", "operation": "read_markdown", "relative_path": "docs/note.md"})
        self.assertEqual(result["result"]["content"], "# note\n")
        self.assertEqual(result["result"]["path_info"]["file_name"], "note.md")

    def test_rejects_parent_traversal(self):
        with self.assertRaises(lato_host.HostError) as error:
            lato_host.process({"version": 1, "request_id": "3", "operation": "read_markdown", "relative_path": "../outside.md"})
        self.assertEqual(error.exception.code, "INVALID_PATH")

    def test_rejects_symlinks(self):
        outside = Path(self.temp.name) / "outside.md"
        outside.write_text("outside", encoding="utf-8")
        (self.root / "link.md").symlink_to(outside)
        with self.assertRaises(lato_host.HostError) as error:
            lato_host.process({"version": 1, "request_id": "4", "operation": "read_markdown", "relative_path": "link.md"})
        self.assertEqual(error.exception.code, "SYMLINK_NOT_ALLOWED")

    def test_rejects_markdown_larger_than_512_kib(self):
        (self.root / "large.md").write_bytes(b"a" * (512 * 1024 + 1))
        with self.assertRaises(lato_host.HostError) as error:
            lato_host.process({"version": 1, "request_id": "5", "operation": "read_markdown", "relative_path": "large.md"})
        self.assertEqual(error.exception.code, "FILE_TOO_LARGE")
