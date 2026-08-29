import QtQuick
import QtQuick.Controls
import ".."

Button {
    id: root
    property string tone: "neutral"
    property bool filled: false
    property color accent: Theme.toneColor(tone)
    implicitHeight: Theme.controlHeight
    implicitWidth: Math.max(74, contentItem.implicitWidth + 24)
    padding: 0
    hoverEnabled: true

    contentItem: Text {
        text: root.text
        color: root.tone === "neutral" ? Theme.textPrimary : (root.filled ? Theme.canvas : root.accent)
        font.family: Theme.interfaceFont
        font.pixelSize: Theme.caption
        font.weight: Font.Medium
        font.letterSpacing: 0.5
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
        color: root.filled ? root.accent : (root.hovered ? Theme.surfaceHover : "transparent")
        border.color: root.tone === "neutral" ? Theme.border : Qt.darker(root.accent, 1.25)
        border.width: 1
        radius: 1
    }
}
