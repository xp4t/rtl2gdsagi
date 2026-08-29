import QtQuick
import QtQuick.Layouts
import ".."

Rectangle {
    id: root
    property string title: ""
    property int contentPadding: Theme.spacingMd
    property color panelColor: Theme.surface
    default property alias contentData: body.data
    color: panelColor
    border.color: Theme.border
    border.width: Theme.borderWidth
    radius: 1
    implicitWidth: 240
    implicitHeight: 120

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: root.contentPadding
        spacing: Theme.spacingSm
        SectionHeader {
            text: root.title
            visible: root.title.length > 0
            Layout.fillWidth: true
        }
        Item {
            id: body
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}

