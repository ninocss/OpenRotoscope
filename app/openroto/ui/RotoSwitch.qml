import QtQuick
import QtQuick.Controls
import QtQuick.Window

Switch {
    id: control
    required property var theme
    readonly property bool compactTouchMode: control.Window.window !== null && control.Window.window.width < 1120

    implicitHeight: compactTouchMode ? 44 : 30
    spacing: 9
    activeFocusOnTab: enabled && visible
    opacity: enabled ? 1.0 : 0.42

    indicator: Rectangle {
        implicitWidth: compactTouchMode ? 42 : 38
        implicitHeight: compactTouchMode ? 24 : 20
        x: 0
        y: Math.round((control.height - height) / 2)
        radius: height / 2
        color: control.checked ? control.theme.accent : control.theme.surfaceSunken
        border.width: control.visualFocus ? 2 : 1
        border.color: control.visualFocus ? control.theme.focus : control.checked ? control.theme.accent : control.theme.borderStrong

        Rectangle {
            width: compactTouchMode ? 16 : 14
            height: compactTouchMode ? 16 : 14
            radius: width / 2
            y: Math.round((parent.height - height) / 2)
            x: control.checked ? parent.width - width - 4 : 4
            color: control.checked ? control.theme.textOnAccent : control.theme.textSecondary
            Behavior on x { NumberAnimation { duration: 100; easing.type: Easing.OutCubic } }
        }
    }

    contentItem: Text {
        text: control.text
        color: control.theme.text
        font.family: control.theme.fontFamily
        font.pixelSize: 11
        verticalAlignment: Text.AlignVCenter
        leftPadding: control.indicator.width + control.spacing
    }
}
