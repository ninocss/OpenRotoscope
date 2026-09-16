"""Studio bridge wrapper adding OpenRoto object-removal apply support.

The stable bridge implementation is installed beside this file as
``OpenRotoBridgeBase.py``. It is loaded without auto-running so this wrapper can
reuse its Resolve/export/session helpers while keeping the existing rotoscope
path unchanged.
"""

from __future__ import annotations

import contextlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import time
import traceback
import uuid
from pathlib import Path

_BASE_PATH = Path(__file__).with_name("OpenRotoBridgeBase.py")
if not _BASE_PATH.is_file():
    raise FileNotFoundError(f"OpenRoto base bridge is missing: {_BASE_PATH}")

_base = {"__name__": "_openroto_bridge_base", "__file__": str(_BASE_PATH)}
exec(compile(_BASE_PATH.read_text(encoding="utf-8"), str(_BASE_PATH), "exec"), _base, _base)
for _name in ("resolve", "app", "fusion"):
    if globals().get(_name) is not None:
        _base[_name] = globals()[_name]


def _removal_comp_text(sequence_path, frame_count):
    filename = str(sequence_path).replace("\\", "\\\\").replace('"', '\\"')
    last = max(0, frame_count - 1)
    return f'''Composition {{
    CurrentTime = 0,
    RenderRange = {{ 0, {last} }},
    GlobalRange = {{ 0, {last} }},
    Tools = ordered() {{
        MediaIn1 = MediaIn {{
            Extent_Set = true,
            ViewInfo = OperatorInfo {{ Pos = {{ 0, 0 }} }},
        }},
        OpenRotoRemoval = Loader {{
            Clips = {{
                Clip {{
                    ID = "Clip1",
                    Filename = "{filename}",
                    FormatID = "PNGFormat",
                    StartFrame = 0,
                    Length = {frame_count},
                    LengthSetManually = true,
                    TrimIn = 0,
                    TrimOut = {last},
                    ExtendFirst = 0,
                    ExtendLast = 0,
                    Loop = 0,
                    AspectMode = 0,
                    Depth = 0,
                    TimeCode = 0,
                    GlobalStart = 0,
                    GlobalEnd = {last}
                }}
            }},
            Inputs = {{ Clip = Input {{ Value = FuID {{ "Clip1" }} }} }},
            ViewInfo = OperatorInfo {{ Pos = {{ 150, 0 }} }},
        }},
        MediaOut1 = MediaOut {{
            Inputs = {{ Input = Input {{ SourceOp = "OpenRotoRemoval", Source = "Output" }} }},
            ViewInfo = OperatorInfo {{ Pos = {{ 300, 0 }} }},
        }}
    }}
}}
'''


def _linked_audio(target, manifest):
    expected_linked_ids = set(manifest.get("linked_item_ids", []))
    try:
        current_linked_items = list(target.GetLinkedItems() or [])
        current_linked_ids = {item.GetUniqueId() for item in current_linked_items}
        if current_linked_ids != expected_linked_ids:
            raise _base["OpenRotoError"](
                "The target clip's linked audio changed while OpenRoto was open."
            )
        linked = []
        for item in current_linked_items:
            if (
                item.GetType() == "audio"
                and _base["_as_int"](item.GetStart()) == manifest["record_start"]
                and _base["_as_int"](item.GetEnd()) == manifest["record_end"]
            ):
                linked.append(item)
        return linked
    except _base["OpenRotoError"]:
        raise
    except Exception as error:
        raise _base["OpenRotoError"](
            "Resolve could not validate the clip's linked audio."
        ) from error


