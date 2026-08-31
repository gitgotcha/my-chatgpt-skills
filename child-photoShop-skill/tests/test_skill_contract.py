"""Contract tests for child-photoShop-skill.

These assert that the skill still says what it must say.  A skill is a
document, and documents rot silently: a well-meaning edit can drop the
identity lock or soften a prohibition without any test failing.  These tests
are the tripwire.
"""

from pathlib import Path
import os
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
REFERENCES = ROOT / "references"
SCRIPTS = ROOT / "scripts"
AGENTS = ROOT / "agents" / "openai.yaml"

EXPECTED_REFERENCES = [
    "style-learning.md",
    "identity-preservation.md",
    "childhood-preservation.md",
    "expression-preservation.md",
    "portrait-retouch-guidelines.md",
    "photo-culling-guidelines.md",
    "background-cleanup.md",
    "color-grading.md",
    "style-camping-child.md",
    "qa-guidelines.md",
    "child-photography-principles.md",
    "open-source-research.md",
]

EXPECTED_SCRIPTS = [
    "style_profile.py",
    "apply_style.py",
    "build_generation_prompt.py",
    "analyze_image.py",
    "image_quality.py",
    "duplicate_detection.py",
    "batch_manifest.py",
    "contact_sheet.py",
]


def frontmatter(text: str):
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, "SKILL.md must start with YAML frontmatter"
    return match.group(1)


class SkillFrontmatterTests(unittest.TestCase):
    def setUp(self):
        self.skill = SKILL.read_text(encoding="utf-8")

    def test_frontmatter_declares_name_and_description(self):
        fm = frontmatter(self.skill)
        self.assertIn("name: child-photoShop-skill", fm)
        self.assertIn("description:", fm)
        self.assertIn("agent_created: true", fm)

    def test_description_covers_the_core_business(self):
        fm = frontmatter(self.skill)
        description = fm.split("description:", 1)[1]
        for term in ("reference", "style", "children", "retouch", "culling"):
            self.assertIn(term, description.lower())

    def test_description_carries_chinese_triggers(self):
        fm = frontmatter(self.skill)
        for trigger in ("儿童摄影", "选片", "精修", "风格参考", "露营风"):
            self.assertIn(trigger, fm)

    def test_skill_body_is_lean_enough_to_load(self):
        # Progressive disclosure: under ~5k words, details live in references.
        words = len(self.skill.split())
        self.assertLess(words, 5000, "SKILL.md is {} words; move detail to references/".format(words))


class SkillContentTests(unittest.TestCase):
    def setUp(self):
        self.skill = SKILL.read_text(encoding="utf-8")

    def test_supremacy_clause_comes_first_and_is_explicit(self):
        for phrase in (
            "保持身份",
            "保持童真",
            "保持表情",
            "保持真实性",
            "提升成片质量",
            "Do not redesign the child",
        ):
            self.assertIn(phrase, self.skill)
        # the ordering must be stated, not implied
        self.assertRegex(self.skill, r"保持身份\s*>\s*保持童真\s*>\s*保持表情")

    def test_facial_reshaping_is_banned_at_every_level(self):
        self.assertIn("恒为 0%", self.skill)
        for banned in ("瘦脸", "大眼", "开眼角", "丰唇", "拉长腿"):
            self.assertIn(banned, self.skill)

    def test_creative_edit_is_separated_from_standard_retouch(self):
        self.assertIn("Creative Edit", self.skill)
        self.assertIn("必须与标准精修", self.skill)

    def test_style_learning_is_a_first_class_workflow(self):
        for phrase in (
            "模板风格学习",
            "学风格，不换脸",
            "style_profile.py",
            "apply_style.py",
            "--strength",
        ):
            self.assertIn(phrase, self.skill)

    def test_reference_roles_are_enumerated(self):
        for role in ("Color reference", "Lighting reference", "Target reference",
                     "Negative reference", "Degree reference"):
            self.assertIn(role, self.skill)

    def test_culling_rules_are_child_specific(self):
        self.assertIn("不强制看镜头", self.skill)
        self.assertIn("表情质量", self.skill)
        self.assertIn("连拍", self.skill)

    def test_prop_protection_is_stated_before_cleanup(self):
        self.assertIn("Is this prop part of the theme?", self.skill)
        self.assertIn("道具保护", self.skill)

    def test_backend_routing_prefers_traditional_editing(self):
        self.assertIn("传统调整", self.skill)
        self.assertIn("Full Regeneration", self.skill)
        self.assertIn("Full Regeneration 不属于标准写真精修", self.skill)

    def test_retry_ladder_ends_at_keeping_the_original(self):
        for step in ("降低编辑强度", "缩小 mask", "切换后端", "回退到传统编辑", "保留原图"):
            self.assertIn(step, self.skill)
        self.assertIn("不得为了", self.skill)

    def test_privacy_rules_are_non_negotiable(self):
        self.assertIn("third-party image processing service", self.skill)
        self.assertIn("local-first", self.skill)
        self.assertIn("永不覆盖原图", self.skill)
        self.assertIn("不得在用户不知情的情况下上传儿童照片", self.skill)

    def test_qa_gate_is_mandatory(self):
        for qa in ("Identity", "Childhood", "Skin", "Artifact", "Theme", "Batch Consistency"):
            self.assertIn(qa, self.skill)
        self.assertIn("每次生成式修改后必须 QA", self.skill)

    def test_scope_exclusions_are_declared(self):
        self.assertIn("何时不使用", self.skill)
        self.assertIn("成人写真", self.skill)


