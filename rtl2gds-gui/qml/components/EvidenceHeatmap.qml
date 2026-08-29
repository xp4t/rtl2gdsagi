import QtQuick
import ".."

Canvas {
    id: root
    property int variant: 0
    property bool showRegions: true
    property color lowColor: "#142B73"
    property color midColor: "#D69B08"
    property color highColor: Theme.fail

    onVariantChanged: requestPaint()
    onShowRegionsChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()

    onPaint: {
        var c = getContext("2d")
        c.reset()
        c.fillStyle = "#09152B"
        c.fillRect(0, 0, width, height)
        var cell = Math.max(3, Math.floor(width / 54))
        for (var y = 2; y < height - 2; y += cell + 1) {
            for (var x = 2; x < width - 2; x += cell + 1) {
                var wave = Math.sin((x + variant * 31) * .041) + Math.cos((y - variant * 17) * .083)
                var hotspot1 = Math.max(0, 1 - Math.hypot(x - width * (.28 + variant * .02), y - height * .48) / (width * .24))
                var hotspot2 = Math.max(0, 1 - Math.hypot(x - width * .70, y - height * (.55 - variant * .03)) / (width * .20))
                var heat = hotspot1 + hotspot2 + wave * .12
                c.fillStyle = heat > .82 ? highColor : (heat > .50 ? midColor : (heat > .22 ? Theme.live : lowColor))
                c.globalAlpha = .62 + ((x * 13 + y * 7 + variant) % 30) / 100
                c.fillRect(x, y, cell, cell)
            }
        }
        c.globalAlpha = 1
        c.strokeStyle = Theme.border
        c.strokeRect(.5, .5, width - 1, height - 1)
        if (showRegions) {
            c.strokeStyle = Theme.white
            c.lineWidth = 1
            c.strokeRect(width * .23, height * .16, width * .18, height * .64)
            c.strokeRect(width * .61, height * .28, width * .20, height * .54)
        }
    }
}
