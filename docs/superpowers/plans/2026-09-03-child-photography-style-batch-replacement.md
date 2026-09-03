# Child Photography Style Batch Replacement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `child-photoShop-skill` with a sample-first, identity-locked `child-photography-editing` Skill and publish that replacement through the local `my-chatgpt-skills` plugin.

**Architecture:** The Skill first compiles developer reference images into a `StyleProfile`, then merges only dimension-scoped `ApprovedTreatmentHints` from positively reviewed prior edits. It creates a protected `EditPlan` per source image, compiles background/peripheral-only edit prompts, freezes one `BatchStyleLock`, and admits outputs only after per-image and batch QA.

**Tech Stack:** Markdown Skill instructions, Python 3 standard library, Pillow and NumPy for image analysis, `unittest`, Codex Skill validator, Codex plugin CLI.

**Spec:** `docs/superpowers/specs/2026-09-03-child-photography-style-batch-replacement-design.md`

## Global Constraints

- Visual-edit priority is exactly: person authenticity > current user request > new reference samples > approved treatment methods > default style recipes.
- Never change face, facial features, face/head shape, eye shape or spacing, nose, mouth, ears, hairline, hairstyle, hair amount, body/limb proportions, hands/feet, age, pose, action, or original expression.
- Preserve crying expressions; keep clothing unchanged by default; never remove hair; eyes may receive only subtle refresh and must not be enlarged.
- Standard child-photo editing forbids full-frame regeneration; generation may target only background and peripheral non-person regions.
- Skin brightening is limited to approximately 3%–5%, with subtle natural color only on cheeks, nose tip, ears, hands, and feet; preserve infant texture.
- New reference samples own color, theme, light, background, elements, typography, texture, and overall direction. Approved prior results contribute methods only and may not leak old style values.
- Default output is 3:5 at 1200×2000, originals are never overwritten, and no real child photograph may enter the repository.
- Other repository Skills and their persistence contracts remain behaviorally unchanged.

---

### Task 1: Establish repository replacement and routing contracts

**Files:**
- Create: `tests/test_child_photography_routing_contract.py`
- Modify: `AGENTS.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: repository root layout and Skill-routing text.
- Produces: one canonical directory name, `child-photography-editing`, and routing language used by later packaging checks.

- [ ] **Step 1: Write the failing route and replacement tests**

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_router_describes_sample_first_batch_workflow():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "child-photography-editing/SKILL.md" in text
    for phrase in ("开发者样本", "学习风格", "批量处理", "人物不失真"):
        assert phrase in text
    assert "child-photoShop-skill/SKILL.md" not in text
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m unittest tests.test_child_photography_routing_contract -v`

Expected: FAIL because the new route does not exist.

- [ ] **Step 3: Apply the minimal routing and README rename**

Change the route to:

```markdown
- 儿童摄影创作（开发者样本学风格、背景/主题/元素编辑、批量处理、人物不失真）：`child-photography-editing/SKILL.md`
```

Rename only the README entries and links needed for the new directory and describe the sample-first pipeline. Do not change other Skill descriptions.

- [ ] **Step 4: Re-run the focused tests**

Run: `python -m unittest tests.test_child_photography_routing_contract -v`

Expected: PASS.

- [ ] **Step 5: Commit the contract and route**

```bash
git add tests/test_child_photography_routing_contract.py AGENTS.md README.md
git commit -m "test: define child photography replacement route"
```

---

### Task 2: Create the new Skill entrypoint and reference contract

**Files:**
- Create: `child-photography-editing/SKILL.md`
- Create: `child-photography-editing/agents/openai.yaml`
- Create: `child-photography-editing/references/workflow-contract.md`
- Create: `child-photography-editing/references/identity-preservation.md`
- Create: `child-photography-editing/references/edit-modes.md`
- Create: `child-photography-editing/references/style-recipes.md`
- Create: `child-photography-editing/references/batch-consistency.md`
- Create: `child-photography-editing/references/qa-and-fallback.md`
- Create: `child-photography-editing/references/prompt-templates.md`
- Create: `child-photography-editing/references/style-learning.md`
- Create: `child-photography-editing/tests/test_skill_contract.py`

**Interfaces:**
- Consumes: the design spec and canonical route from Task 1.
- Produces: discoverable Skill instructions, reference routing, hard constraints, and the JSON field names consumed by Tasks 3–6.

