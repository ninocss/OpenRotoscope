from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FreeDevInstallTests(unittest.TestCase):
    def test_dev_install_replaces_old_free_agent_before_starting_new_one(self):
        script = (ROOT / "scripts" / "install-dev.ps1").read_text(encoding="utf-8")
        stop_marker = "Get-CimInstance Win32_Process"
        start_marker = 'Start-Process -FilePath $appPath -ArgumentList "--free-agent"'
        self.assertIn(stop_marker, script)
        self.assertIn("--free-agent", script)
        self.assertIn("Stop-Process -Id $agent.ProcessId -Force", script)
        self.assertIn(start_marker, script)
        self.assertLess(script.index(stop_marker), script.index(start_marker))
        self.assertIn("Do not terminate an active --session UI", script)


if __name__ == "__main__":
    unittest.main()
