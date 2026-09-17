from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one match in {path}, found {count}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


polished = ROOT / "app" / "openroto" / "ui" / "PolishedMain.qml"
timed = ROOT / "app" / "openroto" / "ui" / "TimedMain.qml"
removal = ROOT / "app" / "openroto" / "ui" / "ObjectRemovalMain.qml"

replace_once(
    polished,
    """    width: 1360\n    height: 850\n    minimumWidth: 1120\n    minimumHeight: 700\n""",
    """    width: 1360\n    height: 850\n    minimumWidth: 900\n    minimumHeight: 480\n""",
)

replace_once(
    polished,
    """    readonly property bool blocked: window.appController.busy || window.modelManager.busy\n    readonly property int motionDuration: window.appController.reducedMotion ? 0 : 120\n""",
    """    readonly property bool blocked: window.appController.busy || window.modelManager.busy\n    readonly property int motionDuration: window.appController.reducedMotion ? 0 : 120\n    readonly property bool compactMode: window.width < 1120\n""",
)

replace_once(
    polished,
    """    property string viewerTitle: \"Viewer\"\n    property int sidePanelWidth: 332\n\n    signal settingsRequested()\n\n    function resetViewer() {\n""",
    """    property string viewerTitle: \"Viewer\"\n    property int sidePanelWidth: 332\n    property Component activeSidePanelComponent: window.customSidePanelComponent !== null\n        ? window.customSidePanelComponent : rotoscopeControlsComponent\n\n    signal settingsRequested()\n\n    function openCompactControls() {\n        if (window.compactMode)\n            controlsDrawer.open()\n    }\n\n    function resetViewer() {\n""",
)

replace_once(
    polished,
    """                            Text {\n                                width: Math.min(390, implicitWidth)\n                                text: window.appController.clipName + \"  ·  \" + window.appController.clipMeta\n""",
    """                            Text {\n                                visible: !window.compactMode\n                                width: Math.min(390, implicitWidth)\n                                text: window.appController.clipName + \"  ·  \" + window.appController.clipMeta\n""",
)

replace_once(
    polished,
    """                        StatusPill {\n                            theme: window.uiTheme\n                            label: window.appController.bridgeConnected ? \"Resolve linked\" : \"Resolve offline\"\n""",
    """                        StatusPill {\n                            theme: window.uiTheme\n                            compact: window.compactMode\n                            label: window.appController.bridgeConnected ? \"Resolve linked\" : \"Resolve offline\"\n""",
)

replace_once(
    polished,
    """                        StatusPill {\n                            theme: window.uiTheme\n                            label: window.appController.computeBadge\n                            dotColor: window.appController.computeDevice.indexOf(\"CUDA\") >= 0 ? theme.success : theme.warning\n                            toolTip: window.appController.computeDevice + \"\\n\" + window.appController.computeDetail\n                        }\n                        RotoButton {\n                            theme: window.uiTheme\n                            width: 34; height: 34; leftPadding: 0; rightPadding: 0\n                            quiet: true\n                            text: \"⚙\"\n""",
    """                        StatusPill {\n                            theme: window.uiTheme\n                            compact: window.compactMode\n                            label: window.appController.computeBadge\n                            dotColor: window.appController.computeDevice.indexOf(\"CUDA\") >= 0 ? theme.success : theme.warning\n                            toolTip: window.appController.computeDevice + \"\\n\" + window.appController.computeDetail\n                        }\n                        RotoButton {\n                            visible: window.compactMode\n                            theme: window.uiTheme\n                            width: 34; height: 34; leftPadding: 0; rightPadding: 0\n                            quiet: true\n                            text: \"☰\"\n                            font.family: \"Segoe UI Symbol\"; font.pixelSize: 15\n                            toolTip: \"Open controls\"\n                            onClicked: window.openCompactControls()\n                        }\n                        RotoButton {\n                            theme: window.uiTheme\n                            width: 34; height: 34; leftPadding: 0; rightPadding: 0\n                            quiet: true\n                            text: \"⚙\"\n""",
)

replace_once(
    polished,
    """                    Layout.fillWidth: true\n                    Layout.fillHeight: true\n                    Layout.minimumWidth: 700\n                    theme: window.uiTheme\n""",
    """                    Layout.fillWidth: true\n                    Layout.fillHeight: true\n                    Layout.minimumWidth: window.compactMode ? 0 : 700\n                    theme: window.uiTheme\n""",
)

replace_once(
    polished,
    """                                width: hintRow.implicitWidth + 24\n                                height: 32\n""",
    """                                width: Math.min(hintRow.implicitWidth + 24, parent.width - theme.spaceLg * 2)\n                                height: 32\n""",
)