class ResourceTests(unittest.TestCase):
    def test_every_expected_reference_exists_and_has_content(self):
        for name in EXPECTED_REFERENCES:
            path = REFERENCES / name
            with self.subTest(reference=name):
                self.assertTrue(path.is_file(), "missing {}".format(path))
                self.assertGreater(len(path.read_text(encoding="utf-8").strip()), 400)

    def test_every_expected_script_exists(self):
        for name in EXPECTED_SCRIPTS:
            with self.subTest(script=name):
                self.assertTrue((SCRIPTS / name).is_file())

    def test_every_reference_named_in_skill_md_exists(self):
        skill = SKILL.read_text(encoding="utf-8")
        for name in re.findall(r"references/([a-z0-9\-]+\.md)", skill):
            with self.subTest(reference=name):
                self.assertTrue((REFERENCES / name).is_file(), "dangling link: {}".format(name))

    def test_every_script_named_in_skill_md_exists(self):
        skill = SKILL.read_text(encoding="utf-8")
        for name in re.findall(r"scripts/([a-z0-9_]+\.py)", skill):
            with self.subTest(script=name):
                self.assertTrue((SCRIPTS / name).is_file(), "dangling link: {}".format(name))

    def test_openai_interface_file_is_present(self):
        self.assertTrue(AGENTS.is_file())
        text = AGENTS.read_text(encoding="utf-8")
        for field in ("display_name", "short_description", "default_prompt"):
            self.assertIn(field, text)


class IdentityRuleConsistencyTests(unittest.TestCase):
    """The references must not quietly contradict each other."""

    def test_identity_reference_bans_reshaping_and_whitening(self):
        text = (REFERENCES / "identity-preservation.md").read_text(encoding="utf-8")
        self.assertIn("0%", text)
        self.assertIn("不做美白提亮皮肤", text)
        for banned in ("瘦脸", "大眼", "缩鼻翼", "拉长腿"):
            self.assertIn(banned, text)

    def test_childhood_reference_protects_mixed_dentition(self):
        text = (REFERENCES / "childhood-preservation.md").read_text(encoding="utf-8")
        self.assertIn("换牙期", text)
        self.assertIn("15%", text)

    def test_expression_reference_forbids_standardising_smiles(self):
        text = (REFERENCES / "expression-preservation.md").read_text(encoding="utf-8")
        self.assertIn("expression quality", text)
        self.assertIn("强制闭嘴", text)
        self.assertIn("not looking at camera = bad", text)

    def test_culling_reference_makes_eye_contact_a_weak_signal(self):
        text = (REFERENCES / "photo-culling-guidelines.md").read_text(encoding="utf-8")
        self.assertIn("弱评分项", text)
        self.assertIn("60", text)   # child-specific dimensions outweigh technical

    def test_style_learning_reference_forbids_identity_transfer(self):
        text = (REFERENCES / "style-learning.md").read_text(encoding="utf-8")
        self.assertIn("学风格，不换脸", text)
        self.assertIn("脸型、五官比例、眼距", text)
        self.assertIn("拒绝", text)

    def test_open_source_research_records_licences(self):
        text = (REFERENCES / "open-source-research.md").read_text(encoding="utf-8")
        for licence in ("MIT", "Apache-2.0", "无许可证"):
            self.assertIn(licence, text)
        self.assertIn("未复制任何一行外部代码", text)


def _readme_tree():
    """Parse the ASCII directory tree in README.md into a list of paths.

    Returns paths in the order they are drawn, using '/' as the separator.
    Indentation is the only structure the format has, so we track the parent
    by indentation width rather than guessing from the name.
    """
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("child-photoShop-skill/"))
    end = next(i for i, line in enumerate(lines[start:], start) if line.strip() == "```")

    parent_of = {}
    paths = []
    for line in lines[start + 1:end]:
        match = re.match(r"^([│ ]*)(\s*)[├└]── (.+)$", line)
        if not match:
            continue
        indent = len(match.group(1)) + len(match.group(2))
        name = match.group(3).split("  ")[0].strip().rstrip("/")
        parent = parent_of.get(indent - 4, "") if indent >= 4 else ""
        path = "{}/{}".format(parent, name) if parent else name
        parent_of[indent] = path
        paths.append(path)
    return paths


