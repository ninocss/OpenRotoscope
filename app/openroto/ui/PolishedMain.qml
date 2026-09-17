pragma ComponentBehavior: Bound

import QtCore
import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: window
    required property var appController
    required property var modelManager

    width: 1360
    height: 850
    minimumWidth: 900
    minimumHeight: 480
    visible: true
    title: "OpenRoto — " + window.appController.clipName
    color: "transparent"

    Settings {
        id: interfaceSettings
        category: "Interface"
        property string themeMode: "system"
    }

    property alias themeMode: interfaceSettings.themeMode
    readonly property bool dark: interfaceSettings.themeMode === "dark"
        || (interfaceSettings.themeMode === "system" && window.appController.darkMode)
    readonly property bool blocked: window.appController.busy || window.modelManager.busy
    readonly property int motionDuration: window.appController.reducedMotion ? 0 : 120
    readonly property bool compactMode: window.width < 1120

    RotoTheme { id: theme; dark: window.dark }
    readonly property var uiTheme: theme

    property Component workflowSwitcherComponent: null
    property Component customSidePanelComponent: null
    property url viewerFrameSource: window.appController.currentFrameUrl
    property bool maskOverlayEnabled: true
    property bool selectionPointsVisible: true
    property bool selectionEnabled: true
    property string viewerTitle: "Viewer"
    property int sidePanelWidth: 332
    property Component activeSidePanelComponent: window.customSidePanelComponent !== null
        ? window.customSidePanelComponent : rotoscopeControlsComponent

    signal settingsRequested()

    function openCompactControls() {
        if (window.compactMode)
            controlsDrawer.open()
    }

    function resetViewer() {
        imageStack.zoom = 1
        imageStack.x = 0
        imageStack.y = 0
    }

    component CenteredTip: ToolTip {
        id: tip
        delay: 420
        timeout: 5000
        padding: 8
        contentItem: Text {
            text: tip.text
            color: theme.text
            font.family: theme.fontFamily
            font.pixelSize: 10
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
        }
        background: Rectangle {
            radius: theme.radiusSm
            color: theme.surfaceRaised
            border.width: 1
            border.color: theme.borderStrong
        }
    }

    component SectionLabel: Text {
        color: theme.textMuted
        font.family: theme.fontFamily
        font.pixelSize: 10
        font.weight: Font.DemiBold
        font.letterSpacing: 0.7
    }

    component SubjectMarker: Item {
        id: marker
        property bool positive: true
        implicitWidth: 22
        implicitHeight: 22
        Rectangle {
            anchors.centerIn: parent
            width: marker.positive ? 18 : 16
            height: marker.positive ? 18 : 16
            radius: marker.positive ? 9 : 4
            rotation: marker.positive ? 0 : 45
            color: "#94080A0D"
            border.width: 2
            border.color: marker.positive ? theme.accent : theme.danger
        }
        Rectangle {
            anchors.centerIn: parent
            width: marker.positive ? 6 : 5
            height: marker.positive ? 6 : 5
            radius: marker.positive ? 3 : 1
            rotation: marker.positive ? 0 : 45
            color: marker.positive ? theme.accent : theme.danger
        }
    }

    Rectangle {
        anchors.fill: parent
        color: theme.canvas

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: theme.spaceMd
            spacing: theme.spaceSm

            GlassPanel {
                Layout.fillWidth: true
                Layout.preferredHeight: 58
                theme: window.uiTheme
                elevated: true
                strong: true

                Item {
                    anchors.fill: parent
                    anchors.leftMargin: theme.spaceMd
                    anchors.rightMargin: theme.spaceSm

                    Row {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: theme.spaceSm
                        Image {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 30
                            height: 30
                            source: "openroto.svg"
                            fillMode: Image.PreserveAspectFit
                        }
                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: -1
                            Text {
                                text: "OpenRoto"
                                color: theme.text
                                font.family: theme.displayFontFamily
                                font.pixelSize: 16
                                font.weight: Font.DemiBold
                            }
                            Text {
                                visible: !window.compactMode
                                width: Math.min(390, implicitWidth)
                                text: window.appController.clipName + "  ·  " + window.appController.clipMeta
                                color: theme.textSecondary
                                font.family: theme.fontFamily
                                font.pixelSize: 10
                                elide: Text.ElideRight
                            }
                        }
                    }

                    Loader {
                        anchors.centerIn: parent
                        sourceComponent: window.workflowSwitcherComponent
                        visible: sourceComponent !== null
                    }

                    Row {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: theme.spaceXs
                        RotoButton {
                            theme: window.uiTheme
                            width: 34; height: 34; leftPadding: 0; rightPadding: 0
                            quiet: true
                            text: "↶"
                            font.family: "Segoe UI Symbol"; font.pixelSize: 15
                            toolTip: "Undo · Ctrl+Z"
                            enabled: window.appController.canUndo && !window.blocked
                            onClicked: window.appController.undo()
                        }
                        RotoButton {
                            theme: window.uiTheme
                            width: 34; height: 34; leftPadding: 0; rightPadding: 0
                            quiet: true
                            text: "↷"
                            font.family: "Segoe UI Symbol"; font.pixelSize: 15
                            toolTip: "Redo · Ctrl+Y"
                            enabled: window.appController.canRedo && !window.blocked
                            onClicked: window.appController.redo()
                        }
                        RotoButton {
                            theme: window.uiTheme
                            width: 34; height: 34; leftPadding: 0; rightPadding: 0
                            quiet: true
                            text: "⌫"
                            font.family: "Segoe UI Symbol"; font.pixelSize: 14
                            toolTip: "Clear selection points on this frame"
                            enabled: !window.blocked
                            onClicked: window.appController.clearFrame()
                        }
                        Rectangle {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 1; height: 22
                            color: theme.borderStrong
                        }
                        StatusPill {
                            theme: window.uiTheme
                            compact: window.compactMode
                            label: window.appController.bridgeConnected ? "Resolve linked" : "Resolve offline"
                            dotColor: window.appController.bridgeConnected ? theme.success : theme.danger
                            toolTip: window.appController.bridgeConnected
                                ? "OpenRoto is connected to this Resolve session."
                                : "Start a new OpenRoto session from DaVinci Resolve."
                        }
                        StatusPill {
                            theme: window.uiTheme
                            compact: window.compactMode
                            label: window.appController.computeBadge
                            dotColor: window.appController.computeDevice.indexOf("CUDA") >= 0 ? theme.success : theme.warning
                            toolTip: window.appController.computeDevice + "\n" + window.appController.computeDetail
                        }
                        RotoButton {
                            visible: window.compactMode
                            theme: window.uiTheme
                            width: 34; height: 34; leftPadding: 0; rightPadding: 0
                            quiet: true
                            text: "☰"
                            font.family: "Segoe UI Symbol"; font.pixelSize: 15
                            toolTip: "Open controls"
                            onClicked: window.openCompactControls()
                        }
                        RotoButton {
                            theme: window.uiTheme
                            width: 34; height: 34; leftPadding: 0; rightPadding: 0
                            quiet: true
                            text: "⚙"
                            font.family: "Segoe UI Symbol"; font.pixelSize: 15
                            toolTip: "Settings · Ctrl+,"
                            onClicked: window.settingsRequested()
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: theme.spaceSm

                GlassPanel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: window.compactMode ? 0 : 700
                    theme: window.uiTheme

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: theme.spaceSm
                        spacing: theme.spaceSm

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 30
                            spacing: theme.spaceSm
                            Text {
                                text: window.viewerTitle
                                color: theme.text
                                font.family: theme.fontFamily
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                            }
                            StatusPill {
                                theme: window.uiTheme
                                label: window.appController.promptCount === 0
                                    ? "No selection"
                                    : window.appController.promptCount + (window.appController.promptCount === 1 ? " point" : " points")
                                dotColor: window.appController.promptCount > 0 ? theme.accent : theme.textMuted
                                toolTip: "Left click adds Subject points. Right click adds Exclude points."
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: Math.round(imageStack.zoom * 100) + "%"
                                color: theme.textSecondary
                                font.family: theme.monoFontFamily
                                font.pixelSize: 10
                            }
                            RotoButton {
                                theme: window.uiTheme
                                implicitWidth: 46
                                implicitHeight: 32
                                text: "1:1"
                                quiet: true
                                toolTip: "Reset viewer zoom and position"
                                onClicked: window.resetViewer()
                            }
                        }

                        Rectangle {
                            id: viewport
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: theme.radiusMd
                            color: theme.viewer
                            clip: true
                            border.width: 1
                            border.color: theme.border

                            Item {
                                id: imageStack
                                width: parent.width
                                height: parent.height
                                property real zoom: 1
                                x: 0; y: 0; scale: zoom
                                transformOrigin: Item.Center
                                Behavior on scale {
                                    NumberAnimation { duration: window.motionDuration; easing.type: Easing.OutCubic }
                                }

                                Image {
                                    id: frameImage
                                    anchors.fill: parent
                                    source: window.viewerFrameSource
                                    fillMode: Image.PreserveAspectFit
                                    asynchronous: true
                                    cache: true
                                    smooth: true
                                }

                                Item {
                                    id: paintedArea
                                    width: frameImage.paintedWidth
                                    height: frameImage.paintedHeight
                                    anchors.centerIn: parent

                                    Image {
                                        id: maskImage
                                        anchors.fill: parent
                                        source: window.appController.currentMaskUrl
                                        fillMode: Image.Stretch
                                        visible: false
                                        cache: false
                                    }
                                    MultiEffect {
                                        anchors.fill: maskImage
                                        source: maskImage
                                        visible: window.maskOverlayEnabled && maskImage.status === Image.Ready
                                        opacity: window.appController.overlayOpacity
                                        colorization: 1
                                        colorizationColor: theme.accent
                                    }
                                    Repeater {
                                        model: window.selectionPointsVisible ? window.appController.points : []
                                        delegate: Item {
                                            id: pointItem
                                            required property var modelData
                                            x: pointItem.modelData.x * paintedArea.width - 11
                                            y: pointItem.modelData.y * paintedArea.height - 11
                                            width: 22; height: 22
                                            SubjectMarker { anchors.fill: parent; positive: pointItem.modelData.positive }
                                        }
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                                        enabled: window.selectionEnabled && !window.blocked
                                        cursorShape: Qt.CrossCursor
                                        onClicked: mouse => window.appController.addPoint(
                                            Math.max(0, Math.min(1, mouse.x / width)),
                                            Math.max(0, Math.min(1, mouse.y / height)),
                                            mouse.button === Qt.LeftButton
                                        )
                                        onPressed: mouse => mouse.accepted = true
                                    }
                                }

                                WheelHandler {
                                    target: null
                                    onWheel: event => {
                                        const factor = event.angleDelta.y > 0 ? 1.12 : 0.89
                                        imageStack.zoom = Math.max(1, Math.min(6, imageStack.zoom * factor))
                                        if (imageStack.zoom <= 1.01)
                                            window.resetViewer()
                                    }
                                }
                                DragHandler {
                                    target: imageStack
                                    acceptedButtons: Qt.MiddleButton
                                    enabled: imageStack.zoom > 1
                                }
                            }

                            GlassPanel {
                                anchors.horizontalCenter: parent.horizontalCenter
                                anchors.bottom: parent.bottom
                                anchors.bottomMargin: theme.spaceMd
                                width: Math.min(hintRow.implicitWidth + 24, parent.width - theme.spaceLg * 2)
                                height: 32
                                radius: 16
                                theme: window.uiTheme
                                strong: true
                                visible: !window.appController.busy
                                Row {
                                    id: hintRow
                                    anchors.centerIn: parent
                                    spacing: window.compactMode ? theme.spaceSm : theme.spaceLg
                                    Row {
                                        spacing: theme.spaceXs
                                        SubjectMarker { width: 16; height: 16; positive: true; anchors.verticalCenter: parent.verticalCenter }
                                        Text {
                                            text: window.compactMode ? "Subject · LMB" : "Subject · Left click"
                                            color: theme.text; font.family: theme.fontFamily
                                            font.pixelSize: window.compactMode ? 9 : 10
                                            anchors.verticalCenter: parent.verticalCenter
                                        }
                                    }
                                    Row {
                                        spacing: theme.spaceXs
                                        SubjectMarker { width: 16; height: 16; positive: false; anchors.verticalCenter: parent.verticalCenter }
                                        Text {
                                            text: window.compactMode ? "Exclude · RMB" : "Exclude · Right click"
                                            color: theme.text; font.family: theme.fontFamily
                                            font.pixelSize: window.compactMode ? 9 : 10
                                            anchors.verticalCenter: parent.verticalCenter
                                        }
                                    }
                                    Text {
                                        text: window.compactMode ? "Wheel · MMB drag" : "Wheel zoom · Middle drag"
                                        color: theme.textSecondary; font.family: theme.fontFamily
                                        font.pixelSize: window.compactMode ? 9 : 10
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }
                            }

                            MultiEffect {
                                anchors.fill: imageStack
                                source: imageStack
                                visible: window.appController.busy
                                blurEnabled: true
                                blur: 0.78
                                blurMax: 48
                                opacity: 0.96
                            }
                            Rectangle { anchors.fill: parent; visible: window.appController.busy; color: theme.scrim }
                            GlassPanel {
                                anchors.centerIn: parent
                                width: Math.min(390, parent.width - 48)
                                height: busyColumn.implicitHeight + 32
                                visible: window.appController.busy
                                theme: window.uiTheme
                                strong: true
                                elevated: true
                                Column {
                                    id: busyColumn
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.leftMargin: theme.spaceLg
                                    anchors.rightMargin: theme.spaceLg
                                    spacing: theme.spaceSm
                                    BusyIndicator { width: 24; height: 24; running: parent.parent.visible; anchors.horizontalCenter: parent.horizontalCenter }
                                    Text {
                                        width: parent.width
                                        text: window.appController.status
                                        color: theme.text
                                        font.family: theme.fontFamily
                                        font.pixelSize: 12
                                        font.weight: Font.DemiBold
                                        horizontalAlignment: Text.AlignHCenter
                                        wrapMode: Text.WordWrap
                                    }
                                    Text {
                                        width: parent.width
                                        visible: text.length > 0
                                        text: window.appController.detail
                                        color: theme.textSecondary
                                        font.family: theme.fontFamily
                                        font.pixelSize: 10
                                        horizontalAlignment: Text.AlignHCenter
                                        wrapMode: Text.WordWrap
                                    }
                                    ProgressBar { width: parent.width; from: 0; to: 1; value: window.appController.progress }
                                }
                            }
                        }

                        GlassPanel {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 58
                            theme: window.uiTheme
                            strong: true
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: theme.spaceSm
                                anchors.rightMargin: theme.spaceSm
                                spacing: theme.spaceSm
                                RotoButton {
                                    theme: window.uiTheme
                                    width: 34; height: 34; leftPadding: 0; rightPadding: 0
                                    quiet: true
                                    text: "‹"; font.pixelSize: 18
                                    toolTip: "Previous frame"
                                    enabled: !window.blocked && window.appController.currentFrame > 0
                                    onClicked: window.appController.setFrame(window.appController.currentFrame - 1)
                                }
                                Text {
                                    Layout.preferredWidth: window.compactMode ? 70 : 88
                                    text: window.appController.frameLabel
                                    color: theme.textSecondary
                                    font.family: theme.monoFontFamily
                                    font.pixelSize: 10
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                                RotoSlider {
                                    Layout.fillWidth: true
                                    theme: window.uiTheme
                                    from: 0
                                    to: Math.max(0, window.appController.frameCount - 1)
                                    stepSize: 1
                                    value: window.appController.currentFrame
                                    enabled: !window.blocked
                                    toolTip: window.appController.frameLabel
                                    onMoved: window.appController.setFrame(Math.round(value))
                                }
                                RotoButton {
                                    theme: window.uiTheme
                                    width: 34; height: 34; leftPadding: 0; rightPadding: 0
                                    quiet: true
                                    text: "›"; font.pixelSize: 18
                                    toolTip: "Next frame"
                                    enabled: !window.blocked && window.appController.currentFrame < window.appController.frameCount - 1
                                    onClicked: window.appController.setFrame(window.appController.currentFrame + 1)
                                }
                            }
                        }
                    }
                }

                Loader {
                    visible: !window.compactMode
                    Layout.preferredWidth: visible ? window.sidePanelWidth : 0
                    Layout.minimumWidth: visible ? window.sidePanelWidth : 0
                    Layout.maximumWidth: visible ? window.sidePanelWidth : 0
                    Layout.fillHeight: true
                    sourceComponent: visible ? window.activeSidePanelComponent : null
                }
            }
        }
    }

    Drawer {
        id: controlsDrawer
        edge: Qt.RightEdge
        width: Math.min(380, Math.max(300, window.width * 0.86))
        height: window.height
        modal: true
        interactive: window.compactMode
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: theme.canvas
            border.width: 1
            border.color: theme.borderStrong
        }

        contentItem: Item {
            Loader {
                anchors.fill: parent
                anchors.margins: theme.spaceSm
                sourceComponent: window.compactMode ? window.activeSidePanelComponent : null
            }
        }
    }

    Component {
        id: rotoscopeControlsComponent
        GlassPanel {
            theme: window.uiTheme
            ColumnLayout {
                anchors.fill: parent
                spacing: 0
                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 48
                    Layout.leftMargin: theme.spaceLg
                    Layout.rightMargin: theme.spaceMd
                    Text {
                        Layout.fillWidth: true
                        text: "Rotoscope"
                        color: theme.text
                        font.family: theme.displayFontFamily
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                    }
                    StatusPill {
                        theme: window.uiTheme
                        label: window.appController.trackingReady ? "Tracked" : window.appController.hasPrompts ? "Needs track" : "Select"
                        dotColor: window.appController.trackingReady ? theme.success : window.appController.hasPrompts ? theme.accent : theme.textMuted
                    }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: theme.border }
                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    contentWidth: availableWidth
                    ColumnLayout {
                        width: parent.width
                        spacing: theme.spaceSm
                        Item { Layout.preferredHeight: theme.spaceXs }
                        SectionLabel { text: "SELECTION"; Layout.leftMargin: theme.spaceLg }
                        Text {
                            Layout.fillWidth: true
                            Layout.leftMargin: theme.spaceLg
                            Layout.rightMargin: theme.spaceLg
                            text: "Mark the subject with left click. Add Exclude points only where the mask includes unwanted background."
                            color: theme.textSecondary
                            font.family: theme.fontFamily
                            font.pixelSize: 11
                            wrapMode: Text.WordWrap
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.leftMargin: theme.spaceLg
                            Layout.rightMargin: theme.spaceLg
                            spacing: theme.spaceMd
                            Row {
                                Layout.fillWidth: true
                                spacing: theme.spaceXs
                                SubjectMarker { width: 20; height: 20; positive: true; anchors.verticalCenter: parent.verticalCenter }
                                Column {
                                    Text { text: "Subject"; color: theme.text; font.family: theme.fontFamily; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    Text { text: "Left click"; color: theme.textMuted; font.family: theme.fontFamily; font.pixelSize: 9 }
                                }
                            }
                            Row {
                                Layout.fillWidth: true
                                spacing: theme.spaceXs
                                SubjectMarker { width: 20; height: 20; positive: false; anchors.verticalCenter: parent.verticalCenter }
                                Column {
                                    Text { text: "Exclude"; color: theme.text; font.family: theme.fontFamily; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    Text { text: "Right click"; color: theme.textMuted; font.family: theme.fontFamily; font.pixelSize: 9 }
                                }
                            }
                        }
                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: theme.border; Layout.topMargin: theme.spaceXs }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.leftMargin: theme.spaceLg
                            Layout.rightMargin: theme.spaceMd
                            SectionLabel { text: "TRACKING"; Layout.fillWidth: true }
                            RotoButton {
                                theme: window.uiTheme
                                width: 30; height: 30; leftPadding: 0; rightPadding: 0
                                quiet: true
                                text: "ⓘ"; font.pixelSize: 13
                                toolTip: "Choose the SAM 2.1 model and tracking direction. Balanced is the default for most clips."
                            }
                        }
                        RotoComboBox {
                            Layout.fillWidth: true
                            Layout.leftMargin: theme.spaceLg
                            Layout.rightMargin: theme.spaceLg
                            theme: window.uiTheme
                            model: ["Fast", "Balanced", "High"]
                            currentIndex: window.appController.modelPreset === "fast" ? 0 : window.appController.modelPreset === "high" ? 2 : 1
                            enabled: !window.blocked
                            onActivated: index => window.appController.setModelPreset(index === 0 ? "fast" : index === 2 ? "high" : "balanced")
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.leftMargin: theme.spaceLg
                            Layout.rightMargin: theme.spaceLg
                            spacing: theme.spaceXs
                            Repeater {
                                model: [
                                    {"label": "Backward", "value": "backward"},
                                    {"label": "Both", "value": "both"},
                                    {"label": "Forward", "value": "forward"}
                                ]
                                delegate: RotoButton {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    theme: window.uiTheme
                                    text: modelData.label
                                    selected: window.appController.trackingDirection === modelData.value
                                    quiet: !selected
                                    enabled: !window.blocked
                                    onClicked: window.appController.setTrackingDirection(modelData.value)
                                }
                            }
                        }
                        RotoButton {
                            Layout.fillWidth: true
                            Layout.leftMargin: theme.spaceLg
                            Layout.rightMargin: theme.spaceLg
                            theme: window.uiTheme
                            primary: window.appController.hasPrompts
                            text: window.appController.trackingReady ? "Track again" : "Track selection"
                            enabled: window.appController.hasPrompts && !window.blocked
                            toolTip: window.appController.hasPrompts ? "Track the selected subject through the chosen direction." : "Add at least one Subject point first."
                            onClicked: window.appController.track()
                        }
                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: theme.border; Layout.topMargin: theme.spaceXs }
                        SectionLabel { text: "MATTE"; Layout.leftMargin: theme.spaceLg }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.leftMargin: theme.spaceLg
                            Layout.rightMargin: theme.spaceLg
                            Text { text: "Overlay"; color: theme.text; font.family: theme.fontFamily; font.pixelSize: 11; Layout.fillWidth: true }
                            Text { text: Math.round(window.appController.overlayOpacity * 100) + "%"; color: theme.textSecondary; font.family: theme.monoFontFamily; font.pixelSize: 10 }
                        }
                        RotoSlider {
                            Layout.fillWidth: true
                            Layout.leftMargin: theme.spaceLg
                            Layout.rightMargin: theme.spaceLg
                            theme: window.uiTheme
                            from: 0; to: 1
                            value: window.appController.overlayOpacity
                            enabled: !window.blocked
                            toolTip: Math.round(value * 100) + "% overlay"
                            onMoved: window.appController.setOverlayOpacity(value)
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.leftMargin: theme.spaceLg
                            Layout.rightMargin: theme.spaceLg
                            Text { text: "Expand / Contract"; color: theme.text; font.family: theme.fontFamily; font.pixelSize: 11; Layout.fillWidth: true }
                            Text { text: (window.appController.expandContract > 0 ? "+" : "") + window.appController.expandContract + " px"; color: theme.textSecondary; font.family: theme.monoFontFamily; font.pixelSize: 10 }
                        }
                        RotoSlider {
                            Layout.fillWidth: true
                            Layout.leftMargin: theme.spaceLg
                            Layout.rightMargin: theme.spaceLg
                            theme: window.uiTheme
                            from: -16; to: 16; stepSize: 1
                            value: window.appController.expandContract
                            enabled: !window.blocked
                            toolTip: Math.round(value) + " px"
                            onMoved: window.appController.setExpandContract(Math.round(value))
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.leftMargin: theme.spaceLg
                            Layout.rightMargin: theme.spaceLg
                            Text { text: "Feather"; color: theme.text; font.family: theme.fontFamily; font.pixelSize: 11; Layout.fillWidth: true }
                            Text { text: window.appController.feather.toFixed(1) + " px"; color: theme.textSecondary; font.family: theme.monoFontFamily; font.pixelSize: 10 }
                        }
                        RotoSlider {
                            Layout.fillWidth: true
                            Layout.leftMargin: theme.spaceLg
                            Layout.rightMargin: theme.spaceLg
                            theme: window.uiTheme
                            from: 0; to: 24; stepSize: 0.5
                            value: window.appController.feather
                            enabled: !window.blocked
                            toolTip: value.toFixed(1) + " px"
                            onMoved: window.appController.setFeather(value)
                        }
                        RotoSwitch {
                            Layout.leftMargin: theme.spaceLg
                            theme: window.uiTheme
                            text: "Invert matte"
                            checked: window.appController.invert
                            enabled: !window.blocked
                            onToggled: window.appController.setInvert(checked)
                        }
                        Item { Layout.preferredHeight: theme.spaceSm }
                    }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: theme.border }
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: theme.spaceMd
                    Layout.rightMargin: theme.spaceMd
                    Layout.topMargin: theme.spaceSm
                    Layout.bottomMargin: theme.spaceMd
                    spacing: theme.spaceXs
                    Text {
                        Layout.fillWidth: true
                        text: window.appController.status
                        color: theme.text
                        font.family: theme.fontFamily
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                        horizontalAlignment: Text.AlignHCenter
                        elide: Text.ElideRight
                    }
                    Text {
                        Layout.fillWidth: true
                        visible: text.length > 0 && !window.appController.busy
                        text: window.appController.detail
                        color: theme.textSecondary
                        font.family: theme.fontFamily
                        font.pixelSize: 9
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                    }
                    RotoButton {
                        Layout.fillWidth: true
                        theme: window.uiTheme
                        visible: window.appController.busy
                        dangerStyle: window.appController.status !== "Waiting for Resolve"
                        text: window.appController.status === "Waiting for Resolve" ? "Resolve is applying…" : "Cancel operation"
                        enabled: window.appController.status !== "Waiting for Resolve"
                        onClicked: window.appController.cancel()
                    }
                    RotoButton {
                        Layout.fillWidth: true
                        implicitHeight: 40
                        theme: window.uiTheme
                        primary: true
                        visible: !window.appController.busy
                        text: window.appController.trackingDirty ? "Track, Render & Apply" : "Render & Apply"
                        enabled: window.appController.hasPrompts && window.appController.bridgeConnected && !window.blocked
                        toolTip: !window.appController.bridgeConnected
                            ? "Start a new session from DaVinci Resolve."
                            : !window.appController.hasPrompts ? "Add at least one Subject point first." : "Render the matte and apply it in Resolve."
                        onClicked: window.appController.renderAndApply()
                    }
                }
            }
        }
    }

    Popup {
        id: closeGuard
        anchors.centerIn: parent
        width: Math.min(500, window.width - 48)
        implicitHeight: closeContent.implicitHeight + theme.spaceXl * 2
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape
        background: GlassPanel { theme: window.uiTheme; elevated: true; strong: true }
        contentItem: ColumnLayout {
            id: closeContent
            anchors.fill: parent
            anchors.margins: theme.spaceXl
            spacing: theme.spaceMd
            RowLayout {
                Layout.fillWidth: true
                spacing: theme.spaceMd
                Rectangle {
                    Layout.preferredWidth: 36; Layout.preferredHeight: 36
                    radius: 18
                    color: window.appController.status === "Waiting for Resolve" ? theme.warningSoft : theme.dangerSoft
                    Text {
                        anchors.centerIn: parent
                        text: "!"
                        color: window.appController.status === "Waiting for Resolve" ? theme.warning : theme.danger
                        font.family: theme.displayFontFamily
                        font.pixelSize: 18
                        font.weight: Font.Bold
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Text {
                        Layout.fillWidth: true
                        text: window.appController.status === "Waiting for Resolve"
                            ? "Resolve is still applying the result"
                            : "An operation is still running"
                        color: theme.text
                        font.family: theme.displayFontFamily
                        font.pixelSize: 17
                        font.weight: Font.DemiBold
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        Layout.fillWidth: true
                        text: window.appController.status
                        color: theme.textMuted
                        font.family: theme.fontFamily
                        font.pixelSize: 10
                        elide: Text.ElideRight
                    }
                }
            }
            Text {
                Layout.fillWidth: true
                text: window.appController.status === "Waiting for Resolve"
                    ? "OpenRoto keeps this session open until DaVinci Resolve confirms that the matte was applied. Closing is delayed to avoid an incomplete handoff."
                    : "Closing now cancels the current tracking or render operation. Partial output is not applied to Resolve; OpenRoto closes as soon as cancellation finishes."
                color: theme.textSecondary
                font.family: theme.fontFamily
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: theme.spaceSm
                Item { Layout.fillWidth: true }
                RotoButton { theme: window.uiTheme; text: "Keep working"; onClicked: closeGuard.close() }
                RotoButton {
                    theme: window.uiTheme
                    primary: window.appController.status === "Waiting for Resolve"
                    dangerStyle: window.appController.status !== "Waiting for Resolve"
                    text: window.appController.status === "Waiting for Resolve" ? "Close when finished" : "Cancel & close"
                    onClicked: {
                        closeGuard.close()
                        window.appController.requestClose()
                    }
                }
            }
        }
    }

    Shortcut { sequence: "Ctrl+Z"; onActivated: window.appController.undo() }
    Shortcut { sequence: "Ctrl+Y"; onActivated: window.appController.redo() }
    Shortcut { sequence: "Ctrl+,"; onActivated: window.settingsRequested() }

    onCompactModeChanged: {
        if (!window.compactMode)
            controlsDrawer.close()
    }

    onClosing: close => {
        if (window.appController.busy) {
            close.accepted = false
            closeGuard.open()
            return
        }
        close.accepted = window.appController.requestClose()
        if (close.accepted)
            window.appController.closeSession()
    }
}
