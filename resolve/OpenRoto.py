"""OpenRoto bridge for DaVinci Resolve 21.1+.

The Lua Utility launcher executes this source as OpenRoto.py3. The explicit
extension forces Resolve's embedded Python 3 interpreter while RunScript keeps
the bridge inside the Free-compatible application scripting context.
"""

from __future__ import annotations

import contextlib
import ctypes
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import time
import traceback
import uuid
from pathlib import Path

APP_NAME = "OpenRoto"
PROTOCOL_VERSION = 1
LOOPBACK = "127.0.0.1"
ACCEPT_TIMEOUT_SECONDS = 45
RENDER_TIMEOUT_SECONDS = 60 * 60 * 12


class OpenRotoError(RuntimeError):
    pass


def _bootstrap_log(message):
    """Record entry before any Resolve API or application startup work."""
    try:
        root = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "OpenRoto"
        root.mkdir(parents=True, exist_ok=True)
        with (root / "bridge.log").open("a", encoding="utf-8") as handle:
            handle.write(time.strftime("%Y-%m-%d %H:%M:%S ") + str(message) + "\n")
    except Exception:
        pass


class TimelineMutationError(OpenRotoError):
    """An apply failure after Resolve already changed the timeline."""

    pass


def _message(title, text, error=False):
    print(f"{APP_NAME}: {title}: {text}")
    if os.name == "nt":
        try:
            flags = 0x10 if error else 0x40
            ctypes.windll.user32.MessageBoxW(None, str(text), f"{APP_NAME} — {title}", flags)
        except Exception:
            pass


def _resolve_instance():
    instance = globals().get("resolve")
    if instance is not None:
        return instance

    # Resolve Free does not allow a new external scripting connection. Scripts
    # invoked internally through Fusion already have an application object, so
    # reuse that connection before trying DaVinciResolveScript.scriptapp().
    app_instance = globals().get("app") or globals().get("fusion")
    if app_instance is not None and hasattr(app_instance, "GetResolve"):
        instance = app_instance.GetResolve()
        if instance is not None:
            return instance

    import DaVinciResolveScript as dvr_script

    return dvr_script.scriptapp("Resolve")


def _safe_name(value):
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", str(value)).strip(" .")
    return cleaned[:80] or "clip"


def _as_float(value, fallback=0.0):
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return fallback


def _as_int(value, fallback=0):
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return fallback


def _atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def _session_root(session_id):
    local_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return local_data / APP_NAME / "Sessions" / session_id


def _check_disk_space(root, width, height, frame_count):
    # RGB export plus raw/final alpha, with headroom for PNGs that compress poorly.
    estimated = width * height * frame_count * 5
    reserve = 2 * 1024**3
    free = shutil.disk_usage(root).free
    required = estimated + reserve
    if free < required:
        needed_gb = required / 1024**3
        free_gb = free / 1024**3
        raise OpenRotoError(
            f"This clip needs approximately {needed_gb:.1f} GB of working space, "
            f"but only {free_gb:.1f} GB is available. Free some disk space and try again."
        )


