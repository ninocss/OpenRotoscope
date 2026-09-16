import QtQuick

Rectangle {
    id: panel
    required property var theme
    property bool elevated: false
    property bool strong: false

    radius: theme.radiusLg
    color: strong || elevated ? theme.surfaceRaised : theme.surface
    border.width: 1
    border.color: elevated ? theme.borderStrong : theme.border

    // Avoid layer/effect shadows here. On software/offscreen Qt renderers the
    // layer can disappear together with its contents. Depth stays visible via
    // the stronger surface and border; viewer operation blur remains separate.
}
