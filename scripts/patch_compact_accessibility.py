from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_checked(path: Path, old: str, new: str, *, minimum: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count < minimum:
        raise RuntimeError(f"{path}: expected at least {minimum} occurrences, found {count}: {old!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")


polished = ROOT / "app" / "openroto" / "ui" / "PolishedMain.qml"
replace_checked(
    polished,
    "width: 34; height: 34; leftPadding: 0; rightPadding: 0",
    "width: window.compactMode ? 44 : 34; height: window.compactMode ? 44 : 34; leftPadding: 0; rightPadding: 0",
    minimum=5,
)
replace_checked(
    polished,
    "width: 30; height: 30; leftPadding: 0; rightPadding: 0",
    "width: window.compactMode ? 44 : 30; height: window.compactMode ? 44 : 30; leftPadding: 0; rightPadding: 0",
)
replace_checked(
    polished,
    "implicitWidth: 46\n                                implicitHeight: 32",
    "implicitWidth: 46\n                                implicitHeight: window.compactMode ? 44 : 32",
)
replace_checked(
    polished,
    "RotoButton {\n                            visible: window.compactMode\n                            theme: window.uiTheme",
    "RotoButton {\n                            id: compactControlsButton\n                            visible: window.compactMode\n                            theme: window.uiTheme",
)
replace_checked(
    polished,
    "Drawer {\n        id: controlsDrawer\n        edge: Qt.RightEdge",
    "Drawer {\n        id: controlsDrawer\n        objectName: \"compactControlsDrawer\"\n        edge: Qt.RightEdge",
)
replace_checked(
    polished,
    "modal: true\n        interactive: window.compactMode",
    "modal: true\n        focus: true\n        interactive: window.compactMode",
)
replace_checked(
    polished,
    "contentItem: Item {\n            Loader {",
    "onOpened: Qt.callLater(function() { compactDrawerFocusScope.forceActiveFocus(Qt.TabFocusReason) })\n        onClosed: {\n            if (window.compactMode && compactControlsButton.visible)\n                compactControlsButton.forceActiveFocus(Qt.TabFocusReason)\n        }\n\n        contentItem: FocusScope {\n            id: compactDrawerFocusScope\n            focus: controlsDrawer.opened\n            Keys.onEscapePressed: event => {\n                controlsDrawer.close()\n                event.accepted = true\n            }\n\n            Loader {",
)

removal = ROOT / "app" / "openroto" / "ui" / "ObjectRemovalMain.qml"
replace_checked(
    removal,
    "height: 38\n            radius: 19",
    "height: window.compactMode ? 50 : 38\n            radius: height / 2",
)
replace_checked(
    removal,
    "width: 30; height: 30; leftPadding: 0; rightPadding: 0",
    "width: window.compactMode ? 44 : 30; height: window.compactMode ? 44 : 30; leftPadding: 0; rightPadding: 0",
)

timed = ROOT / "app" / "openroto" / "ui" / "TimedMain.qml"
replace_checked(
    timed,
    "width: 26; height: 26; leftPadding: 0; rightPadding: 0",
    "width: window.compactMode ? 44 : 26; height: window.compactMode ? 44 : 26; leftPadding: 0; rightPadding: 0",
)
replace_checked(
    timed,
    "width: 34; height: 34; leftPadding: 0; rightPadding: 0",
    "width: window.compactMode ? 44 : 34; height: window.compactMode ? 44 : 34; leftPadding: 0; rightPadding: 0",
)
replace_checked(
    timed,
    "Popup {\n        id: settingsPopup\n        anchors.centerIn: parent",
    "Popup {\n        id: settingsPopup\n        objectName: \"settingsPopup\"\n        anchors.centerIn: parent",
)
