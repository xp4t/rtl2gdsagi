import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../components"

ScrollView {
    id: scroll
    clip: true; contentWidth: availableWidth
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ScrollBar.vertical.policy: ScrollBar.AsNeeded

    RowLayout {
        width: scroll.availableWidth; height: Math.max(scroll.availableHeight, 920); spacing: 12

        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12

            ColumnLayout {
                Layout.fillWidth: true; Layout.preferredHeight: 96; spacing: 6
                Text { text: "←  BACK TO RUNS HISTORY"; color: Theme.live; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; font.weight: Theme.weightMedium }
                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout { spacing: 4
                        RowLayout { spacing: 8
                            Text { text: "run_041"; color: Theme.white; font.family: Theme.monoFont; font.pixelSize: Theme.title }
                            StatusBadge { text: "RECOVERY"; tone: "purple" }
                        }
                        Text { text: "Route recovery   ·   Fix congestion hotspots"; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
                    }
                    Item { Layout.fillWidth: true }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 28
                    Repeater { model: ["OVERVIEW","DETAILS","ARTIFACTS","CONFIGURATION","METRICS","LOGS","DIFF"]
                        Text { required property string modelData; text:modelData;color:modelData==="OVERVIEW"?Theme.textPrimary:Theme.textMuted;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption;font.weight:modelData==="OVERVIEW"?Theme.weightMedium:Theme.weightRegular }
                    }
                    Item { Layout.fillWidth: true }
                }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.border }
            }

            Panel {
                title: "STAGE TIMELINE     11 of 14 stages completed"; Layout.fillWidth: true; Layout.preferredHeight: 134; contentPadding: 12
                ColumnLayout {
                    anchors.fill: parent; spacing: 4
                    RowLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 0
                        Repeater { model: appController.pipelineModel
                            PipelineStage { number:model.number;name:model.name;status:number<10?"pass":(number===10?"fail":"pending");Layout.fillWidth:true;last:number===14 }
                        }
                    }
                    RowLayout { spacing:18
                        Repeater { model:[{t:"● PASS",c:Theme.pass},{t:"● ACTIVE",c:Theme.review},{t:"● FAILED",c:Theme.fail},{t:"○ PENDING",c:Theme.textSecondary},{t:"ⓘ ISSUE",c:Theme.textSecondary}]
                            Text { required property var modelData;text:modelData.t;color:modelData.c;font.family:Theme.interfaceFont;font.pixelSize:Theme.tiny }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true; Layout.preferredHeight: 432; Layout.minimumHeight: 432; Layout.maximumHeight: 432; spacing: 12
                Panel {
                    title: "RUN SUMMARY"; Layout.preferredWidth: 280; Layout.fillHeight: true; contentPadding: 14
                    ColumnLayout { anchors.fill: parent; spacing: 12
                        Repeater { model:[
                            {l:"Branch",v:"main  (a1b2c3d)"},{l:"Flow",v:"default_v3.2"},{l:"Design",v:"chipcore_top"},
                            {l:"Initiated by",v:"pd@company.com"},{l:"Machine",v:"runner-07"},{l:"Started",v:"May 21 16:48:10"},
                            {l:"Duration",v:"00:58:33"},{l:"Status",v:"● Completed with issues"},{l:"Terminal stage",v:"Route   11"}
                        ]
                            RowLayout { required property var modelData;Layout.fillWidth:true
                                Text { text:modelData.l;color:Theme.textMuted;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption;Layout.preferredWidth:112 }
                                Text { text:modelData.v;color:modelData.l==="Status"?Theme.review:Theme.textSecondary;font.family:modelData.l==="Branch"||modelData.l==="Flow"||modelData.l==="Design"||modelData.l==="Started"||modelData.l==="Duration"?Theme.monoFont:Theme.interfaceFont;font.pixelSize:Theme.caption;Layout.fillWidth:true }
                            }
                        }
                    }
                }
                Panel {
                    title: "FAILURE EVIDENCE (ROUTE)"; Layout.fillWidth: true; Layout.fillHeight: true; contentPadding: 12
                    ColumnLayout {
                        anchors.fill: parent; spacing: 7
                        Text { text: "Routing congestion exceeds policy limits in multiple regions."; color: Theme.fail; font.family: Theme.interfaceFont; font.pixelSize: Theme.body; font.weight: Theme.weightMedium }
                        RowLayout {
                            Layout.fillWidth: true; Layout.preferredHeight: 112; spacing: 0
                            Repeater { model:[
                                {l:"CONGESTION (OVERFLOW)",v:"71.3%",s:"Limit ≤ 10%",p:"Peak 74.8%",t:"fail"},
                                {l:"WNS (ns)",v:"+0.018",s:"Limit ≥ 0.000",p:"Prev +0.024",t:"pass"},
                                {l:"TNS (ns)",v:"-0.642",s:"—",p:"Prev -0.512",t:"fail"},
                                {l:"ROUTED NETS",v:"89.7%",s:"Limit ≥ 95%",p:"Prev 91.2%",t:"review"}
                            ]
                                Rectangle { required property var modelData;Layout.fillWidth:true;Layout.fillHeight:true;color:Theme.surfaceRaised;border.color:Theme.border;border.width:1
                                    ColumnLayout { anchors.fill:parent;anchors.margins:10;spacing:5
                                        Text { text:modelData.l;color:Theme.textSecondary;font.family:Theme.interfaceFont;font.pixelSize:Theme.tiny }
                                        Text { text:modelData.v;color:Theme.toneColor(modelData.t);font.family:Theme.monoFont;font.pixelSize:18 }
                                        Text { text:modelData.s;color:Theme.textSecondary;font.family:Theme.interfaceFont;font.pixelSize:Theme.tiny }
                                        MiniSparkline { Layout.fillWidth:true;Layout.preferredHeight:14;lineColor:Theme.toneColor(modelData.t);seed:modelData.l.length }
                                        Text { text:modelData.p;color:Theme.textMuted;font.family:Theme.monoFont;font.pixelSize:Theme.tiny }
                                    }
                                }
                            }
                        }
                        SectionHeader { text: "CONGESTION HOTSPOTS (TOP 3)"; Layout.fillWidth: true }
                        RowLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
                            Item {
                                Layout.preferredWidth: 430; Layout.minimumWidth: 360; Layout.fillHeight: true
                                EvidenceHeatmap { anchors.fill: parent; variant: 8; showRegions: false; midColor: Theme.live; highColor: Theme.fail }
                                Repeater { model:[{x:.12,y:.25,n:"1"},{x:.48,y:.58,n:"3"},{x:.70,y:.14,n:"2"}]
                                    Rectangle { required property var modelData;x:parent.width*modelData.x;y:parent.height*modelData.y;width:52;height:48;color:"transparent";border.color:Theme.fail;border.width:2
                                        Rectangle { width:18;height:18;color:"#631B18";border.color:Theme.fail;border.width:1;anchors.left:parent.left;anchors.top:parent.top;anchors.margins:-6
                                            Text { anchors.centerIn:parent;text:modelData.n;color:Theme.white;font.family:Theme.monoFont;font.pixelSize:10 }
                                        }
                                    }
                                }
                            }
                            ColumnLayout {
                                Layout.preferredWidth: 230; Layout.fillHeight: true; spacing: 7
                                RowLayout { Layout.fillWidth:true;Repeater{model:[{t:"ID",w:34},{t:"AREA (µm²)",w:82},{t:"OVERFLOW",w:70},{t:"DETAIL",w:44}]
                                    Text{required property var modelData;text:modelData.t;color:Theme.textMuted;font.family:Theme.interfaceFont;font.pixelSize:Theme.tiny;Layout.preferredWidth:modelData.w}}
                                }
                                Repeater { model:[{i:"1",a:"1.28M",o:"178.6%"},{i:"2",a:"0.94M",o:"134.2%"},{i:"3",a:"0.61M",o:"102.7%"}]
                                    RowLayout { required property var modelData;Layout.fillWidth:true
                                        StatusBadge{text:modelData.i;tone:"danger";Layout.preferredWidth:24}
                                        Text{text:modelData.a;color:Theme.textSecondary;font.family:Theme.monoFont;font.pixelSize:Theme.caption;Layout.preferredWidth:76}
                                        Text{text:modelData.o;color:Theme.fail;font.family:Theme.monoFont;font.pixelSize:Theme.caption;Layout.preferredWidth:70}
                                        Text{text:"View";color:Theme.live;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption}
                                    }
                                }
                                Item { Layout.fillHeight:true }
                                SectionHeader { text:"OVERFLOW";Layout.fillWidth:true }
                                Text { text:"■ < 10%     ■ 10–20%     ■ 20–40%\n■ 40–80%    ■ > 80%";color:Theme.textSecondary;font.family:Theme.monoFont;font.pixelSize:Theme.tiny;lineHeight:1.5 }
                            }
                        }
                    }
                }
            }

            Panel {
                Layout.fillWidth: true; Layout.fillHeight: true; title: "VIOLATIONS SUMMARY"; contentPadding: 12
                RowLayout {
                    anchors.fill: parent; spacing: 18
                    ColumnLayout {
                        Layout.preferredWidth: 430; Layout.fillHeight: true; spacing: 9
                        RowLayout { Layout.fillWidth:true;Repeater{model:[{t:"VIOLATION TYPE",w:240},{t:"COUNT",w:80},{t:"SEVERITY",w:100}]
                            Text{required property var modelData;text:modelData.t;color:Theme.textMuted;font.family:Theme.interfaceFont;font.pixelSize:Theme.tiny;Layout.preferredWidth:modelData.w}}
                        }
                        Repeater { model:[{v:"Routing congestion overflow",c:"12",s:"●  High",t:"fail"},{v:"Min metal spacing",c:"3",s:"●  Medium",t:"review"},{v:"Via enclosure",c:"7",s:"●  Medium",t:"review"},{v:"Antenna ratio",c:"2",s:"●  Low",t:"pass"}]
                            RowLayout { required property var modelData;Layout.fillWidth:true;Layout.fillHeight:true
                                Text{text:modelData.v;color:Theme.textSecondary;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption;Layout.preferredWidth:240}
                                Text{text:modelData.c;color:Theme.textSecondary;font.family:Theme.monoFont;font.pixelSize:Theme.caption;Layout.preferredWidth:80}
                                Text{text:modelData.s;color:Theme.toneColor(modelData.t);font.family:Theme.interfaceFont;font.pixelSize:Theme.caption;Layout.preferredWidth:100}
                            }
                        }
                    }
                    Rectangle { Layout.preferredWidth:1;Layout.fillHeight:true;color:Theme.border }
                    ColumnLayout {
                        Layout.fillWidth:true;Layout.fillHeight:true;spacing:7
                        Text{text:"LATEST VIOLATIONS (ROUTE)";color:Theme.textMuted;font.family:Theme.interfaceFont;font.pixelSize:Theme.tiny;font.weight:Theme.weightMedium}
                        Text{text:"16:57:12   [CONGESTION] Overflow 178.6% in region (x: 1.2M, y: 3.8M)\n16:57:12   [CONGESTION] Overflow 134.2% in region (x: 8.4M, y: 2.1M)\n16:57:13   [CONGESTION] Overflow 102.7% in region (x: 4.6M, y: 7.3M)\n16:57:18   [DRC] MinMetalSpacing on net n456_789 (M2)\n16:57:21   [DRC] ViaEnclosure on net n12_345 (V12)";color:Theme.textSecondary;font.family:Theme.monoFont;font.pixelSize:Theme.caption;lineHeight:1.45}
                        Item{Layout.fillHeight:true}
                        Text{text:"VIEW FULL VIOLATION REPORT  →";color:Theme.live;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption;Layout.alignment:Qt.AlignRight}
                    }
                }
            }
        }

        Rectangle {
            Layout.preferredWidth: 336; Layout.fillHeight: true; color: Theme.surface; border.color: Theme.border; border.width: 1
            ColumnLayout {
                anchors.fill: parent; spacing: 0
                ColumnLayout {
                    Layout.fillWidth:true;Layout.preferredHeight:460;Layout.margins:16;spacing:12
                    SectionHeader{text:"ACTIONS";Layout.fillWidth:true}
                    Repeater { model:[
                        {h:"RESUME FROM ROUTE",d:"Resume flow from the route stage with\ncurrent configuration and fixes.",b:"RESUME FROM ROUTE  →",t:"warning"},
                        {h:"REPLAY FROM FLOORPLAN",d:"Replay flow from floorplan with the exact\noriginal configuration.",b:"REPLAY FROM FLOORPLAN  →",t:"active"},
                        {h:"CREATE BRANCH & EXPERIMENT",d:"Create a new branch from this run and\nexperiment with different fixes.",b:"CREATE BRANCH  →",t:"purple"}
                    ]
                        Rectangle { required property var modelData;Layout.fillWidth:true;Layout.fillHeight:true;color:Theme.surfaceRaised;border.color:Qt.darker(Theme.toneColor(modelData.t),1.6);border.width:1
                            ColumnLayout { anchors.fill:parent;anchors.margins:12;spacing:7
                                Text{text:modelData.h;color:Theme.toneColor(modelData.t);font.family:Theme.interfaceFont;font.pixelSize:Theme.body;font.weight:Theme.weightMedium}
                                Text{text:modelData.d;color:Theme.textSecondary;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption;lineHeight:1.3}
                                Item{Layout.fillHeight:true}
                                ActionButton{text:modelData.b;tone:modelData.t;Layout.fillWidth:true}
                            }
                        }
                    }
                }
                Rectangle{Layout.fillWidth:true;Layout.preferredHeight:1;color:Theme.border}
                ColumnLayout {
                    Layout.fillWidth:true;Layout.preferredHeight:250;Layout.margins:16;spacing:6
                    SectionHeader{text:"RETAINED CHECKPOINTS";Layout.fillWidth:true}
                    ListView { Layout.fillWidth:true;Layout.fillHeight:true;model:appController.checkpointModel;spacing:2;interactive:false
                        delegate:RowLayout { required property string stage;required property string timestamp;required property string size;width:ListView.view.width;height:31;spacing:7
                            Rectangle{width:12;height:12;radius:6;color:Theme.pass;Text{anchors.centerIn:parent;text:"✓";color:Theme.canvas;font.pixelSize:8}}
                            Text{text:stage;color:Theme.textPrimary;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption;Layout.fillWidth:true}
                            Text{text:timestamp;color:Theme.textMuted;font.family:Theme.monoFont;font.pixelSize:8}
                            Text{text:size;color:Theme.textSecondary;font.family:Theme.monoFont;font.pixelSize:8;Layout.preferredWidth:38;horizontalAlignment:Text.AlignRight}
                            Text{text:"⇩";color:Theme.textSecondary;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption}
                        }
                    }
                }
                Rectangle{Layout.fillWidth:true;Layout.preferredHeight:1;color:Theme.border}
                ColumnLayout { Layout.fillWidth:true;Layout.fillHeight:true;Layout.margins:16;spacing:12
                    SectionHeader{text:"RUN NOTES";Layout.fillWidth:true}
                    Text{text:"Auto-recovery triggered after congestion\nthreshold exceeded.";color:Theme.textSecondary;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption;lineHeight:1.45}
                    Item{Layout.fillHeight:true}
                }
            }
        }
    }
}
