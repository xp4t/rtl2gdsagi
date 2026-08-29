import QtQuick
import QtQuick.Layouts
import ".."

Rectangle {
    id: root
    property var runState
    property real fitScale: Math.min(1.0, width / 1536.0)
    color: Theme.surface
    height: Theme.topBarHeight
    z: 10

    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Item {
            Layout.preferredWidth: 128 * root.fitScale
            Layout.fillHeight: true
            Rectangle {
                width: 36; height: 39
                anchors.left: parent.left; anchors.leftMargin: 15
                anchors.verticalCenter: parent.verticalCenter
                color: "transparent"; border.color: Theme.review; border.width: 1
                Text {
                    anchors.centerIn: parent
                    text: "RTL\nGDS"; color: Theme.review
                    font.family: Theme.monoFont; font.pixelSize: 10; font.weight: Theme.weightMedium
                    lineHeight: 1.0; horizontalAlignment: Text.AlignHCenter
                }
            }
            Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.border }
        }

        Repeater {
            model: [
                {label: "PROJECT", value: root.runState.project, width: 148, tone: "neutral"},
                {label: "TOP MODULE", value: root.runState.topModule, width: 152, tone: "neutral"},
                {label: "BRANCH / COMMIT", value: root.runState.branchCommit, width: 168, tone: "neutral"},
                {label: "RUN", value: root.runState.runId, width: 122, tone: "neutral"},
                {label: "STATUS", value: root.runState.status, width: 126, tone: root.runState.statusTone},
                {label: "ELAPSED", value: root.runState.elapsed, width: 124, tone: "neutral"},
                {label: "EST. REMAIN", value: root.runState.remaining, width: 124, tone: "neutral"},
                {label: "STARTED", value: root.runState.started, width: 182, tone: "neutral"}
            ]
            delegate: Item {
                required property var modelData
                Layout.preferredWidth: modelData.width * root.fitScale
                Layout.fillHeight: true
                Rectangle { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; width: 1; height: 42; color: Theme.borderSubtle }
                ColumnLayout {
                    anchors.left: parent.left; anchors.leftMargin: Math.max(10, 18 * root.fitScale)
                    anchors.verticalCenter: parent.verticalCenter; spacing: 5
                    Text {
                        text: modelData.label; color: Theme.textMuted
                        font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny; font.weight: Theme.weightMedium
                        font.letterSpacing: 0.45
                    }
                    RowLayout {
                        spacing: 6
                        Rectangle { visible: modelData.tone !== "neutral" && modelData.value !== "—"; width: 6; height: 6; radius: 3; color: Theme.toneColor(modelData.tone) }
                        Text {
                            text: modelData.value
                            color: modelData.tone !== "neutral" && modelData.value !== "—" ? Theme.toneColor(modelData.tone) : Theme.textPrimary
                            font.family: modelData.label === "STATUS" ? Theme.interfaceFont : Theme.monoFont
                            font.pixelSize: Theme.bodyLarge
                            wrapMode: modelData.label === "STATUS" ? Text.WordWrap : Text.NoWrap
                            maximumLineCount: modelData.label === "STATUS" ? 2 : 1
                            lineHeight: modelData.label === "STATUS" ? .9 : 1.0
                            elide: Text.ElideRight
                            Layout.preferredWidth: (modelData.width - 24) * root.fitScale
                            Layout.maximumWidth: (modelData.width - 24) * root.fitScale
                        }
                    }
                }
            }
        }

        Item { Layout.fillWidth: true }

        Repeater {
            model: ["terminal", "messages", "notifications", "help"]
            delegate: Item {
                required property string modelData
                Layout.preferredWidth: 50 * root.fitScale
                Layout.fillHeight: true
                Rectangle { anchors.left: parent.left; width: 1; height: parent.height; color: Theme.border }
                ConsoleIcon { anchors.centerIn: parent; name: modelData; strokeColor: Theme.textSecondary; width: 18; height: 18 }
            }
        }

        Item {
            Layout.preferredWidth: 60 * root.fitScale
            Layout.fillHeight: true
            Rectangle { anchors.left: parent.left; width: 1; height: parent.height; color: Theme.border }
            Rectangle {
                anchors.centerIn: parent; width: 36; height: 36; radius: 18
                color: "transparent"; border.color: Theme.textMuted; border.width: 1
                Text { anchors.centerIn: parent; text: "PD"; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.bodyLarge }
            }
        }
    }
}
