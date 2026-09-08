from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReviewModelRoutingRouterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        cls.active = cls.router.split("## Persistence contract", 1)[0]

    def test_router_keeps_exactly_one_workflow_rule(self):
        self.assertIn("Read exactly one workflow before responding", self.active)

    def test_plan_generation_has_its_own_route(self):
        lines = [line for line in self.active.splitlines() if "生成或修改软件执行计划" in line]
        self.assertEqual(len(lines), 1)
        self.assertIn("review-model-routing/SKILL.md", lines[0])

    def test_neighbor_routes_remain_disjoint(self):
        project_line = next(
            line for line in self.active.splitlines()
            if "software-project-learning/SKILL.md" in line
        )
        creator_line = next(
            line for line in self.active.splitlines()
            if "profile-aware-skill-creator/SKILL.md" in line
        )
        self.assertIn("学习", project_line)
        self.assertNotIn("生成或修改软件执行计划", project_line)
        self.assertIn("仅显式调用", creator_line)


if __name__ == "__main__":
    unittest.main()