- [ ] **Step 1: Write a failing Skill contract**

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"


def test_person_authenticity_hard_lock_is_complete():
    text = SKILL.read_text(encoding="utf-8")
    banned = (
        "换脸", "五官", "脸型", "头型", "眼型", "鼻子", "嘴型", "耳朵",
        "发际线", "发型", "发量", "身体比例", "四肢比例", "手脚结构",
        "年龄感", "姿势", "动作", "原始表情",
    )
    for term in banned:
        assert term in text
    assert "人物真实性 > 用户本次明确要求 > 新参考样本 > 已肯定的处理方法" in text


def test_new_photo_skill_replaces_old_directory():
    assert ROOT.is_dir()
    assert ROOT.name == "child-photography-editing"


def test_core_modes_and_defaults_are_declared():
    text = SKILL.read_text(encoding="utf-8")
    for mode in ("background-only", "skin-only", "crop-only", "theme-edit", "poster-edit", "batch-style-transfer"):
        assert mode in text
    for value in ("3:5", "1200×2000", "3%–5%", "哭泣"):
        assert value in text


def test_references_are_routed_and_exist():
    text = SKILL.read_text(encoding="utf-8")
    for name in (
        "workflow-contract.md", "identity-preservation.md", "style-learning.md",
        "edit-modes.md", "style-recipes.md", "batch-consistency.md",
        "qa-and-fallback.md", "prompt-templates.md",
    ):
        assert f"references/{name}" in text
        assert (ROOT / "references" / name).is_file()
```

- [ ] **Step 2: Run the contract and verify RED**

Run: `python -m unittest child-photography-editing.tests.test_skill_contract -v`

Expected: import/path failure because the replacement does not exist.

- [ ] **Step 3: Write the minimal Skill entrypoint and references**

Use this frontmatter shape:

```yaml
---
name: child-photography-editing
description: Use when children’s photographs need developer-reference style learning, background or theme edits, poster elements, local retouching, or consistent batch processing; triggers include 儿童摄影、参考样本、换背景、批量修图、人物不失真、绿色背景、儿童海报.
---
```

Keep `SKILL.md` as a concise router. Put the exhaustive contracts in references and explicitly require:

```text
analyze references → compile StyleProfile → collect ApprovedTreatmentHints
→ build per-image EditPlan → freeze BatchStyleLock → edit → QA → deliver/fallback
```

Set `agents/openai.yaml` with display name `儿童摄影样本学习与批量创作` and a default prompt that asks the Skill to learn developer samples before editing source images.

- [ ] **Step 4: Verify GREEN and validate the Skill shape**

Run: `python -m unittest child-photography-editing.tests.test_skill_contract tests.test_child_photography_routing_contract -v`

Run: `python C:/Users/27846/.codex/skills/.system/skill-creator/scripts/quick_validate.py child-photography-editing`

Expected: PASS for all checks.

- [ ] **Step 5: Commit the entrypoint and contracts**

```bash
git add child-photography-editing AGENTS.md README.md tests
git commit -m "feat: add sample-first child photography skill"
```

---

### Task 3: Compile new-reference style authority and approved treatment hints

**Files:**
- Create: `child-photography-editing/scripts/style_profile.py`
- Create: `child-photography-editing/tests/fixtures.py`
- Create: `child-photography-editing/tests/test_style_profile.py`

**Interfaces:**
- Consumes: `developerReferences`, observation dictionaries, user overrides, and context-positive feedback mapped to allowed treatment fields.
- Produces: `compile_style_profile(observations, overrides, approved_hints) -> dict` and `validate_approved_hints(hints) -> dict`.

- [ ] **Step 1: Write failing tests for authority and leakage prevention**

```python
from scripts.style_profile import compile_style_profile, validate_approved_hints


def test_new_reference_owns_style_while_old_approval_keeps_method_only():
    profile = compile_style_profile(
        observations={"palette": ["cream", "orange"], "theme": "little-explorers"},
        overrides={},
        approved_hints={"skin": {"brightness_delta_percent": 4}, "elements": {"subject_avoidance": "strict"}},
    )
    assert profile["styleAuthority"]["palette"] == ["cream", "orange"]
    assert profile["styleAuthority"]["theme"] == "little-explorers"
    assert profile["approvedTreatmentHints"]["skin"]["brightness_delta_percent"] == 4