PHOTO_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".tif", ".tiff", ".bmp",
    ".raw", ".cr2", ".cr3", ".nef", ".arw", ".orf", ".rw2", ".dng", ".raf",
    ".pef", ".srw", ".x3f", ".3fr", ".mos", ".mrw", ".erf", ".kdc", ".dcr",
    ".psd", ".psb", ".xcf", ".dcp",
}


class NoPhotographsTests(unittest.TestCase):
    """No photograph may enter this repository, ever.

    The skill works on real children's photographs, and the V2 benchmark needs
    a real set of them. That set has to live somewhere, and the obvious place
    -- a folder next to the code -- is one `git add -A` away from publishing
    photographs of children on a public repo.

    .gitignore makes the accident hard; this makes it loud. It is the same
    argument as the identity lock: do not rely on remembering, make the wrong
    thing impossible to do quietly.
    """

    def test_no_photograph_sits_in_the_skill_directory(self):
        offenders = []
        for dirpath, dirnames, filenames in os.walk(str(ROOT)):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
            for name in filenames:
                if os.path.splitext(name)[1].lower() in PHOTO_EXTENSIONS:
                    offenders.append(os.path.join(dirpath, name))
        self.assertEqual([], offenders, "photographs found: {}".format(offenders))

    def test_no_photograph_is_tracked_by_git(self):
        """.gitignore can be overridden with `git add -f`; tracked files cannot be hidden."""
        repo = ROOT.parent
        try:
            listed = subprocess.run(
                ["git", "ls-files"], cwd=str(repo),
                capture_output=True, text=True, timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            self.skipTest("git unavailable")
        if listed.returncode != 0:
            self.skipTest("not a git working tree")

        offenders = [
            path for path in listed.stdout.splitlines()
            if path.startswith("child-photoShop-skill/")
            and os.path.splitext(path)[1].lower() in PHOTO_EXTENSIONS
        ]
        self.assertEqual([], offenders, "tracked photographs: {}".format(offenders))

    def test_gitignore_declares_the_photo_rules(self):
        rules = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for pattern in ("benchmark/", "*.jpg", "*.dng", "*.dcp"):
            self.assertIn(pattern, rules)


class ReadmeTreeTests(unittest.TestCase):
    """The README tree is documentation too, so it rots the same way.

    It is easy to add a script and forget the tree, or to list it in one
    document and not the other. These tests make the three places agree.
    """

    def test_every_path_drawn_in_the_tree_exists(self):
        for path in _readme_tree():
            with self.subTest(path=path):
                self.assertTrue((ROOT / path.replace("/", os.sep)).exists(), "dangling: " + path)

    def test_tree_lists_every_script(self):
        drawn = {p.rsplit("/", 1)[-1] for p in _readme_tree() if p.startswith("scripts/")}
        self.assertEqual(drawn, set(EXPECTED_SCRIPTS))

    def test_tree_lists_every_reference(self):
        drawn = {p.rsplit("/", 1)[-1] for p in _readme_tree() if p.startswith("references/")}
        self.assertEqual(drawn, set(EXPECTED_REFERENCES))

    def test_script_order_agrees_across_readme_and_skill_md(self):
        """README tree, SKILL.md table and EXPECTED_SCRIPTS must not drift apart."""
        drawn = [p.rsplit("/", 1)[-1] for p in _readme_tree() if p.startswith("scripts/")]
        tabled = re.findall(r"^\| `scripts/([a-z0-9_]+\.py)`", SKILL.read_text(encoding="utf-8"), re.M)
        self.assertEqual(drawn, EXPECTED_SCRIPTS, "README tree order drifted")
        self.assertEqual(tabled, EXPECTED_SCRIPTS, "SKILL.md table order drifted")

    def test_tree_comments_are_aligned(self):
        """A misaligned comment column is the usual symptom of a botched edit."""
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        script_lines = [
            line for line in text.splitlines()
            if re.match(r"^│\s+[├└]── \S+\.py\s{2,}\S", line)
        ]
        self.assertGreaterEqual(len(script_lines), 5)
        columns = {len(line) - len(line.lstrip()) + len(line.lstrip().split("  ")[0])
                   for line in script_lines}
        self.assertEqual(len({c for c in columns if c}), 1, "comment column is ragged")


if __name__ == "__main__":
    unittest.main()
