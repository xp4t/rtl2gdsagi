import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../components"

ScrollView {
    id: scroll
    clip: true
    contentWidth: availableWidth
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ScrollBar.vertical.policy: ScrollBar.AsNeeded

    ColumnLayout {
        width: scroll.availableWidth
        spacing: 10

        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 9
            Text { text: "RUNS"; color: Theme.live; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; font.weight: Theme.weightMedium }
            Text { text: ">"; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
            Text { text: "run_042"; color: Theme.live; font.family: Theme.monoFont; font.pixelSize: Theme.caption }
            Text { text: ">"; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
            Text { text: "Placement"; color: Theme.textPrimary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
            Item { Layout.fillWidth: true }
        }

        PipelineBand {
            Layout.fillWidth: true; Layout.preferredHeight: 152
            stageTitle: "Placement"; stageTone: "active"
            actionText: "VIEW LIVE PLACEMENT"
        }

        Panel {
            Layout.fillWidth: true; Layout.preferredHeight: 84
            border.color: Theme.review; panelColor: "#121108"; contentPadding: 12
            RowLayout {
                anchors.fill: parent; spacing: 18
                Canvas {
                    Layout.preferredWidth: 28; Layout.preferredHeight: 28
                    onPaint: { var c=getContext("2d"); c.reset(); c.strokeStyle=Theme.review; c.lineWidth=1.5; c.beginPath(); c.moveTo(14,2); c.lineTo(26,25); c.lineTo(2,25); c.closePath(); c.stroke(); c.beginPath(); c.moveTo(14,8); c.lineTo(14,17); c.stroke(); c.fillStyle=Theme.review; c.fillRect(13.2,20,1.6,1.6) }
                }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 5
                    RowLayout {
                        spacing: 9
                        Text { text: "PROPOSED BOUNDED RETUNE AFTER CONGESTION REPAIR"; color: Theme.review; font.family: Theme.interfaceFont; font.pixelSize: 13; font.weight: Theme.weightMedium }
                        StatusBadge { text: "REVIEW"; tone: "warning" }
                    }
                    Text {
                        text: "Global placement completed congestion repair. Timing remains unresolved. A bounded retune is proposed\nwith reduced density and increased displacement allowance in high-congestion zones."
                        color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; lineHeight: 1.35
                    }
                }
                ColumnLayout {
                    Layout.preferredWidth: 160; spacing: 6
                    Text { text: "CONFIDENCE"; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny; font.weight: Theme.weightMedium }
                    Text { text: "Medium"; color: Theme.review; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
                    RowLayout { spacing: 3; Repeater { model: 5; Rectangle { required property int index; width: 18; height: 5; color: index < 3 ? Theme.review : Theme.border } } }
                }
                Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: Theme.border }
                ColumnLayout {
                    Layout.preferredWidth: 195; spacing: 5
                    Text { text: "DECISION REQUIRED"; color: Theme.review; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny; font.weight: Theme.weightSemibold }
                    Text { text: "Send to Human Review"; color: Theme.textPrimary; font.family: Theme.interfaceFont; font.pixelSize: Theme.bodyLarge }
                }
                ActionButton { text: "SEND TO REVIEW"; tone: "warning"; Layout.preferredWidth: 126 }
            }
        }

        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 437; spacing: 12

            Panel {
                title: "METRICS COMPARISON"
                Layout.preferredWidth: 566; Layout.fillHeight: true; contentPadding: 12
                ColumnLayout {
                    anchors.fill: parent; spacing: 0
                    RowLayout {
                        Layout.fillWidth: true; Layout.preferredHeight: 36; spacing: 0
                        Text { text: "METRIC"; Layout.preferredWidth: 140; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                        Text { text: "BEFORE RETUNE"; Layout.preferredWidth: 176; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                        Text { text: "AFTER RETUNE"; Layout.fillWidth: true; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                        Text { text: "DELTA"; Layout.preferredWidth: 70; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                    }
                    Repeater {
                        model: appController.comparisonModel
                        Rectangle {
                            required property string metric
                            required property string helper
                            required property string before
                            required property string after
                            required property string delta
                            required property string tone
                            Layout.fillWidth: true; Layout.preferredHeight: 55
                            color: "transparent"
                            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.borderSubtle }
                            RowLayout {
                                anchors.fill: parent; spacing: 0
                                ColumnLayout {
                                    Layout.preferredWidth: 140; spacing: 2
                                    Text { text: metric; color: Theme.textPrimary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
                                    Text { text: helper; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                                }
                                RowLayout {
                                    Layout.preferredWidth: 176; spacing: 8
                                    Text { text: before; color: Theme.fail; font.family: Theme.monoFont; font.pixelSize: 16; Layout.preferredWidth: 64 }
                                    Canvas {
                                        Layout.preferredWidth: 74; Layout.preferredHeight: 18
                                        onPaint: { var c=getContext("2d"); c.reset(); c.strokeStyle=Theme.fail; c.lineWidth=1; c.beginPath(); for(var x=0;x<74;x+=9){var y=9+((x*7+metric.length*3)%11)-5; x?c.lineTo(x,y):c.moveTo(x,y)} c.stroke() }
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true; spacing: 8
                                    Text { text: after; color: tone === "pass" ? Theme.review : Theme.live; font.family: Theme.monoFont; font.pixelSize: 16; Layout.preferredWidth: 64 }
                                    Canvas {
                                        Layout.preferredWidth: 64; Layout.preferredHeight: 18
                                        onPaint: { var c=getContext("2d"); c.reset(); c.strokeStyle=tone === "pass" ? Theme.review : Theme.live; c.lineWidth=1; c.beginPath(); for(var x=0;x<64;x+=8){var y=9+((x*5+metric.length*2)%9)-4; x?c.lineTo(x,y):c.moveTo(x,y)} c.stroke() }
                                    }
                                }
                                Text { text: delta + (tone === "pass" ? "  ↓" : "  ↑"); Layout.preferredWidth: 70; color: Theme.toneColor(tone); font.family: Theme.monoFont; font.pixelSize: 13 }
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 0
                        Text { text: "METRICS CAPTURED"; Layout.preferredWidth: 140; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                        Text { text: "08:58:12  (2m ago)"; Layout.preferredWidth: 176; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption }
                        Text { text: "08:58:12  (now)"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption }
                    }
                }
            }

            Panel {
                title: "CONGESTION HEATMAP (TOTAL CONGESTION)"
                Layout.preferredWidth: 352; Layout.fillHeight: true; contentPadding: 12
                ColumnLayout {
                    anchors.fill: parent; spacing: 5
                    Text { text: "BEFORE RETUNE"; color: Theme.textPrimary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
                    EvidenceHeatmap { Layout.fillWidth: true; Layout.fillHeight: true; variant: 0 }
                    Text { text: "AFTER RETUNE (PROPOSED)"; color: Theme.textPrimary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
                    EvidenceHeatmap { Layout.fillWidth: true; Layout.fillHeight: true; variant: 2 }
                    Text { text: "■ <0.20    ■ 0.20–0.40    ■ 0.40–0.60    ■ 0.60–0.80    ■ >0.80"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: 8 }
                    Text { text: "□ HIGH CONGESTION ZONES  (Δ > +0.15)"; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: 8 }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
                Panel {
                    title: "AFFECTED CONSTRAINTS"; Layout.fillWidth: true; Layout.preferredHeight: 204; contentPadding: 12
                    ColumnLayout {
                        anchors.fill: parent; spacing: 0
                        RowLayout {
                            Layout.fillWidth: true; Layout.preferredHeight: 25
                            Text { text: "CONSTRAINT"; Layout.fillWidth: true; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                            Text { text: "CHANGE"; Layout.preferredWidth: 190; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                        }
                        Repeater {
                            model: appController.retuneModel
                            Rectangle {
                                required property string parameter; required property string current; required property string proposed
                                Layout.fillWidth: true; Layout.fillHeight: true; color: "transparent"
                                Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: Theme.borderSubtle }
                                RowLayout {
                                    anchors.fill: parent; spacing: 8
                                    ColumnLayout { Layout.fillWidth: true; spacing: 1
                                        Text { text: parameter; color: Theme.textPrimary; font.family: Theme.monoFont; font.pixelSize: Theme.caption }
                                        Text { text: "Placement"; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                                    }
                                    Text { text: current; color: Theme.textPrimary; font.family: Theme.monoFont; font.pixelSize: Theme.caption }
                                    Text { text: "→"; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.body }
                                    Text { text: proposed; color: Theme.textPrimary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 56 }
                                    StatusBadge { text: "RELAXED"; tone: "success" }
                                }
                            }
                        }
                    }
                }
                Panel {
                    title: "TIMING STATUS"; Layout.fillWidth: true; Layout.fillHeight: true; contentPadding: 12
                    ColumnLayout {
                        anchors.fill: parent; spacing: 6
                        Text { text: "UNRESOLVED"; color: Theme.fail; font.family: Theme.interfaceFont; font.pixelSize: 14; font.weight: Theme.weightMedium }
                        Text { text: "WNS is  -0.842 ns  after retune. Review required."; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
                        SectionHeader { text: "CRITICAL PATHS (TOP 3)"; Layout.fillWidth: true }
                        Repeater {
                            model: [
                                {n:"1", p:"u_cpu/ifu/inst_ram", v:"-0.842 ns"},
                                {n:"2", p:"u_cpu/lsu/data_array", v:"-0.787 ns"},
                                {n:"3", p:"u_cpu/fpu/decode", v:"-0.721 ns"}
                            ]
                            RowLayout {
                                required property var modelData; Layout.fillWidth: true
                                Text { text: modelData.n; color: Theme.textPrimary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 14 }
                                Text { text: modelData.p; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.fillWidth: true }
                                Text { text: modelData.v; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption }
                            }
                        }
                        Item { Layout.fillHeight: true }
                        Text { text: "VIEW ALL VIOLATIONS  →"; color: Theme.live; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; font.weight: Theme.weightMedium; Layout.alignment: Qt.AlignRight }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 181; spacing: 12
            Panel {
                Layout.fillWidth: true; Layout.fillHeight: true; contentPadding: 12
                RowLayout {
                    anchors.fill: parent; spacing: 16
                    ColumnLayout {
                        Layout.preferredWidth: 330; Layout.fillHeight: true; spacing: 10
                        SectionHeader { text: "RETUNE SUMMARY"; Layout.fillWidth: true }
                        Repeater {
                            model: [
                                {l:"REASON", v:"High congestion in 12 regions"}, {l:"SCOPE", v:"Global placement"},
                                {l:"CHANGES", v:"3 constraints relaxed"}, {l:"BOUNDED", v:"Yes  (within defined limits)"},
                                {l:"IMPACT", v:"Improved congestion, timing unresolved"}
                            ]
                            RowLayout {
                                required property var modelData; Layout.fillWidth: true
                                Text { text: modelData.l; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny; Layout.preferredWidth: 78 }
                                Text { text: modelData.v; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; Layout.fillWidth: true }
                            }
                        }
                    }
                    Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: Theme.border }
                    ColumnLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 0
                        SectionHeader { text: "HIGH CONGESTION REGIONS (IMPACTED)"; Layout.fillWidth: true }
                        RowLayout {
                            Layout.fillWidth: true; Layout.preferredHeight: 28; spacing: 0
                            Repeater {
                                model: [{t:"REGION ID",w:110},{t:"LOCATION",w:250},{t:"BEFORE",w:105},{t:"AFTER",w:100},{t:"DELTA",w:80}]
                                Text { required property var modelData; text: modelData.t; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny; Layout.preferredWidth: modelData.w }
                            }
                        }
                        Repeater {
                            model: appController.retuneRegionModel
                            Rectangle {
                                required property string region; required property string location; required property string before; required property string after; required property string delta
                                Layout.fillWidth: true; Layout.fillHeight: true; color: "transparent"
                                Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: Theme.borderSubtle }
                                RowLayout { anchors.fill: parent; spacing: 0
                                    Text { text: region; color: Theme.textPrimary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 110 }
                                    Text { text: location; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 250 }
                                    Text { text: before; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 105 }
                                    Text { text: after; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 100 }
                                    Text { text: delta + "   ↓"; color: Theme.pass; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 80 }
                                }
                            }
                        }
                    }
                }
            }
            Panel {
                title: "RECOMMENDATION"; Layout.preferredWidth: 400; Layout.fillHeight: true; contentPadding: 12
                ColumnLayout {
                    anchors.fill: parent; spacing: 8
                    Text { text: "Congestion has improved, but timing remains unresolved."; color: Theme.textPrimary; font.family: Theme.interfaceFont; font.pixelSize: Theme.body }
                    Text { text: "Proceeding without review may risk timing closure."; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
                    Item { Layout.fillHeight: true }
                    ActionButton { text: "SEND TO HUMAN REVIEW"; tone: "warning"; filled: true; implicitHeight: Theme.controlHeightLarge; Layout.fillWidth: true }
                    Text { text: "Notify physical design team for review and decision."; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny; Layout.alignment: Qt.AlignHCenter }
                }
            }
        }
    }
}
