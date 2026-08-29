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
        width: scroll.availableWidth; spacing: 42

        ColumnLayout {
            Layout.fillWidth: true; Layout.minimumWidth: 720; spacing: 14

            ColumnLayout {
                Layout.fillWidth: true; Layout.preferredHeight: 60; spacing: 5
                Text { text: "Runs   /   New Run"; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
                Text { text: "Define New Run"; color: Theme.white; font.family: Theme.interfaceFont; font.pixelSize: Theme.title; font.weight: Theme.weightMedium }
                Text { text: "Create a bounded, reproducible RTL-to-GDS implementation run."; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
            }

            Item {
                Layout.fillWidth: true; Layout.preferredHeight: 60
                Rectangle { x: parent.width*.055; y: 13; width: parent.width*.89; height: 1; color: Theme.textMuted }
                Rectangle { x: parent.width*.055; y: 13; width: parent.width*.30; height: 1; color: Theme.pass }
                Repeater {
                    model: [{n:"1",t:"Run Setup",a:true},{n:"2",t:"Flow Options",a:false},{n:"3",t:"Review & Validate",a:false},{n:"4",t:"Queue",a:false}]
                    Item {
                        required property var modelData; required property int index
                        x: 50 + index * (parent.width - 100) / 3 - 12; width: 24; height: parent.height
                        Rectangle { width:24;height:24;radius:12;color:Theme.canvas;border.color:modelData.a?Theme.pass:Theme.textMuted;border.width:1
                            Text{anchors.centerIn:parent;text:modelData.n;color:modelData.a?Theme.pass:Theme.textSecondary;font.family:Theme.monoFont;font.pixelSize:Theme.caption}
                        }
                        Text { anchors.top:parent.top;anchors.topMargin:34;anchors.horizontalCenter:parent.horizontalCenter;text:modelData.t;color:modelData.a?Theme.textPrimary:Theme.textSecondary;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption;wrapMode:Text.NoWrap }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true; Layout.preferredHeight: 126; spacing: 8
                SectionHeader { text: "BASIC INFORMATION"; Layout.fillWidth: true }
                RowLayout { Layout.fillWidth: true; Layout.fillHeight: true; spacing: 34
                    FormField { label:"Run Name *";value:"chipcore_cpu_run_043";helper:"Unique name for this implementation run.";Layout.preferredWidth:432;Layout.fillHeight:true }
                    FormField { label:"Run Description";value:"Initial implementation with balanced effort targeting 500 MHz\nfor chipcore_cpu.";helper:"68 / 200";multiline:true;Layout.fillWidth:true;Layout.fillHeight:true }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true; Layout.preferredHeight: 113; spacing: 8
                SectionHeader { text: "DESIGN SOURCE"; Layout.fillWidth: true }
                RowLayout { Layout.fillWidth: true; Layout.fillHeight: true; spacing: 34
                    FormField { label:"RTL Revision *";value:"main@a1b2c3d";helper:"Committed 2h ago by jdoe";approved:true;Layout.fillWidth:true;Layout.fillHeight:true }
                    FormField { label:"Top Module *";value:"chipcore_top";helper:"Hierarchy root for implementation.";dropdown:true;Layout.fillWidth:true;Layout.fillHeight:true }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true; Layout.preferredHeight: 113; spacing: 8
                SectionHeader { text: "CONFIGURATION"; Layout.fillWidth: true }
                RowLayout { Layout.fillWidth: true; Layout.fillHeight: true; spacing: 34
                    FormField { label:"Configuration Profile *";value:"cpu_high_performance_v2";helper:"Approved  ·  Updated 1d ago";approved:true;dropdown:true;Layout.fillWidth:true;Layout.fillHeight:true }
                    FormField { label:"PDK Release *";value:"tsmc_n5_1p9m_2024q1";helper:"Production  ·  Q1 2024";approved:true;dropdown:true;Layout.fillWidth:true;Layout.fillHeight:true }
                    FormField { label:"Flow Variant";value:"14-stage (Default)";helper:"Standard implementation flow.";dropdown:true;Layout.fillWidth:true;Layout.fillHeight:true }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true; Layout.preferredHeight: 113; spacing: 8
                SectionHeader { text: "PERFORMANCE TARGETS"; Layout.fillWidth: true }
                RowLayout { Layout.fillWidth: true; Layout.fillHeight: true; spacing: 34
                    FormField { label:"Target Clock (MHz) *";value:"500";suffix:"MHz";helper:"Expected period: 2.000 ns";Layout.fillWidth:true;Layout.fillHeight:true }
                    FormField { label:"Utilization Target (%) *";value:"70";suffix:"%";helper:"Target core area utilization.";Layout.fillWidth:true;Layout.fillHeight:true }
                    FormField { label:"Effort Preset *";value:"Balanced";helper:"Balances runtime and result quality.";dropdown:true;Layout.fillWidth:true;Layout.fillHeight:true }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true; Layout.preferredHeight: 113; spacing: 8
                SectionHeader { text: "RESOURCE LIMITS"; Layout.fillWidth: true }
                RowLayout { Layout.fillWidth: true; Layout.fillHeight: true; spacing: 34
                    FormField { label:"CPU Cores";value:"64";helper:"Max concurrent CPU cores.";Layout.fillWidth:true;Layout.fillHeight:true }
                    FormField { label:"Memory Limit";value:"256";suffix:"GB";helper:"Maximum RAM allocation.";Layout.fillWidth:true;Layout.fillHeight:true }
                    FormField { label:"Walltime Limit";value:"48";suffix:"h";helper:"Maximum allowed run time.";Layout.fillWidth:true;Layout.fillHeight:true }
                }
            }

            RowLayout {
                Layout.fillWidth: true; Layout.preferredHeight: Theme.controlHeightLarge
                ActionButton { text: "CANCEL"; implicitHeight: Theme.controlHeightLarge; Layout.preferredWidth: 108 }
                Item { Layout.fillWidth: true }
                ActionButton { text: "CONTINUE TO REVIEW  →"; tone: "success"; filled: true; implicitHeight: Theme.controlHeightLarge; Layout.preferredWidth: 226 }
            }

            Panel {
                Layout.fillWidth: true; Layout.preferredHeight: 74; contentPadding: 14
                RowLayout { anchors.fill: parent; spacing: 14
                    Rectangle { width:18;height:18;radius:9;color:"transparent";border.color:Theme.pass;border.width:1
                        Text{anchors.centerIn:parent;text:"✓";color:Theme.pass;font.pixelSize:11}
                    }
                    ColumnLayout { spacing: 4
                        Text { text: "All required inputs are valid"; color: Theme.pass; font.family: Theme.interfaceFont; font.pixelSize: Theme.body; font.weight: Theme.weightMedium }
                        Text { text: "You can continue to review your run configuration."; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
                    }
                }
            }
        }

        Panel {
            title: "RUN SUMMARY"; Layout.preferredWidth: 371; Layout.preferredHeight: 824; Layout.alignment: Qt.AlignTop; contentPadding: 14
            ColumnLayout {
                anchors.fill: parent; spacing: 13
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 80; color: Theme.surfaceRaised; border.color: Theme.borderSubtle; border.width: 1
                    ColumnLayout { anchors.fill:parent;anchors.margins:14;spacing:7
                        Text{text:"chipcore_cpu_run_043";color:Theme.white;font.family:Theme.monoFont;font.pixelSize:14}
                        Text{text:"●  Ready to Review";color:Theme.pass;font.family:Theme.interfaceFont;font.pixelSize:Theme.body}
                    }
                }
                Repeater { model:[
                    {l:"RTL Revision",v:"main@a1b2c3d",s:"Approved",t:"pass"},{l:"Top Module",v:"chipcore_top",s:"",t:"neutral"},
                    {l:"Configuration Profile",v:"cpu_high_performance_v2",s:"Approved",t:"pass"},{l:"PDK Release",v:"tsmc_n5_1p9m_2024q1",s:"Production",t:"pass"},
                    {l:"Target Clock",v:"500 MHz\nExpected period: 2.000 ns",s:"",t:"neutral"},{l:"Utilization Target",v:"70 %",s:"",t:"neutral"},
                    {l:"Effort Preset",v:"Balanced",s:"",t:"neutral"},{l:"CPU Cores",v:"64",s:"",t:"neutral"},{l:"Memory Limit",v:"256 GB",s:"",t:"neutral"},{l:"Walltime Limit",v:"48 h",s:"",t:"neutral"}
                ]
                    ColumnLayout { required property var modelData;Layout.fillWidth:true;spacing:3
                        Text{text:modelData.l;color:Theme.textMuted;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption}
                        RowLayout { Layout.fillWidth:true
                            Text{text:modelData.v;color:Theme.textPrimary;font.family:modelData.l==="Top Module"||modelData.l==="RTL Revision"||modelData.l==="Configuration Profile"||modelData.l==="PDK Release"?Theme.monoFont:Theme.interfaceFont;font.pixelSize:Theme.caption;lineHeight:1.3;Layout.fillWidth:true}
                            Text{visible:modelData.s.length>0;text:modelData.s;color:Theme.toneColor(modelData.t);font.family:Theme.interfaceFont;font.pixelSize:Theme.caption}
                        }
                    }
                }
                Item { Layout.fillHeight: true }
                Rectangle {
                    Layout.fillWidth:true;Layout.preferredHeight:78;color:"transparent";border.color:Theme.border;border.width:1
                    ColumnLayout { anchors.fill:parent;anchors.margins:14
                        RowLayout { Layout.fillWidth:true
                            Text{text:"Estimated Runtime";color:Theme.textPrimary;font.family:Theme.interfaceFont;font.pixelSize:Theme.body;Layout.fillWidth:true}
                            Text{text:"18h – 28h";color:Theme.review;font.family:Theme.monoFont;font.pixelSize:18}
                        }
                        Text{text:"Based on similar runs with this configuration.";color:Theme.textSecondary;font.family:Theme.interfaceFont;font.pixelSize:Theme.tiny}
                    }
                }
            }
        }
    }
}
