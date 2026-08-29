import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."
import "../components"

ScrollView {
    id: scroll; clip: true; contentWidth: availableWidth; ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ColumnLayout {
        width: scroll.availableWidth; spacing: 12
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout { spacing: 4
                Text { text: "Runs History"; color: Theme.white; font.family: Theme.interfaceFont; font.pixelSize: Theme.title; font.weight: Theme.weightMedium }
                Text { text: "Browse and inspect past implementation runs."; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
            }
            Item { Layout.fillWidth: true }
            ActionButton { text: "↻  REFRESH" }
            ActionButton { text: "⇩  EXPORT CSV" }
        }
        Panel {
            Layout.fillWidth: true; Layout.preferredHeight: 104
            ColumnLayout { anchors.fill: parent; spacing: 9
                RowLayout { Layout.fillWidth: true; spacing: 12
                    Repeater {
                        model: [{l:"SEARCH",v:"Search runs…"},{l:"BRANCH",v:"main⌄"},{l:"RESULT",v:"All⌄"},{l:"DATE RANGE",v:"Last 14 days⌄"}]
                        Rectangle {
                            required property var modelData; Layout.fillWidth: true; Layout.preferredHeight: 38; color: Theme.input; border.color: Theme.border; border.width: 1
                            ColumnLayout { anchors.fill: parent; anchors.leftMargin: 10; spacing: 0
                                Text { text: modelData.l; color: Theme.textMuted; font.family: Theme.monoFont; font.pixelSize: 8 }
                                Text { text: modelData.v; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption }
                            }
                        }
                    }
                    ActionButton { text: "≋  MORE FILTERS"; Layout.preferredWidth: 130 }
                }
                Text { text: "Filters:   Branch: main  ×    Result: All  ×    Date: Last 14 days  ×    Clear all"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true; spacing: 0
            RowLayout {
                Layout.fillWidth: true; Layout.preferredHeight: 42; spacing: 0
                Repeater { model: [{t:"RUN",w:100},{t:"DESCRIPTION",w:190},{t:"COMMIT",w:90},{t:"STARTED",w:125},{t:"DURATION",w:80},{t:"STATUS",w:130},{t:"TERMINAL STAGE",w:150}]
                    Text { required property var modelData; text: modelData.t; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny; Layout.preferredWidth: modelData.w; Layout.fillWidth: modelData.t === "DESCRIPTION"; Layout.alignment: Qt.AlignBottom }
                }
                ColumnLayout {
                    Layout.preferredWidth: 410; spacing: 3
                    Text { text: "PPA OUTCOME"; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny; Layout.alignment: Qt.AlignHCenter }
                    RowLayout { spacing: 0
                        Repeater { model: [{t:"WNS (ns)",w:80},{t:"TNS (ns)",w:80},{t:"AREA (µm²)",w:90},{t:"POWER (mW)",w:80},{t:"DENSITY",w:80}]
                            Text { required property var modelData; text:modelData.t;color:Theme.textMuted;font.family:Theme.interfaceFont;font.pixelSize:Theme.tiny;Layout.preferredWidth:modelData.w;horizontalAlignment:Text.AlignHCenter }
                        }
                    }
                }
                Text { text: "ACTIONS"; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny; Layout.preferredWidth: 50; Layout.alignment: Qt.AlignBottom }
            }
            Repeater {
                model: appController.runModel
                Rectangle {
                    required property string runId; required property string kind; required property string description; required property string commit; required property string started; required property string duration; required property string status; required property string terminal; required property string wns; required property string tns; required property string area; required property string power; required property string density; required property string tone
                    Layout.fillWidth: true; Layout.preferredHeight: 62; color: runId === "run_042" ? Theme.surfaceHover : Theme.surface; border.color: Theme.border; border.width: 1
                    Rectangle { width: 3; height: parent.height; color: Theme.toneColor(tone) }
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: 12; spacing: 0
                        ColumnLayout { Layout.preferredWidth: 100; spacing: 3
                            Text { text: runId; color: Theme.textPrimary; font.family: Theme.monoFont; font.pixelSize: 13 }
                            StatusBadge { text: kind; tone: tone }
                        }
                        ColumnLayout { Layout.preferredWidth: 190; Layout.fillWidth: true; spacing: 3
                            Text { text: description; color: Theme.textPrimary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
                            Text { text: runId === "run_039" ? "Reference for current branch" : (runId === "run_040" ? "Aggressive multi-Vt swap" : (runId === "run_041" ? "Fix congestion hotspots" : "Mainline improvement")); color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                        }
                        Text { text: commit; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 90 }
                        Text { text: started; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 125 }
                        Text { text: duration; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 80 }
                        Text { text: "● " + status; color: status === "Running" ? Theme.pass : (status.indexOf("issues") >= 0 ? Theme.review : Theme.textSecondary); font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 130; wrapMode: Text.WordWrap }
                        Text { text: terminal; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 150 }
                        ColumnLayout { Layout.preferredWidth:80; spacing:2
                            Text { text:wns;color:wns.charAt(0)==="+"?Theme.pass:Theme.fail;font.family:Theme.monoFont;font.pixelSize:13;Layout.alignment:Qt.AlignHCenter }
                            MiniSparkline { visible:wns!=="—";lineColor:wns.charAt(0)==="+"?Theme.pass:Theme.fail;seed:runId.length+1;Layout.preferredWidth:62;Layout.preferredHeight:11;Layout.alignment:Qt.AlignHCenter }
                        }
                        ColumnLayout { Layout.preferredWidth:80; spacing:2
                            Text { text:tns;color:Theme.fail;font.family:Theme.monoFont;font.pixelSize:13;Layout.alignment:Qt.AlignHCenter }
                            MiniSparkline { visible:tns!=="—";lineColor:Theme.fail;seed:runId.length+3;Layout.preferredWidth:62;Layout.preferredHeight:11;Layout.alignment:Qt.AlignHCenter }
                        }
                        Text { text: area; color: Theme.live; font.family: Theme.monoFont; font.pixelSize: 13; Layout.preferredWidth: 90 }
                        Text { text: power; color: Theme.live; font.family: Theme.monoFont; font.pixelSize: 13; Layout.preferredWidth: 80 }
                        Text { text: density; color: Theme.live; font.family: Theme.monoFont; font.pixelSize: 13; Layout.preferredWidth: 80 }
                        Text { text: "•••"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: 50; horizontalAlignment: Text.AlignHCenter }
                    }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 280; spacing: 0
            Panel { title: "RUN PROGRESS"; Layout.preferredWidth: 320; Layout.fillHeight: true
                ColumnLayout { anchors.fill: parent; spacing: 8
                    Text { text: "STAGE 7 OF 14"; color: Theme.textMuted; font.family: Theme.monoFont; font.pixelSize: Theme.caption }
                    Text { text: "Power Plan & TAP"; color: Theme.white; font.family: Theme.monoFont; font.pixelSize: 15 }
                    Text { text: "Generating power grid and tap cells."; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption }
                    Rectangle { Layout.fillWidth: true; height: 3; color: Theme.borderSubtle; Rectangle { width: parent.width*.62; height: 3; color: Theme.live } }
                    Text { text: "ELAPSED        EST. REMAIN      EST. DONE\n02:47:16       01:12:43         May 22 11:11:46"; color: Theme.textPrimary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; lineHeight: 1.7 }
                    Item { Layout.fillHeight: true }
                    RowLayout { ActionButton{text:"Ⅱ PAUSE"} ActionButton{text:"■ STOP";tone:"danger"} ActionButton{text:"VIEW RUN →";tone:"success"} }
                }
            }
            Panel { title: "STAGE PROGRESS (7/14)"; Layout.preferredWidth: 220; Layout.fillHeight: true
                Text { anchors.fill: parent; text: "●  1  Import RTL\n●  2  Elaborate Design\n●  3  Synthesis\n●  4  STA Pre-CTS\n●  5  Floorplan\n◉  6  Power Plan & TAP\n○  7  Place\n○  8  CTS\n○  9  Post-CTS STA\n○ 10  Route\n○ 11  Signoff STA\n○ 12  DRC\n○ 13  LVS\n○ 14  GDS Packaging"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; lineHeight: 1.3 }
            }
            Panel { title: "KEY METRICS (LATEST)"; Layout.fillWidth: true; Layout.fillHeight: true
                GridLayout { anchors.fill: parent; columns: 3; rowSpacing: 8; columnSpacing: 8
                    Repeater { model: [{l:"WNS",v:"—",p:"PREV +0.092"},{l:"TNS",v:"—",p:"PREV -1.324"},{l:"AREA",v:"—",p:"PREV 12.38M"},{l:"POWER",v:"—",p:"PREV 125.7"},{l:"DENSITY",v:"—",p:"PREV 68.7%"},{l:"CONGESTION",v:"0.72",p:"PREV 0.72"}]
                        MetricCard { required property var modelData; label:modelData.l;value:modelData.v;context:modelData.p;tone:modelData.l==="CONGESTION"?"review":"neutral"; Layout.fillWidth:true;Layout.fillHeight:true }
                    }
                }
            }
            Panel { title: "RUN INFORMATION"; Layout.preferredWidth: 320; Layout.fillHeight: true
                ColumnLayout { anchors.fill: parent
                    Text { text: "Triggered by       push\n\nInitiated by       pd@company.com\n\nMachine            runner-07\n\nFlow config        default_v3.2\n\nTags               mainline  perf  power\n\nArtifacts          142 (1.2 GB)"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.fillWidth: true }
                    Item { Layout.fillHeight: true }
                    ActionButton { text: "VIEW ARTIFACTS  →"; Layout.fillWidth: true }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 150; spacing: 0
            Panel { title: "RUN NOTES"; Layout.fillWidth: true; Layout.fillHeight: true
                ColumnLayout { anchors.fill: parent; spacing: 9
                    Text { text: "May 22 08:11:03     Run started             Triggered by push to main (a1b2c3d)"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption }
                    Text { text: "May 22 09:02:41     Stage 5 completed      Floorplan finalized: utilization 67.1%"; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption }
                    Item { Layout.fillHeight: true }
                    Text { text: "VIEW ALL NOTES  →"; color: Theme.live; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; Layout.alignment: Qt.AlignRight }
                }
            }
            Panel { title: "AGENTS"; Layout.preferredWidth: 365; Layout.fillHeight: true
                GridLayout { anchors.fill: parent; columns: 2; rowSpacing: 10; columnSpacing: 24
                    Repeater { model: ["Claude","Skyline","Orchestrator","Place & Route"]
                        RowLayout { required property string modelData; Layout.fillWidth: true
                            Text { text:modelData;color:Theme.textPrimary;font.family:Theme.interfaceFont;font.pixelSize:Theme.body;Layout.fillWidth:true }
                            Rectangle { width:7;height:7;radius:4;color:Theme.pass }
                        }
                    }
                    Text { text:"VIEW AGENTS  →";color:Theme.live;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption;Layout.columnSpan:2;Layout.alignment:Qt.AlignRight }
                }
            }
            Panel { title: "NEXT ACTIONS"; Layout.preferredWidth: 400; Layout.fillHeight: true
                ColumnLayout { anchors.fill: parent; spacing: 8
                    Repeater { model: ["Review congestion after placement","Compare against run_039 baseline","Create checkpoint at next stage"]
                        RowLayout { required property string modelData; Layout.fillWidth:true
                            Text { text:"○";color:Theme.textSecondary;font.pixelSize:10 }
                            Text { text:modelData;color:Theme.textSecondary;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption;Layout.fillWidth:true }
                            Text { text:"›";color:Theme.textSecondary;font.family:Theme.interfaceFont;font.pixelSize:Theme.body }
                        }
                    }
                }
            }
        }
    }
}
