import QtQuick
import QtQuick.Layouts
import ".."

Rectangle {
    id: root
    property string label: "METRIC"
    property string value: "—"
    property string context: ""
    property string tone: "neutral"
    property string spark: ""
    property color accent: Theme.toneColor(tone)
    color: Theme.surfaceRaised
    border.color: Theme.border
    border.width: 1
    radius: 1
    implicitHeight: 112
    implicitWidth: 120

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 5
        Text {
            text: root.label
            color: Theme.textSecondary
            font.family: Theme.interfaceFont
            font.pixelSize: Theme.caption
            Layout.fillWidth: true
        }
        Text {
            text: root.value
            color: root.accent
            font.family: Theme.monoFont
            font.pixelSize: Theme.value
            font.weight: Theme.weightMedium
            Layout.fillWidth: true
        }
        Canvas {
            id: sparkCanvas
            visible: root.spark.length > 0
            Layout.fillWidth: true
            Layout.preferredHeight: 22
            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                var values = root.spark.split(",")
                if (values.length < 2) return
                ctx.strokeStyle = root.accent
                ctx.lineWidth = 1
                ctx.beginPath()
                for (var i = 0; i < values.length; i++) {
                    var x = i * width / (values.length - 1)
                    var y = height - 2 - Number(values[i]) * (height - 4) / 10
                    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
                }
                ctx.stroke()
            }
            Connections { target: root; function onSparkChanged() { sparkCanvas.requestPaint() } }
            Connections { target: root; function onAccentChanged() { sparkCanvas.requestPaint() } }
            onWidthChanged: requestPaint()
        }
        Item { Layout.fillHeight: true }
        Text {
            text: root.context
            color: Theme.textMuted
            font.family: Theme.monoFont
            font.pixelSize: Theme.tiny
            Layout.fillWidth: true
        }
    }
}