replace_once(
    polished,
    """                                    spacing: theme.spaceLg\n                                    Row {\n                                        spacing: theme.spaceXs\n                                        SubjectMarker { width: 16; height: 16; positive: true; anchors.verticalCenter: parent.verticalCenter }\n                                        Text { text: \"Subject · Left click\"; color: theme.text; font.family: theme.fontFamily; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter }\n                                    }\n                                    Row {\n                                        spacing: theme.spaceXs\n                                        SubjectMarker { width: 16; height: 16; positive: false; anchors.verticalCenter: parent.verticalCenter }\n                                        Text { text: \"Exclude · Right click\"; color: theme.text; font.family: theme.fontFamily; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter }\n                                    }\n                                    Text { text: \"Wheel zoom · Middle drag\"; color: theme.textSecondary; font.family: theme.fontFamily; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter }\n""",
    """                                    spacing: window.compactMode ? theme.spaceSm : theme.spaceLg\n                                    Row {\n                                        spacing: theme.spaceXs\n                                        SubjectMarker { width: 16; height: 16; positive: true; anchors.verticalCenter: parent.verticalCenter }\n                                        Text {\n                                            text: window.compactMode ? \"Subject · LMB\" : \"Subject · Left click\"\n                                            color: theme.text; font.family: theme.fontFamily\n                                            font.pixelSize: window.compactMode ? 9 : 10\n                                            anchors.verticalCenter: parent.verticalCenter\n                                        }\n                                    }\n                                    Row {\n                                        spacing: theme.spaceXs\n                                        SubjectMarker { width: 16; height: 16; positive: false; anchors.verticalCenter: parent.verticalCenter }\n                                        Text {\n                                            text: window.compactMode ? \"Exclude · RMB\" : \"Exclude · Right click\"\n                                            color: theme.text; font.family: theme.fontFamily\n                                            font.pixelSize: window.compactMode ? 9 : 10\n                                            anchors.verticalCenter: parent.verticalCenter\n                                        }\n                                    }\n                                    Text {\n                                        text: window.compactMode ? \"Wheel · MMB drag\" : \"Wheel zoom · Middle drag\"\n                                        color: theme.textSecondary; font.family: theme.fontFamily\n                                        font.pixelSize: window.compactMode ? 9 : 10\n                                        anchors.verticalCenter: parent.verticalCenter\n                                    }\n""",
)

replace_once(
    polished,
    """                                    Layout.preferredWidth: 88\n                                    text: window.appController.frameLabel\n""",
    """                                    Layout.preferredWidth: window.compactMode ? 70 : 88\n                                    text: window.appController.frameLabel\n""",
)

replace_once(
    polished,
    """                Loader {\n                    Layout.preferredWidth: window.sidePanelWidth\n                    Layout.minimumWidth: window.sidePanelWidth\n                    Layout.maximumWidth: window.sidePanelWidth\n                    Layout.fillHeight: true\n                    sourceComponent: window.customSidePanelComponent !== null ? window.customSidePanelComponent : rotoscopeControlsComponent\n                }\n            }\n        }\n    }\n\n    Component {\n        id: rotoscopeControlsComponent\n""",
    """                Loader {\n                    visible: !window.compactMode\n                    Layout.preferredWidth: visible ? window.sidePanelWidth : 0\n                    Layout.minimumWidth: visible ? window.sidePanelWidth : 0\n                    Layout.maximumWidth: visible ? window.sidePanelWidth : 0\n                    Layout.fillHeight: true\n                    sourceComponent: visible ? window.activeSidePanelComponent : null\n                }\n            }\n        }\n    }\n\n    Drawer {\n        id: controlsDrawer\n        edge: Qt.RightEdge\n        width: Math.min(380, Math.max(300, window.width * 0.86))\n        height: window.height\n        modal: true\n        interactive: window.compactMode\n        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside\n\n        background: Rectangle {\n            color: theme.canvas\n            border.width: 1\n            border.color: theme.borderStrong\n        }\n\n        contentItem: Item {\n            Loader {\n                anchors.fill: parent\n                anchors.margins: theme.spaceSm\n                sourceComponent: window.compactMode ? window.activeSidePanelComponent : null\n            }\n        }\n    }\n\n    Component {\n        id: rotoscopeControlsComponent\n""",
)

replace_once(
    polished,
    """    Shortcut { sequence: \"Ctrl+Z\"; onActivated: window.appController.undo() }\n    Shortcut { sequence: \"Ctrl+Y\"; onActivated: window.appController.redo() }\n    Shortcut { sequence: \"Ctrl+,\"; onActivated: window.settingsRequested() }\n\n    onClosing: close => {\n""",
    """    Shortcut { sequence: \"Ctrl+Z\"; onActivated: window.appController.undo() }\n    Shortcut { sequence: \"Ctrl+Y\"; onActivated: window.appController.redo() }\n    Shortcut { sequence: \"Ctrl+,\"; onActivated: window.settingsRequested() }\n\n    onCompactModeChanged: {\n        if (!window.compactMode)\n            controlsDrawer.close()\n    }\n\n    onClosing: close => {\n""",
)

replace_once(
    timed,
    """        x: Math.max(18, Math.round((window.width - window.sidePanelWidth - width) / 2))\n        y: 80\n        width: Math.min(760, window.width - window.sidePanelWidth - 72)\n""",
    """        x: Math.max(18, Math.round(((window.compactMode ? window.width : window.width - window.sidePanelWidth) - width) / 2))\n        y: 80\n        width: Math.min(760, window.width - (window.compactMode ? 0 : window.sidePanelWidth) - 72)\n""",
)

replace_once(
    removal,
    """        GlassPanel {\n            width: 236\n            height: 38\n""",
    """        GlassPanel {\n            width: window.compactMode ? 196 : 236\n            height: 38\n""",
)

print("Compact UI patch applied.")
