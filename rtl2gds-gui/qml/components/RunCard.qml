import QtQuick
import QtQuick.Layouts
import ".."

Rectangle {
    id: root
    property string runId: "run_000"
    property string kind: "RUN"
    property string description: "Implementation run"
    property string status: "Pending"
    property string metric: "—"
    property string tone: "neutral"
    signal clicked()
    color: Theme.surfaceRaised
    border.color: Theme.border
    border.width: 1
    implicitHeight: 58
    implicitWidth: 420

    Rectangle { width: 3; height: parent.height; color: Theme.toneColor(root.tone) }
    RowLayout {
        anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12; spacing: 12
        ColumnLayout {
            spacing: 3; Layout.preferredWidth: 110
            Text { text: root.runId; color: Theme.textPrimary; font.family: Theme.monoFont; font.pixelSize: 13 }
            StatusBadge { text: root.kind; tone: root.tone }
        }
        Text { text: root.description; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.fillWidth: true; elide: Text.ElideRight }
        Text { text: root.metric; color: Theme.toneColor(root.tone); font.family: Theme.monoFont; font.pixelSize: 13 }
        Text { text: root.status; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption }
    }
    MouseArea { anchors.fill: parent; onClicked: root.clicked() }
}
