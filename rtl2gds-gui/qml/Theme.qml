pragma Singleton
import QtQuick

QtObject {
    readonly property color canvas: "#080A0C"
    readonly property color surface: "#0B1012"
    readonly property color surfaceRaised: "#0D1215"
    readonly property color surfaceActive: "#10291A"
    readonly property color surfaceHover: "#12191C"
    readonly property color input: "#080D0F"
    readonly property color border: "#30383D"
    readonly property color borderSubtle: "#252D31"
    readonly property color textPrimary: "#D7DBDC"
    readonly property color textSecondary: "#A1A8AB"
    readonly property color textMuted: "#747D81"
    readonly property color live: "#20B8D2"
    readonly property color pass: "#50B72B"
    readonly property color review: "#E3B40E"
    readonly property color fail: "#E5534C"
    readonly property color purple: "#A967E8"
    readonly property color heatmapDeep: "#10133A"
    readonly property color heatmapMid: "#2546A8"
    readonly property color heatmapSurface: "#0B2530"
    readonly property color white: "#F0F2F2"

    readonly property string interfaceFont: "Fira Sans"
    readonly property string monoFont: "Fira Code"
    readonly property int weightRegular: Font.Normal
    readonly property int weightMedium: Font.Medium
    readonly property int weightSemibold: Font.DemiBold
    readonly property int tiny: 9
    readonly property int caption: 10
    readonly property int body: 11
    readonly property int bodyLarge: 12
    readonly property int section: 11
    readonly property int value: 17
    readonly property int title: 20
    readonly property int spacingXs: 4
    readonly property int spacingSm: 8
    readonly property int spacingMd: 12
    readonly property int spacingLg: 16
    readonly property int spacingXl: 20
    readonly property int spacing2Xl: 24
    readonly property int topBarHeight: 65
    readonly property int sidebarWidth: 153
    readonly property int contentInset: 16
    readonly property int controlHeight: 30
    readonly property int controlHeightLarge: 36
    readonly property int fieldHeight: 32
    readonly property int borderWidth: 1

    function toneColor(tone) {
        if (tone === "pass" || tone === "success" || tone === "running") return pass
        if (tone === "active" || tone === "live") return live
        if (tone === "review" || tone === "warning") return review
        if (tone === "fail" || tone === "danger") return fail
        if (tone === "purple") return purple
        return textSecondary
    }
}
