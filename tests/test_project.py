"""Behavior of the build pipeline, not language-model quality."""

import importlib.util
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = importlib.util.spec_from_file_location("project_tools", ROOT / "tools" / "project.py")
project_tools = importlib.util.module_from_spec(MODULE)
MODULE.loader.exec_module(project_tools)


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="prompt-improver-test-")
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "project"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "*.zip"))
        self.project = project_tools.Project(self.root)
        self.project.build()

    def tearDown(self):
        # Only the dedicated TemporaryDirectory and its children are removed.
        self.temp.cleanup()

    def test_portable_spec_has_no_external_file_dependencies(self):
        text = self.project.spec.read_text(encoding="utf-8")
        for match in project_tools.LINK.finditer(text):
            self.assertTrue(match[1].startswith("#"), match[1])
        self.assertNotIn(str(ROOT), text)
        self.project.check()

    def test_edit_requires_rebuild_and_is_preserved(self):
        source = self.project.skill / "references" / "interview.md"
        source.write_text(source.read_text(encoding="utf-8") + "\nНовая проверяемая поправка.\n", encoding="utf-8")
        with self.assertRaisesRegex(project_tools.ProjectError, "stale"):
            self.project.check()
        self.project.build()
        self.project.check()
        self.assertIn("Новая проверяемая поправка.", self.project.spec.read_text(encoding="utf-8"))

    def test_unbundled_reference_is_rejected(self):
        source = self.project.skill / "references" / "interview.md"
        source.write_text(source.read_text(encoding="utf-8") + "\n[Скрытая зависимость](missing.md)\n", encoding="utf-8")
        with self.assertRaisesRegex(project_tools.ProjectError, "unbundled"):
            self.project.build()

    def test_manifest_cannot_read_outside_project(self):
        config = self.project.config
        config["sections"][0]["path"] = "../private.md"
        (self.root / "project.json").write_text(json.dumps(config), encoding="utf-8")
        with self.assertRaisesRegex(project_tools.ProjectError, "Unsafe"):
            project_tools.Project(self.root)

    def test_archives_have_portable_roots_and_no_test_cache(self):
        cache = self.root / "tests" / "__pycache__"
        cache.mkdir(exist_ok=True)
        (cache / "ignore.pyc").write_bytes(b"test")
        git_data = self.root / ".git"
        git_data.mkdir()
        (git_data / "config").write_text("repository metadata must stay local", encoding="utf-8")
        project_zip, skill_zip = self.project.package(self.base / "archives")
        with zipfile.ZipFile(project_zip) as archive:
            names = archive.namelist()
            self.assertIn("prompt-improver-project/SPECIFICATION.md", names)
            self.assertFalse(any("__pycache__" in name for name in names))
            self.assertFalse(any(".git" in Path(name).parts for name in names))
            archive.extractall(self.base / "extracted")
        # Relocation must preserve all local links and generation rules.
        relocated = project_tools.Project(self.base / "extracted" / "prompt-improver-project")
        relocated.check()
        with zipfile.ZipFile(skill_zip) as archive:
            names = archive.namelist()
            self.assertIn("prompt-improver/SKILL.md", names)
            self.assertTrue(all(name.startswith("prompt-improver/") for name in names))
            self.assertFalse(any("evals/" in name or "tests/" in name for name in names))

    def test_duplicate_evaluation_ids_are_rejected(self):
        path = self.root / "evals" / "cases.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["cases"].append(data["cases"][0])
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(project_tools.ProjectError, "Duplicate"):
            self.project.check()


if __name__ == "__main__":
    unittest.main()
