import QtQuick
import QtQuick.Controls

Slider {
    id: control
    required property var theme
    property string toolTip: ""

    implicitHeight: 28
    opacity: enabled ? 1.0 : 0.42

    background: Rectangle {
        x: control.leftPadding
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: control.availableWidth
        height: 4
        radius: 2
        color: control.theme.surfaceSunken
        border.width: 1
        border.color: control.theme.border

        Rectangle {
            width: control.visualPosition * parent.width
            height: parent.height
            radius: parent.radius
            color: control.theme.accent
        }
    }

    handle: Rectangle {
        x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
        y: control.topPadding + control.availableHeight / 2 - height / 2
        implicitWidth: 18
        implicitHeight: 18
        radius: 9
        color: control.pressed ? control.theme.accent : control.theme.surfaceRaised
        border.width: control.visualFocus ? 3 : 2
        border.color: control.visualFocus ? control.theme.focus : control.theme.accent
        Behavior on color { ColorAnimation { duration: 90 } }
    }

    ToolTip {
        id: tip
        visible: control.pressed && control.toolTip.length > 0
        text: control.toolTip
        y: -height - 6
        x: Math.round(control.handle.x + (control.handle.width - width) / 2)
        contentItem: Text {
            text: tip.text
            color: control.theme.text
            font.family: control.theme.fontFamily
            font.pixelSize: 10
        }
        background: Rectangle {
            radius: control.theme.radiusSm
            color: control.theme.surfaceRaised
            border.width: 1
            border.color: control.theme.borderStrong
        }
    }
}
