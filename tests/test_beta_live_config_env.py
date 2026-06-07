import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.config import load_config
from stock_agent_orchestrator.services.beta_live_config_env import (
    ENV_DEFAULTS,
    beta_live_config_from_env_to_markdown,
    render_beta_live_env_template,
    write_beta_live_config_from_env,
)


class BetaLiveConfigFromEnvTests(unittest.TestCase):
    def test_missing_env_does_not_write_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "configs" / "beta.live.toml"
            (tmp_path / ".gitignore").write_text("configs/beta.live.toml\n", encoding="utf-8")

            result = write_beta_live_config_from_env(output_path=output, repo_root=tmp_path, env={})

            self.assertFalse(result.written)
            self.assertFalse(output.exists())
            self.assertIn("FEISHU_APP_SECRET", result.missing_env)

    def test_refuses_to_write_when_output_is_not_gitignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "configs" / "beta.live.toml"

            result = write_beta_live_config_from_env(output_path=output, repo_root=tmp_path, env=self._env())

            self.assertFalse(result.written)
            self.assertFalse(output.exists())
            self.assertFalse(result.gitignored)

    def test_refuses_to_overwrite_existing_config_without_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "configs" / "beta.live.toml"
            output.parent.mkdir(parents=True)
            output.write_text("existing\n", encoding="utf-8")
            (tmp_path / ".gitignore").write_text("configs/beta.live.toml\n", encoding="utf-8")

            result = write_beta_live_config_from_env(output_path=output, repo_root=tmp_path, env=self._env())

            self.assertFalse(result.written)
            self.assertEqual(output.read_text(encoding="utf-8"), "existing\n")

    def test_writes_complete_config_from_env_with_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "configs" / "beta.live.toml"
            output.parent.mkdir(parents=True)
            output.write_text("existing\n", encoding="utf-8")
            (tmp_path / ".gitignore").write_text("configs/beta.live.toml\n", encoding="utf-8")

            result = write_beta_live_config_from_env(output_path=output, repo_root=tmp_path, env=self._env(), overwrite=True)
            rendered = beta_live_config_from_env_to_markdown(result)
            config = load_config(output)

            self.assertTrue(result.written)
            self.assertTrue(result.ready_for_preflight)
            self.assertEqual(config.feishu.group_chat_id, "oc_beta_chat")
            self.assertEqual(config.feishu.event_mode, "long_connection")
            self.assertEqual(config.feishu.send_allowlist, ["oc_beta_chat"])
            self.assertNotIn("secret-value", rendered)
            self.assertNotIn("verify-token-secret", rendered)
            self.assertNotIn("encrypt-key-secret", rendered)

    def test_template_placeholders_do_not_mark_config_ready_for_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "configs" / "beta.live.toml"
            (tmp_path / ".gitignore").write_text("configs/beta.live.toml\n", encoding="utf-8")

            result = write_beta_live_config_from_env(
                output_path=output,
                repo_root=tmp_path,
                env=ENV_DEFAULTS,
                overwrite=True,
            )

            self.assertTrue(result.written)
            self.assertFalse(result.ready_for_preflight)

    def test_renders_powershell_env_template(self) -> None:
        rendered = render_beta_live_env_template(shell="powershell")

        self.assertIn("$env:FEISHU_APP_ID", rendered)
        self.assertIn("$env:FEISHU_APP_SECRET", rendered)
        self.assertIn("$env:FEISHU_EVENT_MODE", rendered)
        self.assertIn("beta-live-config-from-env", rendered)
        self.assertIn('C:\\path\\to\\candidate_list.md', rendered)

    def test_renders_bash_env_template(self) -> None:
        rendered = render_beta_live_env_template(shell="bash")

        self.assertIn("export FEISHU_APP_ID", rendered)
        self.assertIn("export FEISHU_APP_SECRET", rendered)
        self.assertIn("export FEISHU_EVENT_MODE", rendered)
        self.assertIn("beta-live-config-from-env", rendered)

    def test_renders_powershell_env_template_with_local_defaults(self) -> None:
        rendered = render_beta_live_env_template(shell="powershell", use_local_defaults=True)

        self.assertIn("Local defaults enabled", rendered)
        self.assertIn("\\\\wsl.localhost\\Ubuntu\\home\\jy95\\.openclaw", rendered)
        self.assertIn(".runtime/beta-live/seven_layer", rendered)
        self.assertIn(".runtime/beta-live.db", rendered)

    def test_renders_bash_env_template_with_local_defaults(self) -> None:
        rendered = render_beta_live_env_template(shell="bash", use_local_defaults=True)

        self.assertIn("export STOCK_AGENT_CANDIDATE_LIST", rendered)
        self.assertIn("/home/jy95/.openclaw/evolution/shared/recurring/candidate_list.md", rendered)
        self.assertIn(".runtime/beta-live/entry_monitor", rendered)

    def _env(self) -> dict[str, str]:
        return {
            "STOCK_AGENT_CANDIDATE_LIST": "./runtime/candidate_list.md",
            "STOCK_AGENT_SEVEN_LAYER_REPORTS": "./runtime/seven_layer",
            "STOCK_AGENT_ENTRY_MONITOR_REPORTS": "./runtime/entry_monitor",
            "STOCK_AGENT_SQLITE_DB": "./runtime/beta-live.db",
            "FEISHU_GROUP_CHAT_ID": "oc_beta_chat",
            "FEISHU_OWNER_OPEN_ID": "ou_owner",
            "FEISHU_DATA_OPEN_ID": "ou_data",
            "FEISHU_ANALYST_OPEN_ID": "ou_analyst",
            "FEISHU_APP_ID": "cli_a_real_app",
            "FEISHU_APP_SECRET": "secret-value",
            "FEISHU_EVENT_MODE": "long_connection",
            "FEISHU_VERIFICATION_TOKEN": "verify-token-secret",
            "FEISHU_ENCRYPT_KEY": "encrypt-key-secret",
            "FEISHU_WEBHOOK_RATE_LIMIT_PER_MINUTE": "60",
        }


if __name__ == "__main__":
    unittest.main()
