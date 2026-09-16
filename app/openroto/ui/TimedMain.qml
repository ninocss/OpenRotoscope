pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

PolishedMain {
    id: window

    Rectangle {
        parent: window.contentItem
        z: 1000
        anchors.top: parent.top
        anchors.topMargin: 74
        anchors.right: parent.right
        anchors.rightMargin: 330
        width: Math.min(760, parent.width - 360)
        height: 68
        radius: 8
        color: window.dark ? "#F2292929" : "#F7FFFFFF"
        border.width: 1
        border.color: window.strongBorder

        ColumnLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            anchors.topMargin: 7
            anchors.bottomMargin: 7
            spacing: 3

            RowLayout {
                Layout.fillWidth: true
                spacing: 6

                Text {
                    text: "PERFORMANCE"
                    color: window.muted
                    font.family: "Segoe UI Variable Text"
                    font.pixelSize: 9
                    font.weight: Font.DemiBold
                    font.letterSpacing: 0.8
                }
                Text {
                    text: "last measurement · milliseconds"
                    color: window.muted
                    font.family: "Segoe UI Variable Text"
                    font.pixelSize: 9
                }
                Item { Layout.fillWidth: true }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                Repeater {
                    model: window.appController.performanceTimings

                    delegate: Item {
                        id: timingCell
                        required property int index
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        Column {
                            anchors.centerIn: parent
                            spacing: 1

                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: timingCell.modelData.label
                                color: window.secondary
                                font.family: "Segoe UI Variable Text"
                                font.pixelSize: 9
                                horizontalAlignment: Text.AlignHCenter
                            }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: timingCell.modelData.value
                                color: timingCell.modelData.measured ? window.text : window.muted
                                font.family: "Cascadia Mono"
                                font.pixelSize: 11
                                font.weight: timingCell.modelData.measured ? Font.DemiBold : Font.Normal
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }

                        Rectangle {
                            visible: timingCell.index > 0
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            width: 1
                            height: 25
                            color: window.border
                        }
                    }
                }
            }
        }
    }
}
