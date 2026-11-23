import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "trash.py"
spec = importlib.util.spec_from_file_location("skill_trash", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TrashTests(unittest.TestCase):
    def setUp(self):
        # All test files stay inside the skill's gitignored storage.
        module.STORE.mkdir(mode=0o700, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix=".test-", dir=module.STORE)
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.trash = module.Trash(self.base / "store")

    def put(self, path):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.trash.put([path])
        return json.loads(output.getvalue())["id"]

    def restore(self, entry_id, target=None):
        with contextlib.redirect_stdout(io.StringIO()):
            self.trash.restore(entry_id, target)

    def test_file_roundtrip(self):
        source = self.base / "file with spaces.txt"
        source.write_text("test data")
        entry_id = self.put(source)
        self.assertFalse(source.exists())
        self.assertRegex(entry_id, r"^\d{8}-[0-9a-f]{32}$")
        self.restore(entry_id)
        self.assertEqual(source.read_text(), "test data")
        self.assertEqual(self.trash.load(self.trash.entry(entry_id))["state"], "restored")

    def test_directory_roundtrip(self):
        source = self.base / "folder"
        source.mkdir()
        (source / "child").write_text("child data")
        entry_id = self.put(source)
        self.restore(entry_id)
        self.assertEqual((source / "child").read_text(), "child data")

    def test_dangling_symlink_roundtrip(self):
        source = self.base / "link"
        source.symlink_to("missing-target")
        entry_id = self.put(source)
        self.restore(entry_id)
        self.assertTrue(source.is_symlink())
        self.assertEqual(os.readlink(source), "missing-target")

    def test_collision_and_alternate_destination(self):
        source = self.base / "source"
        source.write_text("original")
        entry_id = self.put(source)
        source.write_text("replacement")
        with self.assertRaises(FileExistsError):
            self.restore(entry_id)
        target = self.base / "recovered"
        self.restore(entry_id, target)
        self.assertEqual(source.read_text(), "replacement")
        self.assertEqual(target.read_text(), "original")

    def test_native_move_never_overwrites(self):
        source = self.base / "one"
        target = self.base / "two"
        source.write_text("one")
        target.write_text("two")
        with self.assertRaises(OSError):
            module.rename_exclusive(source, target)
        self.assertEqual(source.read_text(), "one")
        self.assertEqual(target.read_text(), "two")

    def test_recover_prepared_record(self):
        source = self.base / "source"
        source.write_text("data")
        entry_id = self.put(source)
        entry = self.trash.entry(entry_id)
        record = self.trash.load(entry)
        record["state"] = "prepared"
        self.trash.save(entry, record)
        self.restore(entry_id)
        self.assertEqual(source.read_text(), "data")

    def test_failed_move_leaves_source_and_record(self):
        source = self.base / "source"
        source.write_text("data")
        with mock.patch.object(module, "rename_exclusive", side_effect=RuntimeError("test failure")):
            with self.assertRaises(RuntimeError):
                self.trash.put([source])
        self.assertEqual(source.read_text(), "data")
        records = list(self.trash.root.glob("*/record.json"))
        self.assertEqual(json.loads(records[0].read_text())["state"], "move_failed")

    def test_reject_storage_and_ancestor(self):
        with self.assertRaises(ValueError):
            self.trash.put([self.base])
        with self.assertRaises(ValueError):
            self.trash.put([self.trash.root])

    def test_reject_symlink_storage(self):
        real = self.base / "real"
        real.mkdir(mode=0o700)
        self.trash.root.symlink_to(real, target_is_directory=True)
        with self.assertRaises(RuntimeError):
            with self.trash.locked():
                pass

    def test_reject_nested_batch_before_moving(self):
        source = self.base / "folder"
        source.mkdir()
        child = source / "child"
        child.write_text("data")
        with self.assertRaises(ValueError):
            self.trash.put([source, child])
        self.assertTrue(child.exists())

    def test_missing_parent_does_not_create_folders(self):
        source = self.base / "source"
        source.write_text("data")
        entry_id = self.put(source)
        with self.assertRaises(ValueError):
            self.restore(entry_id, self.base / "missing" / "file")
        self.assertFalse((self.base / "missing").exists())

    def test_list_includes_records_and_hides_restored(self):
        source = self.base / "source"
        source.write_text("data")
        entry_id = self.put(source)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.trash.list()
        self.assertTrue(json.loads(output.getvalue())["payload_present"])
        self.restore(entry_id)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.trash.list()
        self.assertEqual(output.getvalue(), "")

    def test_reject_id_traversal(self):
        with self.assertRaises(ValueError):
            self.restore("../../outside")


if __name__ == "__main__":
    unittest.main()
