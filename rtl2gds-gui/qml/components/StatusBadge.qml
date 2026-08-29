import QtQuick
import ".."

Rectangle {
    id: root
    property string text: "ACTIVE"
    property string tone: "active"
    property color accent: Theme.toneColor(tone)
    implicitWidth: label.implicitWidth + 12
    implicitHeight: 18
    color: "transparent"
    border.color: Qt.darker(accent, 1.25)
    border.width: 1
    radius: 1

    Text {
        id: label
        anchors.centerIn: parent
        text: root.text
        color: root.accent
        font.family: Theme.monoFont
        font.pixelSize: Theme.tiny
        font.weight: Font.Medium
        font.letterSpacing: 0.4
    }
}

