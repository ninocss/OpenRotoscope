pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

TimedMain {
    id: window

    component ModeButton: Button {
        id: control
        property bool active: false
        implicitWidth: 106
        implicitHeight: 30
        font.family: "Segoe UI Variable Text"
        font.pixelSize: 11
        font.weight: active ? Font.DemiBold : Font.Normal
        contentItem: Text {
            text: control.text
            color: control.active ? window.text : window.secondary
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 6
            color: control.active ? window.accentSoft : control.hovered ? (window.dark ? "#28FFFFFF" : "#10000000") : "transparent"
            border.width: control.active ? 1 : 0
            border.color: window.accent
        }
    }

    Rectangle {
        parent: window.contentItem
        z: 1200
        anchors.top: parent.top
        anchors.topMargin: 21
        anchors.horizontalCenter: parent.horizontalCenter
        width: 226
        height: 34
        radius: 8
        color: window.dark ? "#B82A2A2A" : "#DFFFFFFF"
        border.width: 1
        border.color: window.border

        Row {
            anchors.centerIn: parent
            spacing: 4
            ModeButton {
                text: "Rotoscope"
                active: window.appController.workflowMode === "rotoscope"
                onClicked: window.appController.setWorkflowMode("rotoscope")
            }
            ModeButton {
                text: "Remove"
                active: window.appController.workflowMode === "remove"
                onClicked: window.appController.setWorkflowMode("remove")
            }
        }
    }

    Image {
        parent: window.contentItem
        z: 850
        anchors.left: parent.left
        anchors.leftMargin: 19
        anchors.right: parent.right
        anchors.rightMargin: 329
        anchors.top: parent.top
        anchors.topMargin: 113
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 84
        visible: window.appController.workflowMode === "remove"
            && window.appController.viewerMode !== "mask"
            && (window.appController.viewerMode === "original" || window.appController.removalReady)
        source: window.appController.viewerMode === "removed"
            ? window.appController.currentRemovalUrl
            : window.appController.currentFrameUrl
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        cache: window.appController.viewerMode === "original"
        smooth: true
        Rectangle {
            anchors.fill: parent
            color: "transparent"
            border.width: 1
            border.color: window.border
        }
    }

    Rectangle {
        parent: window.contentItem
        z: 1100
        visible: window.appController.workflowMode === "remove"
        anchors.top: parent.top
        anchors.topMargin: 70
        anchors.right: parent.right
        anchors.rightMargin: 10
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 10
        width: 310
        radius: 8
        color: window.panel
        border.width: 1
        border.color: window.border

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                Layout.leftMargin: 14
                Layout.rightMargin: 12
                Text {
                    Layout.fillWidth: true
                    text: "Object removal"
                    color: window.text
                    font.family: "Segoe UI Variable Display"
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                }
                Text {
                    text: window.appController.removalReady ? "Ready" : window.appController.trackingReady ? "Tracked" : window.appController.hasPrompts ? "Needs track" : "Select"
                    color: window.appController.removalReady ? window.success : window.appController.hasPrompts ? window.accent : window.muted
                    font.family: "Segoe UI Variable Text"
                    font.pixelSize: 10
                    font.weight: Font.DemiBold
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
                    spacing: 8
                    Item { Layout.preferredHeight: 4 }

                    Text {
                        Layout.leftMargin: 14
                        text: "SELECT OBJECT"
                        color: window.muted
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: 10
                        font.weight: Font.DemiBold
                        font.letterSpacing: 0.8
                    }
                    Text {
                        Layout.fillWidth: true
                        Layout.leftMargin: 14
                        Layout.rightMargin: 14
                        text: "Use the same Subject and Exclude points as Rotoscope. Track the object, then reconstruct the background."
                        color: window.secondary
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }

                    ComboBox {
                        id: removeModelBox
                        Layout.fillWidth: true
                        Layout.leftMargin: 14
                        Layout.rightMargin: 14
                        model: ["Fast", "Balanced", "High"]
                        currentIndex: window.appController.modelPreset === "fast" ? 0 : window.appController.modelPreset === "high" ? 2 : 1
                        enabled: !window.blocked
                        onActivated: index => window.appController.setModelPreset(index === 0 ? "fast" : index === 2 ? "high" : "balanced")
                        background: Rectangle {
                            radius: 6
                            color: window.panel2
                            border.width: 1
                            border.color: removeModelBox.visualFocus ? window.accent : window.strongBorder
                        }
                        contentItem: Text {
                            leftPadding: 10
                            text: removeModelBox.displayText
                            color: window.text
                            font.family: "Segoe UI Variable Text"
                            font.pixelSize: 11
                            verticalAlignment: Text.AlignVCenter
                        }
                    }

                    Button {
                        Layout.fillWidth: true
                        Layout.leftMargin: 14
                        Layout.rightMargin: 14
                        implicitHeight: 34
                        text: window.appController.trackingReady ? "Track again" : "Track object"
                        enabled: window.appController.hasPrompts && !window.blocked
                        onClicked: window.appController.track()
                    }

                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.border; Layout.topMargin: 5 }
                    Text {
                        Layout.leftMargin: 14
                        text: "BACKGROUND FILL"
                        color: window.muted
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: 10
                        font.weight: Font.DemiBold
                        font.letterSpacing: 0.8
                    }
                    Text {
                        Layout.fillWidth: true
                        Layout.leftMargin: 14
                        Layout.rightMargin: 14
                        text: "Temporal Fill uses nearby frames where the background is visible and keeps the result local to your machine."
                        color: window.secondary
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: 14
                        Layout.rightMargin: 14
                        Text { text: "Mask padding"; color: window.text; font.family: "Segoe UI Variable Text"; font.pixelSize: 11; Layout.fillWidth: true }
                        Text { text: window.appController.removalPadding + " px"; color: window.secondary; font.family: "Segoe UI Variable Text"; font.pixelSize: 10 }
                    }
                    Slider {
                        Layout.fillWidth: true
                        Layout.leftMargin: 14
                        Layout.rightMargin: 14
                        from: 0; to: 32; stepSize: 1
                        value: window.appController.removalPadding
                        enabled: !window.blocked
                        onMoved: window.appController.setRemovalPadding(Math.round(value))
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: 14
                        Layout.rightMargin: 14
                        Text { text: "Edge feather"; color: window.text; font.family: "Segoe UI Variable Text"; font.pixelSize: 11; Layout.fillWidth: true }
                        Text { text: window.appController.removalFeather.toFixed(1) + " px"; color: window.secondary; font.family: "Segoe UI Variable Text"; font.pixelSize: 10 }
                    }
                    Slider {
                        Layout.fillWidth: true
                        Layout.leftMargin: 14
                        Layout.rightMargin: 14
                        from: 0; to: 16; stepSize: 0.5
                        value: window.appController.removalFeather
                        enabled: !window.blocked
                        onMoved: window.appController.setRemovalFeather(value)
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: 14
                        Layout.rightMargin: 14
                        Text { text: "Temporal search"; color: window.text; font.family: "Segoe UI Variable Text"; font.pixelSize: 11; Layout.fillWidth: true }
                        Text { text: "±" + window.appController.removalTemporalRadius + " f"; color: window.secondary; font.family: "Segoe UI Variable Text"; font.pixelSize: 10 }
                    }
                    Slider {
                        Layout.fillWidth: true
                        Layout.leftMargin: 14
                        Layout.rightMargin: 14
                        from: 2; to: 60; stepSize: 1
                        value: window.appController.removalTemporalRadius
                        enabled: !window.blocked
                        onMoved: window.appController.setRemovalTemporalRadius(Math.round(value))
                    }

                    Button {
                        Layout.fillWidth: true
                        Layout.leftMargin: 14
                        Layout.rightMargin: 14
                        implicitHeight: 34
                        text: window.appController.removalReady ? "Rebuild preview" : "Preview removal"
                        enabled: window.appController.hasPrompts && !window.blocked
                        onClicked: window.appController.previewRemoval()
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: 14
                        Layout.rightMargin: 14
                        spacing: 4
                        Repeater {
                            model: [
                                {"label": "Original", "value": "original"},
                                {"label": "Mask", "value": "mask"},
                                {"label": "Removed", "value": "removed"}
                            ]
                            delegate: Button {
                                required property var modelData
                                Layout.fillWidth: true
                                implicitHeight: 30
                                text: modelData.label
                                checkable: true
                                checked: window.appController.viewerMode === modelData.value
                                enabled: modelData.value !== "removed" || window.appController.removalReady
                                onClicked: window.appController.setViewerMode(modelData.value)
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.border; Layout.topMargin: 5 }
                    Text {
                        Layout.leftMargin: 14
                        text: "REMOVAL PERFORMANCE"
                        color: window.muted
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: 10
                        font.weight: Font.DemiBold
                        font.letterSpacing: 0.8
                    }
                    Repeater {
                        model: window.appController.removalTimings
                        delegate: RowLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.leftMargin: 14
                            Layout.rightMargin: 14
                            Text { text: modelData.label; color: window.secondary; font.family: "Segoe UI Variable Text"; font.pixelSize: 10; Layout.fillWidth: true }
                            Text { text: modelData.value; color: window.text; font.family: "Cascadia Mono"; font.pixelSize: 10 }
                        }
                    }
                    Item { Layout.preferredHeight: 8 }
                }
            }

            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.border }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 12
                Layout.rightMargin: 12
                Layout.topMargin: 9
                Layout.bottomMargin: 11
                spacing: 6
                Text {
                    Layout.fillWidth: true
                    text: window.appController.status
                    color: window.text
                    font.family: "Segoe UI Variable Text"
                    font.pixelSize: 11
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                }
                Button {
                    Layout.fillWidth: true
                    implicitHeight: 40
                    text: window.appController.trackingDirty ? "Track, Remove & Apply" : "Remove & Apply"
                    enabled: window.appController.hasPrompts && window.appController.bridgeConnected && !window.blocked
                    onClicked: window.appController.renderAndApply()
                }
            }
        }
    }
}
