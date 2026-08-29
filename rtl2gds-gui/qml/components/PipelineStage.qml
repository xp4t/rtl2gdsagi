import QtQuick
import ".."

Item {
    id: root
    property int number: 1
    property string name: "STAGE"
    property string status: "pending"
    property bool last: false
    property color accent: Theme.toneColor(status)
    implicitHeight: 72

    Rectangle {
        x: root.width / 2
        y: 11
        width: root.width
        height: 1
        visible: !root.last
        color: root.status === "pass" ? Theme.pass : Theme.border
    }
    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 4
        width: 16
        height: 16
        radius: 8
        color: Theme.canvas
        border.width: root.status === "active" ? 2 : 1
        border.color: root.status === "pending" ? Theme.textMuted : root.accent
        Rectangle {
            anchors.centerIn: parent
            width: 6
            height: 6
            radius: 3
            color: root.status === "pending" ? "transparent" : root.accent
        }
        Text {
            anchors.centerIn: parent
            visible: root.status === "pending"
            text: root.number
            color: Theme.textSecondary
            font.family: Theme.monoFont
            font.pixelSize: 6
        }
    }
    Text {
        anchors.top: parent.top
        anchors.topMargin: 30
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width - 4
        text: root.name
        color: root.status === "active" ? Theme.white : Theme.textPrimary
        font.family: Theme.monoFont
        font.pixelSize: Theme.tiny
        lineHeight: 1.4
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
    }
}

