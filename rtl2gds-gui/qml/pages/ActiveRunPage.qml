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
        height: Math.max(implicitHeight, scroll.availableHeight)
        spacing: Theme.spacingLg

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 122
            ColumnLayout {
                anchors.fill: parent
                spacing: 6
                SectionHeader { text: "14-STAGE RTL-TO-GDS FLOW"; Layout.fillWidth: true }
                RowLayout {
                    Layout.fillWidth: true; spacing: 0
                    Repeater {
                        model: appController.pipelineModel
                        delegate: PipelineStage {
                            number: model.number
                            name: model.name
                            status: model.status
                            Layout.fillWidth: true
                            Layout.preferredWidth: 70
                            last: number === 14
                        }
                    }
                }
                RowLayout {
                    spacing: 18
                    Repeater {
                        model: [{t: "● PASS", c: Theme.pass}, {t: "● ACTIVE", c: Theme.live}, {t: "● REVIEW", c: Theme.review}, {t: "● FAIL", c: Theme.fail}, {t: "○ PENDING", c: Theme.textSecondary}]
                        Text { required property var modelData; text: modelData.t; color: modelData.c; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny }
                    }
                }
            }
        }

        DiagnosisPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: implicitHeight
            diagnosisModel: appController.diagnosisModel
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignTop
            spacing: Theme.spacingLg

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumWidth: 720
                spacing: Theme.spacingMd

                Panel {
                    Layout.fillWidth: true; Layout.preferredHeight: 143
                    ColumnLayout {
                        anchors.fill: parent; spacing: 8
                        RowLayout {
                            Layout.fillWidth: true
                            ColumnLayout {
                                spacing: 4
                                Text {
                                    text: appController.flowController.stageNumber > 0
                                          ? "STAGE " + appController.flowController.stageNumber + " OF " + appController.flowController.stageCount
                                          : "NO ACTIVE STAGE"
                                    color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; font.weight: Theme.weightMedium
                                }
                                RowLayout {
                                    spacing: 12
                                    Text { text: appController.flowController.currentStage || "Flow ready"; color: Theme.white; font.family: Theme.interfaceFont; font.pixelSize: Theme.title; font.weight: Theme.weightMedium }
                                    StatusBadge {
                                        text: appController.flowController.state === "Running" ? "ACTIVE" : appController.flowController.state.toUpperCase()
                                        tone: appController.flowController.statusTone
                                    }
                                }
                                Text {
                                    text: appController.flowController.stageDescription || (appController.flowController.configured
                                          ? "Configured flow is ready for execution."
                                          : "Set RTL2GDS_FLOW_CONFIG to load an execution plan.")
                                    color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption
                                }
                            }
                            Item { Layout.fillWidth: true }
                            ActionButton { text: "Ⅱ  PAUSE"; enabled: appController.flowController.state === "Running"; onClicked: appController.flowController.pause() }
                            ActionButton { text: "■  STOP"; tone: "danger"; enabled: appController.flowController.running; onClicked: appController.flowController.stop() }
                            ActionButton { text: "RESUME ⌄"; tone: "success"; enabled: appController.flowController.paused || !appController.flowController.running; onClicked: appController.flowController.resume() }
                        }
                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.border }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 14
                            Text { text: "PROGRESS"; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; font.weight: Theme.weightMedium }
                            Text { text: appController.flowController.progress + "%"; color: Theme.white; font.family: Theme.monoFont; font.pixelSize: Theme.caption }
                            Item {
                                Layout.fillWidth: true; Layout.preferredHeight: 3
                                Rectangle { anchors.fill: parent; color: Theme.borderSubtle }
                                Rectangle { width: parent.width * appController.flowController.progress / 100; height: parent.height; color: Theme.live }
                            }
                            Text { text: "ELAPSED  " + appController.flowController.elapsed; color: Theme.textPrimary; font.family: Theme.monoFont; font.pixelSize: Theme.caption }
                            Text { text: "EST. REMAIN  —"; color: Theme.textPrimary; font.family: Theme.monoFont; font.pixelSize: Theme.caption }
                        }
                    }
                }

                Panel {
                    title: "LIVE DESIGN METRICS"
                    Layout.fillWidth: true; Layout.preferredHeight: 160
                    RowLayout {
                        anchors.fill: parent; spacing: 7
                        Repeater {
                            model: appController.metricsModel
                            delegate: MetricCard {
                                label: model.label
                                value: model.value
                                context: model.context
                                tone: model.tone
                                spark: model.spark
                                Layout.fillWidth: true; Layout.fillHeight: true
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true; Layout.preferredHeight: 214; spacing: Theme.spacingSm
                    Panel {
                        title: "STAGE TASKS"
                        Layout.fillWidth: true; Layout.preferredWidth: 620; Layout.fillHeight: true
                        ListView {
                            anchors.fill: parent; model: appController.stageTaskModel; clip: true; spacing: 1
                            delegate: RowLayout {
                                id: stageTaskRow
                                required property string code
                                required property string name
                                required property string status
                                required property string duration
                                required property string log
                                required property string tone
                                width: ListView.view.width; height: 27; spacing: 8
                                property bool compact: width < 560
                                Text { text: tone === "pass" ? "●" : "○"; color: Theme.toneColor(tone); font.pixelSize: 13; Layout.preferredWidth: 12 }
                                Text { text: code + "  " + name; color: Theme.textPrimary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.fillWidth: true; Layout.minimumWidth: 0; elide: Text.ElideRight }
                                Text { text: status; color: Theme.toneColor(tone); font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: stageTaskRow.compact ? 54 : 80; elide: Text.ElideRight }
                                Text { text: duration; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: stageTaskRow.compact ? 56 : 68 }
                                Text { text: log; color: tone === "neutral" ? Theme.textMuted : Theme.live; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.preferredWidth: stageTaskRow.compact ? 88 : 116; elide: Text.ElideRight }
                                Text { text: "•••"; color: Theme.textSecondary; font.pixelSize: 10 }
                            }
                        }
                    }
                    Panel {
                        title: "OUTPUT SNAPSHOT"
                        Layout.preferredWidth: 360; Layout.fillHeight: true
                        ColumnLayout {
                            anchors.fill: parent; spacing: 6
                            Canvas {
                                id: placementCanvas
                                Layout.fillWidth: true; Layout.fillHeight: true
                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.reset(); ctx.fillStyle = Theme.canvas; ctx.fillRect(0, 0, width, height)
                                    for (var y = 5; y < height - 6; y += 7) {
                                        var rowOffset = ((y / 7) % 2) * 3
                                        for (var x = 4 + rowOffset; x < width - 5; x += 8) {
                                            var n = (x * 13 + y * 7) % 23
                                            ctx.fillStyle = n < 3 ? Theme.review : (n < 16 ? Theme.live : Theme.pass)
                                            ctx.fillRect(x, y, n < 5 ? 5 : 3, 3)
                                        }
                                    }
                                    ctx.fillStyle = Theme.canvas; ctx.fillRect(width*.17,height*.18,width*.18,height*.34); ctx.fillRect(width*.60,height*.37,width*.22,height*.30)
                                    ctx.strokeStyle = Theme.textMuted; ctx.lineWidth = 1
                                    ctx.strokeRect(width * 0.17, height * 0.18, width * 0.18, height * 0.34)
                                    ctx.strokeRect(width * 0.60, height * 0.37, width * 0.22, height * 0.30)
                                }
                                onWidthChanged: requestPaint()
                                onHeightChanged: requestPaint()
                            }
                            RowLayout {
                                spacing: 12
                                Repeater {
                                    model: [{t:"■ CELL",c:Theme.pass},{t:"■ MACRO",c:Theme.review},{t:"■ BLOCKAGE",c:Theme.textSecondary},{t:"■ ROW",c:Theme.review}]
                                    Text { required property var modelData; text: modelData.t; color: modelData.c; font.family: Theme.monoFont; font.pixelSize: 8 }
                                }
                            }
                        }
                    }
                }

                LogConsole { Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredHeight: 232; logModel: appController.logModel }
            }

            ColumnLayout {
                Layout.preferredWidth: Math.max(320, Math.min(356, scroll.availableWidth * 0.265))
                Layout.minimumWidth: 300
                Layout.alignment: Qt.AlignTop
                spacing: Theme.spacingSm

                Panel {
                    title: "SIGNOFF GATES"; Layout.fillWidth: true; Layout.preferredHeight: 152
                    ColumnLayout {
                        anchors.fill: parent; spacing: 5
                        Repeater {
                            model: appController.gateModel
                            QualityGate {
                                label: model.label
                                status: model.status
                                tone: model.tone
                                Layout.fillWidth: true
                            }
                        }
                    }
                }

                Panel {
                    title: "AGENT: CLAUDE"; Layout.fillWidth: true; Layout.preferredHeight: 370
                    ColumnLayout {
                        anchors.fill: parent; spacing: 8
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "CURRENT OBJECTIVE"; color: Theme.textMuted; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.fillWidth: true }
                            StatusBadge { text: "ACTIVE"; tone: "success" }
                        }
                        Text { text: "Reduce congestion and improve WNS\nwithout increasing area >1%."; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.caption; lineHeight: 1.35 }
                        SectionHeader { text: "LATEST DECISION       08:48:12"; Layout.fillWidth: true }
                        Text { text: "Reduce placement effort and target density while\nincreasing bounded displacement in congestion zones."; color: Theme.textPrimary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; lineHeight: 1.35 }
                        SectionHeader { text: "PARAMETER RETUNE (BOUNDED)"; Layout.fillWidth: true }
                        RowLayout {
                            Layout.fillWidth: true
                            Repeater {
                                model: ["PARAMETER", "CURRENT", "PROPOSED", "LIMITS"]
                                Text { required property string modelData; text: modelData; color: Theme.textMuted; font.family: Theme.monoFont; font.pixelSize: 8; Layout.fillWidth: true }
                            }
                        }
                        Repeater {
                            model: appController.retuneModel
                            RowLayout {
                                required property string parameter
                                required property string current
                                required property string proposed
                                required property string limits
                                required property string tone
                                Layout.fillWidth: true
                                Text { text: parameter; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: 8; Layout.preferredWidth: 100 }
                                Text { text: current; color: Theme.textPrimary; font.family: Theme.monoFont; font.pixelSize: 8; Layout.fillWidth: true }
                                Text { text: proposed; color: Theme.toneColor(tone); font.family: Theme.monoFont; font.pixelSize: 8; Layout.fillWidth: true }
                                Text { text: limits; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: 8; Layout.fillWidth: true }
                            }
                        }
                        Item { Layout.fillHeight: true }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 7
                            ActionButton { text: "REJECT"; tone: "danger"; Layout.preferredWidth: 60; Layout.minimumWidth: 0 }
                            ActionButton { text: "APPLY"; tone: "warning"; Layout.preferredWidth: 60; Layout.minimumWidth: 0 }
                            ActionButton { text: "APPLY & CONTINUE"; tone: "success"; Layout.preferredWidth: 128; Layout.minimumWidth: 0 }
                        }
                    }
                }

                Panel {
                    title: "KEY ARTIFACTS"; Layout.fillWidth: true; Layout.preferredHeight: 246
                    ColumnLayout {
                        anchors.fill: parent; spacing: 6
                        Repeater {
                            model: appController.artifactModel
                            RowLayout {
                                required property string name
                                required property string time
                                required property string size
                                Layout.fillWidth: true; Layout.preferredHeight: 24
                                Text { text: "▧"; color: Theme.live; font.pixelSize: 11 }
                                Text { text: name; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: Theme.tiny; Layout.fillWidth: true }
                                Text { text: time; color: Theme.textMuted; font.family: Theme.monoFont; font.pixelSize: 8 }
                                Text { text: size; color: Theme.textSecondary; font.family: Theme.monoFont; font.pixelSize: 8; Layout.preferredWidth: 42; horizontalAlignment: Text.AlignRight }
                            }
                        }
                        Item { Layout.fillHeight: true }
                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.border }
                        Text { text: "VIEW ALL ARTIFACTS  →"; color: Theme.live; font.family: Theme.monoFont; font.pixelSize: Theme.caption; Layout.alignment: Qt.AlignRight }
                    }
                }
            }
        }
    }
}
