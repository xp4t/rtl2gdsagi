import QtQuick

Canvas {
    id: root
    property color lineColor: "#20B8D2"
    property int seed: 1
    property bool flat: false
    implicitWidth: 64
    implicitHeight: 14
    onLineColorChanged: requestPaint()
    onSeedChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onPaint: {
        var c = getContext("2d")
        c.reset(); c.strokeStyle = lineColor; c.lineWidth = 1
        c.beginPath()
        for (var x = 0; x <= width; x += Math.max(5, width / 9)) {
            var y = flat ? height * .5 : height * .5 + Math.sin((x + seed * 11) * .16) * height * .23 + (((x * seed) % 7) - 3) * .35
            x === 0 ? c.moveTo(x, y) : c.lineTo(x, y)
        }
        c.stroke()
    }
}