def _apply_removal(project, timeline, target, manifest, removal_dir):
    current = project.GetCurrentTimeline()
    if current is None or current.GetUniqueId() != manifest["timeline_id"]:
        raise _base["OpenRotoError"](
            "Return to the original timeline before applying the OpenRoto removal."
        )
    if target.GetUniqueId() != manifest["clip_id"]:
        raise _base["OpenRotoError"]("The original clip is no longer available on the timeline.")
    moved = _base["_as_int"](target.GetStart()) != manifest["record_start"]
    trimmed = _base["_as_int"](target.GetEnd()) != manifest["record_end"]
    if moved or trimmed:
        raise _base["OpenRotoError"]("The target clip was moved or trimmed while OpenRoto was open.")

    expected_count = manifest["record_end"] - manifest["record_start"]
    missing = [
        index
        for index in range(expected_count)
        if not (Path(removal_dir) / f"removed_{index:08d}.png").is_file()
    ]
    if missing:
        raise _base["OpenRotoError"](
            f"The object-removal sequence is incomplete at frame {missing[0] + 1}."
        )

    comp_path = Path(manifest["matte_dir"]) / "OpenRoto.comp"
    comp_path.write_text(
        _removal_comp_text(Path(removal_dir) / "removed_00000000.png", expected_count),
        encoding="utf-8",
    )

    compound = timeline.CreateCompoundClip(
        [target] + _linked_audio(target, manifest),
        {"name": f"OpenRoto Remove — {_base['_safe_name'](manifest['clip_name'])}"},
    )
    if compound is None:
        raise _base["OpenRotoError"](
            "Resolve could not create the non-destructive OpenRoto removal compound clip."
        )
    try:
        composition = compound.ImportFusionComp(str(comp_path))
    except Exception as error:
        raise _base["TimelineMutationError"](
            "Resolve could not attach the OpenRoto removal composition."
        ) from error
    if composition is None:
        raise _base["TimelineMutationError"](
            "Resolve could not attach the OpenRoto removal composition."
        )
    with contextlib.suppress(Exception):
        compound.SetClipColor("Sky")
    return compound