def test_style_bearing_values_are_rejected_from_approved_hints():
    try:
        validate_approved_hints({"background": {"color": "old-green"}})
    except ValueError as exc:
        assert "style-bearing" in str(exc)
    else:
        raise AssertionError("old color leaked through approved hints")
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m unittest child-photography-editing.tests.test_style_profile -v`

Expected: FAIL because `style_profile` does not exist.

- [ ] **Step 3: Implement the allowlisted treatment-hint compiler**

```python
ALLOWED_HINTS = {
    "skin": {"brightness_delta_percent", "texture_preservation", "natural_blush_strength", "eye_refresh"},
    "background": {"edge_cleanliness", "shadow_integration", "depth_quality", "simplicity"},
    "elements": {"density", "scale_balance", "subject_avoidance", "childlike_tone"},
    "layout": {"negative_space_use", "text_safe_zone", "hierarchy"},
}


def validate_approved_hints(hints: dict) -> dict:
    for section, values in hints.items():
        if section not in ALLOWED_HINTS:
            raise ValueError(f"style-bearing section is not allowed: {section}")
        rejected = set(values) - ALLOWED_HINTS[section]
        if rejected:
            raise ValueError(f"style-bearing fields are not allowed: {sorted(rejected)}")
    return hints


def compile_style_profile(observations: dict, overrides: dict, approved_hints: dict) -> dict:
    authority = {**observations, **overrides}
    return {
        "schemaVersion": "1.0",
        "styleAuthority": authority,
        "approvedTreatmentHints": validate_approved_hints(approved_hints),
        "precedence": ["personAuthenticity", "currentRequest", "newReference", "approvedTreatment", "defaultRecipe"],
    }
```

Clamp `brightness_delta_percent` to 3–5 and restrict `eye_refresh` to `none` or `subtle`.

- [ ] **Step 4: Re-run tests and add CLI validation**

Run: `python -m unittest child-photography-editing.tests.test_style_profile -v`

Run: `python child-photography-editing/scripts/style_profile.py --help`

Expected: PASS and exit code 0.

- [ ] **Step 5: Commit the Style Profile compiler**

```bash
git add child-photography-editing/scripts/style_profile.py child-photography-editing/tests
git commit -m "feat: isolate current style from approved treatment hints"
```

---

### Task 4: Build and validate person-protected per-image Edit Plans

**Files:**
- Create: `child-photography-editing/scripts/validate_edit_plan.py`
- Create: `child-photography-editing/tests/test_edit_plan.py`

**Interfaces:**
- Consumes: `build_edit_plan(source_id, mode, pose, expression, output_spec, requested_changes) -> dict`.
- Produces: validated Edit Plans with `protectedRegions`, `allowedRegions`, `crop`, `textSafeZones`, and `forbiddenOperations`.

- [ ] **Step 1: Write failing mode and protection tests**

```python
from scripts.validate_edit_plan import build_edit_plan, validate_edit_plan


def test_crying_background_edit_protects_expression_and_person():
    plan = build_edit_plan("img-1", "background-only", "lying", "crying", {"ratio": "3:5", "width": 1200, "height": 2000}, {})
    assert "entire-person" in plan["protectedRegions"]
    assert "original-expression" in plan["protectedRegions"]
    assert plan["allowedRegions"] == ["background"]
    assert plan["preserveCrying"] is True


def test_full_frame_regeneration_is_rejected():
    plan = {"mode": "full-frame", "protectedRegions": [], "allowedRegions": ["entire-frame"]}
    try:
        validate_edit_plan(plan)
    except ValueError as exc:
        assert "full-frame" in str(exc)
    else:
        raise AssertionError("unsafe plan accepted")
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m unittest child-photography-editing.tests.test_edit_plan -v`

Expected: FAIL because the validator does not exist.

- [ ] **Step 3: Implement plan construction and validation**

```python
MODES = {"background-only", "skin-only", "crop-only", "theme-edit", "poster-edit", "batch-style-transfer"}
IMMUTABLE = [
    "face", "facial-features", "head-shape", "eyes", "nose", "mouth", "ears",
    "hairline", "hair", "body-proportions", "limb-proportions", "hands-feet",
    "age", "pose", "action", "original-expression",
]


