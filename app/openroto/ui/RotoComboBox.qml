pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

ComboBox {
    id: control
    required property var theme

    implicitHeight: 36
    leftPadding: 11
    rightPadding: 34
    opacity: enabled ? 1.0 : 0.42
    font.family: theme.fontFamily
    font.pixelSize: 11

    contentItem: Text {
        leftPadding: 0
        rightPadding: 0
        text: control.displayText
        color: control.theme.text
        font: control.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    indicator: Text {
        x: control.width - width - 11
        y: Math.round((control.height - height) / 2) - 1
        text: "⌄"
        color: control.theme.textSecondary
        font.family: "Segoe UI Symbol"
        font.pixelSize: 13
    }

    background: Rectangle {
        radius: control.theme.radiusSm
        color: control.down ? control.theme.surfacePressed : control.hovered ? control.theme.surfaceHover : control.theme.surfaceRaised
        border.width: 1
        border.color: control.visualFocus || control.popup.visible ? control.theme.focus : control.theme.borderStrong
    }

    delegate: ItemDelegate {
        id: delegateItem
        required property int index
        required property var modelData
        width: control.width - 8
        height: 34
        highlighted: control.highlightedIndex === index
        text: typeof modelData === "string" ? modelData : String(modelData)
        font.family: control.theme.fontFamily
        font.pixelSize: 11
        contentItem: Text {
            text: delegateItem.text
            color: control.theme.text
            font: delegateItem.font
            verticalAlignment: Text.AlignVCenter
            leftPadding: 9
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: control.theme.radiusSm
            color: delegateItem.highlighted ? control.theme.accentSoft : delegateItem.hovered ? control.theme.surfaceHover : "transparent"
        }
    }

    popup: Popup {
        y: control.height + 5
        width: control.width
        implicitHeight: Math.min(contentItem.implicitHeight + 8, 240)
        padding: 4
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator { }
        }

        background: Rectangle {
            radius: control.theme.radiusMd
            color: control.theme.surfaceRaised
            border.width: 1
            border.color: control.theme.borderStrong
        }
    }
}
