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

    width: 1360
    height: 850
    minimumWidth: 1080
    minimumHeight: 700
    visible: true
    title: "OpenRoto — " + window.appController.clipName
    color: "transparent"

    readonly property bool dark: window.appController.darkMode
    readonly property bool blocked: window.appController.busy || window.modelManager.busy
    readonly property color bg: dark ? "#EA1B1B1B" : "#EEF3F3F3"
    readonly property color panel: dark ? "#F02A2A2A" : "#FAFFFFFF"
    readonly property color panel2: dark ? "#F4343434" : "#FFFFFFFF"
    readonly property color viewerBg: "#0D0D0D"
    readonly property color border: dark ? "#2EFFFFFF" : "#22000000"
    readonly property color strongBorder: dark ? "#46FFFFFF" : "#36000000"
    readonly property color text: dark ? "#F4F4F4" : "#191919"
    readonly property color secondary: dark ? "#B6B6B6" : "#5E5E5E"
    readonly property color muted: dark ? "#858585" : "#777777"
    readonly property color accent: dark ? "#60CDFF" : "#0067C0"
    readonly property color accentPressed: dark ? "#4CB6E8" : "#005A9E"
    readonly property color accentSoft: dark ? "#2460CDFF" : "#170067C0"
    readonly property color danger: dark ? "#FF7888" : "#C42B1C"
    readonly property color dangerSoft: dark ? "#20FF7888" : "#14C42B1C"
    readonly property color success: dark ? "#6CCB9F" : "#107C5C"
    readonly property color warning: dark ? "#FCE100" : "#9D5D00"
    readonly property int anim: window.appController.reducedMotion ? 0 : 120

    function resetViewer() {
        imageStack.zoom = 1
        imageStack.x = 0
        imageStack.y = 0
    }

    component CenteredTip: ToolTip {
        id: tip
        delay: 350
        timeout: 4500
        padding: 8
        contentItem: Text {
            text: tip.text
            color: window.dark ? "#F6F6F6" : "#202020"
            font.family: "Segoe UI Variable Text"
            font.pixelSize: 11
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 6
            color: window.dark ? "#F2393939" : "#FAFFFFFF"
            border.width: 1
            border.color: window.strongBorder
        }
    }

    component Panel: Rectangle {
        radius: 8
        color: window.panel
        border.width: 1
        border.color: window.border
    }

    component FluentButton: Button {
        id: control
        property bool primary: false
        property bool selected: false
        property bool dangerStyle: false
        property string toolTip: ""
        implicitHeight: 34
        leftPadding: 12
        rightPadding: 12
        font.family: "Segoe UI Variable Text"
        font.pixelSize: 12
        font.weight: primary ? Font.DemiBold : Font.Normal
        contentItem: Text {
            text: control.text
            color: control.primary ? "white" : control.dangerStyle ? window.danger : window.text
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 6
            color: control.primary
                ? (control.down ? window.accentPressed : window.accent)
                : control.selected ? window.accentSoft
                : control.hovered ? (window.dark ? "#3FFFFFFF" : "#10000000")
                : "transparent"
            border.width: control.primary || control.selected || control.visualFocus ? 1 : 0
            border.color: control.primary || control.selected ? window.accent : window.strongBorder
            Behavior on color { ColorAnimation { duration: window.anim } }
        }
        CenteredTip {
            visible: control.hovered && control.toolTip.length > 0
            text: control.toolTip
            x: Math.round((control.width - width) / 2)
            y: control.height + 5
        }
    }

    component ToolButtonFluent: Button {
        id: control
        property string toolTip: ""
        property bool selected: false
        implicitWidth: 34
        implicitHeight: 34
        font.family: "Segoe UI Symbol"
        font.pixelSize: 16
        contentItem: Text {
            text: control.text
            color: control.selected ? window.accent : window.text
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 6
            color: control.selected ? window.accentSoft
                : control.hovered ? (window.dark ? "#3FFFFFFF" : "#10000000")
                : "transparent"
            border.width: control.selected || control.visualFocus ? 1 : 0
            border.color: control.selected ? window.accent : window.strongBorder
        }
        CenteredTip {
            visible: control.hovered && control.toolTip.length > 0
            text: control.toolTip
            x: Math.round((control.width - width) / 2)
            y: control.height + 5
        }
    }

    component StatusChip: Rectangle {
        id: chip
        property string label: ""
        property color dotColor: window.accent
        property string toolTip: ""
        implicitWidth: row.implicitWidth + 18
        implicitHeight: 28
        radius: 6
        color: window.dark ? "#78323232" : "#DFFFFFFF"
        border.width: 1
        border.color: window.border
        Row {
            id: row
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
                color: window.secondary
                font.family: "Segoe UI Variable Text"
                font.pixelSize: 10
            }
        }
        HoverHandler { id: statusHover }
        CenteredTip {
            visible: statusHover.hovered && chip.toolTip.length > 0
            text: chip.toolTip
            x: Math.round((chip.width - width) / 2)
            y: chip.height + 5
        }
    }

    component SectionLabel: Text {
        color: window.muted
        font.family: "Segoe UI Variable Text"
        font.pixelSize: 10
        font.weight: Font.DemiBold
        font.letterSpacing: 0.8
    }

    component RotoSlider: Slider {
        id: slider
        implicitHeight: 24
        background: Rectangle {
            x: slider.leftPadding
            y: slider.topPadding + slider.availableHeight / 2 - height / 2
            width: slider.availableWidth
            height: 4
            radius: 2
            color: window.dark ? "#515151" : "#D2D2D2"
            Rectangle {
                width: slider.visualPosition * parent.width
                height: parent.height
                radius: 2
                color: window.accent
            }
        }
        handle: Rectangle {
            x: slider.leftPadding + slider.visualPosition * (slider.availableWidth - width)
            y: slider.topPadding + slider.availableHeight / 2 - height / 2
            implicitWidth: 16
            implicitHeight: 16
            radius: 8
            color: slider.pressed ? window.accent : window.panel2
            border.width: 2
            border.color: window.accent
        }
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
            color: "#800D0D0D"
            border.width: 2
            border.color: marker.positive ? window.accent : window.danger
        }
        Rectangle {
            anchors.centerIn: parent
            width: marker.positive ? 6 : 5
            height: marker.positive ? 6 : 5
            radius: marker.positive ? 3 : 1
            rotation: marker.positive ? 0 : 45
            color: marker.positive ? window.accent : window.danger
        }
    }

    Rectangle {
        anchors.fill: parent
        color: window.bg

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 8

            Panel {
                Layout.fillWidth: true
                Layout.preferredHeight: 52

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 8
                    spacing: 8

                    Image {
                        Layout.preferredWidth: 27
                        Layout.preferredHeight: 27
                        source: "openroto.svg"
                        fillMode: Image.PreserveAspectFit
                    }
                    ColumnLayout {
                        spacing: -2
                        Text {
                            text: "OpenRoto"
                            color: window.text
                            font.family: "Segoe UI Variable Display"
                            font.pixelSize: 15
                            font.weight: Font.DemiBold
                        }
                        Text {
                            text: window.appController.clipName + "  ·  " + window.appController.clipMeta
                            color: window.secondary
                            font.family: "Segoe UI Variable Text"
                            font.pixelSize: 10
                            elide: Text.ElideRight
                            Layout.maximumWidth: 430
                        }
                    }

                    Item { Layout.fillWidth: true }

                    ToolButtonFluent {
                        text: "↶"
                        toolTip: "Undo · Ctrl+Z"
                        enabled: window.appController.canUndo && !window.blocked
                        opacity: enabled ? 1 : 0.35
                        onClicked: window.appController.undo()
                    }
                    ToolButtonFluent {
                        text: "↷"
                        toolTip: "Redo · Ctrl+Y"
                        enabled: window.appController.canRedo && !window.blocked
                        opacity: enabled ? 1 : 0.35
                        onClicked: window.appController.redo()
                    }
                    ToolButtonFluent {
                        text: "⌫"
                        toolTip: "Clear selection points on this frame"
                        enabled: !window.blocked
                        opacity: enabled ? 1 : 0.35
                        onClicked: window.appController.clearFrame()
                    }

                    Rectangle {
                        Layout.preferredWidth: 1
                        Layout.preferredHeight: 22
                        color: window.strongBorder
                        Layout.leftMargin: 3
                        Layout.rightMargin: 3
                    }

                    StatusChip {
                        label: window.appController.bridgeConnected ? "Resolve linked" : "Resolve offline"
                        dotColor: window.appController.bridgeConnected ? window.success : window.danger
                    }
                    StatusChip {
                        label: window.appController.computeBadge
                        dotColor: window.appController.computeDevice.indexOf("CUDA") >= 0 ? window.success : window.warning
                        toolTip: window.appController.computeDevice + "\n" + window.appController.computeDetail
                    }
                    ToolButtonFluent {
                        text: "⚙"
                        toolTip: "Settings · Ctrl+,"
                        onClicked: {
                            window.modelManager.refresh()
                            settingsPopup.open()
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 8

                Panel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: 650

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 7

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 28
                            Text {
                                text: "Viewer"
                                color: window.text
                                font.family: "Segoe UI Variable Text"
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                            }
                            StatusChip {
                                label: window.appController.promptCount === 0
                                    ? "No selection"
                                    : window.appController.promptCount + (window.appController.promptCount === 1 ? " point" : " points")
                                dotColor: window.appController.promptCount > 0 ? window.accent : window.muted
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: Math.round(imageStack.zoom * 100) + "%"
                                color: window.secondary
                                font.family: "Segoe UI Variable Text"
                                font.pixelSize: 10
                            }
                            ToolButtonFluent {
                                text: "1:1"
                                font.pixelSize: 10
                                implicitWidth: 42
                                toolTip: "Reset zoom"
                                onClicked: window.resetViewer()
                            }
                        }

                        Rectangle {
                            id: viewport
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 6
                            color: window.viewerBg
                            clip: true

                            Item {
                                id: imageStack
                                width: parent.width
                                height: parent.height
                                property real zoom: 1
                                x: 0
                                y: 0
                                scale: zoom
                                transformOrigin: Item.Center
                                Behavior on scale { NumberAnimation { duration: window.anim; easing.type: Easing.OutCubic } }

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
                                            id: pointItem
                                            required property var modelData
                                            x: pointItem.modelData.x * paintedArea.width - 11
                                            y: pointItem.modelData.y * paintedArea.height - 11
                                            width: 22
                                            height: 22
                                            SubjectMarker {
                                                anchors.fill: parent
                                                positive: pointItem.modelData.positive
                                            }
                                        }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                                        enabled: !window.blocked
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

                            Rectangle {
                                anchors.horizontalCenter: parent.horizontalCenter
                                anchors.bottom: parent.bottom
                                anchors.bottomMargin: 10
                                width: hintRow.implicitWidth + 20
                                height: 30
                                radius: 7
                                color: "#C5222222"
                                border.width: 1
                                border.color: "#3AFFFFFF"
                                Row {
                                    id: hintRow
                                    anchors.centerIn: parent
                                    spacing: 16
                                    Row {
                                        spacing: 6
                                        SubjectMarker { width: 16; height: 16; positive: true; anchors.verticalCenter: parent.verticalCenter }
                                        Text { text: "Subject · Left click"; color: "#E8FFFFFF"; font.family: "Segoe UI Variable Text"; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter }
                                    }
                                    Row {
                                        spacing: 6
                                        SubjectMarker { width: 16; height: 16; positive: false; anchors.verticalCenter: parent.verticalCenter }
                                        Text { text: "Exclude · Right click"; color: "#E8FFFFFF"; font.family: "Segoe UI Variable Text"; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter }
                                    }
                                    Text { text: "Wheel zoom · Middle drag pan"; color: "#BFFFFFFF"; font.family: "Segoe UI Variable Text"; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter }
                                }
                            }

                            Rectangle {
                                anchors.centerIn: parent
                                width: 270
                                height: busyColumn.implicitHeight + 30
                                radius: 9
                                visible: window.appController.busy
                                color: "#EE292929"
                                border.width: 1
                                border.color: "#4FFFFFFF"

                                Column {
                                    id: busyColumn
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.leftMargin: 16
                                    anchors.rightMargin: 16
                                    spacing: 7
                                    BusyIndicator {
                                        width: 22
                                        height: 22
                                        running: parent.parent.visible
                                        anchors.horizontalCenter: parent.horizontalCenter
                                    }
                                    Text {
                                        width: parent.width
                                        text: window.appController.status
                                        color: "white"
                                        font.family: "Segoe UI Variable Text"
                                        font.pixelSize: 12
                                        font.weight: Font.DemiBold
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        wrapMode: Text.WordWrap
                                    }
                                    ProgressBar {
                                        width: parent.width
                                        from: 0
                                        to: 1
                                        value: window.appController.progress
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 58
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
                                    toolTip: "Previous frame"
                                    enabled: !window.blocked && window.appController.currentFrame > 0
                                    opacity: enabled ? 1 : 0.35
                                    onClicked: window.appController.setFrame(window.appController.currentFrame - 1)
                                }
                                Text {
                                    text: window.appController.frameLabel
                                    color: window.secondary
                                    font.family: "Segoe UI Variable Text"
                                    font.pixelSize: 10
                                    Layout.preferredWidth: 76
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                                RotoSlider {
                                    Layout.fillWidth: true
                                    from: 0
                                    to: Math.max(0, window.appController.frameCount - 1)
                                    stepSize: 1
                                    value: window.appController.currentFrame
                                    enabled: !window.blocked
                                    onMoved: window.appController.setFrame(Math.round(value))
                                }
                                ToolButtonFluent {
                                    text: "›"
                                    toolTip: "Next frame"
                                    enabled: !window.blocked && window.appController.currentFrame < window.appController.frameCount - 1
                                    opacity: enabled ? 1 : 0.35
                                    onClicked: window.appController.setFrame(window.appController.currentFrame + 1)
                                }
                            }
                        }
                    }
                }

                Panel {
                    Layout.preferredWidth: 310
                    Layout.minimumWidth: 310
                    Layout.maximumWidth: 310
                    Layout.fillHeight: true

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 0

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 44
                            Layout.leftMargin: 14
                            Layout.rightMargin: 10
                            Text {
                                Layout.fillWidth: true
                                text: "Controls"
                                color: window.text
                                font.family: "Segoe UI Variable Display"
                                font.pixelSize: 15
                                font.weight: Font.DemiBold
                            }
                            Text {
                                text: window.appController.trackingReady ? "Tracked" : window.appController.hasPrompts ? "Needs track" : "Select"
                                color: window.appController.trackingReady ? window.success : window.appController.hasPrompts ? window.accent : window.muted
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

                                SectionLabel { text: "SELECTION"; Layout.leftMargin: 14 }
                                Text {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 14
                                    text: "Mark the subject, then exclude background only where the mask needs correction."
                                    color: window.secondary
                                    font.family: "Segoe UI Variable Text"
                                    font.pixelSize: 11
                                    wrapMode: Text.WordWrap
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 14
                                    spacing: 10
                                    Row {
                                        Layout.fillWidth: true
                                        spacing: 7
                                        SubjectMarker { width: 20; height: 20; positive: true; anchors.verticalCenter: parent.verticalCenter }
                                        Column {
                                            Text { text: "Subject"; color: window.text; font.family: "Segoe UI Variable Text"; font.pixelSize: 11; font.weight: Font.DemiBold }
                                            Text { text: "Left click"; color: window.muted; font.family: "Segoe UI Variable Text"; font.pixelSize: 9 }
                                        }
                                    }
                                    Row {
                                        Layout.fillWidth: true
                                        spacing: 7
                                        SubjectMarker { width: 20; height: 20; positive: false; anchors.verticalCenter: parent.verticalCenter }
                                        Column {
                                            Text { text: "Exclude"; color: window.text; font.family: "Segoe UI Variable Text"; font.pixelSize: 11; font.weight: Font.DemiBold }
                                            Text { text: "Right click"; color: window.muted; font.family: "Segoe UI Variable Text"; font.pixelSize: 9 }
                                        }
                                    }
                                }

                                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.border; Layout.topMargin: 5 }

                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 10
                                    SectionLabel { text: "TRACKING"; Layout.fillWidth: true }
                                    ToolButtonFluent {
                                        text: "⚙"
                                        implicitWidth: 30
                                        implicitHeight: 30
                                        toolTip: "Manage models"
                                        onClicked: {
                                            window.modelManager.refresh()
                                            settingsPopup.open()
                                        }
                                    }
                                }

                                ComboBox {
                                    id: modelBox
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
                                        border.color: modelBox.visualFocus ? window.accent : window.strongBorder
                                    }
                                    contentItem: Text {
                                        leftPadding: 10
                                        text: modelBox.displayText
                                        color: window.text
                                        font.family: "Segoe UI Variable Text"
                                        font.pixelSize: 11
                                        verticalAlignment: Text.AlignVCenter
                                    }
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
                                            enabled: !window.blocked
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
                                    enabled: window.appController.hasPrompts && !window.blocked
                                    opacity: enabled ? 1 : 0.45
                                    onClicked: window.appController.track()
                                }

                                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.border; Layout.topMargin: 5 }

                                SectionLabel { text: "MATTE"; Layout.leftMargin: 14 }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 14
                                    Text { text: "Overlay"; color: window.text; font.family: "Segoe UI Variable Text"; font.pixelSize: 11; Layout.fillWidth: true }
                                    Text { text: Math.round(window.appController.overlayOpacity * 100) + "%"; color: window.secondary; font.family: "Segoe UI Variable Text"; font.pixelSize: 10 }
                                }
                                RotoSlider {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 14
                                    from: 0; to: 1
                                    value: window.appController.overlayOpacity
                                    enabled: !window.blocked
                                    onMoved: window.appController.setOverlayOpacity(value)
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 14
                                    Text { text: "Expand / Contract"; color: window.text; font.family: "Segoe UI Variable Text"; font.pixelSize: 11; Layout.fillWidth: true }
                                    Text { text: (window.appController.expandContract > 0 ? "+" : "") + window.appController.expandContract + " px"; color: window.secondary; font.family: "Segoe UI Variable Text"; font.pixelSize: 10 }
                                }
                                RotoSlider {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 14
                                    from: -16; to: 16; stepSize: 1
                                    value: window.appController.expandContract
                                    enabled: !window.blocked
                                    onMoved: window.appController.setExpandContract(Math.round(value))
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 14
                                    Text { text: "Feather"; color: window.text; font.family: "Segoe UI Variable Text"; font.pixelSize: 11; Layout.fillWidth: true }
                                    Text { text: window.appController.feather.toFixed(1) + " px"; color: window.secondary; font.family: "Segoe UI Variable Text"; font.pixelSize: 10 }
                                }
                                RotoSlider {
                                    Layout.fillWidth: true
                                    Layout.leftMargin: 14
                                    Layout.rightMargin: 14
                                    from: 0; to: 24; stepSize: 0.5
                                    value: window.appController.feather
                                    enabled: !window.blocked
                                    onMoved: window.appController.setFeather(value)
                                }
                                Switch {
                                    id: invertSwitch
                                    Layout.leftMargin: 14
                                    text: "Invert matte"
                                    checked: window.appController.invert
                                    enabled: !window.blocked
                                    onToggled: window.appController.setInvert(checked)
                                    contentItem: Text {
                                        text: invertSwitch.text
                                        color: window.text
                                        font.family: "Segoe UI Variable Text"
                                        font.pixelSize: 11
                                        leftPadding: invertSwitch.indicator.width + invertSwitch.spacing
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                                Item { Layout.preferredHeight: 5 }
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
                            Text {
                                Layout.fillWidth: true
                                visible: text.length > 0 && !window.appController.busy
                                text: window.appController.detail
                                color: window.secondary
                                font.family: "Segoe UI Variable Text"
                                font.pixelSize: 9
                                horizontalAlignment: Text.AlignHCenter
                                wrapMode: Text.WordWrap
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
                                    implicitHeight: 40
                                    primary: true
                                    text: window.appController.trackingDirty ? "Track, Render & Apply" : "Render & Apply"
                                    enabled: window.appController.hasPrompts && window.appController.bridgeConnected && !window.blocked
                                    opacity: enabled ? 1 : 0.45
                                    toolTip: !window.appController.bridgeConnected ? "Start a new session from DaVinci Resolve" : ""
                                    onClicked: window.appController.renderAndApply()
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
        width: Math.min(window.width - 80, 720)
        height: Math.min(window.height - 80, 570)
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
                ToolButtonFluent {
                    text: "×"
                    toolTip: "Close settings"
                    onClicked: settingsPopup.close()
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
                        text: "Install only the models you want to keep locally. The selected default is used for new sessions."
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
                            Layout.preferredHeight: 92
                            radius: 8
                            color: window.panel2
                            border.width: modelData.selected ? 1 : 1
                            border.color: modelData.selected ? window.accent : window.border

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 12
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    RowLayout {
                                        Text {
                                            text: modelCard.modelData.name
                                            color: window.text
                                            font.family: "Segoe UI Variable Text"
                                            font.pixelSize: 13
                                            font.weight: Font.DemiBold
                                        }
                                        Text {
                                            text: modelCard.modelData.selected ? "Default" : modelCard.modelData.status
                                            color: modelCard.modelData.selected ? window.accent : modelCard.modelData.installed ? window.success : window.muted
                                            font.family: "Segoe UI Variable Text"
                                            font.pixelSize: 10
                                        }
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: modelCard.modelData.description
                                        color: window.secondary
                                        font.family: "Segoe UI Variable Text"
                                        font.pixelSize: 10
                                        elide: Text.ElideRight
                                    }
                                    Text {
                                        text: "~" + modelCard.modelData.downloadMb + " MB  ·  " + modelCard.modelData.minimumVramGb + " GB VRAM recommended"
                                        color: window.muted
                                        font.family: "Segoe UI Variable Text"
                                        font.pixelSize: 9
                                    }
                                }
                                FluentButton {
                                    visible: modelCard.modelData.installed && !modelCard.modelData.selected
                                    text: "Set default"
                                    enabled: !window.modelManager.busy && !window.appController.busy
                                    onClicked: window.modelManager.setDefaultModel(modelCard.modelData.id)
                                }
                                FluentButton {
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

                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.border; Layout.leftMargin: 18; Layout.rightMargin: 18; Layout.topMargin: 4 }
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
