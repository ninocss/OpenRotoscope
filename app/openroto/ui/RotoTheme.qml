import QtQuick

QtObject {
    id: theme
    required property bool dark

    readonly property string fontFamily: "Segoe UI Variable Text"
    readonly property string displayFontFamily: "Segoe UI Variable Display"
    readonly property string monoFontFamily: "Cascadia Mono"

    readonly property int space2xs: 4
    readonly property int spaceXs: 6
    readonly property int spaceSm: 8
    readonly property int spaceMd: 12
    readonly property int spaceLg: 16
    readonly property int spaceXl: 20
    readonly property int space2xl: 24

    readonly property int radiusSm: 6
    readonly property int radiusMd: 9
    readonly property int radiusLg: 12
    readonly property int radiusXl: 16

    readonly property color canvas: dark ? "#C7181A1D" : "#DCF2F5F8"
    readonly property color surface: dark ? "#D625282C" : "#EAFBFCFD"
    readonly property color surfaceRaised: dark ? "#EE2C3035" : "#F8FFFFFF"
    readonly property color surfaceSunken: dark ? "#B914171A" : "#DCE8EDF2"
    readonly property color surfaceHover: dark ? "#36FFFFFF" : "#12000000"
    readonly property color surfacePressed: dark ? "#52FFFFFF" : "#1C000000"
    readonly property color viewer: "#090B0E"

    readonly property color border: dark ? "#35FFFFFF" : "#26000000"
    readonly property color borderStrong: dark ? "#58FFFFFF" : "#3D000000"
    readonly property color focus: dark ? "#7DD7FF" : "#005FB8"

    readonly property color text: dark ? "#F7F8FA" : "#121417"
    readonly property color textSecondary: dark ? "#C0C5CB" : "#4D555E"
    readonly property color textMuted: dark ? "#9198A1" : "#68727D"
    readonly property color textOnAccent: "#FFFFFF"

    readonly property color accent: dark ? "#3ABFF8" : "#0067C0"
    readonly property color accentHover: dark ? "#58CAFA" : "#0B73CE"
    readonly property color accentPressed: dark ? "#25A8E0" : "#00579F"
    readonly property color accentSoft: dark ? "#303ABFF8" : "#1B0067C0"

    readonly property color success: dark ? "#71D6A8" : "#087B50"
    readonly property color successSoft: dark ? "#2871D6A8" : "#16087B50"
    readonly property color warning: dark ? "#FFD66B" : "#8A5400"
    readonly property color warningSoft: dark ? "#2BFFD66B" : "#188A5400"
    readonly property color danger: dark ? "#FF8290" : "#B42318"
    readonly property color dangerSoft: dark ? "#2DFF8290" : "#18B42318"

    readonly property color shadow: dark ? "#B0000000" : "#52000000"
    readonly property color scrim: dark ? "#7A06080A" : "#520D1117"
}
