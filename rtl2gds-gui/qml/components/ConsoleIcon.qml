import QtQuick

Canvas {
    id: root
    property string name: "terminal"
    property color strokeColor: "#A1A8AB"
    property real strokeWidth: 1.35
    implicitWidth: 18
    implicitHeight: 18

    onNameChanged: requestPaint()
    onStrokeColorChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()

    function line(ctx, x1, y1, x2, y2) {
        ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke()
    }
    function circle(ctx, x, y, r) {
        ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke()
    }

    onPaint: {
        var c = getContext("2d")
        c.reset()
        c.strokeStyle = strokeColor
        c.fillStyle = strokeColor
        c.lineWidth = strokeWidth
        c.lineCap = "round"
        c.lineJoin = "round"
        c.scale(width / 18, height / 18)

        if (name === "terminal") {
            line(c, 3, 4, 7, 8); line(c, 7, 8, 3, 12); line(c, 9, 13, 15, 13)
        } else if (name === "messages") {
            c.beginPath(); c.moveTo(2.5, 3.5); c.lineTo(15.5, 3.5); c.lineTo(15.5, 12.5); c.lineTo(8, 12.5); c.lineTo(4.5, 15); c.lineTo(4.5, 12.5); c.lineTo(2.5, 12.5); c.closePath(); c.stroke()
            line(c, 5.5, 7, 12.5, 7); line(c, 5.5, 9.5, 10, 9.5)
        } else if (name === "notifications") {
            c.beginPath(); c.moveTo(4, 12.5); c.quadraticCurveTo(5.2, 11.4, 5.2, 8); c.quadraticCurveTo(5.2, 3.7, 9, 3.7); c.quadraticCurveTo(12.8, 3.7, 12.8, 8); c.quadraticCurveTo(12.8, 11.4, 14, 12.5); c.stroke(); line(c, 3.6, 12.5, 14.4, 12.5); c.beginPath(); c.arc(9, 14.1, 1.2, 0, Math.PI); c.stroke()
        } else if (name === "help") {
            circle(c, 9, 9, 7); c.beginPath(); c.moveTo(6.8, 6.8); c.quadraticCurveTo(7.2, 4.8, 9.2, 4.8); c.quadraticCurveTo(11.3, 4.8, 11.3, 6.7); c.quadraticCurveTo(11.3, 8.1, 9.1, 9.5); c.stroke(); line(c, 9.1, 9.5, 9.1, 10.5); circle(c, 9.1, 13.1, .35)
        } else if (name === "flow") {
            c.beginPath(); c.moveTo(1.5, 10); c.lineTo(4, 10); c.lineTo(6, 4); c.lineTo(8.5, 14); c.lineTo(11, 7); c.lineTo(13, 10); c.lineTo(16.5, 10); c.stroke()
        } else if (name === "runs") {
            circle(c, 9.5, 9, 6.2); line(c, 9.5, 5, 9.5, 9); line(c, 9.5, 9, 6.5, 11); line(c, 1.8, 4.2, 4.7, 4.2); line(c, 1.8, 4.2, 1.8, 7)
        } else if (name === "designs") {
            c.strokeRect(3, 2.5, 11.5, 13); line(c, 6, 6, 11.5, 6); line(c, 6, 9, 9, 9); line(c, 11, 12.5, 14, 9.5); line(c, 11, 12.5, 8.5, 10)
        } else if (name === "compare") {
            line(c, 3, 5, 13, 5); line(c, 11, 3, 13, 5); line(c, 11, 7, 13, 5); line(c, 15, 13, 5, 13); line(c, 7, 11, 5, 13); line(c, 7, 15, 5, 13); line(c, 5, 2, 5, 9); line(c, 13, 9, 13, 16)
        } else if (name === "reports") {
            c.beginPath(); c.moveTo(4, 2.5); c.lineTo(11.5, 2.5); c.lineTo(14.5, 5.5); c.lineTo(14.5, 15.5); c.lineTo(4, 15.5); c.closePath(); c.stroke(); line(c, 11.5, 2.5, 11.5, 5.5); line(c, 11.5, 5.5, 14.5, 5.5); line(c, 6.5, 9, 12, 9); line(c, 6.5, 12, 12, 12)
        } else if (name === "evidence") {
            c.beginPath(); c.moveTo(3, 4); c.lineTo(7, 4); c.lineTo(8.5, 6); c.lineTo(15, 6); c.lineTo(15, 14.5); c.lineTo(3, 14.5); c.closePath(); c.stroke(); line(c, 6, 10, 12, 10)
        } else if (name === "config" || name === "settings") {
            circle(c, 9, 9, 2.5); circle(c, 9, 9, 6); line(c, 9, 1.3, 9, 3); line(c, 9, 15, 9, 16.7); line(c, 1.3, 9, 3, 9); line(c, 15, 9, 16.7, 9)
        } else if (name === "policies") {
            c.beginPath(); c.moveTo(9, 2); c.lineTo(14.5, 5); c.lineTo(13.5, 12); c.lineTo(9, 16); c.lineTo(4.5, 12); c.lineTo(3.5, 5); c.closePath(); c.stroke(); circle(c, 9, 8, 1.5)
        } else if (name === "agents") {
            circle(c, 9, 5.3, 2.7); c.beginPath(); c.moveTo(3.5, 15); c.quadraticCurveTo(4.2, 9.5, 9, 9.5); c.quadraticCurveTo(13.8, 9.5, 14.5, 15); c.stroke()
        } else if (name === "integrations") {
            line(c, 3, 5, 7, 5); line(c, 7, 5, 7, 9); line(c, 7, 9, 11, 9); line(c, 11, 9, 11, 13); line(c, 11, 13, 15, 13); circle(c, 3, 5, 1.3); circle(c, 15, 13, 1.3)
        }
    }
}
