"""Validation for the system-design AI skill (skills/system-design).

A skill is instructions-as-an-artifact; these checks are its 'compiler':
frontmatter must parse and stay within harness limits, every reference file the
skill points at must exist, and no reference file may be orphaned (unreachable
content silently rots).
"""

import re
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent / "skills" / "system-design"
SKILL_MD = SKILL_DIR / "SKILL.md"


def read_frontmatter() -> dict:
    text = SKILL_MD.read_text()
    match = re.match(r"\A---\n(.*?)\n---\n", text, flags=re.DOTALL)
    assert match, "SKILL.md must start with a YAML frontmatter block"
    fields = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def test_skill_file_exists():
    assert SKILL_MD.exists(), "SKILL.md missing"


def test_frontmatter_name_and_description():
    fields = read_frontmatter()
    # Name: lowercase letters/digits/hyphens, matching the directory name.
    assert re.fullmatch(r"[a-z0-9-]+", fields.get("name", "")), "invalid skill name"
    assert fields["name"] == SKILL_DIR.name, "skill name must match its directory"
    description = fields.get("description", "")
    assert len(description) >= 100, "description too thin to trigger reliably"
    assert len(description) <= 1024, "description exceeds the 1024-char harness limit"
    # The description is the trigger surface: it must say when to use the skill.
    assert "Use when" in description, "description must state when to use the skill"


def test_all_referenced_files_exist():
    body = SKILL_MD.read_text()
    referenced = set(re.findall(r"`(reference/[\w-]+\.md)`", body))
    assert referenced, "SKILL.md should point at its reference files"
    for rel in referenced:
        assert (SKILL_DIR / rel).exists(), f"SKILL.md references missing file {rel}"


def test_no_orphaned_reference_files():
    body = SKILL_MD.read_text()
    for path in (SKILL_DIR / "reference").glob("*.md"):
        rel = f"reference/{path.name}"
        assert rel in body, f"{rel} exists but SKILL.md never tells the model to read it"


def test_reference_files_are_substantial():
    for path in (SKILL_DIR / "reference").glob("*.md"):
        assert len(path.read_text()) > 1_000, f"{path.name} looks like a stub"


def test_no_personal_paths_in_skill():
    # Skills get shared and copied between machines; keep them portable.
    for path in [SKILL_MD, *(SKILL_DIR / "reference").glob("*.md")]:
        text = path.read_text()
        assert "/home/" not in text and "zeno" not in text, \
            f"{path.name} contains a machine-specific path"
