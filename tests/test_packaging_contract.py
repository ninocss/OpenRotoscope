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

        # Resolve 21.1 Workspace scripts can run with OS-facing Lua facilities
        # stripped. The menu launcher must not depend on any of them.
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
                self.assertNotIn(token, launcher)

    def test_python_bootstrap_reports_status_without_lua_file_markers(self):
        bootstrap = (ROOT / "resolve" / "OpenRotoEntry.py").read_text(encoding="utf-8")
        self.assertIn('STATUS_KEY = "OpenRoto.BootstrapStatus"', bootstrap)
        self.assertIn('host.SetData(STATUS_KEY, str(value))', bootstrap)
        self.assertIn('_set_status("entered")', bootstrap)
        self.assertIn('_set_status("bridge-running")', bootstrap)
        self.assertIn('_set_status("bridge-returned")', bootstrap)
        self.assertIn('_set_status(f"failed:', bootstrap)

    def test_installer_deploys_bootstrap_bridge_and_python_home(self):
        installer = (ROOT / "installer" / "OpenRoto.iss").read_text(encoding="utf-8")
        self.assertIn('Source: "..\\resolve\\OpenRotoEntry.py"', installer)
        self.assertIn('DestName: "OpenRoto.py3"', installer)
        self.assertIn('Source: "..\\resolve\\OpenRoto.py"', installer)
        self.assertIn('DestName: "OpenRotoBridge.py"', installer)
        self.assertIn('ValueName: "FUSION_Python3_Home"', installer)
        self.assertIn('ValueData: "{app}\\python-runtime"', installer)
        self.assertIn("ChangesEnvironment=yes", installer)

    def test_dev_install_deploys_same_bridge_pair(self):
        script = (ROOT / "scripts" / "install-dev.ps1").read_text(encoding="utf-8")
        self.assertIn(
            '"resolve\\OpenRotoEntry.py") -Destination (Join-Path $dir "OpenRoto.py3")',
            script,
        )
        self.assertIn(
            '"resolve\\OpenRoto.py") -Destination (Join-Path $dir "OpenRotoBridge.py")',
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
        self.assertIn("python.org/ftp/python", prepare)
        self.assertIn("embed-amd64.zip", prepare)
        self.assertIn("python3*.dll", prepare)

    def test_packaged_app_uses_crash_logging_entrypoint(self):
        build = (ROOT / "scripts" / "build.ps1").read_text(encoding="utf-8")
        launcher = (ROOT / "app" / "openroto_launcher.py").read_text(encoding="utf-8")
        self.assertIn("app\\openroto_launcher.py", build)
        self.assertIn('return root / "app.log"', launcher)
        self.assertIn("unhandled startup exception", launcher)


if __name__ == "__main__":
    unittest.main()
