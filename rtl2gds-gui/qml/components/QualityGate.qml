import QtQuick
import QtQuick.Layouts
import ".."

RowLayout {
    id: root
    property string label: "GATE"
    property string status: "PENDING"
    property string tone: "neutral"
    spacing: 7
    Rectangle {
        implicitWidth: 10; implicitHeight: 10; radius: 5
        color: "transparent"
        border.width: 1
        border.color: Theme.toneColor(parent.tone)
        Rectangle {
            anchors.centerIn: parent; width: 5; height: 5; radius: 3
            color: root.tone === "neutral" ? "transparent" : Theme.toneColor(root.tone)
        }
    }
    Text { text: root.label; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; Layout.fillWidth: true }
    Text { text: root.status; color: Theme.toneColor(root.tone); font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; font.weight: Theme.weightMedium }
}
