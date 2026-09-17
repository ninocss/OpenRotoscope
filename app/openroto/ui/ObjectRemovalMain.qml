pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

TimedMain {
    id: window
    required property var removalController

    workflowSwitcherComponent: workflowSwitcher
    customSidePanelComponent: window.removalController.workflowMode === "remove" ? removalPanel : null
    viewerTitle: window.removalController.workflowMode === "remove" ? "Removal viewer" : "Viewer"
    viewerFrameSource: window.removalController.workflowMode === "remove"
        && window.removalController.viewerMode === "removed"
        && window.removalController.ready
        ? window.removalController.currentRemovalUrl
        : window.appController.currentFrameUrl
    maskOverlayEnabled: window.removalController.workflowMode === "rotoscope"
        || window.removalController.viewerMode === "mask"
    selectionPointsVisible: window.removalController.workflowMode === "rotoscope"
        || window.removalController.viewerMode !== "removed"
    selectionEnabled: window.removalController.workflowMode === "rotoscope"
        || window.removalController.viewerMode !== "removed"

    Component {
        id: workflowSwitcher
        GlassPanel {
            width: window.compactMode ? 196 : 236
            height: window.compactMode ? 50 : 38
            radius: height / 2
            theme: window.uiTheme
            strong: true
            RowLayout {
                anchors.fill: parent
                anchors.margins: 3
                spacing: 3
                RotoButton {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    theme: window.uiTheme
                    text: "Rotoscope"
                    selected: window.removalController.workflowMode === "rotoscope"
                    quiet: !selected
                    toolTip: "Create and refine a tracked matte."
                    onClicked: window.removalController.setWorkflowMode("rotoscope")
                }
                RotoButton {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    theme: window.uiTheme
                    text: "Remove"
                    selected: window.removalController.workflowMode === "remove"
                    quiet: !selected
                    toolTip: "Track an object, reconstruct its background, then apply the result in Resolve."
                    onClicked: window.removalController.setWorkflowMode("remove")
                }
            }
        }
    }

    Component {
        id: removalPanel
        GlassPanel {
            theme: window.uiTheme
            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 48
                    Layout.leftMargin: window.uiTheme.spaceLg
                    Layout.rightMargin: window.uiTheme.spaceMd
                    Text {
                        Layout.fillWidth: true
                        text: "Object removal"
                        color: window.uiTheme.text
                        font.family: window.uiTheme.displayFontFamily
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                    }
                    StatusPill {
                        theme: window.uiTheme
                        label: window.removalController.ready ? "Ready"
                            : window.appController.trackingReady ? "Tracked"
                            : window.appController.hasPrompts ? "Needs track" : "Select"
                        dotColor: window.removalController.ready ? window.uiTheme.success
                            : window.appController.hasPrompts ? window.uiTheme.accent : window.uiTheme.textMuted
                    }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.uiTheme.border }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    contentWidth: availableWidth
                    ColumnLayout {
                        width: parent.width
                        spacing: window.uiTheme.spaceSm
                        Item { Layout.preferredHeight: window.uiTheme.spaceXs }

                        Text {
                            Layout.leftMargin: window.uiTheme.spaceLg
                            text: "SELECT OBJECT"
                            color: window.uiTheme.textMuted
                            font.family: window.uiTheme.fontFamily
                            font.pixelSize: 10
                            font.weight: Font.DemiBold
                            font.letterSpacing: 0.7
                        }
                        Text {
                            Layout.fillWidth: true
                            Layout.leftMargin: window.uiTheme.spaceLg
                            Layout.rightMargin: window.uiTheme.spaceLg
                            text: "Use Subject and Exclude points in the viewer. Removal tracks both directions so every output frame has a mask."
                            color: window.uiTheme.textSecondary
                            font.family: window.uiTheme.fontFamily
                            font.pixelSize: 11
                            wrapMode: Text.WordWrap
                        }
                        RotoComboBox {
                            Layout.fillWidth: true
                            Layout.leftMargin: window.uiTheme.spaceLg
                            Layout.rightMargin: window.uiTheme.spaceLg
                            theme: window.uiTheme
                            model: ["Fast", "Balanced", "High"]
                            currentIndex: window.appController.modelPreset === "fast" ? 0 : window.appController.modelPreset === "high" ? 2 : 1
                            enabled: !window.blocked
                            onActivated: index => window.appController.setModelPreset(index === 0 ? "fast" : index === 2 ? "high" : "balanced")
                        }
                        RotoButton {
                            Layout.fillWidth: true
                            Layout.leftMargin: window.uiTheme.spaceLg
                            Layout.rightMargin: window.uiTheme.spaceLg
                            theme: window.uiTheme
                            primary: window.appController.hasPrompts && !window.appController.trackingReady
                            text: window.appController.trackingReady ? "Track again" : "Track object"
                            enabled: window.appController.hasPrompts && !window.blocked
                            toolTip: window.appController.hasPrompts ? "Track the selected object through the full clip." : "Add at least one Subject point first."
                            onClicked: {
                                window.appController.setTrackingDirection("both")
                                window.appController.track()
                            }
                        }

                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; Layout.topMargin: window.uiTheme.spaceXs; color: window.uiTheme.border }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.leftMargin: window.uiTheme.spaceLg
                            Layout.rightMargin: window.uiTheme.spaceMd
                            Text {
                                Layout.fillWidth: true
                                text: "BACKGROUND FILL"
                                color: window.uiTheme.textMuted
                                font.family: window.uiTheme.fontFamily
                                font.pixelSize: 10
                                font.weight: Font.DemiBold
                                font.letterSpacing: 0.7
                            }
                            RotoButton {
                                theme: window.uiTheme
                                width: window.compactMode ? 44 : 30; height: window.compactMode ? 44 : 30; leftPadding: 0; rightPadding: 0
                                quiet: true
                                text: "ⓘ"
                                font.pixelSize: 13
                                toolTip: "Temporal Fill is built in. Optional backends may require separate local environments."
                            }
                        }
                        RotoComboBox {
                            Layout.fillWidth: true
                            Layout.leftMargin: window.uiTheme.spaceLg
                            Layout.rightMargin: window.uiTheme.spaceLg
                            theme: window.uiTheme
                            model: ["Temporal Fill", "FGT++", "SVOR"]
                            currentIndex: window.removalController.backend === "fgt" ? 1 : window.removalController.backend === "svor" ? 2 : 0
                            enabled: !window.blocked
                            onActivated: index => window.removalController.setBackend(index === 1 ? "fgt" : index === 2 ? "svor" : "temporal")
                        }
                        GlassPanel {
                            Layout.fillWidth: true
                            Layout.leftMargin: window.uiTheme.spaceLg
                            Layout.rightMargin: window.uiTheme.spaceLg
                            implicitHeight: backendInfo.implicitHeight + window.uiTheme.spaceMd * 2
                            theme: window.uiTheme
                            strong: true
                            ColumnLayout {
                                id: backendInfo
                                anchors.fill: parent
                                anchors.margins: window.uiTheme.spaceMd
                                spacing: 3
                                Text {
                                    Layout.fillWidth: true
                                    text: window.removalController.backendInfo.description
                                    color: window.uiTheme.textSecondary
                                    font.family: window.uiTheme.fontFamily
                                    font.pixelSize: 10
                                    wrapMode: Text.WordWrap
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: window.removalController.backendInfo.status + "  ·  "
                                        + window.removalController.backendInfo.license + "  ·  "
                                        + window.removalController.backendInfo.vram
                                    color: window.removalController.backendInfo.available ? window.uiTheme.success : window.uiTheme.warning
                                    font.family: window.uiTheme.fontFamily
                                    font.pixelSize: 9
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.leftMargin: window.uiTheme.spaceLg
                            Layout.rightMargin: window.uiTheme.spaceLg
                            Text { text: "Mask padding"; color: window.uiTheme.text; font.family: window.uiTheme.fontFamily; font.pixelSize: 11; Layout.fillWidth: true }
                            Text { text: window.removalController.padding + " px"; color: window.uiTheme.textSecondary; font.family: window.uiTheme.monoFontFamily; font.pixelSize: 10 }
                        }
                        RotoSlider {
                            Layout.fillWidth: true
                            Layout.leftMargin: window.uiTheme.spaceLg
                            Layout.rightMargin: window.uiTheme.spaceLg
                            theme: window.uiTheme
                            from: 0; to: 32; stepSize: 1
                            value: window.removalController.padding
                            enabled: !window.blocked
                            toolTip: Math.round(value) + " px padding"
                            onMoved: window.removalController.setPadding(Math.round(value))
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.leftMargin: window.uiTheme.spaceLg
                            Layout.rightMargin: window.uiTheme.spaceLg
                            Text { text: "Edge feather"; color: window.uiTheme.text; font.family: window.uiTheme.fontFamily; font.pixelSize: 11; Layout.fillWidth: true }
                            Text { text: window.removalController.feather.toFixed(1) + " px"; color: window.uiTheme.textSecondary; font.family: window.uiTheme.monoFontFamily; font.pixelSize: 10 }
                        }
                        RotoSlider {
                            Layout.fillWidth: true
                            Layout.leftMargin: window.uiTheme.spaceLg
                            Layout.rightMargin: window.uiTheme.spaceLg
                            theme: window.uiTheme
                            from: 0; to: 16; stepSize: 0.5
                            value: window.removalController.feather
                            enabled: !window.blocked
                            toolTip: value.toFixed(1) + " px feather"
                            onMoved: window.removalController.setFeather(value)
                        }

                        RowLayout {
                            visible: window.removalController.backend === "temporal"
                            Layout.fillWidth: true
                            Layout.leftMargin: window.uiTheme.spaceLg
                            Layout.rightMargin: window.uiTheme.spaceLg
                            Text { text: "Temporal search"; color: window.uiTheme.text; font.family: window.uiTheme.fontFamily; font.pixelSize: 11; Layout.fillWidth: true }
                            Text { text: "±" + window.removalController.temporalRadius + " f"; color: window.uiTheme.textSecondary; font.family: window.uiTheme.monoFontFamily; font.pixelSize: 10 }
                        }
                        RotoSlider {
                            visible: window.removalController.backend === "temporal"
                            Layout.fillWidth: true
                            Layout.leftMargin: window.uiTheme.spaceLg
                            Layout.rightMargin: window.uiTheme.spaceLg
                            theme: window.uiTheme
                            from: 2; to: 60; stepSize: 1
                            value: window.removalController.temporalRadius
                            enabled: !window.blocked
                            toolTip: "±" + Math.round(value) + " frames"
                            onMoved: window.removalController.setTemporalRadius(Math.round(value))
                        }

                        RotoButton {
                            Layout.fillWidth: true
                            Layout.leftMargin: window.uiTheme.spaceLg
                            Layout.rightMargin: window.uiTheme.spaceLg
                            theme: window.uiTheme
                            text: window.removalController.ready ? "Rebuild preview" : "Preview removal"
                            enabled: window.appController.hasPrompts && !window.blocked && window.removalController.backendInfo.available
                            toolTip: window.removalController.backendInfo.available
                                ? "Build a local preview without applying anything in Resolve."
                                : "This removal backend is not available on this system."
                            onClicked: window.removalController.preview()
                        }

                        Text {
                            Layout.leftMargin: window.uiTheme.spaceLg
                            text: "VIEW"
                            color: window.uiTheme.textMuted
                            font.family: window.uiTheme.fontFamily
                            font.pixelSize: 10
                            font.weight: Font.DemiBold
                            font.letterSpacing: 0.7
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.leftMargin: window.uiTheme.spaceLg
                            Layout.rightMargin: window.uiTheme.spaceLg
                            spacing: window.uiTheme.spaceXs
                            Repeater {
                                model: [
                                    {"label": "Original", "value": "original"},
                                    {"label": "Mask", "value": "mask"},
                                    {"label": "Removed", "value": "removed"}
                                ]
                                delegate: RotoButton {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    theme: window.uiTheme
                                    text: modelData.label
                                    selected: window.removalController.viewerMode === modelData.value
                                    quiet: !selected
                                    enabled: modelData.value !== "removed" || window.removalController.ready
                                    onClicked: window.removalController.setViewerMode(modelData.value)
                                }
                            }
                        }

                        Rectangle {
                            visible: window.modelManager.performanceStatsVisible
                            Layout.fillWidth: true
                            Layout.preferredHeight: 1
                            Layout.topMargin: window.uiTheme.spaceXs
                            color: window.uiTheme.border
                        }
                        Text {
                            visible: window.modelManager.performanceStatsVisible
                            Layout.leftMargin: window.uiTheme.spaceLg
                            text: "REMOVAL PERFORMANCE"
                            color: window.uiTheme.textMuted
                            font.family: window.uiTheme.fontFamily
                            font.pixelSize: 10
                            font.weight: Font.DemiBold
                            font.letterSpacing: 0.7
                        }
                        Repeater {
                            model: window.modelManager.performanceStatsVisible ? window.removalController.timings : []
                            delegate: RowLayout {
                                required property var modelData
                                Layout.fillWidth: true
                                Layout.leftMargin: window.uiTheme.spaceLg
                                Layout.rightMargin: window.uiTheme.spaceLg
                                Text { text: modelData.label; color: window.uiTheme.textSecondary; font.family: window.uiTheme.fontFamily; font.pixelSize: 10; Layout.fillWidth: true }
                                Text { text: modelData.value; color: window.uiTheme.text; font.family: window.uiTheme.monoFontFamily; font.pixelSize: 10 }
                            }
                        }
                        Item { Layout.preferredHeight: window.uiTheme.spaceSm }
                    }
                }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.uiTheme.border }
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: window.uiTheme.spaceMd
                    Layout.rightMargin: window.uiTheme.spaceMd
                    Layout.topMargin: window.uiTheme.spaceSm
                    Layout.bottomMargin: window.uiTheme.spaceMd
                    spacing: window.uiTheme.spaceXs
                    Text {
                        Layout.fillWidth: true
                        text: window.appController.status
                        color: window.uiTheme.text
                        font.family: window.uiTheme.fontFamily
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                        horizontalAlignment: Text.AlignHCenter
                        elide: Text.ElideRight
                    }
                    RotoButton {
                        Layout.fillWidth: true
                        theme: window.uiTheme
                        visible: window.appController.busy
                        dangerStyle: window.appController.status !== "Waiting for Resolve"
                        text: window.appController.status === "Waiting for Resolve" ? "Resolve is applying…" : "Cancel operation"
                        enabled: window.appController.status !== "Waiting for Resolve"
                        onClicked: window.removalController.cancel()
                    }
                    RotoButton {
                        Layout.fillWidth: true
                        implicitHeight: 40
                        theme: window.uiTheme
                        primary: true
                        visible: !window.appController.busy
                        text: window.appController.trackingDirty ? "Track, Remove & Apply" : "Remove & Apply"
                        enabled: window.appController.hasPrompts
                            && window.appController.bridgeConnected
                            && window.removalController.backendInfo.available
                            && !window.blocked
                        toolTip: !window.appController.bridgeConnected
                            ? "Start a new session from DaVinci Resolve."
                            : !window.removalController.backendInfo.available
                                ? "Choose an available background-fill backend."
                                : "Build the removal result and apply it in Resolve."
                        onClicked: window.removalController.removeAndApply()
                    }
                }
            }
        }
    }
}
