import QtQuick
import QtQuick.Layouts
import ".."

Panel {
    id: root
    property var diagnosisModel
    title: "AI DIAGNOSIS"
    contentPadding: Theme.spacingMd
    implicitHeight: diagnosisModel && diagnosisModel.state === "AVAILABLE" ? 278 : 82

    function stateTone() {
        if (!diagnosisModel) return "neutral"
        if (diagnosisModel.state === "AVAILABLE") return "review"
        if (diagnosisModel.state === "ANALYZING") return "active"
        if (diagnosisModel.state === "ERROR") return "fail"
        return "neutral"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.spacingSm

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacingMd
            StatusBadge {
                text: root.diagnosisModel ? root.diagnosisModel.state.replace("_", " ") : "NO DIAGNOSIS"
                tone: root.stateTone()
            }
            Text {
                text: root.diagnosisModel && root.diagnosisModel.state === "AVAILABLE"
                      ? "READ-ONLY ANALYSIS — NO CHANGES HAVE BEEN APPLIED."
                      : (root.diagnosisModel ? root.diagnosisModel.message : "AI diagnosis unavailable")
                color: root.diagnosisModel && root.diagnosisModel.state === "ERROR" ? Theme.fail : Theme.textSecondary
                font.family: Theme.interfaceFont
                font.pixelSize: Theme.caption
                font.weight: Theme.weightMedium
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
            ActionButton {
                visible: root.diagnosisModel && root.diagnosisModel.hasFailures
                enabled: root.diagnosisModel && !root.diagnosisModel.analyzing
                text: root.diagnosisModel && root.diagnosisModel.available ? "REFRESH ANALYSIS" : "ANALYZE FAILURE"
                tone: "warning"
                onClicked: appController.analyzeFailure()
            }
        }

        RowLayout {
            visible: root.diagnosisModel && root.diagnosisModel.state === "AVAILABLE"
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.spacingLg

            ColumnLayout {
                Layout.preferredWidth: 300
                Layout.fillHeight: true
                spacing: 5
                SectionHeader { text: "LIKELY ROOT CAUSE"; Layout.fillWidth: true }
                Text {
                    text: root.diagnosisModel ? root.diagnosisModel.summary : ""
                    color: Theme.textPrimary
                    font.family: Theme.interfaceFont
                    font.pixelSize: Theme.body
                    wrapMode: Text.Wrap
                    maximumLineCount: 4
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
                Item { Layout.fillHeight: true }
                RowLayout {
                    Layout.fillWidth: true; spacing: Theme.spacingLg
                    ColumnLayout { spacing: 2
                        Text { text: "ROOT CAUSE STAGE"; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                        Text { text: root.diagnosisModel ? root.diagnosisModel.rootCauseStage.toUpperCase() : "—"; color: Theme.review; font.family: Theme.monoFont; font.pixelSize: Theme.body; font.weight: Theme.weightMedium }
                    }
                    ColumnLayout { spacing: 2
                        Text { text: "CONFIDENCE"; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                        Text { text: root.diagnosisModel ? root.diagnosisModel.confidence : "—"; color: Theme.textPrimary; font.family: Theme.monoFont; font.pixelSize: Theme.body }
                    }
                    Item { Layout.fillWidth: true }
                }
            }

            Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: Theme.borderSubtle }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 280
                spacing: 5
                SectionHeader { text: "EVIDENCE"; Layout.fillWidth: true }
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: root.diagnosisModel ? root.diagnosisModel.evidenceModel : null
                    spacing: 4
                    delegate: RowLayout {
                        required property string evidenceType
                        required property string name
                        required property string value
                        required property string stage
                        required property string source
                        required property string detail
                        required property string tone
                        width: ListView.view.width
                        spacing: Theme.spacingSm
                        Text { text: "●"; color: Theme.toneColor(tone); font.pixelSize: Theme.caption; Layout.preferredWidth: 10 }
                        Text { text: name; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 112; elide: Text.ElideRight }
                        Text { text: value; color: Theme.textPrimary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 92; elide: Text.ElideRight }
                        Text { text: stage; color: Theme.textMuted; font.family: Theme.monoFont; font.pixelSize: Theme.tiny; Layout.fillWidth: true; elide: Text.ElideRight }
                    }
                }
            }

            Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: Theme.borderSubtle }

            ColumnLayout {
                Layout.preferredWidth: 320
                Layout.fillHeight: true
                spacing: 5
                SectionHeader { text: "RECOMMENDED CHECKS"; Layout.fillWidth: true }
                Repeater {
                    model: root.diagnosisModel ? root.diagnosisModel.recommendedChecks : []
                    RowLayout {
                        required property string modelData
                        Layout.fillWidth: true
                        Layout.maximumHeight: 38
                        spacing: 7
                        Text { text: "•"; color: Theme.live; font.family: Theme.interfaceFont; font.pixelSize: Theme.body; Layout.alignment: Qt.AlignTop }
                        Text {
                            text: modelData
                            color: Theme.textSecondary
                            font.family: Theme.interfaceFont
                            font.pixelSize: Theme.caption
                            wrapMode: Text.Wrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }
                }
                Item { Layout.fillHeight: true }
                Text {
                    text: root.diagnosisModel && root.diagnosisModel.limitations.length
                          ? root.diagnosisModel.limitations[0] : "Deterministic signoff remains authoritative."
                    color: Theme.textMuted
                    font.family: Theme.interfaceFont
                    font.pixelSize: Theme.tiny
                    wrapMode: Text.Wrap
                    maximumLineCount: 2
                    Layout.fillWidth: true
                }
            }
        }
    }
}
