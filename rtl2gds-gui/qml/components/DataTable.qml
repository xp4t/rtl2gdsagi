import QtQuick
import QtQuick.Layouts
import ".."

Rectangle {
    id: root
    property var headers: []
    property int headerHeight: 32
    default property alias rows: rowContainer.data
    color: Theme.surface
    border.color: Theme.border
    border.width: 1
    implicitWidth: 600
    implicitHeight: 240

    ColumnLayout {
        anchors.fill: parent; spacing: 0
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: root.headerHeight
            color: Theme.surfaceRaised; border.color: Theme.border; border.width: 1
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10
                Repeater {
                    model: root.headers
                    Text {
                        required property var modelData
                        text: typeof modelData === "string" ? modelData : modelData.label
                        color: Theme.textSecondary
                        font.family: Theme.monoFont
                        font.pixelSize: Theme.tiny
                        Layout.fillWidth: true
                    }
                }
            }
        }
        Item { id: rowContainer; Layout.fillWidth: true; Layout.fillHeight: true }
    }
}
