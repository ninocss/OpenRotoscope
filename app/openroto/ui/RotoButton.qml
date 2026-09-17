import QtQuick
import QtQuick.Controls
import QtQuick.Window

Button {
    id: control
    required property var theme
    property bool primary: false
    property bool selected: false
    property bool dangerStyle: false
    property bool quiet: false
    property string toolTip: ""
    readonly property bool compactTouchMode: control.Window.window !== null && control.Window.window.width < 1120

    implicitWidth: Math.max(compactTouchMode ? 44 : 0, contentItem.implicitWidth + leftPadding + rightPadding)
    implicitHeight: compactTouchMode ? 44 : 36
    leftPadding: 12
    rightPadding: 12
    activeFocusOnTab: enabled && visible
    opacity: enabled ? 1.0 : 0.42
    font.family: theme.fontFamily
    font.pixelSize: 11
    font.weight: primary || selected ? Font.DemiBold : Font.Normal

    contentItem: Text {
        text: control.text
        color: control.primary
            ? control.theme.textOnAccent
            : control.dangerStyle ? control.theme.danger : control.theme.text
        font: control.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: control.theme.radiusSm
        color: control.primary
            ? (control.down ? control.theme.accentPressed : control.hovered ? control.theme.accentHover : control.theme.accent)
            : control.selected ? control.theme.accentSoft
            : control.down ? control.theme.surfacePressed
            : control.hovered ? control.theme.surfaceHover
            : control.quiet ? "transparent" : control.theme.surfaceRaised
        border.width: control.visualFocus || control.primary || control.selected || !control.quiet ? 1 : 0
        border.color: control.visualFocus
            ? control.theme.focus
            : control.primary || control.selected ? control.theme.accent : control.theme.borderStrong
        Behavior on color { ColorAnimation { duration: 90 } }
    }

    ToolTip {
        id: tip
        visible: (control.hovered || control.visualFocus) && control.toolTip.length > 0
        text: control.toolTip
        delay: control.visualFocus ? 0 : 420
        timeout: 5000
        y: control.height + 6
        x: Math.round((control.width - implicitWidth) / 2)
        contentItem: Text {
            text: tip.text
            color: control.theme.text
            font.family: control.theme.fontFamily
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
        background: Rectangle {
            radius: control.theme.radiusSm
            color: control.theme.surfaceRaised
            border.width: 1
            border.color: control.theme.borderStrong
        }
    }
}
