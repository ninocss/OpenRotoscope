pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

PolishedMain {
    id: window

    onSettingsRequested: {
        window.modelManager.refresh()
        settingsPopup.open()
    }

    GlassPanel {
        parent: window.contentItem
        z: 1200
        x: Math.max(18, Math.round(((window.compactMode ? window.width : window.width - window.sidePanelWidth) - width) / 2))
        y: 80
        width: Math.min(760, window.width - (window.compactMode ? 0 : window.sidePanelWidth) - 72)
        height: 72
        visible: window.modelManager.performanceStatsVisible
        theme: window.uiTheme
        strong: true
        elevated: true

        ColumnLayout {
            anchors.fill: parent
            anchors.leftMargin: window.uiTheme.spaceMd
            anchors.rightMargin: window.uiTheme.spaceMd
            anchors.topMargin: window.uiTheme.spaceSm
            anchors.bottomMargin: window.uiTheme.spaceSm
            spacing: 3

            RowLayout {
                Layout.fillWidth: true
                spacing: window.uiTheme.spaceXs
                Text {
                    text: "PERFORMANCE"
                    color: window.uiTheme.textMuted
                    font.family: window.uiTheme.fontFamily
                    font.pixelSize: 9
                    font.weight: Font.DemiBold
                    font.letterSpacing: 0.7
                }
                Text {
                    text: "last measurement · milliseconds"
                    color: window.uiTheme.textMuted
                    font.family: window.uiTheme.fontFamily
                    font.pixelSize: 9
                }
                Item { Layout.fillWidth: true }
                RotoButton {
                    theme: window.uiTheme
                    width: window.compactMode ? 44 : 26; height: window.compactMode ? 44 : 26; leftPadding: 0; rightPadding: 0
                    quiet: true
                    text: "×"
                    toolTip: "Hide performance statistics"
                    onClicked: window.modelManager.setPerformanceStatsVisible(false)
                }
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
                                color: window.uiTheme.textSecondary
                                font.family: window.uiTheme.fontFamily
                                font.pixelSize: 9
                            }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: timingCell.modelData.value
                                color: timingCell.modelData.measured ? window.uiTheme.text : window.uiTheme.textMuted
                                font.family: window.uiTheme.monoFontFamily
                                font.pixelSize: 11
                                font.weight: timingCell.modelData.measured ? Font.DemiBold : Font.Normal
                            }
                        }
                        Rectangle {
                            visible: timingCell.index > 0
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            width: 1; height: 26
                            color: window.uiTheme.border
                        }
                    }
                }
            }
        }
    }

    Popup {
        id: settingsPopup
        objectName: "settingsPopup"
        anchors.centerIn: parent
        width: Math.min(window.width - 64, 760)
        height: Math.min(window.height - 64, 650)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: GlassPanel { theme: window.uiTheme; strong: true; elevated: true }

        contentItem: ColumnLayout {
            spacing: 0

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 58
                Layout.leftMargin: window.uiTheme.spaceXl
                Layout.rightMargin: window.uiTheme.spaceMd
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    Text {
                        text: "Settings"
                        color: window.uiTheme.text
                        font.family: window.uiTheme.displayFontFamily
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                    }
                    Text {
                        text: "Interface, local models and runtime information"
                        color: window.uiTheme.textMuted
                        font.family: window.uiTheme.fontFamily
                        font.pixelSize: 9
                    }
                }
                RotoButton {
                    theme: window.uiTheme
                    width: window.compactMode ? 44 : 34; height: window.compactMode ? 44 : 34; leftPadding: 0; rightPadding: 0
                    quiet: true
                    text: "×"
                    font.pixelSize: 16
                    toolTip: "Close settings"
                    onClicked: settingsPopup.close()
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
                    spacing: window.uiTheme.spaceMd
                    Item { Layout.preferredHeight: window.uiTheme.spaceXs }

                    Text {
                        Layout.leftMargin: window.uiTheme.spaceXl
                        text: "Interface"
                        color: window.uiTheme.text
                        font.family: window.uiTheme.displayFontFamily
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                    }

                    GlassPanel {
                        Layout.fillWidth: true
                        Layout.leftMargin: window.uiTheme.spaceXl
                        Layout.rightMargin: window.uiTheme.spaceXl
                        Layout.preferredHeight: 92
                        theme: window.uiTheme
                        strong: true
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: window.uiTheme.spaceMd
                            spacing: window.uiTheme.spaceSm
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 1
                                Text {
                                    text: "Appearance"
                                    color: window.uiTheme.text
                                    font.family: window.uiTheme.fontFamily
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                }
                                Text {
                                    text: "System follows Windows. Light and Dark stay selected for future sessions."
                                    color: window.uiTheme.textSecondary
                                    font.family: window.uiTheme.fontFamily
                                    font.pixelSize: 10
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: window.uiTheme.spaceXs
                                Repeater {
                                    model: [
                                        {"label": "System", "value": "system"},
                                        {"label": "Light", "value": "light"},
                                        {"label": "Dark", "value": "dark"}
                                    ]
                                    delegate: RotoButton {
                                        required property var modelData
                                        Layout.fillWidth: true
                                        theme: window.uiTheme
                                        text: modelData.label
                                        selected: window.themeMode === modelData.value
                                        quiet: !selected
                                        onClicked: window.themeMode = modelData.value
                                    }
                                }
                            }
                        }
                    }

                    GlassPanel {
                        Layout.fillWidth: true
                        Layout.leftMargin: window.uiTheme.spaceXl
                        Layout.rightMargin: window.uiTheme.spaceXl
                        Layout.preferredHeight: 76
                        theme: window.uiTheme
                        strong: true
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: window.uiTheme.spaceMd
                            anchors.rightMargin: window.uiTheme.spaceMd
                            spacing: window.uiTheme.spaceMd
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text {
                                    text: "Performance statistics"
                                    color: window.uiTheme.text
                                    font.family: window.uiTheme.fontFamily
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: "Show live selection and removal timings. Measurements continue while the overlay is hidden."
                                    color: window.uiTheme.textSecondary
                                    font.family: window.uiTheme.fontFamily
                                    font.pixelSize: 10
                                    wrapMode: Text.WordWrap
                                }
                            }
                            RotoSwitch {
                                theme: window.uiTheme
                                checked: window.modelManager.performanceStatsVisible
                                onToggled: window.modelManager.setPerformanceStatsVisible(checked)
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        Layout.leftMargin: window.uiTheme.spaceXl
                        Layout.rightMargin: window.uiTheme.spaceXl
                        color: window.uiTheme.border
                    }

                    Text {
                        Layout.leftMargin: window.uiTheme.spaceXl
                        text: "SAM 2.1 models"
                        color: window.uiTheme.text
                        font.family: window.uiTheme.displayFontFamily
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                    }
                    Text {
                        Layout.fillWidth: true
                        Layout.leftMargin: window.uiTheme.spaceXl
                        Layout.rightMargin: window.uiTheme.spaceXl
                        text: "Install only the selection models you want to keep locally. The selected default is used for new sessions."
                        color: window.uiTheme.textSecondary
                        font.family: window.uiTheme.fontFamily
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: window.modelManager.models
                        delegate: GlassPanel {
                            id: modelCard
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.leftMargin: window.uiTheme.spaceXl
                            Layout.rightMargin: window.uiTheme.spaceXl
                            Layout.preferredHeight: 92
                            theme: window.uiTheme
                            strong: true
                            border.color: modelCard.modelData.selected ? window.uiTheme.accent : window.uiTheme.border
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: window.uiTheme.spaceMd
                                spacing: window.uiTheme.spaceMd
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    RowLayout {
                                        Text {
                                            text: modelCard.modelData.name
                                            color: window.uiTheme.text
                                            font.family: window.uiTheme.fontFamily
                                            font.pixelSize: 12
                                            font.weight: Font.DemiBold
                                        }
                                        StatusPill {
                                            theme: window.uiTheme
                                            label: modelCard.modelData.selected ? "Default" : modelCard.modelData.status
                                            dotColor: modelCard.modelData.selected ? window.uiTheme.accent : modelCard.modelData.installed ? window.uiTheme.success : window.uiTheme.textMuted
                                        }
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: modelCard.modelData.description
                                        color: window.uiTheme.textSecondary
                                        font.family: window.uiTheme.fontFamily
                                        font.pixelSize: 9
                                        elide: Text.ElideRight
                                    }
                                    Text {
                                        text: "~" + modelCard.modelData.downloadMb + " MB  ·  " + modelCard.modelData.minimumVramGb + " GB VRAM recommended"
                                        color: window.uiTheme.textMuted
                                        font.family: window.uiTheme.fontFamily
                                        font.pixelSize: 9
                                    }
                                }
                                RotoButton {
                                    theme: window.uiTheme
                                    visible: modelCard.modelData.installed && !modelCard.modelData.selected
                                    text: "Set default"
                                    enabled: !window.modelManager.busy && !window.appController.busy
                                    onClicked: window.modelManager.setDefaultModel(modelCard.modelData.id)
                                }
                                RotoButton {
                                    theme: window.uiTheme
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
                        Layout.leftMargin: window.uiTheme.spaceXl
                        Layout.rightMargin: window.uiTheme.spaceXl
                        color: window.uiTheme.border
                    }
                    Text {
                        Layout.leftMargin: window.uiTheme.spaceXl
                        text: "Object removal backends"
                        color: window.uiTheme.text
                        font.family: window.uiTheme.displayFontFamily
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                    }
                    Text {
                        Layout.fillWidth: true
                        Layout.leftMargin: window.uiTheme.spaceXl
                        Layout.rightMargin: window.uiTheme.spaceXl
                        text: "Temporal Fill is built in. Optional backends run in isolated local environments so they do not alter OpenRoto or Resolve dependencies."
                        color: window.uiTheme.textSecondary
                        font.family: window.uiTheme.fontFamily
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }
                    Repeater {
                        model: window.modelManager.removalBackends
                        delegate: GlassPanel {
                            id: backendCard
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.leftMargin: window.uiTheme.spaceXl
                            Layout.rightMargin: window.uiTheme.spaceXl
                            Layout.preferredHeight: 84
                            theme: window.uiTheme
                            strong: true
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: window.uiTheme.spaceMd
                                spacing: 2
                                RowLayout {
                                    Layout.fillWidth: true
                                    Text {
                                        text: backendCard.modelData.display_name
                                        color: window.uiTheme.text
                                        font.family: window.uiTheme.fontFamily
                                        font.pixelSize: 12
                                        font.weight: Font.DemiBold
                                    }
                                    StatusPill {
                                        theme: window.uiTheme
                                        label: backendCard.modelData.status
                                        dotColor: backendCard.modelData.available ? window.uiTheme.success : window.uiTheme.warning
                                    }
                                    Item { Layout.fillWidth: true }
                                    Text {
                                        text: backendCard.modelData.license
                                        color: window.uiTheme.textMuted
                                        font.family: window.uiTheme.fontFamily
                                        font.pixelSize: 9
                                    }
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: backendCard.modelData.quality + " quality  ·  " + backendCard.modelData.speed + "  ·  " + backendCard.modelData.vram
                                    color: window.uiTheme.textSecondary
                                    font.family: window.uiTheme.fontFamily
                                    font.pixelSize: 9
                                    elide: Text.ElideRight
                                }
                                Text {
                                    Layout.fillWidth: true
                                    visible: backendCard.modelData.id !== "temporal"
                                    text: backendCard.modelData.available ? backendCard.modelData.root : "Configure " + backendCard.modelData.python_env + " and " + backendCard.modelData.root_env
                                    color: window.uiTheme.textMuted
                                    font.family: window.uiTheme.monoFontFamily
                                    font.pixelSize: 8
                                    elide: Text.ElideMiddle
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        Layout.leftMargin: window.uiTheme.spaceXl
                        Layout.rightMargin: window.uiTheme.spaceXl
                        color: window.uiTheme.border
                    }
                    Text {
                        Layout.leftMargin: window.uiTheme.spaceXl
                        text: "System"
                        color: window.uiTheme.text
                        font.family: window.uiTheme.displayFontFamily
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                    }
                    GlassPanel {
                        Layout.fillWidth: true
                        Layout.leftMargin: window.uiTheme.spaceXl
                        Layout.rightMargin: window.uiTheme.spaceXl
                        Layout.preferredHeight: 116
                        theme: window.uiTheme
                        strong: true
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: window.uiTheme.spaceMd
                            spacing: 4
                            Text {
                                Layout.fillWidth: true
                                text: window.appController.computeDevice + "\n" + window.appController.computeDetail
                                color: window.uiTheme.textSecondary
                                font.family: window.uiTheme.fontFamily
                                font.pixelSize: 10
                                wrapMode: Text.WordWrap
                            }
                            Text {
                                Layout.fillWidth: true
                                text: "Model cache: " + window.modelManager.cachePath
                                color: window.uiTheme.textMuted
                                font.family: window.uiTheme.monoFontFamily
                                font.pixelSize: 9
                                wrapMode: Text.WrapAnywhere
                            }
                            Text {
                                Layout.fillWidth: true
                                visible: window.modelManager.lastError.length > 0
                                text: window.modelManager.lastError
                                color: window.uiTheme.danger
                                font.family: window.uiTheme.fontFamily
                                font.pixelSize: 10
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                    Item { Layout.preferredHeight: window.uiTheme.spaceLg }
                }
            }
        }
    }
}
