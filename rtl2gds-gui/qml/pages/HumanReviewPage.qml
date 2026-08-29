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
        spacing: 12

        PipelineBand {
            Layout.fillWidth: true; Layout.preferredHeight: 126
            flowMode: true; showAction: false; stageTone: "fail"
        }

        Panel {
            Layout.fillWidth: true; Layout.preferredHeight: 94; contentPadding: 12
            RowLayout {
                anchors.fill: parent; spacing: 18
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 4
                    Text { text: "STAGE 7 OF 14   ›   HUMAN REVIEW"; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; font.weight: Theme.weightMedium }
                    Text { text: "Review placement escalation: run_042"; color: Theme.white; font.family: Theme.interfaceFont; font.pixelSize: Theme.title; font.weight: Theme.weightMedium }
                    Text { text: "Auto-retune proposes bounded adjustments to resolve congestion and timing violations."; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
                }
                ColumnLayout {
                    Layout.preferredWidth: 155; spacing: 5
                    Text { text: "REVIEW DUE IN"; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny; font.weight: Theme.weightMedium }
                    RowLayout { spacing: 7
                        Rectangle {
                            width: 14; height: 14; radius: 7
                            color: "transparent"; border.color: Theme.fail; border.width: 1
                            Rectangle { width: 1; height: 4; color: Theme.fail; anchors.horizontalCenter: parent.horizontalCenter; y: 3 }
                            Rectangle { width: 4; height: 1; color: Theme.fail; x: 7; y: 7 }
                        }
                        Text { text: "02:15:36"; color: Theme.fail; font.family: Theme.monoFont; font.pixelSize: 15 }
                    }
                    Text { text: "by May 22 10:15:36"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.tiny }
                }
                Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: Theme.border }
                ColumnLayout {
                    Layout.preferredWidth: 410; spacing: 7
                    Text { text: "ESCALATION REASON"; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny; font.weight: Theme.weightMedium }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "Congestion and timing violations persist\nafter 12 retune iterations."; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; lineHeight: 1.35; Layout.fillWidth: true }
                        Text { text: "View details  ↗"; color: Theme.live; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; font.weight: Theme.weightMedium; Layout.alignment: Qt.AlignBottom }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 678; spacing: 12

            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
                RowLayout {
                    Layout.fillWidth: true; Layout.preferredHeight: 345; Layout.minimumHeight: 345; Layout.maximumHeight: 345; spacing: 12

                    Panel {
                        title: "METRICS DELTA (CURRENT vs TARGET)"; Layout.fillWidth: true; Layout.fillHeight: true; contentPadding: 12
                        ColumnLayout {
                            anchors.fill: parent; spacing: 0
                            RowLayout {
                                Layout.fillWidth: true; Layout.preferredHeight: 28; spacing: 0
                                Repeater {
                                    model: [{t:"METRIC",w:130},{t:"CURRENT",w:80},{t:"Δ",w:65},{t:"TARGET",w:75},{t:"STATUS",w:45}]
                                    Text { required property var modelData; text: modelData.t; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny; Layout.preferredWidth: modelData.w }
                                }
                            }
                            Repeater {
                                model: [
                                    {m:"WNS (ns)", c:"-1.324", d:"+0.876", t:"≥ 0.000", s:"FAIL", st:"fail"},
                                    {m:"TNS (ns)", c:"-12.487", d:"+7.145", t:"≥ 0.000", s:"FAIL", st:"fail"},
                                    {m:"Congestion (%)", c:"68.7", d:"-8.2", t:"≤ 60.0", s:"FAIL", st:"fail"},
                                    {m:"Density (%)", c:"72.4", d:"-3.7", t:"60.0–70.0", s:"HIGH", st:"review"},
                                    {m:"Area (mm²)", c:"12.38M", d:"+0.18M", t:"≤ 12.50M", s:"HIGH", st:"review"}
                                ]
                                Rectangle {
                                    required property var modelData; Layout.fillWidth: true; Layout.preferredHeight: 47; color: "transparent"
                                    RowLayout {
                                        anchors.fill: parent; spacing: 0
                                        RowLayout { Layout.preferredWidth: 130; spacing: 5
                                            Text { text: modelData.m; color: Theme.textPrimary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 70 }
                                            Canvas { Layout.preferredWidth: 50; Layout.preferredHeight: 16; onPaint: { var c=getContext("2d");c.reset();c.strokeStyle=modelData.st==="fail"?Theme.fail:Theme.review;c.beginPath();for(var x=0;x<50;x+=7){var y=8+((x*5+modelData.m.length)%9)-4;x?c.lineTo(x,y):c.moveTo(x,y)}c.stroke() } }
                                        }
                                        Text { text: modelData.c; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 80 }
                                        Text { text: modelData.d; color: modelData.d.charAt(0)==="-"?Theme.pass:Theme.pass; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 65 }
                                        Text { text: modelData.t; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 75 }
                                        Text { text: modelData.s; color: Theme.toneColor(modelData.st); font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; font.weight: Theme.weightMedium; Layout.preferredWidth: 45 }
                                    }
                                }
                            }
                            Item { Layout.fillHeight: true }
                            Text { text: "All values compared to pre-retune baseline (iteration 0)."; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                        }
                    }

                    Panel {
                        title: "PROPOSED BOUNDED CHANGES"; Layout.fillWidth: true; Layout.fillHeight: true; contentPadding: 12
                        ColumnLayout {
                            anchors.fill: parent; spacing: 0
                            RowLayout {
                                Layout.fillWidth: true; Layout.preferredHeight: 28; spacing: 0
                                Repeater {
                                    model: [{t:"PARAMETER",w:110},{t:"CURRENT",w:70},{t:"PROPOSED",w:84},{t:"BOUNDS",w:90},{t:"Δ",w:40}]
                                    Text { required property var modelData; text: modelData.t; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny; Layout.preferredWidth: modelData.w }
                                }
                            }
                            Repeater {
                                model: [
                                    {p:"place_opt_effort",c:"high",n:"medium",b:"med–vhigh",d:"↓ 1",tone:"pass"},
                                    {p:"target_density",c:"0.70",n:"0.66",b:"0.60–0.75",d:"↓ 0.04",tone:"pass"},
                                    {p:"max_displacement",c:"0.20",n:"0.30",b:"0.10–0.30",d:"↑ 0.10",tone:"review"},
                                    {p:"congestion_opt",c:"aggressive",n:"very_aggr.",b:"default–v.agg",d:"↑ 1",tone:"review"},
                                    {p:"cell_padding (%)",c:"2.0",n:"2.5",b:"1.0–3.0",d:"↑ 0.5",tone:"review"}
                                ]
                                RowLayout {
                                    required property var modelData; Layout.fillWidth: true; Layout.preferredHeight: 43; spacing: 0
                                    Text { text: modelData.p; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 110 }
                                    Text { text: modelData.c; color: Theme.textPrimary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 70 }
                                    Text { text: modelData.n; color: Theme.live; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 84 }
                                    Text { text: modelData.b; color: Theme.textMuted; font.family: Theme.monoFont; font.pixelSize: Theme.tiny; Layout.preferredWidth: 90 }
                                    Text { text: modelData.d; color: Theme.toneColor(modelData.tone); font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 40 }
                                }
                            }
                            Item { Layout.fillHeight: true }
                            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.border }
                            Text { text: "Estimated impact: WNS +0.82 ns, Congestion -7.6%, Density -2.9%"; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; Layout.topMargin: 7 }
                            Text { text: "How are these estimated?  ↗"; color: Theme.live; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
                        }
                    }
                }

                Panel {
                    title: "PRIOR CONTEXT"; Layout.fillWidth: true; Layout.fillHeight: true; contentPadding: 12
                    RowLayout {
                        anchors.fill: parent; spacing: 12
                        Rectangle {
                            Layout.fillWidth: true; Layout.fillHeight: true; color: Theme.surfaceRaised; border.color: Theme.border; border.width: 1
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 12; spacing: 6
                                RowLayout { spacing: 24
                                    Text { text: "AUTO-RETUNE HISTORY"; color: Theme.textPrimary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; font.weight: Theme.weightMedium }
                                    Text { text: "PREVIOUS DECISIONS"; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
                                }
                                Rectangle { Layout.preferredWidth: 142; Layout.preferredHeight: 2; color: Theme.pass }
                                RowLayout {
                                    Layout.fillWidth: true; Layout.preferredHeight: 24; spacing: 0
                                    Repeater { model: [{t:"ITER",w:76},{t:"TIME",w:70},{t:"PARAMETER SET SUMMARY",w:168},{t:"RESULT (vs baseline)",w:160},{t:"DECISION",w:85}]
                                        Text { required property var modelData; text:modelData.t;color:Theme.textMuted;font.family:Theme.interfaceFont;font.pixelSize:Theme.tiny;Layout.preferredWidth:modelData.w }
                                    }
                                }
                                Repeater {
                                    model: [
                                        {i:"0 (baseline)",t:"08:11:03",p:"default",r:"—",d:"—",tone:"neutral"},
                                        {i:"1",t:"08:12:11",p:"effort=high, density=0.68",r:"WNS +0.12, Cong -1.1%",d:"AUTO-APPLIED",tone:"pass"},
                                        {i:"2",t:"08:14:32",p:"max_disp=0.22",r:"WNS +0.18, Cong -1.5%",d:"AUTO-APPLIED",tone:"pass"},
                                        {i:"3",t:"08:17:05",p:"congestion_opt=aggr",r:"WNS +0.21, Cong -2.0%",d:"AUTO-APPLIED",tone:"pass"},
                                        {i:"4",t:"08:20:18",p:"density=0.70",r:"WNS +0.28, Cong -2.6%",d:"AUTO-APPLIED",tone:"pass"},
                                        {i:"…",t:"…",p:"…",r:"…",d:"…",tone:"neutral"},
                                        {i:"12",t:"08:48:01",p:"current (see evidence)",r:"WNS +0.88, Cong -8.2%",d:"ESCALATED",tone:"review"}
                                    ]
                                    RowLayout {
                                        required property var modelData; Layout.fillWidth: true; Layout.fillHeight: true; spacing: 0
                                        Text { text:modelData.i;color:Theme.textSecondary;font.family:Theme.monoFont;font.pixelSize:Theme.tiny;Layout.preferredWidth:76 }
                                        Text { text:modelData.t;color:Theme.textSecondary;font.family:Theme.monoFont;font.pixelSize:Theme.tiny;Layout.preferredWidth:70 }
                                        Text { text:modelData.p;color:Theme.textSecondary;font.family:Theme.monoFont;font.pixelSize:Theme.tiny;Layout.preferredWidth:168 }
                                        Text { text:modelData.r;color:Theme.textSecondary;font.family:Theme.monoFont;font.pixelSize:Theme.tiny;Layout.preferredWidth:160 }
                                        StatusBadge { text:modelData.d;tone:modelData.tone }
                                    }
                                }
                                Item { Layout.fillHeight: true }
                                Text { text: "View full auto-retune history  ↗"; color: Theme.live; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
                            }
                        }
                        Rectangle {
                            Layout.preferredWidth: 255; Layout.fillHeight: true; color: Theme.surfaceRaised; border.color: Theme.border; border.width: 1
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 14; spacing: 10
                                SectionHeader { text: "LAST HUMAN REVIEW"; Layout.fillWidth: true }
                                Item { Layout.fillHeight: true }
                                Text { text: "—  N/A  —"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.body; Layout.alignment: Qt.AlignHCenter }
                                Text { text: "No prior human review for this run.\nThis is the first escalation."; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; horizontalAlignment: Text.AlignHCenter; lineHeight: 1.35; Layout.alignment: Qt.AlignHCenter }
                                Item { Layout.fillHeight: true }
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.preferredWidth: 441; Layout.fillHeight: true; spacing: 4

                Panel {
                    title: "EVIDENCE & ARTIFACTS"; Layout.fillWidth: true; Layout.preferredHeight: 362; Layout.minimumHeight: 362; Layout.maximumHeight: 362; contentPadding: 12
                    ColumnLayout {
                        anchors.fill: parent; spacing: 5
                        GridLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true; columns: 2; rowSpacing: 8; columnSpacing: 12
                            ColumnLayout {
                                Layout.fillWidth: true; Layout.fillHeight: true; spacing: 3
                                Text { text: "PLACEMENT HEATMAP"; color: Theme.textPrimary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; font.weight: Theme.weightMedium }
                                Text { text: "Current congestion"; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                                EvidenceHeatmap { Layout.fillWidth: true; Layout.fillHeight: true; variant: 3; showRegions: false }
                                Text { text: "Open viewer  ↗"; color: Theme.live; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true; Layout.fillHeight: true; spacing: 3
                                Text { text: "TIMING VIOLATIONS"; color: Theme.textPrimary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; font.weight: Theme.weightMedium }
                                Text { text: "Worst endpoints (WNS)"; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                                Repeater {
                                    model: [{v:"-1.324 ns",p:"path_56789"},{v:"-1.218 ns",p:"path_24567"},{v:"-1.103 ns",p:"path_13579"},{v:"-1.097 ns",p:"path_67890"}]
                                    RowLayout { required property var modelData; Layout.fillWidth: true
                                        Text { text:modelData.v;color:Theme.fail;font.family:Theme.monoFont;font.pixelSize:Theme.tiny;Layout.preferredWidth:72 }
                                        Text { text:modelData.p;color:Theme.textSecondary;font.family:Theme.monoFont;font.pixelSize:Theme.tiny;Layout.fillWidth:true }
                                    }
                                }
                                Item { Layout.fillHeight: true }
                                Text { text: "Open timing report  ↗"; color: Theme.live; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true; Layout.fillHeight: true; spacing: 3
                                Text { text: "DENSITY MAP"; color: Theme.textPrimary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; font.weight: Theme.weightMedium }
                                Text { text: "Current density"; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                                EvidenceHeatmap { Layout.fillWidth: true; Layout.fillHeight: true; variant: 6; showRegions: false; midColor: Theme.pass }
                                Text { text: "Open viewer  ↗"; color: Theme.live; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true; Layout.fillHeight: true; spacing: 3
                                Text { text: "CONGESTION HOTSPOTS"; color: Theme.textPrimary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; font.weight: Theme.weightMedium }
                                Text { text: "Top 5 hotspots"; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                                Repeater {
                                    model: [{n:"Region_12",v:.92,t:"fail"},{n:"Region_07",v:.88,t:"fail"},{n:"Region_03",v:.83,t:"review"},{n:"Region_21",v:.79,t:"review"},{n:"Region_16",v:.76,t:"pass"}]
                                    RowLayout { required property var modelData; Layout.fillWidth: true; spacing: 5
                                        Text { text:modelData.n;color:Theme.textSecondary;font.family:Theme.monoFont;font.pixelSize:Theme.tiny;Layout.preferredWidth:66 }
                                        Rectangle { Layout.fillWidth:true;Layout.preferredHeight:6;color:Theme.borderSubtle;Rectangle{width:parent.width*modelData.v;height:parent.height;color:Theme.toneColor(modelData.t)} }
                                        Text { text:Math.round(modelData.v*100)+"%";color:Theme.textSecondary;font.family:Theme.monoFont;font.pixelSize:Theme.tiny;Layout.preferredWidth:26 }
                                    }
                                }
                                Item { Layout.fillHeight: true }
                                Text { text: "Open congestion report  ↗"; color: Theme.live; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                            }
                        }
                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.border }
                        Text { text: "All artifacts generated at iteration 12 (pre-retune)."; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                    }
                }

                Panel {
                    title: "YOUR DECISION  (REQUIRED)"; Layout.fillWidth: true; Layout.fillHeight: true; contentPadding: 12
                    ColumnLayout {
                        anchors.fill: parent; spacing: 6
                        Text { text: "Review the proposed changes and evidence. Choose an action."; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
                        Repeater {
                            model: [
                                {h:"Approve proposed changes",d:"Proceed with the bounded adjustment as proposed."},
                                {h:"Reject and keep current",d:"Continue with current parameters without changes."},
                                {h:"Request different adjustment",d:"Specify alternative bounded changes."}
                            ]
                            RowLayout {
                                required property var modelData; required property int index; Layout.fillWidth: true; spacing: 8
                                Rectangle { Layout.preferredWidth:14;Layout.preferredHeight:14;radius:7;color:"transparent";border.color:index===0?Theme.live:Theme.textSecondary;border.width:1;Rectangle{visible:index===0;anchors.centerIn:parent;width:6;height:6;radius:3;color:Theme.live} }
                                ColumnLayout { Layout.fillWidth: true; spacing: 1
                                    Text { text:modelData.h;color:index===0?Theme.textPrimary:Theme.textSecondary;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption;font.weight:Theme.weightMedium }
                                    Text { text:modelData.d;color:Theme.textMuted;font.family:Theme.interfaceFont;font.pixelSize:Theme.tiny }
                                }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "REASON / NOTES  (required)"; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny; font.weight: Theme.weightMedium }
                            Item { Layout.fillWidth: true }
                            Text { text: "0 / 400"; color: Theme.textMuted; font.family: Theme.monoFont; font.pixelSize: Theme.tiny }
                        }
                        TextArea {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            placeholderText: "Provide rationale or notes for this decision…"
                            color: Theme.textPrimary; placeholderTextColor: Theme.textMuted
                            font.family: Theme.interfaceFont; font.pixelSize: Theme.caption
                            wrapMode: TextEdit.Wrap
                            background: Rectangle { color: Theme.input; border.color: Theme.border; border.width: 1 }
                        }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 8
                            ActionButton { text: "REJECT"; tone: "danger"; Layout.fillWidth: true }
                            ActionButton { text: "REQUEST CHANGE"; tone: "warning"; Layout.fillWidth: true }
                            ActionButton { text: "APPROVE & CONTINUE"; tone: "success"; Layout.fillWidth: true }
                        }
                    }
                }
            }
        }
    }
}
