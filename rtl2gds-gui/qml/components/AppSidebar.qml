import QtQuick
import QtQuick.Layouts
import ".."

Rectangle {
    id: root
    property string currentPage: "activeRun"
    property bool collapsed: false
    signal navigate(string route)
    color: Theme.surface
    implicitWidth: collapsed ? 54 : Theme.sidebarWidth

    function activeRoute() {
        if (currentPage === "activeRun") return "activeRun"
        if (currentPage === "strategySweep") return ""
        return "runHistory"
    }

    Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.border }

    Component {
        id: navDelegate
        Item {
            required property string route
            required property string label
            required property string detail
            required property string icon
            required property int group
            required property bool available
            property int wantedGroup: ListView.view.wantedGroup
            width: ListView.view.width
            height: group === wantedGroup ? 54 : 0
            visible: group === wantedGroup

            Rectangle {
                anchors.left: parent.left; anchors.leftMargin: 13
                anchors.right: parent.right; anchors.rightMargin: 14
                anchors.verticalCenter: parent.verticalCenter
                height: route === root.activeRoute() ? 48 : 44
                color: route === root.activeRoute() ? Theme.surfaceActive : (pointer.containsMouse && available ? Theme.surfaceHover : "transparent")
                radius: 1
                Rectangle { width: 2; height: parent.height; color: Theme.pass; visible: route === root.activeRoute() }
                RowLayout {
                    anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 5; spacing: 12
                    ConsoleIcon {
                        name: icon
                        strokeColor: route === root.activeRoute() ? Theme.pass : Theme.textSecondary
                        Layout.preferredWidth: 18; Layout.preferredHeight: 18
                    }
                    ColumnLayout {
                        visible: !root.collapsed; spacing: 2; Layout.fillWidth: true
                        Text { text: label; color: Theme.textPrimary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; font.weight: Theme.weightMedium; font.letterSpacing: .2 }
                        Text { text: detail; color: route === root.activeRoute() ? Theme.pass : Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                    }
                }
                MouseArea { id: pointer; anchors.fill: parent; hoverEnabled: true; enabled: parent.parent.available; cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor; onClicked: root.navigate(route) }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Item { Layout.fillWidth: true; Layout.preferredHeight: Theme.topBarHeight }
        Item { Layout.preferredHeight: 14 }

        ListView {
            property int wantedGroup: 0
            Layout.fillWidth: true; Layout.preferredHeight: 324
            model: appController.navigationModel; delegate: navDelegate; spacing: 0; interactive: false
        }
        Rectangle { Layout.leftMargin: 14; Layout.rightMargin: 14; Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.border }
        Item { Layout.preferredHeight: 10 }
        ListView {
            property int wantedGroup: 1
            Layout.fillWidth: true; Layout.preferredHeight: 216
            model: appController.navigationModel; delegate: navDelegate; spacing: 0; interactive: false
        }
        Item { Layout.fillHeight: true }
        ListView {
            property int wantedGroup: 2
            Layout.fillWidth: true; Layout.preferredHeight: 54
            model: appController.navigationModel; delegate: navDelegate; spacing: 0; interactive: false
        }

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 55
            color: "transparent"
            Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: Theme.border }
            RowLayout {
                anchors.left: parent.left; anchors.leftMargin: 24; anchors.verticalCenter: parent.verticalCenter; spacing: 12
                ConsoleIcon { name: "compare"; rotation: 180; strokeColor: Theme.textSecondary; Layout.preferredWidth: 14; Layout.preferredHeight: 14 }
                Text { visible: !root.collapsed; text: "COLLAPSE"; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny; font.letterSpacing: .5 }
            }
            MouseArea { anchors.fill: parent; onClicked: root.collapsed = !root.collapsed }
        }
    }
}
