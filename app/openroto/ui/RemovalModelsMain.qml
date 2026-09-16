pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ObjectRemovalMain {
    id: window

    function backendIndex() {
        const rows = window.removalController.backends
        for (let i = 0; i < rows.length; ++i) {
            if (rows[i].id === window.removalController.backendId)
                return i
        }
        return 0
    }

    component BackendButton: Button {
        id: control
        property bool primary: false
        implicitHeight: 32
        leftPadding: 10
        rightPadding: 10
        font.family: "Segoe UI Variable Text"
        font.pixelSize: 11
        font.weight: primary ? Font.DemiBold : Font.Normal
        contentItem: Text {
            text: control.text
            color: control.primary ? "white" : window.text
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 6
            color: control.primary
                ? (control.down ? window.accentPressed : window.accent)
                : control.hovered ? (window.dark ? "#3FFFFFFF" : "#10000000")
                : window.panel2
            border.width: 1
            border.color: control.primary ? window.accent : window.strongBorder
        }
    }

    Rectangle {
        parent: window.contentItem
        z: 1500
        visible: window.removalController.workflowMode === "remove"
        anchors.top: parent.top
        anchors.topMargin: 21
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.horizontalCenterOffset: 258
        width: 258
        height: 34
        radius: 8
        color: window.dark ? "#B82A2A2A" : "#E8FFFFFF"
        border.width: 1
        border.color: window.border

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 5
            anchors.rightMargin: 5
            spacing: 5

            ComboBox {
                id: removeBackendBox
                Layout.fillWidth: true
                Layout.fillHeight: true
                model: window.removalController.backends
                textRole: "name"
                currentIndex: window.backendIndex()
                enabled: !window.appController.busy
                onActivated: index => {
                    const row = window.removalController.backends[index]
                    if (row)
                        window.removalController.setBackend(row.id)
                }
                background: Rectangle {
                    radius: 6
                    color: window.panel2
                    border.width: 0
                }
                contentItem: Text {
                    leftPadding: 8
                    text: removeBackendBox.displayText
                    color: window.text
                    font.family: "Segoe UI Variable Text"
                    font.pixelSize: 10
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }
            }

            BackendButton {
                text: "Models"
                enabled: !window.appController.busy
                onClicked: {
                    window.removalController.refreshBackends()
                    removalModelsPopup.open()
                }
            }
        }
    }

    Popup {
        id: removalModelsPopup
        anchors.centerIn: parent
        width: Math.min(window.width - 70, 820)
        height: Math.min(window.height - 70, 680)
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
                    text: "Object Removal Models"
                    color: window.text
                    font.family: "Segoe UI Variable Display"
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                }
                BackendButton {
                    text: "×"
                    onClicked: removalModelsPopup.close()
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
                    Item { Layout.preferredHeight: 4 }

                    Text {
                        Layout.leftMargin: 18
                        text: "Backends"
                        color: window.text
                        font.family: "Segoe UI Variable Display"
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                    }
                    Text {
                        Layout.fillWidth: true
                        Layout.leftMargin: 18
                        Layout.rightMargin: 18
                        text: "Temporal Fill is built in. FGT and SVOR are installed into isolated local Python environments so their PyTorch versions cannot affect SAM2. Setup requires uv and internet access."
                        color: window.secondary
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: window.removalController.backends
                        delegate: Rectangle {
                            id: backendCard
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.leftMargin: 18
                            Layout.rightMargin: 18
                            Layout.preferredHeight: 116
                            radius: 8
                            color: window.panel2
                            border.width: 1
                            border.color: backendCard.modelData.selected ? window.accent : window.border

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 12

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    RowLayout {
                                        Text {
                                            text: backendCard.modelData.name
                                            color: window.text
                                            font.family: "Segoe UI Variable Text"
                                            font.pixelSize: 13
                                            font.weight: Font.DemiBold
                                        }
                                        Text {
                                            text: backendCard.modelData.selected ? "Selected" : backendCard.modelData.status
                                            color: backendCard.modelData.selected ? window.accent : backendCard.modelData.installed ? window.success : window.muted
                                            font.family: "Segoe UI Variable Text"
                                            font.pixelSize: 9
                                        }
                                        Text {
                                            text: backendCard.modelData.license
                                            color: window.muted
                                            font.family: "Segoe UI Variable Text"
                                            font.pixelSize: 9
                                        }
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: backendCard.modelData.description
                                        color: window.secondary
                                        font.family: "Segoe UI Variable Text"
                                        font.pixelSize: 10
                                        wrapMode: Text.WordWrap
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: backendCard.modelData.quality + " quality  ·  " + backendCard.modelData.speed + "  ·  " + backendCard.modelData.vram
                                        color: window.muted
                                        font.family: "Segoe UI Variable Text"
                                        font.pixelSize: 9
                                        wrapMode: Text.WordWrap
                                    }
                                    Text {
                                        visible: backendCard.modelData.download.length > 0
                                        text: backendCard.modelData.download
                                        color: window.muted
                                        font.family: "Segoe UI Variable Text"
                                        font.pixelSize: 9
                                    }
                                }

                                ColumnLayout {
                                    spacing: 5
                                    BackendButton {
                                        visible: backendCard.modelData.installed && !backendCard.modelData.selected
                                        text: "Use"
                                        enabled: !window.appController.busy
                                        onClicked: window.removalController.setBackend(backendCard.modelData.id)
                                    }
                                    BackendButton {
                                        visible: !backendCard.modelData.installed && backendCard.modelData.id !== "temporal"
                                        primary: true
                                        text: "Install"
                                        enabled: !window.appController.busy
                                        onClicked: window.removalController.setupBackend(backendCard.modelData.id)
                                    }
                                    BackendButton {
                                        visible: backendCard.modelData.installed && backendCard.modelData.id !== "temporal"
                                        text: "Remove"
                                        enabled: !window.appController.busy
                                        onClicked: window.removalController.removeBackend(backendCard.modelData.id)
                                    }
                                }
                            }
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        Layout.leftMargin: 18
                        Layout.rightMargin: 18
                        visible: window.removalController.backendError.length > 0
                        text: window.removalController.backendError
                        color: window.danger
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        Layout.leftMargin: 18
                        Layout.rightMargin: 18
                        Layout.topMargin: 4
                        color: window.border
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: 18
                        Layout.rightMargin: 18
                        Text {
                            Layout.fillWidth: true
                            text: "Local benchmark"
                            color: window.text
                            font.family: "Segoe UI Variable Display"
                            font.pixelSize: 15
                            font.weight: Font.DemiBold
                        }
                        BackendButton {
                            text: "Open results"
                            visible: window.removalController.benchmarkResults.length > 0
                            onClicked: window.removalController.openBenchmarkFolder()
                        }
                        BackendButton {
                            primary: true
                            text: "Benchmark 17 frames"
                            enabled: window.appController.hasPrompts && !window.appController.busy
                            onClicked: window.removalController.benchmarkBackends()
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        Layout.leftMargin: 18
                        Layout.rightMargin: 18
                        text: "Runs every installed backend on the same tracked 17-frame window. Runtime and peak NVIDIA VRAM are measured; the resulting PNG sequences are kept so you can compare visual quality directly."
                        color: window.secondary
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: window.removalController.benchmarkResults
                        delegate: Rectangle {
                            id: benchmarkRow
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.leftMargin: 18
                            Layout.rightMargin: 18
                            Layout.preferredHeight: benchmarkRow.modelData.error ? 72 : 48
                            radius: 7
                            color: window.dark ? "#252525" : "#FAFAFA"
                            border.width: 1
                            border.color: window.border

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                anchors.topMargin: 7
                                anchors.bottomMargin: 7
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text {
                                        Layout.preferredWidth: 115
                                        text: benchmarkRow.modelData.name
                                        color: window.text
                                        font.family: "Segoe UI Variable Text"
                                        font.pixelSize: 11
                                        font.weight: Font.DemiBold
                                    }
                                    Text { Layout.preferredWidth: 75; text: benchmarkRow.modelData.elapsed; color: window.secondary; font.family: "Cascadia Mono"; font.pixelSize: 10 }
                                    Text { Layout.preferredWidth: 105; text: benchmarkRow.modelData.perFrame; color: window.secondary; font.family: "Cascadia Mono"; font.pixelSize: 10 }
                                    Text { Layout.preferredWidth: 70; text: benchmarkRow.modelData.vram; color: window.secondary; font.family: "Cascadia Mono"; font.pixelSize: 10 }
                                    Item { Layout.fillWidth: true }
                                    Text {
                                        text: benchmarkRow.modelData.status
                                        color: benchmarkRow.modelData.status === "Complete" ? window.success : window.danger
                                        font.family: "Segoe UI Variable Text"
                                        font.pixelSize: 10
                                    }
                                }
                                Text {
                                    Layout.fillWidth: true
                                    visible: benchmarkRow.modelData.error !== undefined && benchmarkRow.modelData.error.length > 0
                                    text: benchmarkRow.modelData.error || ""
                                    color: window.danger
                                    font.family: "Segoe UI Variable Text"
                                    font.pixelSize: 9
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }

                    Item { Layout.preferredHeight: 14 }
                }
            }
        }
    }
}
