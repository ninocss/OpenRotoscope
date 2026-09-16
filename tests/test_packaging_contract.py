from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ResolveLauncherPackagingTests(unittest.TestCase):
    def test_lua_launcher_is_workspace_sandbox_safe(self):
        launcher = (ROOT / "resolve" / "OpenRoto.lua").read_text(encoding="utf-8")
        self.assertIn("OpenRoto.py3", launcher)
        self.assertIn("RunScript", launcher)
        self.assertIn("SetData", launcher)
        self.assertIn("GetData", launcher)
        self.assertIn("FUSION_Python3_Home", launcher)
        self.assertIn("UIDispatcher", launcher)
        self.assertIn("OpenRoto — Startfehler", launcher)

        # Check executable lines only. Comments intentionally explain which
        # Resolve-sandbox facilities must never be reintroduced into the code.
        executable = "\n".join(
            line for line in launcher.splitlines() if not line.lstrip().startswith("--")
        )
        forbidden = (
            "io.open",
            "io.read",
            "io.write",
            "os.execute",
            "os.remove",
            "require(",
            'require, "ffi"',
            "ffi.",
            "python-probe.log",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, executable)

    def test_python_bootstrap_reports_status_without_lua_file_markers(self):
        bootstrap = (ROOT / "resolve" / "OpenRotoEntry.py").read_text(encoding="utf-8")
        self.assertIn('STATUS_KEY = "OpenRoto.BootstrapStatus"', bootstrap)
        self.assertIn('host.SetData(STATUS_KEY, str(value))', bootstrap)
        self.assertIn('_set_status("entered")', bootstrap)
        self.assertIn('_set_status("bridge-running")', bootstrap)
        self.assertIn('_set_status("bridge-returned")', bootstrap)
        self.assertIn('_set_status(f"failed:', bootstrap)
        self.assertIn("sys.version_info >= (3, 12)", bootstrap)
        self.assertIn("requires Python 3.10/3.11", bootstrap)

    def test_installer_deploys_launcher_to_both_user_discovery_roots(self):
        installer = (ROOT / "installer" / "OpenRoto.iss").read_text(encoding="utf-8")
        self.assertIn(
            'DestDir: "{userappdata}\\Blackmagic Design\\DaVinci Resolve\\Support\\Fusion\\Scripts\\Utility"',
            installer,
        )
        self.assertIn(
            'DestDir: "{userappdata}\\Blackmagic Design\\DaVinci Resolve\\Fusion\\Scripts\\Utility"',
            installer,
        )
        self.assertEqual(2, installer.count('Source: "..\\resolve\\OpenRoto.lua"'))
        self.assertIn('Source: "..\\resolve\\OpenRotoEntry.py"', installer)
        self.assertIn('DestName: "OpenRoto.py3"', installer)
        self.assertIn('Source: "..\\resolve\\OpenRoto.py"', installer)
        self.assertIn('DestName: "OpenRotoBridge.py"', installer)
        self.assertIn('ValueName: "FUSION_Python3_Home"', installer)
        self.assertIn('ValueData: "{app}\\python-runtime"', installer)
        self.assertIn("ChangesEnvironment=yes", installer)

    def test_dev_install_uses_both_user_discovery_roots(self):
        script = (ROOT / "scripts" / "install-dev.ps1").read_text(encoding="utf-8")
        self.assertIn(
            'DaVinci Resolve\\Support\\Fusion\\Scripts\\Utility',
            script,
        )
        self.assertIn(
            'DaVinci Resolve\\Fusion\\Scripts\\Utility',
            script,
        )
        self.assertIn("foreach ($dir in $scriptDirs)", script)
        self.assertIn(
            '"resolve\\OpenRotoEntry.py") -Destination (Join-Path $bridgeDir "OpenRoto.py3")',
            script,
        )
        self.assertIn(
            '"resolve\\OpenRoto.py") -Destination (Join-Path $bridgeDir "OpenRotoBridge.py")',
            script,
        )
        self.assertIn('SetEnvironmentVariable("FUSION_Python3_Home"', script)

    def test_build_downloads_a_private_resolve_python_runtime(self):
        build = (ROOT / "scripts" / "build.ps1").read_text(encoding="utf-8")
        prepare = (ROOT / "scripts" / "prepare-python-runtime.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("prepare-python-runtime.ps1", build)
        self.assertIn("python-runtime", build)
        self.assertIn('[string]$Version = "3.10.11"', prepare)
        self.assertIn("python.org/ftp/python", prepare)
        self.assertIn("embed-amd64.zip", prepare)
        self.assertIn("python3*.dll", prepare)
        self.assertIn("sys.version_info[:2] == (3, 10)", prepare)

    def test_packaged_app_uses_crash_logging_entrypoint(self):
        build = (ROOT / "scripts" / "build.ps1").read_text(encoding="utf-8")
        launcher = (ROOT / "app" / "openroto_launcher.py").read_text(encoding="utf-8")
        self.assertIn("app\\openroto_launcher.py", build)
        self.assertIn('return root / "app.log"', launcher)
        self.assertIn("unhandled startup exception", launcher)


if __name__ == "__main__":
    unittest.main()