def validate_edit_plan(plan: dict) -> dict:
    if plan.get("mode") not in MODES:
        raise ValueError(f"full-frame or unknown mode is forbidden: {plan.get('mode')}")
    if not set(IMMUTABLE).issubset(set(plan.get("forbiddenOperations", []))):
        raise ValueError("person authenticity lock is incomplete")
    return plan
```

Mode-specific allowed regions must be exact: background-only → background; skin-only → skin tone adjustments; crop-only → crop canvas; theme/poster/batch → background plus peripheral elements and safe text zones.

- [ ] **Step 4: Verify GREEN**

Run: `python -m unittest child-photography-editing.tests.test_edit_plan -v`

Expected: PASS.

- [ ] **Step 5: Commit Edit Plan validation**

```bash
git add child-photography-editing/scripts/validate_edit_plan.py child-photography-editing/tests/test_edit_plan.py
git commit -m "feat: validate identity-locked edit plans"
```

---

### Task 5: Compile safe generation prompts without old-style leakage

**Files:**
- Create: `child-photography-editing/scripts/build_generation_prompt.py`
- Create: `child-photography-editing/tests/test_generation_prompt.py`

**Interfaces:**
- Consumes: `build_prompt(profile: dict, plan: dict) -> dict` using Task 3 and Task 4 contracts.
- Produces: `{instruction, negativeConstraints, maskPolicy, outputSpec}` for an image editing backend.

- [ ] **Step 1: Write failing prompt invariants**

```python
from scripts.build_generation_prompt import build_prompt


def test_prompt_uses_new_palette_and_methods_but_never_old_style():
    profile = {
        "styleAuthority": {"palette": ["cream", "orange"], "theme": "little-explorers"},
        "approvedTreatmentHints": {"background": {"edge_cleanliness": "high"}},
    }
    plan = {"mode": "background-only", "allowedRegions": ["background"], "outputSpec": {"ratio": "3:5", "width": 1200, "height": 2000}}
    prompt = build_prompt(profile, plan)
    assert "cream" in prompt["instruction"]
    assert "little-explorers" in prompt["instruction"]
    assert "edge_cleanliness" in prompt["instruction"]
    assert prompt["maskPolicy"] == "background-only"
    assert "full-frame regeneration" in prompt["negativeConstraints"]
```

Add one assertion for every immutable person attribute from the spec and for crying preservation.

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m unittest child-photography-editing.tests.test_generation_prompt -v`

Expected: FAIL because the prompt compiler does not exist.

- [ ] **Step 3: Implement the prompt compiler**

```python
NEGATIVE_CONSTRAINTS = (
    "no face replacement; no changes to facial features, face shape, head shape, eye shape, "
    "eye spacing, nose, mouth shape, ears, hairline, hairstyle, hair amount, body proportions, "
    "limb proportions, hands or feet, age, pose, action, clothing, or original expression; "
    "preserve crying; no full-frame regeneration; do not cover the person with text or elements"
)


def build_prompt(profile: dict, plan: dict) -> dict:
    return {
        "instruction": _serialize_authority_then_methods(profile, plan),
        "negativeConstraints": NEGATIVE_CONSTRAINTS,
        "maskPolicy": plan["mode"] if plan["mode"] in {"background-only", "skin-only", "crop-only"} else "person-protected-periphery",
        "outputSpec": plan["outputSpec"],
    }
```

The serializer must emit `styleAuthority` first and label `approvedTreatmentHints` as execution quality only; it must never infer colors, themes, props, typography, or composition from approved hints.

- [ ] **Step 4: Verify GREEN and CLI behavior**

Run: `python -m unittest child-photography-editing.tests.test_generation_prompt -v`

Run: `python child-photography-editing/scripts/build_generation_prompt.py --help`

Expected: PASS and exit code 0.

- [ ] **Step 5: Commit the prompt compiler**

```bash
git add child-photography-editing/scripts/build_generation_prompt.py child-photography-editing/tests/test_generation_prompt.py
git commit -m "feat: compile person-protected edit prompts"
```

---

### Task 6: Freeze batch style and enforce two-stage QA

**Files:**
- Create: `child-photography-editing/scripts/batch_manifest.py`
- Create: `child-photography-editing/scripts/analyze_image.py`
- Create: `child-photography-editing/tests/test_batch_manifest.py`

