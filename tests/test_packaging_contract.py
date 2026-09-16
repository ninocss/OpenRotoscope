from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ResolveLauncherPackagingTests(unittest.TestCase):
    def test_lua_launcher_targets_embedded_python3_bridge(self):
        launcher = (ROOT / "resolve" / "OpenRoto.lua").read_text(encoding="utf-8")
        self.assertIn("OpenRoto.py3", launcher)
        self.assertNotIn("py -3.12", launcher)
        self.assertNotIn("fallback Python", launcher)

    def test_installer_and_launcher_use_same_bridge_filename(self):
        installer = (ROOT / "installer" / "OpenRoto.iss").read_text(encoding="utf-8")
        self.assertIn('DestName: "OpenRoto.py3"', installer)
        self.assertIn(
            "DaVinci Resolve\\Support\\OpenRoto\\OpenRoto.py3",
            installer,
        )

    def test_dev_install_only_deploys_python3_bridge(self):
        script = (ROOT / "scripts" / "install-dev.ps1").read_text(encoding="utf-8")
        self.assertIn(
            '-Destination (Join-Path $dir "OpenRoto.py3") -Force',
            script,
        )
        self.assertNotIn(
            '-Destination (Join-Path $dir "OpenRoto.py") -Force',
            script,
        )


if __name__ == "__main__":
    unittest.main()
