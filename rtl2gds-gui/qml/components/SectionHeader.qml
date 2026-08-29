import QtQuick
import QtQuick.Layouts
import ".."

RowLayout {
    id: root
    property string text: "SECTION"
    property color color: Theme.textSecondary
    spacing: Theme.spacingSm
    implicitHeight: 16

    Text {
        text: root.text
        color: root.color
        font.family: Theme.interfaceFont
        font.pixelSize: Theme.section
        font.weight: Theme.weightMedium
        font.letterSpacing: 0.6
        Layout.alignment: Qt.AlignVCenter
    }
    Rectangle {
        color: Theme.border
        implicitHeight: 1
        Layout.preferredHeight: 1
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignVCenter
    }
}
