import importlib.util
import pathlib
import unittest
from unittest import mock


SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "plugin-manager.py"
SPEC = importlib.util.spec_from_file_location("plugin_manager", SCRIPT_PATH)
plugin_manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(plugin_manager)


class PluginScriptInstallTests(unittest.TestCase):
    def test_skips_npm_global_install_when_installed_tool_exists(self):
        plugin_config = {
            "scripts": {
                "install": "npm i -g open-computer-use",
            },
        }

        with mock.patch("shutil.which", return_value="C:/bin/open-computer-use.cmd"):
            with mock.patch.object(plugin_manager.subprocess, "run") as run:
                plugin_manager.run_plugin_scripts(plugin_config)

        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