def run():
    resolve_api = _base["_resolve_instance"]()
    if resolve_api is None:
        raise _base["OpenRotoError"]("DaVinci Resolve is not available.")
    (
        manager,
        project,
        timeline,
        target,
        media,
        track_index,
        start,
        end,
        width,
        height,
        fps,
    ) = _base["_target_context"](resolve_api)
    application = _base["_find_application"]()
    session_id = uuid.uuid4().hex
    token = secrets.token_urlsafe(32)
    root = _base["_session_root"](session_id)
    frames_dir = root / "frames"
    matte_dir = root / "matte"
    frames_dir.mkdir(parents=True, exist_ok=False)
    matte_dir.mkdir(parents=True, exist_ok=True)
    try:
        _base["_check_disk_space"](root, width, height, end - start)
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise
    snapshot_path = root / f"{_base['_safe_name'](timeline.GetName())}.drt"
    if not timeline.Export(str(snapshot_path), resolve_api.EXPORT_DRT, resolve_api.EXPORT_NONE):
        raise _base["OpenRotoError"]("Resolve could not create the safety snapshot.")
    fingerprint = _base["_timeline_fingerprint"](timeline)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((_base["LOOPBACK"], 0))
    server.listen(1)
    server.settimeout(_base["ACCEPT_TIMEOUT_SECONDS"])
    port = server.getsockname()[1]

    keep_session = False
    applied = False
    try:
        frame_pattern = _base["_export_target"](
            resolve_api, project, timeline, track_index, start, end, frames_dir
        )
        linked_ids = []
        with contextlib.suppress(Exception):
            linked_ids = [item.GetUniqueId() for item in target.GetLinkedItems() or []]
        manifest = {
            "schema_version": _base["PROTOCOL_VERSION"],
            "session_id": session_id,
            "token": token,
            "bridge_host": _base["LOOPBACK"],
            "bridge_port": port,
            "project_id": project.GetUniqueId(),
            "project_name": project.GetName(),
            "timeline_id": timeline.GetUniqueId(),
            "timeline_name": timeline.GetName(),
            "clip_id": target.GetUniqueId(),
            "clip_name": target.GetName(),
            "track_index": track_index,
            "record_start": start,
            "record_end": end,
            "source_start": _base["_as_int"](target.GetSourceStartFrame()),
            "source_end": _base["_as_int"](target.GetSourceEndFrame()),
            "fps": fps,
            "width": width,
            "height": height,
            "frames_dir": str(frames_dir.resolve()),
            "matte_dir": str(matte_dir.resolve()),
            "snapshot_path": str(snapshot_path.resolve()),
            "state": "ready",
            "frame_pattern": frame_pattern,
            "matte_pattern": "matte_%08d.png",
            "linked_item_ids": linked_ids,
        }
        manifest_path = root / "session.json"
        _base["_atomic_json"](manifest_path, manifest)
        subprocess.Popen(
            [str(application), "--session", str(manifest_path)],
            cwd=str(application.parent),
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
        connection, _ = server.accept()
        connection.settimeout(0.5)
        with connection:
            authenticated = False
            for message in _base["_read_messages"](connection):
                if not secrets.compare_digest(str(message.get("token", "")), token):
                    _base["_send"](
                        connection, "error", message="OpenRoto session authentication failed."
                    )
                    return
                if message.get("type") == "hello":
                    if _base["_as_int"](message.get("protocol")) != _base["PROTOCOL_VERSION"]:
                        _base["_send"](
                            connection,
                            "error",
                            message="This OpenRoto app uses an incompatible bridge protocol.",
                        )
                        return
                    authenticated = True
                    _base["_send"](connection, "ready", session_id=session_id)
                    continue
                if not authenticated:
                    _base["_send"](
                        connection, "error", message="OpenRoto handshake is incomplete."
                    )
                    continue
                if message.get("type") == "cancel":
                    return
                if message.get("type") != "apply":
                    continue
                if message.get("session_id") != session_id:
                    _base["_send"](connection, "error", message="Session ID mismatch.")
                    continue
                if _base["_timeline_fingerprint"](timeline) != fingerprint:
                    _base["_send"](
                        connection,
                        "error",
                        message=(
                            "The timeline changed while OpenRoto was open. Start a new "
                            "session to avoid applying the result to the wrong edit."
                        ),
                    )
                    keep_session = True
                    return
                if _base["_as_int"](message.get("frame_count")) != end - start:
                    _base["_send"](
                        connection, "error", message="Output frame count does not match the clip."
                    )
                    keep_session = True
                    return

                mode = str(message.get("mode", "rotoscope"))
                if mode == "remove":
                    requested_output = Path(str(message.get("removal_dir", ""))).resolve()
                    if (
                        requested_output.parent != matte_dir.resolve()
                        or requested_output.name != "removed"
                    ):
                        _base["_send"](
                            connection,
                            "error",
                            message="Object-removal path is outside this session.",
                        )
                        keep_session = True
                        return
                else:
                    requested_output = Path(str(message.get("matte_dir", ""))).resolve()
                    if requested_output.parent != matte_dir.resolve() or requested_output.name != "final":
                        _base["_send"](
                            connection, "error", message="Matte path is outside this session."
                        )
                        keep_session = True
                        return

                _base["_send"](
                    connection,
                    "progress",
                    progress=0.2,
                    message="Creating Resolve compound",
                )
                keep_session = True
                try:
                    if mode == "remove":
                        _apply_removal(project, timeline, target, manifest, requested_output)
                    else:
                        _base["_apply_matte"](
                            project, timeline, target, manifest, requested_output
                        )
                except Exception as error:
                    suffix = ""
                    if isinstance(error, _base["TimelineMutationError"]):
                        restored = _base["_restore_timeline"](
                            project, timeline, snapshot_path, manifest["timeline_name"]
                        )
                        suffix = (
                            " The timeline snapshot was restored."
                            if restored
                            else " The safety DRT remains in the OpenRoto session folder."
                        )
                    _base["_send"](connection, "error", message=str(error) + suffix)
                    return
                _base["_send"](connection, "completed", session_id=session_id)
                applied = True
                time.sleep(1.5)
                return
    finally:
        server.close()
        if applied:
            shutil.rmtree(frames_dir, ignore_errors=True)
            shutil.rmtree(matte_dir / "raw", ignore_errors=True)
            shutil.rmtree(matte_dir / "preview", ignore_errors=True)
            snapshot_path.unlink(missing_ok=True)
        elif not keep_session:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__" or any(
    globals().get(name) is not None for name in ("resolve", "app", "fusion")
):
    _base["_bootstrap_log"]("entered object-removal Studio bridge wrapper")
    try:
        run()
    except Exception as error:
        traceback.print_exc()
        _base["_message"]("Could not start", str(error), error=True)
