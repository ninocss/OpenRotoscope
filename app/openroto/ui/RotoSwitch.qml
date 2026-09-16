import QtQuick
import QtQuick.Controls

Switch {
    id: control
    required property var theme

    implicitHeight: 30
    spacing: 9
    opacity: enabled ? 1.0 : 0.42

    indicator: Rectangle {
        implicitWidth: 38
        implicitHeight: 20
        x: 0
        y: Math.round((control.height - height) / 2)
        radius: height / 2
        color: control.checked ? control.theme.accent : control.theme.surfaceSunken
        border.width: control.visualFocus ? 2 : 1
        border.color: control.visualFocus ? control.theme.focus : control.checked ? control.theme.accent : control.theme.borderStrong

        Rectangle {
            width: 14
            height: 14
            radius: 7
            y: 3
            x: control.checked ? parent.width - width - 3 : 3
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