def _find_application():
    override = os.environ.get("OPENROTO_APP")
    candidates = []
    if override:
        candidates.append(Path(override))
    local_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    candidates.extend(
        [
            local_data / "Programs" / APP_NAME / "OpenRoto.exe",
            local_data / APP_NAME / "OpenRoto.exe",
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise OpenRotoError(
        "OpenRoto is not installed. Run OpenRotoSetup.exe, restart Resolve, and try again."
    )


def _timeline_settings(project, timeline):
    settings = {}
    with contextlib.suppress(Exception):
        settings.update(project.GetSettings() or {})
    with contextlib.suppress(Exception):
        settings.update(timeline.GetSettings() or {})
    width = _as_int(settings.get("timelineResolutionWidth"), 1920)
    height = _as_int(settings.get("timelineResolutionHeight"), 1080)
    fps = _as_float(
        settings.get("timelineFrameRate") or settings.get("timelinePlaybackFrameRate"), 24.0
    )
    return width, height, fps


def _target_context(resolve_api):
    manager = resolve_api.GetProjectManager()
    project = manager.GetCurrentProject() if manager else None
    if project is None:
        raise OpenRotoError("Open a Resolve project before starting OpenRoto.")
    timeline = project.GetCurrentTimeline()
    if timeline is None:
        raise OpenRotoError("Open a timeline before starting OpenRoto.")
    target = timeline.GetCurrentVideoItem()
    if target is None or target.GetType() != "video":
        raise OpenRotoError("Place the playhead over the video clip you want to mask.")
    media = target.GetMediaPoolItem()
    if media is None:
        raise OpenRotoError("The current item is not a supported file-backed video clip.")
    properties = media.GetClipProperty() or {}
    file_path = properties.get("File Path") or properties.get("FilePath")
    if file_path and not Path(file_path).exists():
        raise OpenRotoError("The selected clip is offline. Relink it before using OpenRoto.")
    track_info = target.GetTrackTypeAndIndex()
    track_index = _as_int(track_info[1] if len(track_info) > 1 else 0)
    if track_index < 1:
        raise OpenRotoError("Could not determine the selected clip's video track.")
    start = _as_int(target.GetStart())
    end = _as_int(target.GetEnd())
    if end <= start:
        raise OpenRotoError("The selected clip has no renderable frames.")
    width, height, fps = _timeline_settings(project, timeline)
    return manager, project, timeline, target, media, track_index, start, end, width, height, fps


def _timeline_fingerprint(timeline):
    rows = []
    for track_type in ("video", "audio"):
        for track_index in range(1, timeline.GetTrackCount(track_type) + 1):
            for item in timeline.GetItemListInTrack(track_type, track_index) or []:
                try:
                    rows.append(
                        (
                            track_type,
                            track_index,
                            item.GetUniqueId(),
                            float(item.GetStart(True)),
                            float(item.GetEnd(True)),
                            item.GetName(),
                        )
                    )
                except Exception:
                    rows.append((track_type, track_index, item.GetName()))
    return tuple(sorted(rows, key=str))


def _pick_image_sequence_codec(project):
    formats = project.GetRenderFormats() or {}
    preferred_extensions = ("png",)
    for extension in preferred_extensions:
        for format_name, format_extension in formats.items():
            if str(format_extension).lower().lstrip(".") != extension:
                continue
            codecs = (
                project.GetRenderCodecs(format_extension)
                or project.GetRenderCodecs(format_name)
                or {}
            )
            if not codecs:
                continue
            for codec_name, codec_id in codecs.items():
                if extension == "png" and "16" in str(codec_name):
                    continue
                return str(format_extension), codec_id, extension
            return str(format_extension), next(iter(codecs.values())), extension
    raise OpenRotoError("Resolve does not expose a PNG image-sequence renderer.")


def _normalise_rendered_frames(frames_dir, extension, expected_count):
    files = sorted(
        frames_dir.glob(f"*.{extension}"),
        key=lambda path: [
            int(value) if value.isdigit() else value.lower()
            for value in re.split(r"(\d+)", path.name)
        ],
    )
    if len(files) != expected_count:
        raise OpenRotoError(
            f"Resolve rendered {len(files)} frames, but the clip contains {expected_count}."
        )
    staged = []
    for index, source in enumerate(files):
        temporary = frames_dir / f".__openroto_{index:08d}.{extension}"
        source.replace(temporary)
        staged.append(temporary)
    for index, temporary in enumerate(staged):
        destination = frames_dir / f"{index:08d}.{extension}"
        temporary.replace(destination)
    return f"%08d.{extension}"


def _export_target(resolve_api, project, timeline, track_index, start, end, frames_dir):
    preset_name = f"__OpenRoto_{uuid.uuid4().hex}"
    temporary_timeline = None
    job_id = None
    saved_preset = False
    original_format = project.GetCurrentRenderFormatAndCodec() or {}
    original_mode = project.GetCurrentRenderMode()
    try:
        saved_preset = bool(project.SaveAsNewRenderPreset(preset_name))
        if not saved_preset:
            raise OpenRotoError(
                "Resolve could not snapshot the current render settings, so OpenRoto "
                "stopped before changing them."
            )
        temporary_timeline = timeline.DuplicateTimeline(f"__OpenRoto Export {uuid.uuid4().hex[:8]}")
        if temporary_timeline is None:
            raise OpenRotoError("Resolve could not create the isolated export timeline.")
        if not project.SetCurrentTimeline(temporary_timeline):
            raise OpenRotoError("Resolve could not activate the isolated export timeline.")

        for index in range(1, temporary_timeline.GetTrackCount("video") + 1):
            temporary_timeline.SetTrackEnable("video", index, index == track_index)
        for index in range(1, temporary_timeline.GetTrackCount("audio") + 1):
            temporary_timeline.SetTrackEnable("audio", index, False)

        format_name, codec_id, extension = _pick_image_sequence_codec(project)
        if not project.SetCurrentRenderFormatAndCodec(format_name, codec_id):
            raise OpenRotoError("Resolve rejected the OpenRoto image-sequence format.")
        project.SetCurrentRenderMode(1)
        settings = {
            "SelectAllFrames": False,
            "MarkIn": start,
            "MarkOut": end - 1,
            "TargetDir": str(frames_dir),
            "CustomName": "frame",
            "UseUniqueFilenames": False,
            "ExportVideo": True,
            "ExportAudio": False,
        }
        if not project.SetRenderSettings(settings):
            raise OpenRotoError("Resolve rejected the OpenRoto render range.")
        job_id = project.AddRenderJob()
        if not job_id:
            raise OpenRotoError("Resolve could not add the temporary OpenRoto render job.")
        if not project.StartRendering([job_id], False):
            raise OpenRotoError("Resolve could not start the OpenRoto frame export.")

        deadline = time.monotonic() + RENDER_TIMEOUT_SECONDS
        while project.IsRenderingInProgress():
            if time.monotonic() > deadline:
                project.StopRendering()
                raise OpenRotoError("Frame export timed out.")
            time.sleep(0.25)
        status = project.GetRenderJobStatus(job_id) or {}
        if status.get("JobStatus") != "Complete":
            error = status.get("Error") or status.get("JobStatus") or "unknown render error"
            raise OpenRotoError(f"Resolve frame export failed: {error}")
        return _normalise_rendered_frames(frames_dir, extension, end - start)
    finally:
        if job_id:
            with contextlib.suppress(Exception):
                project.DeleteRenderJob(job_id)
        with contextlib.suppress(Exception):
            project.SetCurrentTimeline(timeline)
        if temporary_timeline is not None:
            with contextlib.suppress(Exception):
                project.GetMediaPool().DeleteTimelines([temporary_timeline])
        if saved_preset:
            with contextlib.suppress(Exception):
                project.LoadRenderPreset(preset_name)
                project.DeleteRenderPreset(preset_name)
        elif original_format:
            with contextlib.suppress(Exception):
                project.SetCurrentRenderFormatAndCodec(
                    original_format.get("format"), original_format.get("codec")
                )
        with contextlib.suppress(Exception):
            project.SetCurrentRenderMode(original_mode)


def _fusion_comp_text(mask_path, frame_count, width, height):
    filename = str(mask_path).replace("\\", "\\\\").replace('"', '\\"')
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
        OpenRotoMask = Loader {{
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
            ViewInfo = OperatorInfo {{ Pos = {{ 0, 110 }} }},
        }},
        Transparent = Background {{
            Inputs = {{
                GlobalOut = Input {{ Value = {last} }},
                Width = Input {{ Value = {width} }},
                Height = Input {{ Value = {height} }},
                TopLeftAlpha = Input {{ Value = 0 }},
            }},
            ViewInfo = OperatorInfo {{ Pos = {{ 110, -55 }} }},
        }},
        ApplyOpenRotoMask = Merge {{
            Inputs = {{
                Background = Input {{ SourceOp = "Transparent", Source = "Output" }},
                Foreground = Input {{ SourceOp = "MediaIn1", Source = "Output" }},
                EffectMask = Input {{ SourceOp = "OpenRotoMask", Source = "Output" }},
                PerformDepthMerge = Input {{ Value = 0 }},
            }},
            ViewInfo = OperatorInfo {{ Pos = {{ 220, 0 }} }},
        }},
        MediaOut1 = MediaOut {{
            Inputs = {{ Input = Input {{ SourceOp = "ApplyOpenRotoMask", Source = "Output" }} }},
            ViewInfo = OperatorInfo {{ Pos = {{ 330, 0 }} }},
        }}
    }}
}}
'''


def _restore_timeline(project, broken_timeline, snapshot_path, original_name):
    media_pool = project.GetMediaPool()
    restored = media_pool.ImportTimelineFromFile(str(snapshot_path))
    if restored is None:
        return False
    try:
        broken_timeline.SetName(f"__OpenRoto failed {uuid.uuid4().hex[:6]}")
        restored.SetName(original_name)
        project.SetCurrentTimeline(restored)
        media_pool.DeleteTimelines([broken_timeline])
        return True
    except Exception:
        return False


def _apply_matte(project, timeline, target, manifest, matte_dir):
    current = project.GetCurrentTimeline()
    if current is None or current.GetUniqueId() != manifest["timeline_id"]:
        raise OpenRotoError(
            "Return to the original timeline before applying the OpenRoto matte."
        )
    if target.GetUniqueId() != manifest["clip_id"]:
        raise OpenRotoError("The original clip is no longer available on the timeline.")
    moved = _as_int(target.GetStart()) != manifest["record_start"]
    trimmed = _as_int(target.GetEnd()) != manifest["record_end"]
    if moved or trimmed:
        raise OpenRotoError("The target clip was moved or trimmed while OpenRoto was open.")

    expected_count = manifest["record_end"] - manifest["record_start"]
    missing = [
        index
        for index in range(expected_count)
        if not (Path(matte_dir) / f"matte_{index:08d}.png").is_file()
    ]
    if missing:
        first = missing[0] + 1
        raise OpenRotoError(f"The rendered matte is incomplete at frame {first}.")

    first_mask = Path(matte_dir) / "matte_00000000.png"
    comp_path = Path(manifest["matte_dir"]) / "OpenRoto.comp"
    comp_path.write_text(
        _fusion_comp_text(
            first_mask,
            expected_count,
            manifest["width"],
            manifest["height"],
        ),
        encoding="utf-8",
    )

    expected_linked_ids = set(manifest.get("linked_item_ids", []))
    current_linked_items = []
    try:
        current_linked_items = list(target.GetLinkedItems() or [])
        current_linked_ids = {item.GetUniqueId() for item in current_linked_items}
        if current_linked_ids != expected_linked_ids:
            raise OpenRotoError(
                "The target clip's linked audio changed while OpenRoto was open."
            )
        linked = []
        for item in current_linked_items:
            if (
                item.GetType() == "audio"
                and _as_int(item.GetStart()) == manifest["record_start"]
                and _as_int(item.GetEnd()) == manifest["record_end"]
            ):
                linked.append(item)
    except OpenRotoError:
        raise
    except Exception as error:
        raise OpenRotoError("Resolve could not validate the clip's linked audio.") from error
    compound = timeline.CreateCompoundClip(
        [target] + linked,
        {"name": f"OpenRoto — {_safe_name(manifest['clip_name'])}"},
    )
    if compound is None:
        raise OpenRotoError("Resolve could not create the non-destructive OpenRoto compound clip.")
    try:
        composition = compound.ImportFusionComp(str(comp_path))
    except Exception as error:
        raise TimelineMutationError(
            "Resolve could not attach the OpenRoto Fusion composition."
        ) from error
    if composition is None:
        raise TimelineMutationError("Resolve could not attach the OpenRoto Fusion composition.")
    with contextlib.suppress(Exception):
        compound.SetClipColor("Sky")
    return compound


def _send(connection, message_type, **payload):
    value = {"type": message_type, **payload}
    connection.sendall((json.dumps(value, separators=(",", ":")) + "\n").encode("utf-8"))


def _read_messages(connection):
    buffer = b""
    while True:
        try:
            chunk = connection.recv(65536)
        except TimeoutError:
            continue
        if not chunk:
            return
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            if not line:
                continue
            value = json.loads(line.decode("utf-8"))
            if isinstance(value, dict):
                yield value


def run():
    resolve_api = _resolve_instance()
    if resolve_api is None:
        raise OpenRotoError("DaVinci Resolve is not available.")
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
    ) = _target_context(resolve_api)
    application = _find_application()
    session_id = uuid.uuid4().hex
    token = secrets.token_urlsafe(32)
    root = _session_root(session_id)
    frames_dir = root / "frames"
    matte_dir = root / "matte"
    frames_dir.mkdir(parents=True, exist_ok=False)
    matte_dir.mkdir(parents=True, exist_ok=True)
    try:
        _check_disk_space(root, width, height, end - start)
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise
    snapshot_path = root / f"{_safe_name(timeline.GetName())}.drt"
    if not timeline.Export(str(snapshot_path), resolve_api.EXPORT_DRT, resolve_api.EXPORT_NONE):
        raise OpenRotoError("Resolve could not create the safety snapshot.")
    fingerprint = _timeline_fingerprint(timeline)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((LOOPBACK, 0))
    server.listen(1)
    server.settimeout(ACCEPT_TIMEOUT_SECONDS)
    port = server.getsockname()[1]

    keep_session = False
    applied = False
    try:
        frame_pattern = _export_target(
            resolve_api, project, timeline, track_index, start, end, frames_dir
        )
        linked_ids = []
        with contextlib.suppress(Exception):
            linked_ids = [item.GetUniqueId() for item in target.GetLinkedItems() or []]
        manifest = {
            "schema_version": PROTOCOL_VERSION,
            "session_id": session_id,
            "token": token,
            "bridge_host": LOOPBACK,
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
            "source_start": _as_int(target.GetSourceStartFrame()),
            "source_end": _as_int(target.GetSourceEndFrame()),
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
        _atomic_json(manifest_path, manifest)
        subprocess.Popen(
            [str(application), "--session", str(manifest_path)],
            cwd=str(application.parent),
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
        connection, _ = server.accept()
        connection.settimeout(0.5)
        with connection:
            authenticated = False
            for message in _read_messages(connection):
                if not secrets.compare_digest(str(message.get("token", "")), token):
                    _send(connection, "error", message="OpenRoto session authentication failed.")
                    return
                if message.get("type") == "hello":
                    if _as_int(message.get("protocol")) != PROTOCOL_VERSION:
                        _send(
                            connection,
                            "error",
                            message="This OpenRoto app uses an incompatible bridge protocol.",
                        )
                        return
                    authenticated = True
                    _send(connection, "ready", session_id=session_id)
                    continue
                if not authenticated:
                    _send(connection, "error", message="OpenRoto handshake is incomplete.")
                    continue
                if message.get("type") == "cancel":
                    return
                if message.get("type") != "apply":
                    continue
                if message.get("session_id") != session_id:
                    _send(connection, "error", message="Session ID mismatch.")
                    continue
                if _timeline_fingerprint(timeline) != fingerprint:
                    _send(
                        connection,
                        "error",
                        message=(
                            "The timeline changed while OpenRoto was open. Start a new "
                            "session to avoid applying the matte to the wrong edit."
                        ),
                    )
                    keep_session = True
                    return
                requested_matte = Path(str(message.get("matte_dir", ""))).resolve()
                if requested_matte.parent != matte_dir.resolve() or requested_matte.name != "final":
                    _send(connection, "error", message="Matte path is outside this session.")
                    keep_session = True
                    return
                if _as_int(message.get("frame_count")) != end - start:
                    _send(connection, "error", message="Matte frame count does not match the clip.")
                    keep_session = True
                    return
                _send(connection, "progress", progress=0.2, message="Creating Resolve compound")
                keep_session = True
                try:
                    _apply_matte(project, timeline, target, manifest, requested_matte)
                except Exception as error:
                    suffix = ""
                    if isinstance(error, TimelineMutationError):
                        restored = _restore_timeline(
                            project, timeline, snapshot_path, manifest["timeline_name"]
                        )
                        suffix = (
                            " The timeline snapshot was restored."
                            if restored
                            else " The safety DRT remains in the OpenRoto session folder."
                        )
                    _send(connection, "error", message=str(error) + suffix)
                    return
                _send(connection, "completed", session_id=session_id)
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
    _bootstrap_log(
        "entered Python bridge"
        f" (__name__={__name__!r}, resolve={globals().get('resolve') is not None},"
        f" app={globals().get('app') is not None}, fusion={globals().get('fusion') is not None})"
    )
    try:
        run()
    except Exception as error:
        traceback.print_exc()
        _message("Could not start", str(error), error=True)
