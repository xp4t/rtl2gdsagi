import QtQuick
import QtQuick.Layouts
import ".."

Rectangle {
    id: root
    property var logModel
    color: Theme.surface
    border.color: Theme.border
    border.width: 1
    implicitHeight: 230

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 32; color: Theme.surface
            border.color: Theme.border; border.width: 1
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 10; spacing: 24
                Text { text: "OPENLANE LOGS"; color: Theme.white; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; font.weight: Theme.weightMedium }
                Text { text: "MESSAGES   " + (root.logModel ? root.logModel.count : 0); color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
                Text { text: "TIMING"; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
                Text { text: "DRC"; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
                Text { text: "LVS"; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
                Text { text: "SYSTEM"; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
                Item { Layout.fillWidth: true }
                Text { text: "● LIVE"; color: Theme.pass; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                Text { text: "Ⅱ"; color: Theme.review; font.family: Theme.monoFont; font.pixelSize: Theme.body }
                Text { text: "⇩"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.body }
                Text { text: "CLEAR"; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
            }
            Rectangle { anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.leftMargin: 14; width: 94; height: 2; color: Theme.pass }
        }
        ListView {
            Layout.fillWidth: true; Layout.fillHeight: true
            Layout.leftMargin: 16; Layout.rightMargin: 10; Layout.topMargin: 7
            model: root.logModel
            clip: true
            spacing: 2
            delegate: RowLayout {
                required property string time
                required property string level
                required property string scope
                required property string message
                width: ListView.view.width; spacing: 12
                Text { text: time; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 58 }
                Text { text: level; color: level === "ERROR" ? Theme.fail : (level === "WARN" ? Theme.review : Theme.pass); font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 36 }
                Text { text: "[" + scope + "]"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 48 }
                Text { text: message; color: Theme.textPrimary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; elide: Text.ElideRight; Layout.fillWidth: true }
            }
        }
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 24; color: Theme.input
            border.color: Theme.border; border.width: 1
            Text { anchors.left: parent.left; anchors.leftMargin: 16; anchors.verticalCenter: parent.verticalCenter; text: "place_opt>│"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption }
        }
    }
}
