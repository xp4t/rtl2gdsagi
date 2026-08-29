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

    ColumnLayout {
        width: scroll.availableWidth; spacing: 8

        ColumnLayout {
            Layout.fillWidth:true;Layout.preferredHeight:46;spacing:4
            RowLayout { spacing:8
                Text{text:"Strategy Sweep";color:Theme.white;font.family:Theme.interfaceFont;font.pixelSize:Theme.title;font.weight:Theme.weightMedium}
                StatusBadge{text:"BETA";tone:"neutral"}
            }
            Text{text:"Explore multiple implementation strategies and select the best candidate to promote.";color:Theme.textSecondary;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption}
        }

        RowLayout {
            Layout.fillWidth:true;Layout.preferredHeight:27;spacing:28
            Text{text:"SWEEP RESULTS";color:Theme.textPrimary;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption;font.weight:Theme.weightMedium}
            Text{text:"SWEEP CONFIG";color:Theme.textMuted;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption}
            Item{Layout.fillWidth:true}
        }

        RowLayout {
            Layout.fillWidth:true;Layout.preferredHeight:824;spacing:16

            ColumnLayout {
                Layout.fillWidth:true;Layout.fillHeight:true;spacing:12

                RowLayout {
                    Layout.fillWidth:true;Layout.preferredHeight:32;Layout.minimumHeight:32;Layout.maximumHeight:32;spacing:8
                    ActionButton{text:"FILTER";Layout.preferredWidth:48}
                    TextField {
                        Layout.preferredWidth:280;Layout.fillHeight:true;placeholderText:"Search strategies…"
                        color:Theme.textPrimary;placeholderTextColor:Theme.textMuted;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption;leftPadding:12
                        background:Rectangle{color:Theme.input;border.color:Theme.border;border.width:1}
                    }
                    Item{Layout.fillWidth:true}
                    Text{text:"4 strategies";color:Theme.textSecondary;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption}
                    ActionButton{text:"EDIT SWEEP";Layout.preferredWidth:112}
                    ActionButton{text:"SETTINGS";Layout.preferredWidth:64}
                }

                Panel {
                    title:"STRATEGY COMPARISON";Layout.fillWidth:true;Layout.preferredHeight:300;Layout.minimumHeight:300;Layout.maximumHeight:300;contentPadding:0
                    ColumnLayout {
                        anchors.fill:parent;spacing:0
                        RowLayout {
                            Layout.fillWidth:true;Layout.preferredHeight:45;Layout.leftMargin:12;spacing:0
                            Repeater{model:[{t:"STRATEGY",w:145},{t:"FOCUS",w:75},{t:"WNS (ns)",w:72},{t:"TNS (ns)",w:72},{t:"AREA (µm²)",w:84},{t:"POWER (mW)",w:84},{t:"CONGESTION",w:88},{t:"RUNTIME",w:80},{t:"CONSTRAINT\nVIOLATIONS",w:88},{t:"STATUS",w:126},{t:"ACTIONS",w:64}]
                                Text{required property var modelData;text:modelData.t;color:Theme.textSecondary;font.family:Theme.interfaceFont;font.pixelSize:Theme.tiny;Layout.preferredWidth:modelData.w;horizontalAlignment:Text.AlignHCenter;wrapMode:Text.WordWrap}
                            }
                        }
                        Repeater {
                            model:appController.strategyModel
                            Rectangle {
                                required property string name;required property string strategyFocus;required property string wns;required property string tns;required property string area;required property string power;required property string congestion;required property string runtime;required property string violations;required property string completed
                                Layout.fillWidth:true;Layout.fillHeight:true;color:name==="sweep_a"?Theme.surfaceHover:"transparent";border.color:Theme.borderSubtle;border.width:1
                                RowLayout {
                                    anchors.fill:parent;anchors.leftMargin:12;spacing:0
                                    RowLayout { Layout.preferredWidth:145;spacing:8
                                        Rectangle{width:14;height:14;radius:7;color:"transparent";border.color:name==="sweep_a"?Theme.live:Theme.textSecondary;border.width:1;Rectangle{visible:name==="sweep_a";anchors.centerIn:parent;width:6;height:6;radius:3;color:Theme.live}}
                                        ColumnLayout { spacing:2
                                            Text{text:name;color:Theme.textPrimary;font.family:Theme.monoFont;font.pixelSize:Theme.body}
                                            Text{text:strategyFocus;color:Theme.textMuted;font.family:Theme.interfaceFont;font.pixelSize:Theme.tiny}
                                        }
                                    }
                                    Item { Layout.preferredWidth:75;Layout.fillHeight:true
                                        RowLayout{anchors.centerIn:parent;spacing:3
                                            Repeater{model:[.45,.86,.61,.72,.54];Rectangle{required property real modelData;required property int index;width:5;height:22*modelData;color:index===4?Theme.live:Theme.textMuted}}
                                        }
                                    }
                                    Text{text:wns;color:wns.charAt(0)==="+"?Theme.pass:Theme.fail;font.family:Theme.monoFont;font.pixelSize:13;Layout.preferredWidth:72;horizontalAlignment:Text.AlignHCenter}
                                    Text{text:tns;color:Theme.fail;font.family:Theme.monoFont;font.pixelSize:13;Layout.preferredWidth:72;horizontalAlignment:Text.AlignHCenter}
                                    Text{text:area;color:name==="sweep_c"?Theme.pass:(name==="sweep_b"?Theme.fail:Theme.live);font.family:Theme.monoFont;font.pixelSize:13;Layout.preferredWidth:84;horizontalAlignment:Text.AlignHCenter}
                                    Text{text:power;color:name==="sweep_d"?Theme.pass:(name==="sweep_b"?Theme.fail:Theme.live);font.family:Theme.monoFont;font.pixelSize:13;Layout.preferredWidth:84;horizontalAlignment:Text.AlignHCenter}
                                    ColumnLayout{Layout.preferredWidth:88;spacing:2
                                        Text{text:congestion;color:name==="sweep_c"?Theme.pass:Theme.review;font.family:Theme.monoFont;font.pixelSize:Theme.body;Layout.alignment:Qt.AlignHCenter}
                                        MiniSparkline{lineColor:name==="sweep_c"?Theme.pass:Theme.review;seed:name.length;Layout.preferredWidth:58;Layout.preferredHeight:10;Layout.alignment:Qt.AlignHCenter}
                                    }
                                    Text{text:runtime;color:Theme.textSecondary;font.family:Theme.monoFont;font.pixelSize:Theme.caption;Layout.preferredWidth:80;horizontalAlignment:Text.AlignHCenter}
                                    Text{text:violations;color:violations==="0"?Theme.textPrimary:Theme.fail;font.family:Theme.monoFont;font.pixelSize:Theme.body;Layout.preferredWidth:88;horizontalAlignment:Text.AlignHCenter}
                                    ColumnLayout{Layout.preferredWidth:126;spacing:2
                                        Text{text:"●  Completed";color:Theme.pass;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption}
                                        Text{text:completed;color:Theme.textMuted;font.family:Theme.monoFont;font.pixelSize:Theme.tiny}
                                    }
                                    RowLayout{Layout.preferredWidth:64;spacing:6
                                        Rectangle{width:28;height:28;color:"transparent";border.color:Theme.border;border.width:1;Canvas{anchors.centerIn:parent;width:12;height:12;onPaint:{var c=getContext("2d");c.reset();c.strokeStyle=Theme.textSecondary;c.beginPath();c.moveTo(3,2);c.lineTo(10,6);c.lineTo(3,10);c.closePath();c.stroke()}}}
                                        Rectangle{width:28;height:28;color:"transparent";border.color:Theme.border;border.width:1;Column{anchors.centerIn:parent;spacing:2;Repeater{model:3;Rectangle{width:2;height:2;radius:1;color:Theme.textSecondary}}}}
                                    }
                                }
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth:true;Layout.preferredHeight:382;Layout.minimumHeight:382;Layout.maximumHeight:382;spacing:0

                    Panel {
                        title:"METRIC RADAR (normalized)";Layout.preferredWidth:310;Layout.fillHeight:true;contentPadding:12
                        ColumnLayout {
                            anchors.fill:parent;spacing:5
                            RowLayout{spacing:9
                                Repeater{model:[{n:"sweep_a",c:Theme.live},{n:"sweep_b",c:Theme.fail},{n:"sweep_c",c:Theme.pass},{n:"sweep_d",c:Theme.review}]
                                    RowLayout{required property var modelData;spacing:4;Rectangle{width:7;height:7;radius:4;color:modelData.c}Text{text:modelData.n;color:Theme.textSecondary;font.family:Theme.interfaceFont;font.pixelSize:8}}
                                }
                            }
                            Canvas {
                                Layout.fillWidth:true;Layout.fillHeight:true
                                onPaint:{
                                    var c=getContext("2d"),cx=width/2,cy=height/2+4,r=Math.min(width,height)*.34
                                    c.reset();c.lineWidth=1;c.font="9px 'Fira Sans'";c.textAlign="center";c.textBaseline="middle"
                                    var labels=["WNS","TNS","AREA","POWER","CONGESTION","RUNTIME\n(inv)"]
                                    for(var k=1;k<=4;k++){c.strokeStyle=Theme.border;c.beginPath();for(var i=0;i<6;i++){var a=-Math.PI/2+i*Math.PI/3,x=cx+Math.cos(a)*r*k/4,y=cy+Math.sin(a)*r*k/4;i?c.lineTo(x,y):c.moveTo(x,y)}c.closePath();c.stroke()}
                                    c.fillStyle=Theme.textSecondary;for(var l=0;l<6;l++){var la=-Math.PI/2+l*Math.PI/3;c.fillText(labels[l],cx+Math.cos(la)*(r+18),cy+Math.sin(la)*(r+14))}
                                    var colors=[Theme.live,Theme.fail,Theme.pass,Theme.review]
                                    for(var s=0;s<4;s++){c.strokeStyle=colors[s];c.beginPath();for(var j=0;j<6;j++){var aa=-Math.PI/2+j*Math.PI/3,rr=r*(.58+((s*5+j*3)%7)/18),xx=cx+Math.cos(aa)*rr,yy=cy+Math.sin(aa)*rr;j?c.lineTo(xx,yy):c.moveTo(xx,yy)}c.closePath();c.stroke()}
                                    c.fillStyle=Theme.textMuted;c.font="8px 'Fira Code'";for(var q=1;q<=4;q++)c.fillText((q*.25).toFixed(2),cx+6,cy-r*q/4)
                                }
                                onWidthChanged:requestPaint();onHeightChanged:requestPaint()
                            }
                        }
                    }

                    Panel {
                        title:"METRIC TRENDS (normalized)";Layout.fillWidth:true;Layout.fillHeight:true;contentPadding:8
                        GridLayout {
                            anchors.fill:parent;columns:7;rowSpacing:0;columnSpacing:0
                            Item{Layout.preferredWidth:58;Layout.preferredHeight:32}
                            Repeater{model:["WNS (↑)","TNS (↓)","AREA (↓)","POWER (↓)","CONGESTION (↓)","RUNTIME (↓)"]
                                Text{required property string modelData;text:modelData;color:Theme.textSecondary;font.family:Theme.interfaceFont;font.pixelSize:8;Layout.fillWidth:true;horizontalAlignment:Text.AlignHCenter}
                            }
                            Repeater { model:4
                                RowLayout {
                                    required property int index;Layout.columnSpan:7;Layout.fillWidth:true;Layout.fillHeight:true;spacing:0
                                    property color rowColor:[Theme.live,Theme.fail,Theme.pass,Theme.review][index]
                                    Text{text:"sweep_"+String.fromCharCode(97+index);color:parent.rowColor;font.family:Theme.monoFont;font.pixelSize:Theme.tiny;Layout.preferredWidth:58}
                                    Repeater{model:6
                                        Rectangle{required property int index;Layout.fillWidth:true;Layout.fillHeight:true;color:"transparent";border.color:Theme.borderSubtle;border.width:1
                                            MiniSparkline{anchors.centerIn:parent;width:Math.max(34,parent.width-8);height:18;lineColor:parent.parent.rowColor;seed:index*7+parent.parent.index*3+1}
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Panel {
                        title:"SWEEP INSIGHTS";Layout.preferredWidth:260;Layout.fillHeight:true;contentPadding:12
                        ColumnLayout { anchors.fill:parent;spacing:14
                            Repeater{model:[
                                {h:"sweep_b achieves the best timing",d:"WNS improved by +213% vs. baseline",t:"active"},
                                {h:"sweep_c has the lowest congestion and area",d:"Ideal if routability is the priority",t:"success"},
                                {h:"sweep_d delivers the lowest power",d:"14.9% lower power vs. baseline",t:"warning"},
                                {h:"All strategies meet the constraint policy",d:"No blocking violations detected",t:"success"}
                            ]
                                RowLayout{required property var modelData;Layout.fillWidth:true;spacing:9
                                    Rectangle{width:18;height:18;radius:9;color:"transparent";border.color:Theme.toneColor(modelData.t);border.width:1;Rectangle{anchors.centerIn:parent;width:5;height:5;radius:3;color:Theme.toneColor(modelData.t)}}
                                    ColumnLayout{Layout.fillWidth:true;spacing:2
                                        Text{text:modelData.h;color:Theme.textPrimary;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption;font.weight:Theme.weightMedium;wrapMode:Text.WordWrap;Layout.fillWidth:true}
                                        Text{text:modelData.d;color:Theme.textMuted;font.family:Theme.interfaceFont;font.pixelSize:Theme.tiny;wrapMode:Text.WordWrap;Layout.fillWidth:true}
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth:true;Layout.preferredHeight:62;Layout.minimumHeight:62;Layout.maximumHeight:62;color:Theme.surface;border.color:Theme.border;border.width:1
                    RowLayout { anchors.fill:parent;anchors.leftMargin:16;anchors.rightMargin:16;spacing:12
                        Text{text:"Select a strategy to view details or take action.";color:Theme.textMuted;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption;Layout.fillWidth:true}
                        ActionButton{text:"VIEW DETAILS";Layout.preferredWidth:106}
                        ActionButton{text:"REPLAY";tone:"active";Layout.preferredWidth:90}
                        ActionButton{text:"PROMOTE";tone:"success";Layout.preferredWidth:102}
                        ActionButton{text:"COMPARE";Layout.preferredWidth:102}
                    }
                }
            }

            Panel {
                title:"SWEEP SUMMARY";Layout.preferredWidth:265;Layout.fillHeight:true;contentPadding:14
                ColumnLayout {
                    anchors.fill:parent;spacing:10
                    Repeater{model:[
                        {l:"SWEEP ID",v:"sweep_007",t:"neutral"},{l:"STATUS",v:"●  Completed",t:"pass"},{l:"STARTED",v:"May 22 05:12:41",t:"neutral"},{l:"COMPLETED",v:"May 22 08:29:10",t:"neutral"},{l:"DURATION",v:"03:16:29",t:"neutral"},{l:"STRATEGIES",v:"4",t:"neutral"},{l:"CONSTRAINT SET",v:"default_v1.2",t:"neutral"},{l:"DESIGN",v:"chipcore_cpu",t:"neutral"},{l:"TOP MODULE",v:"chipcore_top",t:"neutral"},{l:"TARGET PVT",v:"SS_0P72V_125C",t:"neutral"}
                    ]
                        RowLayout{required property var modelData;Layout.fillWidth:true
                            Text{text:modelData.l;color:Theme.textMuted;font.family:Theme.interfaceFont;font.pixelSize:Theme.tiny;Layout.fillWidth:true}
                            Text{text:modelData.v;color:modelData.t==="pass"?Theme.pass:Theme.textPrimary;font.family:Theme.monoFont;font.pixelSize:Theme.caption}
                        }
                    }
                    Rectangle{Layout.fillWidth:true;Layout.preferredHeight:1;color:Theme.border;Layout.topMargin:8}
                    SectionHeader{text:"SELECTION";Layout.fillWidth:true}
                    Text{text:"SELECTED STRATEGY";color:Theme.textMuted;font.family:Theme.interfaceFont;font.pixelSize:Theme.tiny}
                    Text{text:"sweep_a";color:Theme.live;font.family:Theme.monoFont;font.pixelSize:Theme.caption;Layout.alignment:Qt.AlignRight}
                    Text{text:"REASON";color:Theme.textMuted;font.family:Theme.interfaceFont;font.pixelSize:Theme.tiny}
                    Text{text:"Balanced PPA and runtime";color:Theme.textPrimary;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption}
                    Text{text:"SELECTED BY          pd@chipdesign.io\nSELECTED AT          May 22 08:29:10";color:Theme.textSecondary;font.family:Theme.monoFont;font.pixelSize:Theme.caption;lineHeight:1.6}
                    ActionButton{text:"LOCK SELECTION";tone:"success";Layout.fillWidth:true}
                    Item{Layout.fillHeight:true}
                    Rectangle{Layout.fillWidth:true;Layout.preferredHeight:1;color:Theme.border}
                    SectionHeader{text:"ARTIFACTS";Layout.fillWidth:true}
                    Text{text:"Sweep report\nsweep_007.html          18.6 MB\n\nRaw metrics (JSON)\nsweep_007.json           1.2 MB";color:Theme.textSecondary;font.family:Theme.monoFont;font.pixelSize:Theme.caption;lineHeight:1.45}
                    Text{text:"VIEW ALL ARTIFACTS  →";color:Theme.live;font.family:Theme.interfaceFont;font.pixelSize:Theme.caption;Layout.alignment:Qt.AlignRight}
                }
            }
        }
    }
}
