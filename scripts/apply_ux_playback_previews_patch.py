from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Patch anchor not found in {path}: {old[:80]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


# --- Controller: non-blocking preview cache, progressive masks, viewer proxies. ---
controller = "app/openroto/ui/controller.py"
replace_once(controller, "import shutil\n", "import os\nimport shutil\n")
replace_once(
    controller,
    "    workerTiming = Signal(str, float)\n    operationFinished = Signal(str, str)\n",
    "    workerTiming = Signal(str, float)\n"
    "    workerMaskReady = Signal(int)\n"
    "    previewRendered = Signal(int, int)\n"
    "    viewerFrameReady = Signal(int)\n"
    "    operationFinished = Signal(str, str)\n",
)
replace_once(
    controller,
    "        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=\"OpenRoto\")\n",
    "        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=\"OpenRoto\")\n"
    "        self._preview_executor = ThreadPoolExecutor(\n"
    "            max_workers=1, thread_name_prefix=\"OpenRotoPreview\"\n"
    "        )\n"
    "        self._viewer_executor = ThreadPoolExecutor(\n"
    "            max_workers=2, thread_name_prefix=\"OpenRotoViewer\"\n"
    "        )\n"
    "        self._preview_settings_revision = 0\n"
    "        self._preview_versions: dict[int, int] = {}\n"
    "        self._viewer_pending: set[int] = set()\n",
)
replace_once(
    controller,
    "        self._preview_dir = Path(manifest.matte_dir) / \"preview\"\n"
    "        self._raw_dir.mkdir(parents=True, exist_ok=True)\n"
    "        self._preview_dir.mkdir(parents=True, exist_ok=True)\n",
    "        self._preview_dir = Path(manifest.matte_dir) / \"preview\"\n"
    "        self._viewer_dir = Path(manifest.matte_dir) / \"viewer\"\n"
    "        self._raw_dir.mkdir(parents=True, exist_ok=True)\n"
    "        self._preview_dir.mkdir(parents=True, exist_ok=True)\n"
    "        self._viewer_dir.mkdir(parents=True, exist_ok=True)\n",
)
replace_once(
    controller,
    "        self.workerProgress.connect(self._set_progress_from_worker)\n"
    "        self.workerTiming.connect(self._set_timing_from_worker)\n"
    "        self.operationFinished.connect(self._finish_operation)\n",
    "        self.workerProgress.connect(self._set_progress_from_worker)\n"
    "        self.workerTiming.connect(self._set_timing_from_worker)\n"
    "        self.workerMaskReady.connect(self._on_worker_mask_ready)\n"
    "        self.previewRendered.connect(self._on_preview_rendered)\n"
    "        self.viewerFrameReady.connect(self._on_viewer_frame_ready)\n"
    "        self.operationFinished.connect(self._finish_operation)\n",
)
replace_once(
    controller,
    "        self._theme_timer = QTimer(self)\n",
    "        self._preview_timer = QTimer(self)\n"
    "        self._preview_timer.setSingleShot(True)\n"
    "        self._preview_timer.setInterval(120)\n"
    "        self._preview_timer.timeout.connect(self._queue_current_preview)\n"
    "        self._theme_timer = QTimer(self)\n",
)
replace_once(
    controller,
    "        self._theme_timer.start()\n",
    "        self._theme_timer.start()\n"
    "        QTimer.singleShot(0, lambda: self._queue_viewer_prefetch(self._current_frame))\n",
)
replace_once(
    controller,
    "    @Property(str, notify=frameChanged)\n"
    "    def frameLabel(self) -> str:\n"
    "        return f\"{self._current_frame + 1} / {self.manifest.frame_count}\"\n\n"
    "    @Property(QUrl, notify=frameChanged)\n"
    "    def currentFrameUrl(self) -> QUrl:\n"
    "        path = self._frame_path(self._current_frame)\n"
    "        return QUrl.fromLocalFile(str(path))\n",
    "    @Property(str, notify=frameChanged)\n"
    "    def frameLabel(self) -> str:\n"
    "        return f\"{self._current_frame + 1} / {self.manifest.frame_count}\"\n\n"
    "    @Property(float, constant=True)\n"
    "    def clipFps(self) -> float:\n"
    "        return float(self.manifest.fps)\n\n"
    "    @Property(QUrl, notify=frameChanged)\n"
    "    def currentFrameUrl(self) -> QUrl:\n"
    "        return self._viewer_frame_url(self._current_frame)\n\n"
    "    @Slot(int, result=QUrl)\n"
    "    def frameUrlAt(self, frame: int) -> QUrl:\n"
    "        bounded = max(0, min(int(frame), self.manifest.frame_count - 1))\n"
    "        return self._viewer_frame_url(bounded)\n",
)
replace_once(
    controller,
    "    def currentMaskUrl(self) -> QUrl:\n"
    "        path = self._preview_path(self._current_frame)\n"
    "        if not path.exists():\n"
    "            return QUrl()\n"
    "        url = QUrl.fromLocalFile(str(path))\n"
    "        url.setQuery(f\"v={self._mask_revision}\")\n"
    "        return url\n",
    "    def currentMaskUrl(self) -> QUrl:\n"
    "        frame = self._current_frame\n"
    "        preview = self._preview_path(frame)\n"
    "        if (\n"
    "            self._preview_versions.get(frame) == self._preview_settings_revision\n"
    "            and preview.exists()\n"
    "        ):\n"
    "            path = preview\n"
    "        else:\n"
    "            path = self._raw_path(frame)\n"
    "        if not path.exists():\n"
    "            return QUrl()\n"
    "        url = QUrl.fromLocalFile(str(path))\n"
    "        url.setQuery(f\"v={self._mask_revision}\")\n"
    "        return url\n",
)
replace_once(
    controller,
    "        self._current_frame = bounded\n"
    "        self._refresh_preview()\n"
    "        self.frameChanged.emit()\n"
    "        self.pointsChanged.emit()\n"
    "        self.maskChanged.emit()\n",
    "        self._current_frame = bounded\n"
    "        self.frameChanged.emit()\n"
    "        self.pointsChanged.emit()\n"
    "        self.maskChanged.emit()\n"
    "        self._schedule_preview_refresh()\n"
    "        self._queue_viewer_prefetch(bounded)\n",
)
replace_once(
    controller,
    "        self._preview_path(self._current_frame).unlink(missing_ok=True)\n"
    "        self.pointsChanged.emit()\n",
    "        self._preview_path(self._current_frame).unlink(missing_ok=True)\n"
    "        self._preview_versions.pop(self._current_frame, None)\n"
    "        self.pointsChanged.emit()\n",
)
replace_once(
    controller,
    "        self._matte_settings.expand_contract = max(-32, min(32, int(value)))\n"
    "        self.changed.emit()\n"
    "        self._refresh_preview()\n",
    "        self._matte_settings.expand_contract = max(-32, min(32, int(value)))\n"
    "        self.changed.emit()\n"
    "        self._invalidate_preview_settings()\n",
)
replace_once(
    controller,
    "        self._matte_settings.feather = max(0.0, min(64.0, float(value)))\n"
    "        self.changed.emit()\n"
    "        self._refresh_preview()\n",
    "        self._matte_settings.feather = max(0.0, min(64.0, float(value)))\n"
    "        self.changed.emit()\n"
    "        self._invalidate_preview_settings()\n",
)
replace_once(
    controller,
    "        self._matte_settings.invert = bool(value)\n"
    "        self.changed.emit()\n"
    "        self._refresh_preview()\n",
    "        self._matte_settings.invert = bool(value)\n"
    "        self.changed.emit()\n"
    "        self._invalidate_preview_settings()\n",
)
replace_once(
    controller,
    "        self._theme_timer.stop()\n",
    "        self._theme_timer.stop()\n"
    "        self._preview_timer.stop()\n",
)
replace_once(
    controller,
    "            self._bridge.close()\n"
    "            self._executor.shutdown(wait=False, cancel_futures=True)\n",
    "            self._bridge.close()\n"
    "            self._executor.shutdown(wait=False, cancel_futures=True)\n"
    "            self._preview_executor.shutdown(wait=False, cancel_futures=True)\n"
    "            self._viewer_executor.shutdown(wait=False, cancel_futures=True)\n",
)
replace_once(
    controller,
    "        self._engine.segment_frame(frame, points, self._model_preset, self._worker_progress)\n"
    "        self._refresh_preview(frame)\n",
    "        self._engine.segment_frame(frame, points, self._model_preset, self._worker_progress)\n"
    "        self.workerMaskReady.emit(frame)\n",
)
replace_once(
    controller,
    "            self._direction,\n"
    "            self._worker_progress,\n"
    "        )\n"
    "        self._tracking_dirty = False\n"
    "        self.trackingStateChanged.emit()\n"
    "        self._refresh_preview(self._current_frame)\n",
    "            self._direction,\n"
    "            self._worker_progress,\n"
    "            frame_ready=self.workerMaskReady.emit,\n"
    "        )\n"
    "        self._tracking_dirty = False\n"
    "        self.trackingStateChanged.emit()\n",
)
old_refresh = '''    def _refresh_preview(self, frame: int | None = None) -> None:\n        frame_index = self._current_frame if frame is None else frame\n        raw = self._raw_path(frame_index)\n        if raw.exists():\n            started_ns = time.perf_counter_ns()\n            try:\n                render_preview(raw, self._preview_path(frame_index), self._matte_settings)\n            finally:\n                self.workerTiming.emit(\n                    "preview", (time.perf_counter_ns() - started_ns) / 1_000_000.0\n                )\n            self._mask_revision += 1\n            self.maskChanged.emit()\n'''
new_refresh = '''    def _invalidate_preview_settings(self) -> None:\n        self._preview_settings_revision += 1\n        self._preview_versions.clear()\n        self._mask_revision += 1\n        self.maskChanged.emit()\n        self._schedule_preview_refresh()\n\n    def _schedule_preview_refresh(self) -> None:\n        if self._closed or not self._raw_path(self._current_frame).exists():\n            return\n        self._preview_timer.start()\n\n    @Slot()\n    def _queue_current_preview(self) -> None:\n        if self._closed:\n            return\n        frame = self._current_frame\n        raw = self._raw_path(frame)\n        if not raw.exists():\n            return\n        revision = self._preview_settings_revision\n        settings = MatteSettings(\n            invert=self._matte_settings.invert,\n            expand_contract=self._matte_settings.expand_contract,\n            feather=self._matte_settings.feather,\n            overlay_opacity=self._matte_settings.overlay_opacity,\n        )\n        self._preview_executor.submit(self._render_preview_job, frame, revision, settings)\n\n    def _render_preview_job(\n        self, frame: int, revision: int, settings: MatteSettings\n    ) -> None:\n        raw = self._raw_path(frame)\n        if not raw.exists():\n            return\n        started_ns = time.perf_counter_ns()\n        try:\n            render_preview(raw, self._preview_path(frame), settings)\n        except (FileNotFoundError, OSError):\n            return\n        finally:\n            self.workerTiming.emit(\n                "preview", (time.perf_counter_ns() - started_ns) / 1_000_000.0\n            )\n        self.previewRendered.emit(frame, revision)\n\n    @Slot(int, int)\n    def _on_preview_rendered(self, frame: int, revision: int) -> None:\n        if revision != self._preview_settings_revision:\n            return\n        if not self._preview_path(frame).exists():\n            return\n        self._preview_versions[frame] = revision\n        if frame == self._current_frame:\n            self._mask_revision += 1\n            self.maskChanged.emit()\n\n    @Slot(int)\n    def _on_worker_mask_ready(self, frame: int) -> None:\n        self._preview_versions.pop(frame, None)\n        if frame != self._current_frame:\n            return\n        self._mask_revision += 1\n        self.maskChanged.emit()\n        self._schedule_preview_refresh()\n\n    def _viewer_frame_url(self, frame: int) -> QUrl:\n        proxy = self._viewer_path(frame)\n        path = proxy if proxy.exists() else self._frame_path(frame)\n        return QUrl.fromLocalFile(str(path))\n\n    def _queue_viewer_prefetch(self, center: int) -> None:\n        if self._closed:\n            return\n        for frame in (center, center + 1, center + 2, center - 1):\n            if not 0 <= frame < self.manifest.frame_count:\n                continue\n            if self._viewer_path(frame).exists() or frame in self._viewer_pending:\n                continue\n            self._viewer_pending.add(frame)\n            self._viewer_executor.submit(self._build_viewer_proxy, frame)\n\n    def _build_viewer_proxy(self, frame: int) -> None:\n        try:\n            from PIL import Image\n\n            source = self._frame_path(frame)\n            destination = self._viewer_path(frame)\n            with Image.open(source) as loaded:\n                if loaded.width <= 1920 and loaded.height <= 1080:\n                    return\n                image = loaded.convert("RGB")\n                image.thumbnail((1920, 1080), Image.Resampling.LANCZOS)\n                temporary = destination.with_suffix(".tmp.jpg")\n                image.save(\n                    temporary,\n                    format="JPEG",\n                    quality=91,\n                    subsampling=0,\n                    optimize=False,\n                )\n                os.replace(temporary, destination)\n        except (FileNotFoundError, OSError):\n            return\n        finally:\n            self.viewerFrameReady.emit(frame)\n\n    @Slot(int)\n    def _on_viewer_frame_ready(self, frame: int) -> None:\n        self._viewer_pending.discard(frame)\n'''
replace_once(controller, old_refresh, new_refresh)
replace_once(
    controller,
    "    def _preview_path(self, frame: int) -> Path:\n"
    "        return self._preview_dir / f\"preview_{frame:08d}.png\"\n",
    "    def _preview_path(self, frame: int) -> Path:\n"
    "        return self._preview_dir / f\"preview_{frame:08d}.png\"\n\n"
    "    def _viewer_path(self, frame: int) -> Path:\n"
    "        return self._viewer_dir / f\"frame_{frame:08d}.jpg\"\n",
)

# --- SAM2: publish masks as soon as each tracked frame exists. ---
sam2 = "app/openroto/inference/sam2_engine.py"
replace_once(
    sam2,
    "TimingCallback = Callable[[str, float], None]\n",
    "TimingCallback = Callable[[str, float], None]\nFrameReadyCallback = Callable[[int], None]\n",
)
replace_once(
    sam2,
    "        progress: ProgressCallback | None = None,\n    ) -> None:\n",
    "        progress: ProgressCallback | None = None,\n"
    "        *,\n"
    "        frame_ready: FrameReadyCallback | None = None,\n"
    "    ) -> None:\n",
)
replace_once(
    sam2,
    "                completed.add(frame)\n\n            seed = min(prompts)\n",
    "                completed.add(frame)\n"
    "                if frame_ready is not None:\n"
    "                    frame_ready(frame)\n\n"
    "            seed = min(prompts)\n",
)
replace_once(
    sam2,
    "                        completed.add(frame_index)\n"
    "                        if progress:\n",
    "                        completed.add(frame_index)\n"
    "                        if frame_ready is not None:\n"
    "                            frame_ready(frame_index)\n"
    "                        if progress:\n",
)

# --- QML: retained frames, playback, prefetch, non-modal tracking progress. ---
qml = "app/openroto/ui/PolishedMain.qml"
replace_once(
    qml,
    "    readonly property bool compactMode: window.width < 1120\n",
    "    readonly property bool compactMode: window.width < 1120\n"
    "    property bool playing: false\n"
    "    readonly property int playbackInterval: Math.max(16, Math.round(1000 / Math.max(1, window.appController.clipFps)))\n",
)
replace_once(
    qml,
    "    function resetViewer() {\n"
    "        imageStack.zoom = 1\n"
    "        imageStack.x = 0\n"
    "        imageStack.y = 0\n"
    "    }\n",
    "    function resetViewer() {\n"
    "        imageStack.zoom = 1\n"
    "        imageStack.x = 0\n"
    "        imageStack.y = 0\n"
    "    }\n\n"
    "    function togglePlayback() {\n"
    "        if (window.playing) {\n"
    "            window.playing = false\n"
    "            return\n"
    "        }\n"
    "        if (window.appController.currentFrame >= window.appController.frameCount - 1)\n"
    "            window.appController.setFrame(0)\n"
    "        window.playing = true\n"
    "    }\n\n"
    "    function advancePlayback() {\n"
    "        const next = window.appController.currentFrame + 1\n"
    "        if (next >= window.appController.frameCount) {\n"
    "            window.playing = false\n"
    "            return\n"
    "        }\n"
    "        window.appController.setFrame(next)\n"
    "    }\n\n"
    "    Timer {\n"
    "        id: playbackTimer\n"
    "        interval: window.playbackInterval\n"
    "        repeat: true\n"
    "        running: window.playing && !window.modelManager.busy\n"
    "        onTriggered: window.advancePlayback()\n"
    "    }\n",
)
replace_once(
    qml,
    "                                    asynchronous: true\n"
    "                                    cache: true\n"
    "                                    smooth: true\n"
    "                                }\n\n"
    "                                Item {\n",
    "                                    asynchronous: true\n"
    "                                    retainWhileLoading: true\n"
    "                                    cache: true\n"
    "                                    smooth: true\n"
    "                                }\n"
    "                                Image {\n"
    "                                    visible: false\n"
    "                                    source: window.appController.currentFrame + 1 < window.appController.frameCount\n"
    "                                        ? window.appController.frameUrlAt(window.appController.currentFrame + 1) : \"\"\n"
    "                                    asynchronous: true\n"
    "                                    cache: true\n"
    "                                }\n"
    "                                Image {\n"
    "                                    visible: false\n"
    "                                    source: window.appController.currentFrame + 2 < window.appController.frameCount\n"
    "                                        ? window.appController.frameUrlAt(window.appController.currentFrame + 2) : \"\"\n"
    "                                    asynchronous: true\n"
    "                                    cache: true\n"
    "                                }\n\n"
    "                                Item {\n",
)
replace_once(
    qml,
    "                                        fillMode: Image.Stretch\n"
    "                                        visible: false\n"
    "                                        cache: false\n",
    "                                        fillMode: Image.Stretch\n"
    "                                        visible: false\n"
    "                                        asynchronous: true\n"
    "                                        retainWhileLoading: true\n"
    "                                        cache: false\n",
)
old_busy = '''                            MultiEffect {\n                                anchors.fill: imageStack\n                                source: imageStack\n                                visible: window.appController.busy\n                                blurEnabled: true\n                                blur: 0.78\n                                blurMax: 48\n                                opacity: 0.96\n                            }\n                            Rectangle { anchors.fill: parent; visible: window.appController.busy; color: theme.scrim }\n                            GlassPanel {\n                                anchors.centerIn: parent\n                                width: Math.min(390, parent.width - 48)\n                                height: busyColumn.implicitHeight + 32\n                                visible: window.appController.busy\n                                theme: window.uiTheme\n                                strong: true\n                                elevated: true\n                                Column {\n                                    id: busyColumn\n                                    anchors.left: parent.left\n                                    anchors.right: parent.right\n                                    anchors.verticalCenter: parent.verticalCenter\n                                    anchors.leftMargin: theme.spaceLg\n                                    anchors.rightMargin: theme.spaceLg\n                                    spacing: theme.spaceSm\n                                    BusyIndicator { width: 24; height: 24; running: parent.parent.visible; anchors.horizontalCenter: parent.horizontalCenter }\n                                    Text {\n                                        width: parent.width\n                                        text: window.appController.status\n                                        color: theme.text\n                                        font.family: theme.fontFamily\n                                        font.pixelSize: 12\n                                        font.weight: Font.DemiBold\n                                        horizontalAlignment: Text.AlignHCenter\n                                        wrapMode: Text.WordWrap\n                                    }\n                                    Text {\n                                        width: parent.width\n                                        visible: text.length > 0\n                                        text: window.appController.detail\n                                        color: theme.textSecondary\n                                        font.family: theme.fontFamily\n                                        font.pixelSize: 10\n                                        horizontalAlignment: Text.AlignHCenter\n                                        wrapMode: Text.WordWrap\n                                    }\n                                    ProgressBar { width: parent.width; from: 0; to: 1; value: window.appController.progress }\n                                }\n                            }\n'''
new_busy = '''                            GlassPanel {\n                                anchors.top: parent.top\n                                anchors.right: parent.right\n                                anchors.topMargin: theme.spaceMd\n                                anchors.rightMargin: theme.spaceMd\n                                width: Math.min(360, parent.width - theme.spaceLg * 2)\n                                height: 58\n                                visible: window.appController.busy\n                                theme: window.uiTheme\n                                strong: true\n                                elevated: true\n                                RowLayout {\n                                    anchors.fill: parent\n                                    anchors.margins: theme.spaceSm\n                                    spacing: theme.spaceSm\n                                    BusyIndicator { Layout.preferredWidth: 20; Layout.preferredHeight: 20; running: parent.parent.visible }\n                                    ColumnLayout {\n                                        Layout.fillWidth: true\n                                        spacing: 2\n                                        Text {\n                                            Layout.fillWidth: true\n                                            text: window.appController.status\n                                            color: theme.text\n                                            font.family: theme.fontFamily\n                                            font.pixelSize: 10\n                                            font.weight: Font.DemiBold\n                                            elide: Text.ElideRight\n                                        }\n                                        ProgressBar {\n                                            Layout.fillWidth: true\n                                            from: 0\n                                            to: 1\n                                            value: window.appController.progress\n                                        }\n                                    }\n                                    Text {\n                                        text: Math.round(window.appController.progress * 100) + "%"\n                                        color: theme.textSecondary\n                                        font.family: theme.monoFontFamily\n                                        font.pixelSize: 9\n                                    }\n                                }\n                            }\n'''
replace_once(qml, old_busy, new_busy)
replace_once(
    qml,
    "                                    enabled: !window.blocked && window.appController.currentFrame > 0\n"
    "                                    onClicked: window.appController.setFrame(window.appController.currentFrame - 1)\n"
    "                                }\n"
    "                                Text {\n",
    "                                    enabled: !window.modelManager.busy && window.appController.currentFrame > 0\n"
    "                                    onClicked: {\n"
    "                                        window.playing = false\n"
    "                                        window.appController.setFrame(window.appController.currentFrame - 1)\n"
    "                                    }\n"
    "                                }\n"
    "                                RotoButton {\n"
    "                                    theme: window.uiTheme\n"
    "                                    width: window.compactMode ? 44 : 34; height: window.compactMode ? 44 : 34; leftPadding: 0; rightPadding: 0\n"
    "                                    quiet: true\n"
    "                                    text: window.playing ? \"Ⅱ\" : \"▶\"\n"
    "                                    font.pixelSize: window.playing ? 15 : 13\n"
    "                                    toolTip: window.playing ? \"Pause · Space\" : \"Play · Space\"\n"
    "                                    enabled: !window.modelManager.busy && window.appController.frameCount > 1\n"
    "                                    onClicked: window.togglePlayback()\n"
    "                                }\n"
    "                                Text {\n",
)
replace_once(
    qml,
    "                                    enabled: !window.blocked\n"
    "                                    toolTip: window.appController.frameLabel\n"
    "                                    onMoved: window.appController.setFrame(Math.round(value))\n",
    "                                    enabled: !window.modelManager.busy\n"
    "                                    toolTip: window.appController.frameLabel\n"
    "                                    onPressedChanged: { if (pressed) window.playing = false }\n"
    "                                    onMoved: window.appController.setFrame(Math.round(value))\n",
)
replace_once(
    qml,
    "                                    enabled: !window.blocked && window.appController.currentFrame < window.appController.frameCount - 1\n"
    "                                    onClicked: window.appController.setFrame(window.appController.currentFrame + 1)\n",
    "                                    enabled: !window.modelManager.busy && window.appController.currentFrame < window.appController.frameCount - 1\n"
    "                                    onClicked: {\n"
    "                                        window.playing = false\n"
    "                                        window.appController.setFrame(window.appController.currentFrame + 1)\n"
    "                                    }\n",
)
replace_once(
    qml,
    "    Shortcut { sequence: \"Ctrl+,\"; onActivated: window.settingsRequested() }\n",
    "    Shortcut { sequence: \"Ctrl+,\"; onActivated: window.settingsRequested() }\n"
    "    Shortcut { sequence: \"Space\"; onActivated: window.togglePlayback() }\n",
)
replace_once(
    qml,
    "    onClosing: close => {\n",
    "    onClosing: close => {\n"
    "        window.playing = false\n",
)

# --- CI and regression contract. ---
replace_once(
    ".github/workflows/windows-ci.yml",
    '      - "fix/**"\n',
    '      - "fix/**"\n      - ux-playback-previews\n',
)

test_path = ROOT / "tests" / "test_editor_ux_contract.py"
test_path.write_text(
    '''from __future__ import annotations\n\nimport inspect\nimport sys\nimport unittest\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\nsys.path.insert(0, str(ROOT / "app"))\n\nfrom openroto.inference.sam2_engine import Sam2Engine\nfrom openroto.ui.controller import ApplicationController\n\n\nclass EditorUxContractTests(unittest.TestCase):\n    def test_frame_navigation_never_renders_preview_synchronously(self):\n        source = inspect.getsource(ApplicationController.setFrame)\n        self.assertNotIn("_refresh_preview", source)\n        self.assertIn("_schedule_preview_refresh", source)\n        self.assertIn("_queue_viewer_prefetch", source)\n\n    def test_tracking_publishes_frames_progressively(self):\n        source = inspect.getsource(Sam2Engine.track)\n        self.assertIn("frame_ready", source)\n        self.assertIn("frame_ready(frame_index)", source)\n\n    def test_viewer_retains_frames_and_has_playback_prefetch(self):\n        qml = (ROOT / "app/openroto/ui/PolishedMain.qml").read_text(encoding="utf-8")\n        self.assertGreaterEqual(qml.count("retainWhileLoading: true"), 2)\n        self.assertIn("id: playbackTimer", qml)\n        self.assertIn("frameUrlAt(window.appController.currentFrame + 1)", qml)\n        self.assertNotIn("blurEnabled: true", qml)\n        self.assertIn('sequence: "Space"', qml)\n\n    def test_preview_processing_is_debounced_and_backgrounded(self):\n        source = inspect.getsource(ApplicationController)\n        self.assertIn("setInterval(120)", source)\n        self.assertIn("_preview_executor.submit", source)\n        self.assertIn("_preview_versions", source)\n        self.assertIn("_viewer_executor.submit", source)\n\n\nif __name__ == "__main__":\n    unittest.main()\n''',
    encoding="utf-8",
)

print("UX playback/preview patch applied")
