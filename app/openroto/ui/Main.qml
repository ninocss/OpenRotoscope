pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import QtQuick.Window

ApplicationWindow {
    id: window
    required property var appController
    required property var modelManager

    width: 1380
    height: 860
    minimumWidth: 1080
    minimumHeight: 700
    visible: true
    title: "OpenRoto — " + window.appController.clipName
    color: "transparent"

    readonly property bool dark: window.appController.darkMode
    readonly property bool interactionBlocked: window.appController.busy || window.modelManager.busy
    readonly property color windowBg: dark ? "#E91C1C1C" : "#EEF3F3F3"
    readonly property color surface: dark ? "#E82B2B2B" : "#F8FFFFFF"
    readonly property color surfaceRaised: dark ? "#F3333333" : "#FFFFFFFF"
    readonly property color surfaceHover: dark ? "#3DFFFFFF" : "#11000000"
    readonly property color border: dark ? "#26FFFFFF" : "#1F000000"
    readonly property color borderStrong: dark ? "#40FFFFFF" : "#32000000"
    readonly property color textPrimary: dark ? "#F5F5F5" : "#1A1A1A"
    readonly property color textSecondary: dark ? "#B4B4B4" : "#5C5C5C"
    readonly property color textMuted: dark ? "#858585" : "#7A7A7A"
    readonly property color accent: dark ? "#60CDFF" : "#0067C0"
    readonly property color accentPressed: dark ? "#4DB4E5" : "#005A9E"
    readonly property color accentSoft: dark ? "#2460CDFF" : "#170067C0"
    readonly property color positive: dark ? "#6CCB9F" : "#0F7B55"
    readonly property color negative: dark ? "#FF7A8A" : "#C42B1C"
    readonly property color warning: dark ? "#FCE100" : "#9D5D00"
    readonly property int motionDuration: window.appController.reducedMotion ? 0 : 140

    property int settingsPage: 0

    function resetViewer() {
        imageStack.zoom = 1
        imageStack.x = 0
        imageStack.y = 0
    }

    component Surface: Rectangle {
        radius: 10
        color: window.surface
        border.width: 1
        border.color: window.border
    }

    component FluentButton: Button {
        id: control
        property bool primary: false
        property bool selected: false
        property bool danger: false
        implicitHeight: 34
        leftPadding: 12
        rightPadding: 12
        font.family: "Segoe UI Variable Text"
        font.pixelSize: 13
        font.weight: primary ? Font.DemiBold : Font.Normal
        contentItem: Text {
            text: control.text
            color: control.primary ? "white" : control.danger ? window.negative : window.textPrimary
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 6
            border.width: control.primary || control.selected || control.visualFocus ? 1 : 0
            border.color: control.primary ? window.accent : control.selected ? window.accent : window.borderStrong
            color: control.primary
                ? (control.down ? window.accentPressed : window.accent)
                : control.selected
                    ? window.accentSoft
                    : control.down ? window.surfaceHover : control.hovered ? window.surfaceHover : "transparent"
            Behavior on color { ColorAnimation { duration: window.motionDuration } }
        }
    }

    component ToolButtonFluent: Button {
        id: control
        property bool selected: false
        implicitWidth: 34
        implicitHeight: 34
        font.family: "Segoe UI Symbol"
        font.pixelSize: 16
        contentItem: Text {
            text: control.text
            color: control.selected ? window.accent : window.textPrimary
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 6
            color: control.selected ? window.accentSoft : control.hovered ? window.surfaceHover : "transparent"
            border.width: control.visualFocus || control.selected ? 1 : 0
            border.color: control.selected ? window.accent : window.borderStrong
        }
    }

    component SectionTitle: Text {
        color: window.textMuted
        font.family: "Segoe UI Variable Text"
        font.pixelSize: 10
        font.weight: Font.DemiBold
        font.letterSpacing: 0.8
    }

    component RotoSlider: Slider {
        id: sliderControl
        implicitHeight: 24
        background: Rectangle {
            x: sliderControl.leftPadding
            y: sliderControl.topPadding + sliderControl.availableHeight / 2 - height / 2
            implicitHeight: 4
            width: sliderControl.availableWidth
            height: 4
            radius: 2
            color: window.dark ? "#4B4B4B" : "#D0D0D0"
            Rectangle {
                width: sliderControl.visualPosition * parent.width
                height: parent.height
                radius: 2
                color: window.accent
            }
        }
        handle: Rectangle {
            x: sliderControl.leftPadding + sliderControl.visualPosition * (sliderControl.availableWidth - width)
            y: sliderControl.topPadding + sliderControl.availableHeight / 2 - height / 2
            implicitWidth: 16
            implicitHeight: 16
            radius: 8
            color: sliderControl.pressed ? window.accent : window.surfaceRaised
            border.width: 2
            border.color: window.accent
        }
    }

    component StatusChip: Rectangle {
        id: chip
        property string label: ""
        property color dotColor: window.accent
        implicitWidth: chipRow.implicitWidth + 18
        implicitHeight: 28
        radius: 6
        color: window.dark ? "#772F2F2F" : "#D9FFFFFF"
        border.width: 1
        border.color: window.border
        Row {
            id: chipRow
            anchors.centerIn: parent
            spacing: 7
            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: 7
                height: 7
                radius: 4
                color: chip.dotColor
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: chip.label
                color: window.textSecondary
                font.family: "Segoe UI Variable Text"
                font.pixelSize: 11
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: window.windowBg

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 8

            Surface {
                Layout.fillWidth: true
                Layout.preferredHeight: 54
                radius: 8

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 8
                    spacing: 8

                    Image {
                        Layout.preferredWidth: 28
                        Layout.preferredHeight: 28
                        source: "openroto.svg"
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                    }

                    ColumnLayout {
                        spacing: -1
                        Text {
                            text: "OpenRoto"
                            color: window.textPrimary
                            font.family: "Segoe UI Variable Display"
                            font.pixelSize: 15
                            font.weight: Font.DemiBold
                        }
                        Text {
                            text: window.appController.clipName + "  ·  " + window.appController.clipMeta
                            color: window.textSecondary
                            font.family: "Segoe UI Variable Text"
                            font.pixelSize: 10
                            elide: Text.ElideRight
                            Layout.maximumWidth: 420
                        }
                    }

                    Item { Layout.fillWidth: true }

                    ToolButtonFluent {
                        text: "↶"
                        enabled: window.appController.canUndo && !window.interactionBlocked
                        opacity: enabled ? 1 : 0.35
                        onClicked: window.appController.undo()
                        ToolTip.visible: hovered
                        ToolTip.text: "Undo · Ctrl+Z"
                    }
                    ToolButtonFluent {
                        text: "↷"
                        enabled: window.appController.canRedo && !window.interactionBlocked
                        opacity: enabled ? 1 : 0.35
                        onClicked: window.appController.redo()
                        ToolTip.visible: hovered
                        ToolTip.text: "Redo · Ctrl+Y"
                    }
                    ToolButtonFluent {
                        text: "⌫"
                        enabled: !window.interactionBlocked
                        opacity: enabled ? 1 : 0.35
                        onClicked: window.appController.clearFrame()
                        ToolTip.visible: hovered
                        ToolTip.text: "Clear points on current frame"
                    }

                    Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 24; color: window.borderStrong; Layout.leftMargin: 4; Layout.rightMargin: 4 }

                    StatusChip {
                        label: window.appController.bridgeConnected ? "Resolve linked" : "Resolve offline"
                        dotColor: window.appController.bridgeConnected ? window.positive : window.negative
                    }
                    StatusChip {
                        label: window.appController.computeBadge
                        dotColor: window.appController.computeDevice.indexOf("CUDA") >= 0 ? window.positive : window.warning
                        ToolTip.visible: deviceHover.hovered
                        ToolTip.text: window.appController.computeDevice + "\n" + window.appController.computeDetail
                        HoverHandler { id: deviceHover }
                    }

                    ToolButtonFluent {
                        text: "⚙"
                        onClicked: {
                            window.modelManager.refresh()
                            settingsPopup.open()
                        }
                        ToolTip.visible: hovered
                        ToolTip.text: "Settings · Ctrl+,"
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 8

                Surface {
                    id: viewerSurface
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: 600

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 7

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 28
                            spacing: 8
                            Text {
                                text: "Viewer"
                                color: window.textPrimary
                                font.family: "Segoe UI Variable Text"
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                            }
                            StatusChip {
                                label: window.appController.promptCount === 0
                                    ? "No selection"
                                    : window.appController.promptCount + (window.appController.promptCount === 1 ? " point" : " points")
                                dotColor: window.appController.promptCount > 0 ? window.positive : window.textMuted
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: Math.round(imageStack.zoom * 100) + "%"
                                color: window.textSecondary
                                font.family: "Segoe UI Variable Text"
                                font.pixelSize: 11
                            }
                            ToolButtonFluent {
                                text: "1:1"
                                font.pixelSize: 10
                                implicitWidth: 40
                                onClicked: window.resetViewer()
                                ToolTip.visible: hovered
                                ToolTip.text: "Reset zoom"
                            }
                        }

                        Rectangle {
                            id: viewport
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 6
                            color: "#101010"
                            clip: true

                            Item {
                                id: imageStack
                                width: parent.width
                                height: parent.height
                                x: 0
                                y: 0
                                transformOrigin: Item.Center
                                property real zoom: 1
                                scale: zoom
                                Behavior on scale { NumberAnimation { duration: window.motionDuration; easing.type: Easing.OutCubic } }

                                Image {
                                    id: frameImage
                                    anchors.fill: parent
                                    source: window.appController.currentFrameUrl
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
                                        visible: maskImage.status === Image.Ready
                                        opacity: window.appController.overlayOpacity
                                        colorization: 1
                                        colorizationColor: window.accent
                                    }

                                    Repeater {
                                        model: window.appController.points
                                        delegate: Item {
                                            id: pointMarker
                                            required property var modelData
                                            x: pointMarker.modelData.x * paintedArea.width - 9
                                            y: pointMarker.modelData.y * paintedArea.height - 9
                                            width: 18
                                            height: 18

                                            Rectangle {
                                                anchors.centerIn: parent
                                                width: 26
                                                height: 26
                                                radius: 13
                                                color: "transparent"
                                                border.width: 1
                                                border.color: pointMarker.modelData.positive ? window.accent : window.negative
                                                opacity: 0.55
                                            }
                                            Rectangle {
                                                anchors.fill: parent
                                                radius: 9
                                                color: pointMarker.modelData.positive ? window.accent : window.negative
                                                border.width: 2
                                                border.color: "white"
                                            }
                                            Text {
                                                anchors.centerIn: parent
                                                text: pointMarker.modelData.positive ? "+" : "−"
                                                color: "white"
                                                font.family: "Segoe UI Variable Text"
                                                font.pixelSize: 12
                                                font.bold: true
                                            }
                                        }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                                        enabled: !window.interactionBlocked
                                        cursorShape: Qt.CrossCursor
                                        onClicked: mouse => {
                                            window.appController.addPoint(
                                                Math.max(0, Math.min(1, mouse.x / width)),
                                                Math.max(0, Math.min(1, mouse.y / height)),
                                                mouse.button === Qt.LeftButton
                                            )
                                        }
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

                            Rectangle {
                                anchors.left: parent.left
                                anchors.bottom: parent.bottom
                                anchors.leftMargin: 10
                                anchors.bottomMargin: 10
                                width: viewerHint.implicitWidth + 18
                                height: 28
                                radius: 6
                                color: "#B51D1D1D"
                                border.width: 1
                                border.color: "#33FFFFFF"
                                Text {
                                    id: viewerHint
                                    anchors.centerIn: parent
                                    text: "Left click + subject   ·   Right click − exclude   ·   Wheel zoom   ·   Middle drag pan"
                                    color: "#D8FFFFFF"
                                    font.family: "Segoe UI Variable Text"
                                    font.pixelSize: 10
                                }
                            }

                            Rectangle {
                                anchors.centerIn: parent
                                width: busyRow.implicitWidth + 28
                                height: 44
                                radius: 8
                                visible: window.appController.busy
                                color: "#E62B2B2B"
                                border.width: 1
                                border.color: "#3FFFFFFF"
                                Row {
                                    id: busyRow
                                    anchors.centerIn: parent
                                    spacing: 9
                                    BusyIndicator { width: 20; height: 20; running: visible }
                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: window.appController.status
                                        color: "white"
                                        font.family: "Segoe UI Variable Text"
                                        font.pixelSize: 12
                                        font.weight: Font.DemiBold
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 62
                            radius: 6
                            color: window.dark ? "#242424" : "#FAFAFA"
                            border.width: 1
                            border.color: window.border

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                spacing: 8

                                ToolButtonFluent {
                                    text: "‹"
                                    enabled: !window.interactionBlocked && window.appController.currentFrame > 0
                                    opacity: enabled ? 1 : 0.35
                                    onClicked: window.appController.setFrame(window.appController.currentFrame - 1)
                                    ToolTip.visible: hovered
                                    ToolTip.text: "Previous frame"
                                }
                                Text {
                                    text: window.appController.frameLabel
                                    color: window.textSecondary
                                    font.family: "Segoe UI Variable Text"
                                    font.pixelSize: 11
                                    Layout.preferredWidth: 78
                                    horizontalAlignment: Text.AlignHCenter
                                }
                                RotoSlider {
                                    Layout.fillWidth: true
                                    from: 0
                                    to: Math.max(0, window.appController.frameCount - 1)
                                    stepSize: 1
                                    value: window.appController.currentFrame
                                    enabled: !window.interactionBlocked
                                    onMoved: window.appController.setFrame(Math.round(value))
                                }
                                ToolButtonFluent {
                                    text: "›"
                                    enabled: !window.interactionBlocked && window.appController.currentFrame < window.appController.frameCount - 1
                                    opacity: enabled ? 1 : 0.35
                                    onClicked: window.appController.setFrame(window.appController.currentFrame + 1)
                                    ToolTip.visible: hovered
                                    ToolTip.text: "Next frame"
                                }
                            }
                        }
                    }
                }

                Surface {
                    id: inspector
                    Layout.preferredWidth: 326
                    Layout.minimumWidth: 326
                    Layout.maximumWidth: 326
                    Layout.fillHeight: true

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 0

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 46
                            Layout.leftMargin: 14
                            Layout.rightMargin: 10
                            Text {
                                text: "Controls"
                                color: window.textPrimary
                                font.family: "Segoe UI Variable Display"
                                font.pixelSize: 15
                                font.weight: Font.DemiBold
                                Layout.fillWidth: true
                            }
                            Text {
                                text: window.appController.trackingReady ? "Tracked" : window.appController.hasPrompts ? "Needs track" : "Select"
                                color: window.appController.trackingReady ? window.positive : window.appController.hasPrompts ? window.accent : window.textMuted
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

                                SectionTitle { text: "SELECTION"; Layout.leftMargin: 14 }
                                Text {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 14
                                    text: "Click the subject to add positive points. Right-click background or unwanted areas to exclude them."
                                    color: window.textSecondary
                                    font.family: "Segoe UI Variable Text"
                                    font.pixelSize: 11
                                    wrapMode: Text.WordWrap
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 14
                                    spacing: 6
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 32
                                        radius: 6
                                        color: window.accentSoft
                                        border.width: 1
                                        border.color: window.accent
                                        Text { anchors.centerIn: parent; text: "+  Left click"; color: window.accent; font.family: "Segoe UI Variable Text"; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 32
                                        radius: 6
                                        color: window.dark ? "#20FF7A8A" : "#14C42B1C"
                                        border.width: 1
                                        border.color: window.negative
                                        Text { anchors.centerIn: parent; text: "−  Right click"; color: window.negative; font.family: "Segoe UI Variable Text"; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    }
                                }

                                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.border; Layout.topMargin: 6 }

                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 10
                                    SectionTitle { text: "TRACKING"; Layout.fillWidth: true }
                                    ToolButtonFluent {
                                        text: "⚙"
                                        implicitWidth: 30
                                        implicitHeight: 30
                                        onClicked: {
                                            window.settingsPage = 0
                                            window.modelManager.refresh()
                                            settingsPopup.open()
                                        }
                                        ToolTip.visible: hovered
                                        ToolTip.text: "Manage models"
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 14
                                    spacing: 6
                                    ComboBox {
                                        id: modelBox
                                        Layout.fillWidth: true
                                        model: ["Fast", "Balanced", "High"]
                                        currentIndex: window.appController.modelPreset === "fast" ? 0 : window.appController.modelPreset === "high" ? 2 : 1
                                        enabled: !window.interactionBlocked
                                        onActivated: index => window.appController.setModelPreset(index === 0 ? "fast" : index === 2 ? "high" : "balanced")
                                        background: Rectangle {
                                            radius: 6
                                            color: window.surfaceRaised
                                            border.width: 1
                                            border.color: modelBox.visualFocus ? window.accent : window.borderStrong
                                        }
                                        contentItem: Text {
                                            leftPadding: 10
                                            text: modelBox.displayText
                                            color: window.textPrimary
                                            font.family: "Segoe UI Variable Text"
                                            font.pixelSize: 12
                                            verticalAlignment: Text.AlignVCenter
                                        }
                                    }
                                }

                                Text {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 14
                                    text: window.appController.modelPreset === "fast"
                                        ? "Fastest preview model for straightforward shots."
                                        : window.appController.modelPreset === "high"
                                            ? "Highest detail. Uses the most VRAM and disk space."
                                            : "Recommended balance of speed, quality and memory use."
                                    color: window.textSecondary
                                    font.family: "Segoe UI Variable Text"
                                    font.pixelSize: 10
                                    wrapMode: Text.WordWrap
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 14
                                    spacing: 4
                                    Repeater {
                                        model: [
                                            {"label": "Backward", "value": "backward"},
                                            {"label": "Both", "value": "both"},
                                            {"label": "Forward", "value": "forward"}
                                        ]
                                        delegate: FluentButton {
                                            required property var modelData
                                            Layout.fillWidth: true
                                            text: modelData.label
                                            selected: window.appController.trackingDirection === modelData.value
                                            enabled: !window.interactionBlocked
                                            onClicked: window.appController.setTrackingDirection(modelData.value)
                                        }
                                    }
                                }

                                FluentButton {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 14
                                    primary: window.appController.hasPrompts
                                    text: window.appController.trackingReady ? "Track again" : "Track selection"
                                    enabled: window.appController.hasPrompts && !window.interactionBlocked
                                    opacity: enabled ? 1 : 0.45
                                    onClicked: window.appController.track()
                                }

                                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.border; Layout.topMargin: 6 }

                                SectionTitle { text: "MATTE"; Layout.leftMargin: 14 }

                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 14
                                    Text { text: "Overlay"; color: window.textPrimary; font.family: "Segoe UI Variable Text"; font.pixelSize: 11; Layout.fillWidth: true }
                                    Text { text: Math.round(window.appController.overlayOpacity * 100) + "%"; color: window.textSecondary; font.family: "Segoe UI Variable Text"; font.pixelSize: 10 }
                                }
                                RotoSlider {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 14
                                    from: 0
                                    to: 1
                                    value: window.appController.overlayOpacity
                                    enabled: !window.interactionBlocked
                                    onMoved: window.appController.setOverlayOpacity(value)
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 14
                                    Text { text: "Expand / Contract"; color: window.textPrimary; font.family: "Segoe UI Variable Text"; font.pixelSize: 11; Layout.fillWidth: true }
                                    Text { text: (window.appController.expandContract > 0 ? "+" : "") + window.appController.expandContract + " px"; color: window.textSecondary; font.family: "Segoe UI Variable Text"; font.pixelSize: 10 }
                                }
                                RotoSlider {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 14
                                    from: -16
                                    to: 16
                                    stepSize: 1
                                    value: window.appController.expandContract
                                    enabled: !window.interactionBlocked
                                    onMoved: window.appController.setExpandContract(Math.round(value))
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 14
                                    Text { text: "Feather"; color: window.textPrimary; font.family: "Segoe UI Variable Text"; font.pixelSize: 11; Layout.fillWidth: true }
                                    Text { text: window.appController.feather.toFixed(1) + " px"; color: window.textSecondary; font.family: "Segoe UI Variable Text"; font.pixelSize: 10 }
                                }
                                RotoSlider {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 14
                                    from: 0
                                    to: 24
                                    stepSize: 0.5
                                    value: window.appController.feather
                                    enabled: !window.interactionBlocked
                                    onMoved: window.appController.setFeather(value)
                                }

                                Switch {
                                    id: invertSwitch
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 14
                                    text: "Invert matte"
                                    checked: window.appController.invert
                                    enabled: !window.interactionBlocked
                                    onToggled: window.appController.setInvert(checked)
                                    contentItem: Text {
                                        text: invertSwitch.text
                                        color: window.textPrimary
                                        font.family: "Segoe UI Variable Text"
                                        font.pixelSize: 11
                                        leftPadding: invertSwitch.indicator.width + invertSwitch.spacing
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }

                                Item { Layout.preferredHeight: 6 }
                            }
                        }

                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.border }

                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.leftMargin: 12
                            Layout.rightMargin: 12
                            Layout.topMargin: 10
                            Layout.bottomMargin: 12
                            spacing: 7

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 7
                                Rectangle {
                                    Layout.preferredWidth: 7
                                    Layout.preferredHeight: 7
                                    radius: 4
                                    color: window.appController.status.indexOf("wrong") >= 0 || window.appController.status.indexOf("lost") >= 0
                                        ? window.negative
                                        : window.appController.busy ? window.accent : window.positive
                                }
                                Text {
                                    Layout.fillWidth: true
                                    text: window.appController.status
                                    color: window.textPrimary
                                    font.family: "Segoe UI Variable Text"
                                    font.pixelSize: 11
                                    font.weight: Font.DemiBold
                                    elide: Text.ElideRight
                                }
                            }
                            Text {
                                Layout.fillWidth: true
                                visible: text.length > 0
                                text: window.appController.detail
                                color: window.textSecondary
                                font.family: "Segoe UI Variable Text"
                                font.pixelSize: 10
                                wrapMode: Text.WordWrap
                            }
                            ProgressBar {
                                Layout.fillWidth: true
                                visible: window.appController.busy
                                from: 0
                                to: 1
                                value: window.appController.progress
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 6
                                FluentButton {
                                    text: "Cancel"
                                    visible: window.appController.busy
                                    onClicked: window.appController.cancel()
                                }
                                FluentButton {
                                    Layout.fillWidth: true
                                    primary: true
                                    implicitHeight: 40
                                    text: window.appController.trackingDirty ? "Track, Render & Apply" : "Render & Apply"
                                    enabled: window.appController.hasPrompts && window.appController.bridgeConnected && !window.interactionBlocked
                                    opacity: enabled ? 1 : 0.45
                                    onClicked: window.appController.renderAndApply()
                                    ToolTip.visible: !window.appController.bridgeConnected && hovered
                                    ToolTip.text: "Start a new session from DaVinci Resolve"
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Popup {
        id: settingsPopup
        anchors.centerIn: parent
        width: Math.min(window.width - 70, 780)
        height: Math.min(window.height - 70, 620)
        modal: true
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape

        Overlay.modal: Rectangle { color: "#66000000" }
        background: Rectangle {
            radius: 12
            color: window.dark ? "#F72A2A2A" : "#FCF8F8F8"
            border.width: 1
            border.color: window.borderStrong
        }

        contentItem: ColumnLayout {
            spacing: 0

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 58
                Layout.leftMargin: 18
                Layout.rightMargin: 10
                Text {
                    text: "Settings"
                    color: window.textPrimary
                    font.family: "Segoe UI Variable Display"
                    font.pixelSize: 20
                    font.weight: Font.DemiBold
                    Layout.fillWidth: true
                }
                ToolButtonFluent {
                    text: "×"
                    font.pixelSize: 20
                    onClicked: settingsPopup.close()
                }
            }

            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.border }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                Rectangle {
                    Layout.preferredWidth: 170
                    Layout.fillHeight: true
                    color: window.dark ? "#262626" : "#F1F1F1"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 4

                        FluentButton {
                            Layout.fillWidth: true
                            text: "Models"
                            selected: window.settingsPage === 0
                            onClicked: window.settingsPage = 0
                        }
                        FluentButton {
                            Layout.fillWidth: true
                            text: "System"
                            selected: window.settingsPage === 1
                            onClicked: window.settingsPage = 1
                        }
                        Item { Layout.fillHeight: true }
                        Text {
                            Layout.fillWidth: true
                            text: "OpenRoto 0.1"
                            color: window.textMuted
                            font.family: "Segoe UI Variable Text"
                            font.pixelSize: 10
                            horizontalAlignment: Text.AlignHCenter
                        }
                    }
                }

                Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: window.border }

                StackLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    currentIndex: window.settingsPage

                    Item {
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 20
                            spacing: 10

                            Text {
                                text: "AI models"
                                color: window.textPrimary
                                font.family: "Segoe UI Variable Display"
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                            }
                            Text {
                                Layout.fillWidth: true
                                text: "Download only the SAM 2.1 models you want to keep locally. The selected default is used for new sessions and can still download automatically when first needed."
                                color: window.textSecondary
                                font.family: "Segoe UI Variable Text"
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                visible: window.modelManager.lastError.length > 0
                                implicitHeight: modelError.implicitHeight + 18
                                radius: 6
                                color: window.dark ? "#35FF7A8A" : "#18C42B1C"
                                border.width: 1
                                border.color: window.negative
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 9
                                    Text {
                                        id: modelError
                                        Layout.fillWidth: true
                                        text: window.modelManager.lastError
                                        color: window.textPrimary
                                        font.family: "Segoe UI Variable Text"
                                        font.pixelSize: 10
                                        wrapMode: Text.WordWrap
                                    }
                                    ToolButtonFluent {
                                        text: "×"
                                        implicitWidth: 28
                                        implicitHeight: 28
                                        onClicked: window.modelManager.clearError()
                                    }
                                }
                            }

                            ScrollView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                contentWidth: availableWidth

                                ColumnLayout {
                                    width: parent.width
                                    spacing: 8

                                    Repeater {
                                        model: window.modelManager.models
                                        delegate: Rectangle {
                                            id: modelCard
                                            required property var modelData
                                            Layout.fillWidth: true
                                            implicitHeight: modelBody.implicitHeight + 22
                                            radius: 8
                                            color: window.surfaceRaised
                                            border.width: 1
                                            border.color: modelCard.modelData.selected ? window.accent : window.border

                                            ColumnLayout {
                                                id: modelBody
                                                anchors.left: parent.left
                                                anchors.right: parent.right
                                                anchors.top: parent.top
                                                anchors.margins: 11
                                                spacing: 6

                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    Text {
                                                        text: modelCard.modelData.name
                                                        color: window.textPrimary
                                                        font.family: "Segoe UI Variable Text"
                                                        font.pixelSize: 13
                                                        font.weight: Font.DemiBold
                                                    }
                                                    Rectangle {
                                                        visible: modelCard.modelData.selected
                                                        implicitWidth: defaultText.implicitWidth + 12
                                                        implicitHeight: 22
                                                        radius: 5
                                                        color: window.accentSoft
                                                        Text {
                                                            id: defaultText
                                                            anchors.centerIn: parent
                                                            text: "Default"
                                                            color: window.accent
                                                            font.family: "Segoe UI Variable Text"
                                                            font.pixelSize: 9
                                                            font.weight: Font.DemiBold
                                                        }
                                                    }
                                                    Item { Layout.fillWidth: true }
                                                    Text {
                                                        text: modelCard.modelData.status
                                                        color: modelCard.modelData.installed ? window.positive : window.textSecondary
                                                        font.family: "Segoe UI Variable Text"
                                                        font.pixelSize: 10
                                                    }
                                                }

                                                Text {
                                                    Layout.fillWidth: true
                                                    text: modelCard.modelData.description
                                                    color: window.textSecondary
                                                    font.family: "Segoe UI Variable Text"
                                                    font.pixelSize: 10
                                                    wrapMode: Text.WordWrap
                                                }

                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    Text {
                                                        text: "~" + modelCard.modelData.downloadMb + " MB  ·  " + modelCard.modelData.minimumVramGb + " GB VRAM recommended"
                                                        color: window.textMuted
                                                        font.family: "Segoe UI Variable Text"
                                                        font.pixelSize: 9
                                                        Layout.fillWidth: true
                                                    }
                                                    FluentButton {
                                                        text: modelCard.modelData.selected ? "Default" : "Set default"
                                                        selected: modelCard.modelData.selected
                                                        enabled: !window.modelManager.busy && !window.appController.busy && !modelCard.modelData.selected
                                                        opacity: enabled || modelCard.modelData.selected ? 1 : 0.45
                                                        onClicked: window.modelManager.setDefaultModel(modelCard.modelData.id)
                                                    }
                                                    FluentButton {
                                                        text: modelCard.modelData.busy
                                                            ? (modelCard.modelData.installed ? "Removing…" : "Downloading…")
                                                            : modelCard.modelData.installed ? "Remove" : "Download"
                                                        danger: modelCard.modelData.installed
                                                        enabled: !window.modelManager.busy && !window.appController.busy
                                                        onClicked: {
                                                            if (modelCard.modelData.installed)
                                                                window.modelManager.removeModel(modelCard.modelData.id)
                                                            else
                                                                window.modelManager.downloadModel(modelCard.modelData.id)
                                                        }
                                                    }
                                                }

                                                ProgressBar {
                                                    Layout.fillWidth: true
                                                    visible: modelCard.modelData.busy
                                                    indeterminate: true
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Item {
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 20
                            spacing: 14

                            Text {
                                text: "System"
                                color: window.textPrimary
                                font.family: "Segoe UI Variable Display"
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                            }

                            Surface {
                                Layout.fillWidth: true
                                implicitHeight: systemInfo.implicitHeight + 28
                                ColumnLayout {
                                    id: systemInfo
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 7
                                    Text { text: "Compute device"; color: window.textSecondary; font.family: "Segoe UI Variable Text"; font.pixelSize: 10 }
                                    Text { text: window.appController.computeDevice; color: window.textPrimary; font.family: "Segoe UI Variable Text"; font.pixelSize: 13; font.weight: Font.DemiBold }
                                    Text { text: window.appController.computeDetail; color: window.textSecondary; font.family: "Segoe UI Variable Text"; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                }
                            }

                            Surface {
                                Layout.fillWidth: true
                                implicitHeight: cacheInfo.implicitHeight + 28
                                ColumnLayout {
                                    id: cacheInfo
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 7
                                    Text { text: "Model storage"; color: window.textSecondary; font.family: "Segoe UI Variable Text"; font.pixelSize: 10 }
                                    Text { text: window.modelManager.cachePath; color: window.textPrimary; font.family: "Segoe UI Variable Text"; font.pixelSize: 11; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
                                }
                            }

                            Surface {
                                Layout.fillWidth: true
                                implicitHeight: appearanceInfo.implicitHeight + 28
                                ColumnLayout {
                                    id: appearanceInfo
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 7
                                    Text { text: "Appearance"; color: window.textSecondary; font.family: "Segoe UI Variable Text"; font.pixelSize: 10 }
                                    Text { text: "Follows Windows light/dark mode and accessibility motion settings."; color: window.textPrimary; font.family: "Segoe UI Variable Text"; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                }
                            }

                            Item { Layout.fillHeight: true }
                        }
                    }
                }
            }
        }
    }

    Shortcut { sequence: "Ctrl+Z"; onActivated: window.appController.undo() }
    Shortcut { sequence: "Ctrl+Y"; onActivated: window.appController.redo() }
    Shortcut {
        sequence: "Ctrl+,"
        onActivated: {
            window.modelManager.refresh()
            settingsPopup.open()
        }
    }

    onClosing: close => {
        close.accepted = window.appController.requestClose()
        if (close.accepted)
            window.appController.closeSession()
    }
}