**Interfaces:**
- Consumes: `create_manifest(batch_id, batch_lock) -> dict`, `record_item(manifest, item) -> dict`, and `finalize_batch(manifest) -> dict`.
- Produces: stable `batch-manifest.json` state with one approved anchor, per-image QA, batch-consistency QA, and rejected items excluded from `edited/`.

- [ ] **Step 1: Write failing batch-lock and rejection tests**

```python
from scripts.batch_manifest import create_manifest, record_item, finalize_batch


def test_failed_item_cannot_become_anchor_or_enter_edited_outputs():
    manifest = create_manifest("batch-1", {"palette": ["green"], "approvedTreatmentHints": {"elements": {"density": "light"}}})
    record_item(manifest, {"sourceId": "a", "qa": {"identity": "fail"}, "output": "edited/a.png"})
    result = finalize_batch(manifest)
    assert result["anchorSourceId"] is None
    assert result["editedOutputs"] == []
    assert result["items"][0]["status"] == "rejected"


def test_first_passing_item_becomes_immutable_anchor():
    manifest = create_manifest("batch-1", {"palette": ["cream", "orange"]})
    record_item(manifest, {"sourceId": "a", "qa": {"identity": "pass", "artifact": "pass", "style": "pass"}, "output": "edited/a.png"})
    record_item(manifest, {"sourceId": "b", "qa": {"identity": "pass", "artifact": "pass", "style": "pass"}, "output": "edited/b.png"})
    assert finalize_batch(manifest)["anchorSourceId"] == "a"
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m unittest child-photography-editing.tests.test_batch_manifest -v`

Expected: FAIL because the manifest implementation does not exist.

- [ ] **Step 3: Implement immutable lock, anchor, and QA states**

```python
REQUIRED_QA = ("identity", "childhood", "expression", "skin", "artifact", "theme", "batchConsistency")


def item_passes(item: dict) -> bool:
    qa = item.get("qa", {})
    return all(qa.get(key) == "pass" for key in REQUIRED_QA)
```

`record_item` must copy the batch lock rather than mutate it. `finalize_batch` selects the first passing item as anchor, marks all failures `rejected`, and returns only passing paths in `editedOutputs`. `analyze_image.py` reports dimensions, orientation, color space, and file hash without altering the file.

- [ ] **Step 4: Verify GREEN and script help**

Run: `python -m unittest child-photography-editing.tests.test_batch_manifest -v`

Run: `python child-photography-editing/scripts/batch_manifest.py --help`

Run: `python child-photography-editing/scripts/analyze_image.py --help`

Expected: PASS and exit code 0.

- [ ] **Step 5: Commit batch orchestration**

```bash
git add child-photography-editing/scripts child-photography-editing/tests/test_batch_manifest.py
git commit -m "feat: lock batch style and reject unsafe outputs"
```

---

### Task 7: Remove the old Skill and close repository documentation gaps

**Files:**
- Delete: `child-photoShop-skill/`
- Modify: `README.md`
- Modify: `tests/test_child_photography_routing_contract.py`
- Modify: `tests/test_repository_storage_contract.py`
- Modify: any other repository tests that explicitly enumerate `child-photoShop-skill`.

**Interfaces:**
- Consumes: the complete replacement from Tasks 2–6.
- Produces: one child-photography Skill, no stale path, no stale scripts, and no public child-photo fixtures.

- [ ] **Step 1: Extend the failing test to scan every tracked text file for stale routing**

```python
def test_no_stale_child_photoshop_route_remains():
    allowed = {
        "docs/superpowers/specs/2026-09-03-child-photography-style-batch-replacement-design.md",
        "docs/superpowers/plans/2026-09-03-child-photography-style-batch-replacement.md",
    }
    offenders = []
    for path in ROOT.rglob("*"):
        if path.is_file() and ".git" not in path.parts and path.relative_to(ROOT).as_posix() not in allowed:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if "child-photoShop-skill" in text:
                offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_old_skill_directory_is_removed():
    assert not (ROOT / "child-photoShop-skill").exists()
```

- [ ] **Step 2: Run the test and verify RED**

Run: `python -m unittest tests.test_child_photography_routing_contract -v`

Expected: FAIL with the old Skill files and README references listed.

