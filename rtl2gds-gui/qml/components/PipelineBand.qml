import QtQuick
import QtQuick.Layouts
import ".."

Panel {
    id: root
    property string stageTitle: "Placement"
    property string stageTone: "active"
    property bool showAction: true
    property string actionText: "VIEW LIVE PLACEMENT"
    property bool showLegend: true
    property bool flowMode: false
    contentPadding: 12

    ColumnLayout {
        anchors.fill: parent
        spacing: 5

        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 22
            SectionHeader { visible: root.flowMode; text: "14-STAGE RTL-TO-GDS FLOW"; Layout.fillWidth: true }
            Text { visible: !root.flowMode; text: "STAGE 7 OF 14"; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; font.weight: Theme.weightMedium }
            Text { visible: !root.flowMode; text: root.stageTitle; color: Theme.textPrimary; font.family: Theme.interfaceFont; font.pixelSize: 16; font.weight: Theme.weightMedium }
            StatusBadge { visible: !root.flowMode; text: root.stageTone === "fail" ? "FAILED" : "ACTIVE"; tone: root.stageTone }
            Item { Layout.fillWidth: true }
            ActionButton { visible: root.showAction; text: root.actionText; implicitHeight: 28 }
        }

        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 0
            Repeater {
                model: appController.pipelineModel
                PipelineStage {
                    number: model.number
                    name: model.name
                    status: model.number === 7 ? root.stageTone : model.status
                    Layout.fillWidth: true; Layout.preferredWidth: 70
                    last: number === 14
                }
            }
        }

        RowLayout {
            visible: root.showLegend; spacing: 18; Layout.preferredHeight: 14
            Repeater {
                model: [
                    {t: "●  PASS", c: Theme.pass}, {t: "●  ACTIVE", c: Theme.live},
                    {t: "●  REVIEW", c: Theme.review}, {t: "●  FAIL", c: Theme.fail},
                    {t: "○  PENDING", c: Theme.textSecondary}
                ]
                Text { required property var modelData; text: modelData.t; color: modelData.c; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
            }
        }
    }
}
