import QtQuick
import QtQuick.Controls

Rectangle {
    id: pill
    required property var theme
    property string label: ""
    property color dotColor: theme.accent
    property string toolTip: ""

    implicitWidth: row.implicitWidth + 18
    implicitHeight: 28
    radius: 14
    color: theme.surfaceRaised
    border.width: 1
    border.color: theme.border

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 7
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: 7
            height: 7
            radius: 4
            color: pill.dotColor
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: pill.label
            color: pill.theme.textSecondary
            font.family: pill.theme.fontFamily
            font.pixelSize: 10
        }
    }

    HoverHandler { id: hover }
    ToolTip {
        id: tip
        visible: hover.hovered && pill.toolTip.length > 0
        text: pill.toolTip
        delay: 420
        timeout: 5000
        y: pill.height + 6
        x: Math.round((pill.width - implicitWidth) / 2)
        contentItem: Text {
            text: tip.text
            color: pill.theme.text
            font.family: pill.theme.fontFamily
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
        background: Rectangle {
            radius: pill.theme.radiusSm
            color: pill.theme.surfaceRaised
            border.width: 1
            border.color: pill.theme.borderStrong
        }
    }
}
