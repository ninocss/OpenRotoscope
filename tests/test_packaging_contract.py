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

    def test_lua_launcher_persists_stage_diagnostics(self):
        launcher = (ROOT / "resolve" / "OpenRoto.lua").read_text(encoding="utf-8")
        self.assertIn('stageKey = "OpenRoto.LauncherStage"', launcher)
        self.assertIn('errorKey = "OpenRoto.LauncherError"', launcher)
        self.assertIn('countKey = "OpenRoto.LauncherCount"', launcher)
        self.assertIn('"lua-entered #"', launcher)
        self.assertIn('setStage("fusion-host-ready")', launcher)
        self.assertIn('setStage("free-rendering")', launcher)
        self.assertIn('setStage("free-export-ready:"', launcher)
        self.assertIn('setStage("free-waiting-apply:"', launcher)
        self.assertIn('setStage("free-apply-completed:"', launcher)
        self.assertIn('setStage("python-runscript-requested")', launcher)
        self.assertIn('setStage("python-runscript-returned ok="', launcher)
        self.assertIn('setStage("bootstrap-status ok="', launcher)
        self.assertIn('setStage("launcher-finished status="', launcher)

    def test_free_launcher_uses_resolve_render_api_not_python(self):
        launcher = (ROOT / "resolve" / "OpenRoto.lua").read_text(encoding="utf-8")
        self.assertIn('if tostring(productName) == "DaVinci Resolve" then', launcher)
        self.assertIn("GetCurrentVideoItem", launcher)
        self.assertIn("DuplicateTimeline", launcher)
        self.assertIn("SetTrackEnable", launcher)
        self.assertIn("SetRenderSettings", launcher)
        self.assertIn("AddRenderJob", launcher)
        self.assertIn("StartRendering", launcher)
        self.assertIn("OpenRotoFree_", launcher)
        self.assertIn('setData("OpenRoto.Free.SessionId"', launcher)
        free_branch, studio_branch = launcher.split("-- Studio path:", maxsplit=1)
        self.assertNotIn("RunScript(bridgePath)", free_branch)
        self.assertIn("RunScript(bridgePath)", studio_branch)

    def test_free_session_ids_do_not_repeat_after_resolve_restart(self):
        launcher = (ROOT / "resolve" / "OpenRoto.lua").read_text(encoding="utf-8")
        self.assertIn("local function sessionNonce()", launcher)
        self.assertIn('type(os.time) == "function"', launcher)
        self.assertIn('string.gsub(tostring({}), "[^A-Za-z0-9]", "")', launcher)
        self.assertIn('tostring(launchCount) .. "-" .. sessionNonce()', launcher)
        self.assertNotIn(
            'local sessionId = safeId(targetId) .. "-" .. tostring(launchCount)\n',
            launcher,
        )

    def test_free_launcher_applies_without_secondary_workspace_script(self):
        launcher = (ROOT / "resolve" / "OpenRoto.lua").read_text(encoding="utf-8")
        self.assertIn("pcall(dofile", launcher)
        self.assertIn("CONTROL.lua", launcher)
        self.assertIn("CreateCompoundClip", launcher)
        self.assertIn("ImportFusionComp", launcher)
        self.assertIn("APPLIED.drt", launcher)
        self.assertIn("APPLY_FAILED.drt", launcher)
        self.assertIn("openroto-free-apply:", launcher)
        self.assertIn("openroto-free-cancel:", launcher)
        self.assertFalse((ROOT / "resolve" / "OpenRoto Apply.lua").exists())

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

    def test_installer_deploys_free_and_studio_integration(self):
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
        self.assertEqual(0, installer.count('Source: "..\\resolve\\OpenRoto Apply.lua"'))
        self.assertGreaterEqual(installer.count("OpenRoto Apply.lua"), 2)
        self.assertIn('Source: "..\\resolve\\OpenRotoEntry.py"', installer)
        self.assertIn('DestName: "OpenRoto.py3"', installer)
        self.assertIn('Source: "..\\resolve\\OpenRoto.py"', installer)
        self.assertIn('DestName: "OpenRotoBridgeBase.py"', installer)
        self.assertIn('Source: "..\\resolve\\OpenRotoRemovalBridge.py"', installer)
        self.assertIn('DestName: "OpenRotoBridge.py"', installer)
        self.assertIn('ValueName: "FUSION_Python3_Home"', installer)
        self.assertIn('ValueData: "{app}\\python-runtime"', installer)
        self.assertIn('ValueName: "OpenRoto Free Agent"', installer)
        self.assertIn('Parameters: "--free-agent"', installer)
        self.assertIn('Name: "{localappdata}\\OpenRoto\\FreeExchange"', installer)
        self.assertIn("Remove & Apply", installer)
        self.assertIn("ChangesEnvironment=yes", installer)

    def test_dev_install_uses_both_user_discovery_roots(self):
        script = (ROOT / "scripts" / "install-dev.ps1").read_text(encoding="utf-8")
        self.assertIn('DaVinci Resolve\\Support\\Fusion\\Scripts\\Utility', script)
        self.assertIn('DaVinci Resolve\\Fusion\\Scripts\\Utility', script)
        self.assertIn("foreach ($dir in $scriptDirs)", script)
        self.assertIn('"OpenRoto Apply.lua"', script)
        self.assertNotIn('"resolve\\OpenRoto Apply.lua") -Destination', script)
        self.assertIn(
            '"resolve\\OpenRotoEntry.py") -Destination (Join-Path $bridgeDir "OpenRoto.py3")',
            script,
        )
        self.assertIn(
            '"resolve\\OpenRoto.py") -Destination (Join-Path $bridgeDir "OpenRotoBridgeBase.py")',
            script,
        )
        self.assertIn(
            '"resolve\\OpenRotoRemovalBridge.py") -Destination (Join-Path $bridgeDir "OpenRotoBridge.py")',
            script,
        )
        self.assertIn('SetEnvironmentVariable("FUSION_Python3_Home"', script)
        self.assertIn('"OpenRoto Free Agent"', script)
        self.assertIn('Start-Process -FilePath $appPath -ArgumentList "--free-agent"', script)

    def test_studio_wrapper_preserves_roto_and_adds_removal_mode(self):
        wrapper = (ROOT / "resolve" / "OpenRotoRemovalBridge.py").read_text(encoding="utf-8")
        self.assertIn('OpenRotoBridgeBase.py', wrapper)
        self.assertIn('mode = str(message.get("mode", "rotoscope"))', wrapper)
        self.assertIn('if mode == "remove"', wrapper)
        self.assertIn('_base["_apply_matte"]', wrapper)
        self.assertIn('_apply_removal(', wrapper)
        self.assertIn('f"removed_{index:08d}.png"', wrapper)
        self.assertIn('removed_00000000.png', wrapper)

    def test_build_downloads_a_private_resolve_python_runtime(self):
        build = (ROOT / "scripts" / "build.ps1").read_text(encoding="utf-8")
        prepare = (ROOT / "scripts" / "prepare-python-runtime.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("prepare-python-runtime.ps1", build)
        self.assertIn("python-runtime", build)
        self.assertIn('[string]$ResolvePythonVersion = "3.10.11"', build)
        self.assertIn('[string]$Version = "3.10.11"', prepare)
        self.assertNotIn('ResolvePythonVersion = "3.12', build)
        self.assertIn("python.org/ftp/python", prepare)
        self.assertIn("embed-amd64.zip", prepare)
        self.assertIn("python3*.dll", prepare)
        self.assertIn("sys.version_info[:2] == (3, 10)", prepare)

    def test_build_cleans_only_repo_dist_processes_before_pyinstaller(self):
        build = (ROOT / "scripts" / "build.ps1").read_text(encoding="utf-8")
        self.assertIn("function Stop-OpenRotoProcessesFromPath", build)
        self.assertIn('Get-Process -Name "OpenRoto"', build)
        self.assertIn("StartsWith($root", build)
        self.assertIn("Stop-Process -Id $process.Id -Force", build)
        self.assertIn("function Remove-DirectoryWithRetry", build)
        self.assertIn("Stop-OpenRotoProcessesFromPath $distAppPath", build)
        self.assertIn("Remove-DirectoryWithRetry $distAppPath", build)

    def test_packaged_app_uses_crash_logging_entrypoint(self):
        build = (ROOT / "scripts" / "build.ps1").read_text(encoding="utf-8")
        launcher = (ROOT / "app" / "openroto_launcher.py").read_text(encoding="utf-8")
        main = (ROOT / "app" / "openroto" / "main.py").read_text(encoding="utf-8")
        removal_ui = (ROOT / "app" / "openroto" / "ui" / "ObjectRemovalMain.qml").read_text(
            encoding="utf-8"
        )
        self.assertIn("app\\openroto_launcher.py", build)
        self.assertIn('return root / "app.log"', launcher)
        self.assertIn("unhandled startup exception", launcher)
        self.assertIn('"--free-agent"', main)
        self.assertIn('"--handoff"', main)
        self.assertIn("FreeHandoffController", main)
        self.assertIn("ApplicationController", main)
        self.assertIn("RemovalController", main)
        self.assertIn('"removalController": removal_controller', main)
        self.assertIn("Remove & Apply", removal_ui)

    def test_windowed_build_provides_writable_stdio_for_model_loaders(self):
        build = (ROOT / "scripts" / "build.ps1").read_text(encoding="utf-8")
        launcher = (ROOT / "app" / "openroto_launcher.py").read_text(encoding="utf-8")
        self.assertIn("--windowed", build)
        self.assertIn("def _ensure_standard_streams()", launcher)
        self.assertIn("if sys.stdout is None:", launcher)
        self.assertIn("if sys.stderr is None:", launcher)
        self.assertIn('with_name("console.log")', launcher)
        self.assertIn("_ensure_standard_streams()", launcher)


if __name__ == "__main__":
    unittest.main()
