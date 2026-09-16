pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import QtQuick.Window

ApplicationWindow {
    id: window
    required property var appController
    width: 1440
    height: 900
    minimumWidth: 1120
    minimumHeight: 720
    visible: true
    title: "OpenRoto — " + window.appController.clipName
    color: "transparent"

    readonly property bool dark: window.appController.darkMode
    readonly property color textPrimary: dark ? "#F4F7FC" : "#142039"
    readonly property color textSecondary: dark ? "#9DAAC0" : "#60708C"
    readonly property color textMuted: dark ? "#738096" : "#8491A7"
    readonly property color surface: dark ? "#D9121823" : "#EBF8FAFE"
    readonly property color surfaceStrong: dark ? "#F018202C" : "#FCFFFFFF"
    readonly property color surfaceRaised: dark ? "#FF253044" : "#FFFFFFFF"
    readonly property color surfaceHover: dark ? "#40517CAD" : "#182B6FF3"
    readonly property color border: dark ? "#29FFFFFF" : "#1F172B4D"
    readonly property color borderStrong: dark ? "#40FFFFFF" : "#30213A63"
    readonly property color accent: dark ? "#66B2FF" : "#2474F5"
    readonly property color accentStrong: dark ? "#3B91F5" : "#155CD6"
    readonly property color accentSoft: dark ? "#2A66B2FF" : "#172474F5"
    readonly property color positive: dark ? "#5FE0B1" : "#0A9B70"
    readonly property color negative: dark ? "#FF7584" : "#DC3852"
    readonly property color warning: dark ? "#F3C768" : "#B56A09"
    readonly property int motionDuration: window.appController.reducedMotion ? 0 : 180

    function resetViewer() {
        imageStack.zoom = 1
        imageStack.x = 0
        imageStack.y = 0
    }

    component Panel: Rectangle {
        radius: 16
        color: window.surface
        border.width: 1
        border.color: window.border
    }

    component CleanButton: Button {
        id: control
        property bool primary: false
        property bool selected: false
        implicitHeight: 42
        leftPadding: 14
        rightPadding: 14
        font.family: "Segoe UI Variable Text"
        font.pixelSize: 14
        font.weight: primary ? Font.DemiBold : Font.Medium
        contentItem: Text {
            text: control.text
            color: control.primary ? "white" : window.textPrimary
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 10
            border.width: control.visualFocus || control.selected ? 1 : 0
            border.color: control.primary ? "#70B8FF" : window.accent
            color: control.primary
                ? (control.down ? window.accentStrong : window.accent)
                : control.selected
                    ? window.accentSoft
                    : control.hovered ? window.surfaceHover : "transparent"
            Behavior on color { ColorAnimation { duration: window.motionDuration } }
        }
    }

    component IconButton: Button {
        id: control
        property bool selected: false
        implicitWidth: 40
        implicitHeight: 40
        font.family: "Segoe UI Symbol"
        font.pixelSize: 19
        contentItem: Text {
            text: control.text
            color: control.selected ? window.accent : window.textPrimary
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 10
            color: control.selected
                ? window.accentSoft
                : control.hovered ? window.surfaceHover : "transparent"
            border.width: control.visualFocus || control.selected ? 1 : 0
            border.color: control.selected ? window.accent : window.border
            Behavior on color { ColorAnimation { duration: window.motionDuration } }
        }
    }

    component StatusPill: Rectangle {
        id: pill
        property string label: ""
        property color dotColor: window.accent
        implicitWidth: pillRow.implicitWidth + 22
        implicitHeight: 30
        radius: 15
        color: window.dark ? "#80202A39" : "#BFFFFFFF"
        border.width: 1
        border.color: window.border
        Row {
            id: pillRow
            anchors.centerIn: parent
            spacing: 7
            Rectangle {
                width: 7; height: 7; radius: 4
                color: pill.dotColor
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: pill.label
                color: window.textSecondary
                font.family: "Segoe UI Variable Text"
                font.pixelSize: 11
            }
        }
    }

    component FlowStep: Row {
        id: step
        property int number: 1
        property string label: ""
        property bool complete: false
        property bool active: false
        spacing: 7
        Rectangle {
            width: 24; height: 24; radius: 12
            color: step.complete ? window.positive : step.active ? window.accent : "transparent"
            border.width: step.complete || step.active ? 0 : 1
            border.color: window.borderStrong
            Text {
                anchors.centerIn: parent
                text: step.complete ? "✓" : step.number
                color: step.complete || step.active ? "white" : window.textMuted
                font.family: "Segoe UI Variable Text"
                font.pixelSize: 11
                font.weight: Font.DemiBold
            }
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: step.label
            color: step.active ? window.textPrimary : window.textSecondary
            font.family: "Segoe UI Variable Text"
            font.pixelSize: 11
            font.weight: step.active ? Font.DemiBold : Font.Normal
        }
    }

    component RotoSlider: Slider {
        id: sliderControl
        implicitHeight: 28
        background: Rectangle {
            x: sliderControl.leftPadding
            y: sliderControl.topPadding + sliderControl.availableHeight / 2 - height / 2
            implicitWidth: 200
            implicitHeight: 4
            width: sliderControl.availableWidth
            height: 4
            radius: 2
            color: window.dark ? "#354154" : "#CBD5E4"
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
            implicitWidth: 18
            implicitHeight: 18
            radius: 9
            color: sliderControl.pressed ? window.accent : window.surfaceRaised
            border.width: 2
            border.color: window.accent
            Behavior on color { ColorAnimation { duration: window.motionDuration } }
        }
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0; color: window.dark ? "#111A29" : "#F7FAFF" }
            GradientStop { position: 0.55; color: window.dark ? "#0B111B" : "#EDF3FB" }
            GradientStop { position: 1; color: window.dark ? "#080C13" : "#E7EEF8" }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 66
                spacing: 12

                Rectangle {
                    Layout.preferredWidth: 40
                    Layout.preferredHeight: 40
                    radius: 12
                    gradient: Gradient {
                        GradientStop { position: 0; color: "#6DB7FF" }
                        GradientStop { position: 1; color: "#306DD8" }
                    }
                    Image {
                        anchors.centerIn: parent
                        width: 34
                        height: 34
                        source: "openroto.svg"
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                    }
                }

                ColumnLayout {
                    spacing: 0
                    Text {
                        text: "OpenRoto"
                        color: window.textPrimary
                        font.family: "Segoe UI Variable Display"
                        font.pixelSize: 18
                        font.weight: Font.Bold
                    }
                    Text {
                        text: window.appController.clipName + "  ·  " + window.appController.clipMeta
                        color: window.textSecondary
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: 11
                        elide: Text.ElideRight
                        Layout.maximumWidth: 330
                    }
                }

                Item { Layout.preferredWidth: 6 }
                FlowStep {
                    number: 1
                    label: "Select"
                    complete: window.appController.hasPrompts
                    active: !window.appController.hasPrompts
                }
                Rectangle { Layout.preferredWidth: 22; Layout.preferredHeight: 1; color: window.borderStrong }
                FlowStep {
                    number: 2
                    label: "Track"
                    complete: window.appController.trackingReady
                    active: window.appController.hasPrompts && window.appController.trackingDirty
                }
                Rectangle { Layout.preferredWidth: 22; Layout.preferredHeight: 1; color: window.borderStrong }
                FlowStep {
                    number: 3
                    label: "Apply"
                    active: window.appController.trackingReady
                }

                Item { Layout.fillWidth: true }

                StatusPill {
                    label: window.appController.bridgeConnected ? "Resolve linked" : "Resolve offline"
                    dotColor: window.appController.bridgeConnected ? window.positive : window.negative
                }
                StatusPill {
                    id: devicePill
                    label: window.appController.computeBadge
                    dotColor: window.appController.computeDevice.indexOf("CUDA") >= 0 ? window.positive : window.warning
                    ToolTip.visible: deviceHover.hovered
                    ToolTip.text: window.appController.computeDevice + "\n" + window.appController.computeDetail
                    HoverHandler { id: deviceHover }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 12

                Panel {
                    Layout.preferredWidth: 68
                    Layout.fillHeight: true
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 8

                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: "SELECT"
                            color: window.textMuted
                            font.family: "Segoe UI Variable Text"
                            font.pixelSize: 9
                            font.weight: Font.DemiBold
                            font.letterSpacing: 0.7
                        }
                        Rectangle {
                            Layout.preferredWidth: 48
                            Layout.preferredHeight: 38
                            Layout.alignment: Qt.AlignHCenter
                            radius: 10
                            color: window.accentSoft
                            border.width: 1
                            border.color: window.accent
                            Row {
                                anchors.centerIn: parent
                                spacing: 4
                                Text { text: "+"; color: window.accent; font.pixelSize: 16; font.bold: true }
                                Text { text: "L"; color: window.textSecondary; font.pixelSize: 9; font.family: "Segoe UI Variable Text" }
                            }
                            ToolTip.visible: positiveHover.hovered
                            ToolTip.text: "Left-click the subject"
                            HoverHandler { id: positiveHover }
                        }
                        Rectangle {
                            Layout.preferredWidth: 48
                            Layout.preferredHeight: 38
                            Layout.alignment: Qt.AlignHCenter
                            radius: 10
                            color: window.dark ? "#20FF7584" : "#12DC3852"
                            border.width: 1
                            border.color: window.negative
                            Row {
                                anchors.centerIn: parent
                                spacing: 4
                                Text { text: "−"; color: window.negative; font.pixelSize: 16; font.bold: true }
                                Text { text: "R"; color: window.textSecondary; font.pixelSize: 9; font.family: "Segoe UI Variable Text" }
                            }
                            ToolTip.visible: negativeHover.hovered
                            ToolTip.text: "Right-click outside the subject"
                            HoverHandler { id: negativeHover }
                        }
                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.border }
                        IconButton {
                            text: "↶"
                            enabled: window.appController.canUndo && !window.appController.busy
                            opacity: enabled ? 1 : 0.35
                            onClicked: window.appController.undo()
                            Accessible.name: "Undo point"
                            ToolTip.visible: hovered
                            ToolTip.text: "Undo · Ctrl+Z"
                        }
                        IconButton {
                            text: "↷"
                            enabled: window.appController.canRedo && !window.appController.busy
                            opacity: enabled ? 1 : 0.35
                            onClicked: window.appController.redo()
                            Accessible.name: "Redo point"
                            ToolTip.visible: hovered
                            ToolTip.text: "Redo · Ctrl+Y"
                        }
                        IconButton {
                            text: "⌫"
                            enabled: !window.appController.busy
                            onClicked: window.appController.clearFrame()
                            Accessible.name: "Clear points on frame"
                            ToolTip.visible: hovered
                            ToolTip.text: "Clear this frame"
                        }
                        Item { Layout.fillHeight: true }
                        IconButton {
                            text: "1:1"
                            font.pixelSize: 11
                            onClicked: window.resetViewer()
                            Accessible.name: "Reset zoom"
                            ToolTip.visible: hovered
                            ToolTip.text: "Reset zoom"
                        }
                    }
                }

                Panel {
                    id: viewerPanel
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: 0
                    Layout.preferredWidth: 760
                    color: window.dark ? "#F0070A10" : "#F7E5EBF4"

                    Item {
                        id: viewport
                        anchors.fill: parent
                        anchors.margins: 10
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
                                        x: pointMarker.modelData.x * paintedArea.width - 10
                                        y: pointMarker.modelData.y * paintedArea.height - 10
                                        width: 20
                                        height: 20
                                        Rectangle {
                                            anchors.centerIn: parent
                                            width: 26; height: 26; radius: 13
                                            color: "transparent"
                                            border.width: 1
                                            border.color: pointMarker.modelData.positive ? window.accent : window.negative
                                            opacity: 0.45
                                        }
                                        Rectangle {
                                            anchors.fill: parent
                                            radius: 10
                                            color: pointMarker.modelData.positive ? window.accent : window.negative
                                            border.width: 2
                                            border.color: "white"
                                        }
                                        Text {
                                            anchors.centerIn: parent
                                            text: pointMarker.modelData.positive ? "+" : "−"
                                            color: "white"
                                            font.bold: true
                                            font.pixelSize: 13
                                        }
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                                    enabled: !window.appController.busy
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
                                    const change = event.angleDelta.y > 0 ? 1.12 : 0.89
                                    imageStack.zoom = Math.max(1, Math.min(6, imageStack.zoom * change))
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

                        RowLayout {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 12
                            StatusPill {
                                label: window.appController.promptCount === 0
                                    ? "No points yet"
                                    : window.appController.promptCount + (window.appController.promptCount === 1 ? " point" : " points")
                                dotColor: window.appController.promptCount > 0 ? window.positive : window.textMuted
                            }
                            Item { Layout.fillWidth: true }
                            StatusPill {
                                label: Math.round(imageStack.zoom * 100) + "%"
                                dotColor: window.accent
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: window.resetViewer()
                                }
                                ToolTip.visible: zoomHover.hovered
                                ToolTip.text: "Click to reset zoom"
                                HoverHandler { id: zoomHover }
                            }
                        }

                        Rectangle {
                            anchors.centerIn: parent
                            width: busyRow.implicitWidth + 30
                            height: 48
                            radius: 14
                            visible: window.appController.busy
                            color: window.dark ? "#E518202C" : "#F5FFFFFF"
                            border.width: 1
                            border.color: window.borderStrong
                            Row {
                                id: busyRow
                                anchors.centerIn: parent
                                spacing: 10
                                BusyIndicator { width: 22; height: 22; running: visible }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: window.appController.status
                                    color: window.textPrimary
                                    font.family: "Segoe UI Variable Text"
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                }
                            }
                        }

                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 12
                            width: Math.min(parent.width - 24, instruction.implicitWidth + 26)
                            height: 34
                            radius: 17
                            color: window.dark ? "#C7171D28" : "#E8FFFFFF"
                            border.width: 1
                            border.color: window.border
                            Text {
                                id: instruction
                                anchors.centerIn: parent
                                text: "Left click  + subject    ·    Right click  − background    ·    Wheel zooms    ·    Middle drag pans"
                                color: window.textSecondary
                                font.family: "Segoe UI Variable Text"
                                font.pixelSize: 12
                                elide: Text.ElideRight
                                width: parent.width - 22
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }
                }

                Panel {
                    Layout.preferredWidth: 310
                    Layout.minimumWidth: 310
                    Layout.maximumWidth: 310
                    Layout.fillHeight: true

                    ScrollView {
                        anchors.fill: parent
                        anchors.margins: 16
                        clip: true
                        contentWidth: availableWidth

                        ColumnLayout {
                            width: parent.width
                            spacing: 12

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "Mask controls"
                                    color: window.textPrimary
                                    font.family: "Segoe UI Variable Display"
                                    font.pixelSize: 17
                                    font.weight: Font.DemiBold
                                    Layout.fillWidth: true
                                }
                                Rectangle {
                                    implicitWidth: stateText.implicitWidth + 16
                                    implicitHeight: 24
                                    radius: 12
                                    color: window.appController.trackingReady
                                        ? (window.dark ? "#245FE0B1" : "#140A9B70")
                                        : window.accentSoft
                                    Text {
                                        id: stateText
                                        anchors.centerIn: parent
                                        text: window.appController.trackingReady ? "Tracked"
                                            : window.appController.hasPrompts ? "Needs track" : "Select"
                                        color: window.appController.trackingReady ? window.positive : window.accent
                                        font.family: "Segoe UI Variable Text"
                                        font.pixelSize: 10
                                        font.weight: Font.DemiBold
                                    }
                                }
                            }

                            Text {
                                text: "MODEL QUALITY"
                                color: window.textMuted
                                font.family: "Segoe UI Variable Text"
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                                font.letterSpacing: 0.8
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 5
                                Repeater {
                                    model: ["fast", "balanced", "high"]
                                    delegate: CleanButton {
                                        required property string modelData
                                        Layout.fillWidth: true
                                        text: modelData === "fast" ? "Fast" : modelData === "high" ? "High" : "Balanced"
                                        selected: window.appController.modelPreset === modelData
                                        enabled: !window.appController.busy
                                        onClicked: window.appController.setModelPreset(modelData)
                                    }
                                }
                            }
                            Text {
                                Layout.fillWidth: true
                                text: window.appController.modelPreset === "fast"
                                    ? "Quick previews and clean silhouettes."
                                    : window.appController.modelPreset === "high"
                                        ? "Best detail, highest VRAM use."
                                        : "Recommended balance of detail and speed."
                                color: window.textSecondary
                                font.family: "Segoe UI Variable Text"
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                            }

                            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.border; Layout.topMargin: 4 }
                            Text {
                                text: "TRACKING"
                                color: window.textMuted
                                font.family: "Segoe UI Variable Text"
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                                font.letterSpacing: 0.8
                            }
                            ComboBox {
                                id: directionBox
                                Layout.fillWidth: true
                                model: ["Both directions", "Forward", "Backward"]
                                currentIndex: window.appController.trackingDirection === "forward" ? 1 : window.appController.trackingDirection === "backward" ? 2 : 0
                                onActivated: index => window.appController.setTrackingDirection(index === 1 ? "forward" : index === 2 ? "backward" : "both")
                                background: Rectangle {
                                    radius: 9
                                    color: window.dark ? "#4026303F" : "#DDF7F9FC"
                                    border.width: 1
                                    border.color: directionBox.visualFocus ? window.accent : window.border
                                }
                                contentItem: Text {
                                    leftPadding: 12
                                    text: directionBox.displayText
                                    color: window.textPrimary
                                    font.family: "Segoe UI Variable Text"
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                            CleanButton {
                                Layout.fillWidth: true
                                primary: window.appController.hasPrompts
                                text: window.appController.busy ? "Working…"
                                    : window.appController.trackingReady ? "Track again" : "Track subject"
                                enabled: window.appController.hasPrompts && !window.appController.busy
                                opacity: enabled ? 1 : 0.45
                                onClicked: window.appController.track()
                            }
                            Text {
                                Layout.fillWidth: true
                                text: window.appController.hasPrompts
                                    ? "Add corrections on difficult frames at any time."
                                    : "Place one positive point in the viewer to begin."
                                color: window.textSecondary
                                font.family: "Segoe UI Variable Text"
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                            }

                            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.border; Layout.topMargin: 4 }
                            Text {
                                text: "MATTE"
                                color: window.textMuted
                                font.family: "Segoe UI Variable Text"
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                                font.letterSpacing: 0.8
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "Overlay"; color: window.textPrimary; Layout.fillWidth: true; font.family: "Segoe UI Variable Text" }
                                Text { text: Math.round(window.appController.overlayOpacity * 100) + "%"; color: window.textSecondary; font.family: "Segoe UI Variable Text" }
                            }
                            RotoSlider {
                                Layout.fillWidth: true
                                from: 0
                                to: 1
                                value: window.appController.overlayOpacity
                                onMoved: window.appController.setOverlayOpacity(value)
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "Expand / Contract"; color: window.textPrimary; Layout.fillWidth: true; font.family: "Segoe UI Variable Text" }
                                Text { text: (window.appController.expandContract > 0 ? "+" : "") + window.appController.expandContract + " px"; color: window.textSecondary; font.family: "Segoe UI Variable Text" }
                            }
                            RotoSlider {
                                Layout.fillWidth: true
                                from: -16
                                to: 16
                                stepSize: 1
                                value: window.appController.expandContract
                                onMoved: window.appController.setExpandContract(Math.round(value))
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "Feather"; color: window.textPrimary; Layout.fillWidth: true; font.family: "Segoe UI Variable Text" }
                                Text { text: window.appController.feather.toFixed(1) + " px"; color: window.textSecondary; font.family: "Segoe UI Variable Text" }
                            }
                            RotoSlider {
                                Layout.fillWidth: true
                                from: 0
                                to: 24
                                stepSize: 0.5
                                value: window.appController.feather
                                onMoved: window.appController.setFeather(value)
                            }
                            Switch {
                                id: invertSwitch
                                text: "Invert matte"
                                checked: window.appController.invert
                                onToggled: window.appController.setInvert(checked)
                                contentItem: Text {
                                    text: invertSwitch.text
                                    color: window.textPrimary
                                    font.family: "Segoe UI Variable Text"
                                    leftPadding: invertSwitch.indicator.width + invertSwitch.spacing
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                        }
                    }
                }
            }

            Panel {
                Layout.fillWidth: true
                Layout.preferredHeight: 132

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        RoundButton {
                            text: "‹"
                            enabled: !window.appController.busy && window.appController.currentFrame > 0
                            onClicked: window.appController.setFrame(window.appController.currentFrame - 1)
                            ToolTip.visible: hovered
                            ToolTip.text: "Previous frame"
                        }
                        Text {
                            text: window.appController.frameLabel
                            color: window.textSecondary
                            font.family: "Segoe UI Variable Text"
                            font.pixelSize: 12
                            Layout.preferredWidth: 88
                        }
                        RotoSlider {
                            id: frameSlider
                            Layout.fillWidth: true
                            from: 0
                            to: Math.max(0, window.appController.frameCount - 1)
                            stepSize: 1
                            value: window.appController.currentFrame
                            enabled: !window.appController.busy
                            onMoved: window.appController.setFrame(Math.round(value))
                        }
                        RoundButton {
                            text: "›"
                            enabled: !window.appController.busy && window.appController.currentFrame < window.appController.frameCount - 1
                            onClicked: window.appController.setFrame(window.appController.currentFrame + 1)
                            ToolTip.visible: hovered
                            ToolTip.text: "Next frame"
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            RowLayout {
                                spacing: 7
                                Rectangle {
                                    Layout.preferredWidth: 8
                                    Layout.preferredHeight: 8
                                    radius: 4
                                    color: window.appController.status.indexOf("wrong") >= 0 || window.appController.status.indexOf("lost") >= 0
                                        ? window.negative
                                        : window.appController.busy ? window.accent : window.positive
                                }
                                Text {
                                    text: window.appController.status
                                    color: window.textPrimary
                                    font.family: "Segoe UI Variable Text"
                                    font.pixelSize: 13
                                    font.weight: Font.DemiBold
                                }
                            }
                            Text {
                                text: window.appController.detail
                                visible: text.length > 0
                                color: window.textSecondary
                                font.family: "Segoe UI Variable Text"
                                font.pixelSize: 11
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            ProgressBar {
                                Layout.fillWidth: true
                                visible: window.appController.busy
                                from: 0
                                to: 1
                                value: window.appController.progress
                            }
                        }
                        CleanButton {
                            text: "Cancel"
                            visible: window.appController.busy
                            onClicked: window.appController.cancel()
                        }
                        CleanButton {
                            text: window.appController.trackingDirty ? "Track, Render & Apply" : "Render & Apply"
                            primary: true
                            implicitWidth: 190
                            enabled: window.appController.hasPrompts && window.appController.bridgeConnected && !window.appController.busy
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

    Shortcut { sequence: "Ctrl+Z"; onActivated: window.appController.undo() }
    Shortcut { sequence: "Ctrl+Y"; onActivated: window.appController.redo() }
    onClosing: close => {
        close.accepted = window.appController.requestClose()
        if (close.accepted)
            window.appController.closeSession()
    }
}
