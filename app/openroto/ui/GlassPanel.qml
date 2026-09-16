import QtQuick
import QtQuick.Effects

Rectangle {
    id: panel
    required property var theme
    property bool elevated: false
    property bool strong: false

    radius: theme.radiusLg
    color: strong ? theme.surfaceRaised : theme.surface
    border.width: 1
    border.color: theme.border

    layer.enabled: elevated
    layer.effect: MultiEffect {
        shadowEnabled: panel.elevated
        shadowColor: panel.theme.shadow
        shadowBlur: 0.75
        shadowOpacity: panel.theme.dark ? 0.38 : 0.18
    }
}