- [ ] **Step 3: Delete the exact old directory and update enumerations**

Before deletion, verify the absolute target ends with `work/my-chatgpt-skills/child-photoShop-skill`. Remove only that directory. Update README trees, `test_repository_storage_contract.py`, and expected file lists to match the new Skill.

- [ ] **Step 4: Run all repository tests and validators**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`

Run: `python -m unittest discover -s child-photography-editing/tests -p "test_*.py" -v`

Run: `python C:/Users/27846/.codex/skills/.system/skill-creator/scripts/quick_validate.py child-photography-editing`

Run: `git diff --check`

Expected: all PASS, no warnings from project code, and no stale route.

- [ ] **Step 5: Commit the removal**

```bash
git add -A child-photoShop-skill child-photography-editing README.md tests AGENTS.md
git commit -m "refactor: replace legacy child photography skill"
```

---

### Task 8: Package, validate, reinstall, and verify the local plugin

**Files:**
- Modify: `C:/Users/27846/plugins/my-chatgpt-skills/.codex-plugin/plugin.json`
- Replace: `C:/Users/27846/plugins/my-chatgpt-skills/skills/child-photoShop-skill/` if present
- Create: `C:/Users/27846/plugins/my-chatgpt-skills/skills/child-photography-editing/`

**Interfaces:**
- Consumes: committed repository Skill source and the existing `personal` marketplace entry.
- Produces: a validated `my-chatgpt-skills@personal` package whose cached installation exposes the new Skill and not the old one.

- [ ] **Step 1: Verify the exact plugin source and marketplace identity**

Run: `python C:/Users/27846/.codex/skills/.system/plugin-creator/scripts/read_marketplace_name.py`

Expected: `personal`.

Run: `codex plugin list`

Expected: `my-chatgpt-skills@personal` points to `C:/Users/27846/plugins/my-chatgpt-skills`.

- [ ] **Step 2: Add a temporary package assertion before copying**

Run this read-only assertion and expect failure before packaging:

```powershell
if (-not (Test-Path -LiteralPath 'C:\Users\27846\plugins\my-chatgpt-skills\skills\child-photography-editing\SKILL.md')) { throw 'new packaged skill missing' }
```

- [ ] **Step 3: Replace only the packaged child photography Skill**

Copy the committed `child-photography-editing/` directory into the plugin source `skills/`. Remove the old packaged child-photo directory only after resolving its exact absolute path beneath `C:/Users/27846/plugins/my-chatgpt-skills/skills/`. Preserve every unrelated packaged Skill.

Update plugin interface text to mention developer-sample style learning and identity-safe batch child-photo editing. Add a default prompt equivalent to:

```text
读取我提供的开发者参考样本，先学习当前风格，再在人物真实性绝对优先的前提下批量处理这些儿童照片。
```

- [ ] **Step 4: Validate and update the cachebuster**

Run: `python C:/Users/27846/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py C:/Users/27846/plugins/my-chatgpt-skills`

Run: `python C:/Users/27846/.codex/skills/.system/plugin-creator/scripts/update_plugin_cachebuster.py C:/Users/27846/plugins/my-chatgpt-skills`

Expected: validation PASS and exactly one `+codex.<timestamp>` suffix.

- [ ] **Step 5: Reinstall from the existing personal marketplace**

Run: `codex plugin add my-chatgpt-skills@personal`

Expected: installed and enabled with the new cachebuster version.

- [ ] **Step 6: Verify installed cache contents and routes**

Resolve the installed version using `codex plugin list`, then assert:

```text
skills/child-photography-editing/SKILL.md exists
skills/child-photoShop-skill does not exist
the new SKILL frontmatter contains name: child-photography-editing
the plugin default prompt mentions developer samples and batch processing
```

Run the new Skill tests from the installed cache and verify all pass.

- [ ] **Step 7: Final repository verification**

Run: `python -m unittest discover -s . -p "test_*.py" -v`

Run: `git status --short`

Run: `git log --oneline -8`

Expected: all tests PASS; repository changes are committed; only intentional local plugin packaging differs outside Git.

Start a new Codex task for the final discovery smoke test because Skill routing is loaded at task creation. Confirm a prompt mentioning developer reference samples, green-background batch editing, or identity-safe child posters selects `child-photography-editing`, while unrelated adult-photo editing does not.
