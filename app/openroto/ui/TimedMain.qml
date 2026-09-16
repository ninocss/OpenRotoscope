pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

PolishedMain {
    id: window

    component SettingsActionButton: Button {
        id: control
        property bool dangerStyle: false
        implicitHeight: 32
        leftPadding: 11
        rightPadding: 11
        font.family: "Segoe UI Variable Text"
        font.pixelSize: 11
        contentItem: Text {
            text: control.text
            color: control.dangerStyle ? window.danger : window.text
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 6
            color: control.hovered ? (window.dark ? "#3FFFFFFF" : "#10000000") : "transparent"
            border.width: 1
            border.color: window.strongBorder
        }
    }

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
        visible: window.modelManager.performanceStatsVisible
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

    // Cover the base settings button with the expanded settings entry. This keeps
    // the inherited layout stable while adding general UI preferences alongside
    // the existing model controls.
    Button {
        parent: window.contentItem
        z: 1600
        anchors.top: parent.top
        anchors.topMargin: 19
        anchors.right: parent.right
        anchors.rightMargin: 18
        width: 34
        height: 34
        text: "⚙"
        font.family: "Segoe UI Symbol"
        font.pixelSize: 16
        contentItem: Text {
            text: parent.text
            color: window.text
            font: parent.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 6
            color: parent.hovered ? (window.dark ? "#3FFFFFFF" : "#10000000") : window.panel
            border.width: parent.visualFocus ? 1 : 0
            border.color: window.strongBorder
        }
        ToolTip.visible: hovered
        ToolTip.text: "Settings"
        onClicked: {
            window.modelManager.refresh()
            enhancedSettings.open()
        }
    }

    Popup {
        id: enhancedSettings
        anchors.centerIn: parent
        width: Math.min(window.width - 80, 720)
        height: Math.min(window.height - 80, 620)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: 10
            color: window.panel
            border.width: 1
            border.color: window.strongBorder
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 54
                Layout.leftMargin: 18
                Layout.rightMargin: 10
                Text {
                    Layout.fillWidth: true
                    text: "Settings"
                    color: window.text
                    font.family: "Segoe UI Variable Display"
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                }
                Button {
                    implicitWidth: 34
                    implicitHeight: 34
                    text: "×"
                    font.family: "Segoe UI Variable Text"
                    font.pixelSize: 18
                    contentItem: Text {
                        text: parent.text
                        color: window.text
                        font: parent.font
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: 6
                        color: parent.hovered ? (window.dark ? "#3FFFFFFF" : "#10000000") : "transparent"
                    }
                    onClicked: enhancedSettings.close()
                }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.border }

            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: availableWidth

                ColumnLayout {
                    width: parent.width
                    spacing: 10
                    Item { Layout.preferredHeight: 5 }

                    Text {
                        Layout.leftMargin: 18
                        text: "Interface"
                        color: window.text
                        font.family: "Segoe UI Variable Display"
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.leftMargin: 18
                        Layout.rightMargin: 18
                        Layout.preferredHeight: 70
                        radius: 8
                        color: window.panel2
                        border.width: 1
                        border.color: window.border

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 12
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text {
                                    text: "Performance statistics"
                                    color: window.text
                                    font.family: "Segoe UI Variable Text"
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: "Show live Model Load, Embedding, Predict, Preview, Init State and Propagate timings over the viewer."
                                    color: window.secondary
                                    font.family: "Segoe UI Variable Text"
                                    font.pixelSize: 10
                                    wrapMode: Text.WordWrap
                                }
                            }
                            Switch {
                                id: performanceSwitch
                                checked: window.modelManager.performanceStatsVisible
                                onToggled: window.modelManager.setPerformanceStatsVisible(checked)
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        Layout.leftMargin: 18
                        Layout.rightMargin: 18
                        Layout.topMargin: 4
                        color: window.border
                    }

                    Text {
                        Layout.leftMargin: 18
                        text: "SAM 2.1 models"
                        color: window.text
                        font.family: "Segoe UI Variable Display"
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                    }
                    Text {
                        Layout.fillWidth: true
                        Layout.leftMargin: 18
                        Layout.rightMargin: 18
                        text: "Install only the selection models you want to keep locally. The selected default is used for new sessions."
                        color: window.secondary
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: window.modelManager.models
                        delegate: Rectangle {
                            id: modelCard
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.leftMargin: 18
                            Layout.rightMargin: 18
                            Layout.preferredHeight: 86
                            radius: 8
                            color: window.panel2
                            border.width: 1
                            border.color: modelCard.modelData.selected ? window.accent : window.border

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 10
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    RowLayout {
                                        Text {
                                            text: modelCard.modelData.name
                                            color: window.text
                                            font.family: "Segoe UI Variable Text"
                                            font.pixelSize: 12
                                            font.weight: Font.DemiBold
                                        }
                                        Text {
                                            text: modelCard.modelData.selected ? "Default" : modelCard.modelData.status
                                            color: modelCard.modelData.selected ? window.accent : modelCard.modelData.installed ? window.success : window.muted
                                            font.family: "Segoe UI Variable Text"
                                            font.pixelSize: 9
                                        }
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: modelCard.modelData.description
                                        color: window.secondary
                                        font.family: "Segoe UI Variable Text"
                                        font.pixelSize: 9
                                        elide: Text.ElideRight
                                    }
                                    Text {
                                        text: "~" + modelCard.modelData.downloadMb + " MB  ·  " + modelCard.modelData.minimumVramGb + " GB VRAM recommended"
                                        color: window.muted
                                        font.family: "Segoe UI Variable Text"
                                        font.pixelSize: 9
                                    }
                                }
                                SettingsActionButton {
                                    visible: modelCard.modelData.installed && !modelCard.modelData.selected
                                    text: "Set default"
                                    enabled: !window.modelManager.busy && !window.appController.busy
                                    onClicked: window.modelManager.setDefaultModel(modelCard.modelData.id)
                                }
                                SettingsActionButton {
                                    text: modelCard.modelData.installed ? "Remove" : "Download"
                                    dangerStyle: modelCard.modelData.installed
                                    enabled: !window.modelManager.busy && !window.appController.busy
                                    onClicked: {
                                        if (modelCard.modelData.installed)
                                            window.modelManager.removeModel(modelCard.modelData.id)
                                        else
                                            window.modelManager.downloadModel(modelCard.modelData.id)
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        Layout.leftMargin: 18
                        Layout.rightMargin: 18
                        Layout.topMargin: 4
                        color: window.border
                    }
                    Text {
                        Layout.leftMargin: 18
                        text: "System"
                        color: window.text
                        font.family: "Segoe UI Variable Display"
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                    }
                    Text {
                        Layout.fillWidth: true
                        Layout.leftMargin: 18
                        Layout.rightMargin: 18
                        text: window.appController.computeDevice + "\n" + window.appController.computeDetail
                        color: window.secondary
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        Layout.fillWidth: true
                        Layout.leftMargin: 18
                        Layout.rightMargin: 18
                        text: "Model cache: " + window.modelManager.cachePath
                        color: window.muted
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: 9
                        wrapMode: Text.WrapAnywhere
                    }
                    Text {
                        Layout.fillWidth: true
                        Layout.leftMargin: 18
                        Layout.rightMargin: 18
                        visible: window.modelManager.lastError.length > 0
                        text: window.modelManager.lastError
                        color: window.danger
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }
                    Item { Layout.preferredHeight: 14 }
                }
            }
        }
    }
}
