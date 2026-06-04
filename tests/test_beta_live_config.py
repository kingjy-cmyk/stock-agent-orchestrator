import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.services.beta_live_config import (
    beta_live_config_init_to_markdown,
    init_beta_live_config,
)


class BetaLiveConfigTests(unittest.TestCase):
    def test_init_beta_live_config_copies_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template = tmp_path / "beta.live.example.toml"
            output = tmp_path / "beta.live.toml"
            template.write_text("app = \"replace-me\"\n", encoding="utf-8")

            result = init_beta_live_config(template_path=template, output_path=output)

            self.assertTrue(result.created)
            self.assertEqual(output.read_text(encoding="utf-8"), "app = \"replace-me\"\n")
            self.assertTrue(any("Do not commit" in warning for warning in result.warnings))

    def test_init_beta_live_config_does_not_overwrite_existing_file_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template = tmp_path / "beta.live.example.toml"
            output = tmp_path / "beta.live.toml"
            template.write_text("template\n", encoding="utf-8")
            output.write_text("existing\n", encoding="utf-8")

            result = init_beta_live_config(template_path=template, output_path=output)

            self.assertFalse(result.created)
            self.assertEqual(output.read_text(encoding="utf-8"), "existing\n")

    def test_init_beta_live_config_force_overwrites_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template = tmp_path / "beta.live.example.toml"
            output = tmp_path / "beta.live.toml"
            template.write_text("template\n", encoding="utf-8")
            output.write_text("existing\n", encoding="utf-8")

            result = init_beta_live_config(template_path=template, output_path=output, force=True)

            self.assertTrue(result.created)
            self.assertEqual(output.read_text(encoding="utf-8"), "template\n")

    def test_markdown_renders_next_steps_and_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            template = tmp_path / "beta.live.example.toml"
            output = tmp_path / "beta.live.toml"
            template.write_text("template\n", encoding="utf-8")
            result = init_beta_live_config(template_path=template, output_path=output)

            rendered = beta_live_config_init_to_markdown(result)

            self.assertIn("Beta Live Config Init", rendered)
            self.assertIn("Next Steps", rendered)
            self.assertIn("Warnings", rendered)

    def test_real_beta_live_config_is_ignored_by_gitignore(self) -> None:
        gitignore = Path(".gitignore").read_text(encoding="utf-8")

        self.assertIn("configs/beta.live.toml", gitignore)


if __name__ == "__main__":
    unittest.main()
