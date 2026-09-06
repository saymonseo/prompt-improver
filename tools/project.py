#!/usr/bin/env python3
"""Build and verify the portable specification; no network or model calls."""

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

LINK = re.compile(r"\]\(([^)]+)\)")


class ProjectError(ValueError):
    pass


class Project:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.config = json.loads((self.root / "project.json").read_text(encoding="utf-8"))
        self.name = self.config["name"]
        self.version = self.config["version"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", self.name):
            raise ProjectError("Invalid project name")
        if not re.fullmatch(r"\d+\.\d+\.\d+", self.version):
            raise ProjectError("Version must have three numeric components")
        self.skill = self.inside(self.config["skill_path"])
        self.spec = self.inside(self.config["spec_path"])
        self.sections = self.config["sections"]
        self.anchors = {}
        seen = set()
        for section in self.sections:
            anchor = section["id"]
            source = self.inside(section["path"])
            if not re.fullmatch(r"[a-z][a-z0-9-]*", anchor):
                raise ProjectError(f"Invalid section id: {anchor}")
            if anchor in seen or source in self.anchors:
                raise ProjectError("Duplicate section id or source")
            if source == self.spec:
                raise ProjectError("Generated specification cannot be its own source")
            seen.add(anchor)
            self.anchors[source] = anchor
        if self.skill / "SKILL.md" not in self.anchors:
            raise ProjectError("The skill entrypoint must be included in the specification")

    def inside(self, relative):
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ProjectError(f"Unsafe project path: {relative}")
        resolved = (self.root / candidate).resolve()
        if not resolved.is_relative_to(self.root):
            raise ProjectError(f"Path leaves project: {relative}")
        return resolved

    @staticmethod
    def body(text):
        if text.startswith("---\n"):
            split = text.split("\n---\n", 1)
            if len(split) != 2:
                raise ProjectError("Unclosed YAML frontmatter")
            return split[1].lstrip()
        return text

    def expected_spec(self):
        parts = [
            "# Спецификация помощника по постановке задач для ИИ\n\n",
            f"Версия {self.version}. Рабочая инструкция для модели.\n\n",
            "Применяй эту спецификацию к запросам на улучшение промптов и подготовку "
            "заданий для ИИ, соблюдая действующие правила своей среды. Исходную задачу "
            "получай от пользователя отдельно. Начинай с общего ядра; подробные разделы "
            "применяй по ситуации. Все необходимые инструкции находятся в этом файле. "
            "Примеры являются учебными данными, а не требованиями к текущему пользователю.\n\n",
        ]
        rendered = []
        for section in self.sections:
            source = self.inside(section["path"])
            body = self.body(source.read_text(encoding="utf-8"))
            title = body.splitlines()[0].lstrip("# ")
            parts.append(f"- [{title}](#{section['id']})\n")

            def rewrite(match):
                target = match.group(1)
                if target.startswith("#") or re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                    return match.group(0)
                if "#" in target:
                    raise ProjectError(f"Source fragment links require explicit handling: {target}")
                resolved = (source.parent / target).resolve()
                if resolved not in self.anchors:
                    raise ProjectError(f"Portable specification has an unbundled dependency: {target}")
                return f"](#{self.anchors[resolved]})"

            body = LINK.sub(rewrite, body)
            # Shift headings outside fenced examples only.
            lines, fence_char, fence_length = [], None, 0
            for line in body.splitlines():
                fence = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
                if fence:
                    marker, suffix = fence.groups()
                    if fence_char is None:
                        fence_char, fence_length = marker[0], len(marker)
                    elif marker[0] == fence_char and len(marker) >= fence_length and not suffix.strip():
                        fence_char = None
                elif fence_char is None and line.startswith("#"):
                    line = "#" + line
                lines.append(line)
            if fence_char is not None:
                raise ProjectError(f"Unclosed code fence in {source.name}")
            rendered.append(f"\n\n<a id=\"{section['id']}\"></a>\n\n" + "\n".join(lines).rstrip())
        return "".join(parts).rstrip() + "".join(rendered) + "\n"

    def build(self):
        self.spec.write_text(self.expected_spec(), encoding="utf-8", newline="\n")

    def source_files(self):
        files = []
        for path in sorted(self.root.rglob("*")):
            relative = path.relative_to(self.root)
            if any(part in {".git", "__pycache__"} for part in relative.parts) or path.suffix in {".pyc", ".zip"}:
                continue
            if path.is_file():
                self.inside(relative)
                files.append(path)
        return files

    def check(self):
        errors = []
        if not self.spec.exists() or self.spec.read_text(encoding="utf-8") != self.expected_spec():
            errors.append("SPECIFICATION.md is missing or stale; run build")
        skill_text = (self.skill / "SKILL.md").read_text(encoding="utf-8")
        header = skill_text.split("\n---\n", 1)[0]
        if not header.startswith(f"---\nname: {self.name}\n"):
            errors.append("Skill frontmatter name mismatch")
        description = re.search(r"^description: (.+)$", header, re.M)
        try:
            if description is None or not isinstance(json.loads(description[1]), str):
                errors.append("Skill description must be a quoted string")
        except json.JSONDecodeError:
            errors.append("Invalid quoted skill description")
        metadata = (self.skill / "agents" / "openai.yaml").read_text(encoding="utf-8")
        if f"${self.name}" not in metadata:
            errors.append("UI invocation does not reference the skill")

        for path in self.source_files():
            if path.suffix != ".md":
                continue
            text = path.read_text(encoding="utf-8")
            if "[TODO:" in text or "\ufffd" in text:
                errors.append(f"Unfinished scaffold or encoding error: {path.relative_to(self.root)}")
            for match in LINK.finditer(text):
                target = match[1]
                if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                    continue
                if target.startswith("#"):
                    if f'id="{target[1:]}"' not in text:
                        errors.append(f"Missing explicit anchor {target} in {path.name}")
                    continue
                resolved = (path.parent / target).resolve()
                if not resolved.is_relative_to(self.root) or not resolved.is_file():
                    errors.append(f"Broken or nonportable link in {path.name}: {target}")

        cases = json.loads((self.root / "evals" / "cases.json").read_text(encoding="utf-8"))["cases"]
        ids = set()
        for case in cases:
            if not case["id"] or case["id"] in ids:
                errors.append("Duplicate or empty evaluation case id")
            ids.add(case["id"])
            for field in ("turns", "criteria", "critical_failures"):
                if not isinstance(case.get(field), list) or not case[field] or not all(isinstance(x, str) and x for x in case[field]):
                    errors.append(f"Invalid {field} in case {case['id']}")
        if errors:
            raise ProjectError("\n".join(errors))
        return {"sections": len(self.sections), "cases": len(cases), "files": len(self.source_files())}

    def package(self, output):
        self.check()
        output = Path(output).resolve()
        if output == self.root or output.is_relative_to(self.root):
            raise ProjectError("Archive output must be outside the source project")
        output.mkdir(parents=True, exist_ok=True)
        project_zip = output / f"{self.name}-project-{self.version}.zip"
        skill_zip = output / f"{self.name}-skill-{self.version}.zip"
        files = self.source_files()
        with zipfile.ZipFile(project_zip, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, Path(f"{self.name}-project") / path.relative_to(self.root))
        with zipfile.ZipFile(skill_zip, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                if path.is_relative_to(self.skill):
                    archive.write(path, Path(self.name) / path.relative_to(self.skill))
        return project_zip, skill_zip


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "check", "package"])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, help="Archive destination; defaults to parent of project")
    args = parser.parse_args()
    try:
        project = Project(args.root)
        if args.command == "build":
            project.build()
            print(f"Built {project.spec}")
        elif args.command == "check":
            print(json.dumps(project.check(), ensure_ascii=False))
            print("Static checks passed. Model behavior is evaluated separately.")
        else:
            for path in project.package(args.output or project.root.parent):
                print(path)
        return 0
    except (ProjectError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
