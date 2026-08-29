import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

ColumnLayout {
    id: root
    property string label: "Field"
    property string value: ""
    property string helper: ""
    property bool dropdown: false
    property bool multiline: false
    property bool approved: false
    property string suffix: ""
    spacing: 4

    Text { text: root.label; color: Theme.textSecondary; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption; font.weight: Theme.weightMedium }

    Loader {
        Layout.fillWidth: true
        Layout.preferredHeight: root.multiline ? 70 : Theme.fieldHeight
        sourceComponent: root.multiline ? areaComponent : (root.dropdown ? comboComponent : fieldComponent)
    }

    RowLayout {
        Layout.fillWidth: true; spacing: 7
        Rectangle { visible: root.approved; width: 10; height: 10; radius: 5; color: Theme.pass
            Text { anchors.centerIn: parent; text: "✓"; color: Theme.canvas; font.pixelSize: 7 }
        }
        Text { text: root.helper; color: root.approved ? Theme.pass : Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.tiny; Layout.fillWidth: true }
    }

    Component {
        id: fieldComponent
        TextField {
            text: root.value
            color: Theme.textPrimary; selectionColor: Theme.live
            font.family: Theme.monoFont; font.pixelSize: Theme.caption
            leftPadding: 12; rightPadding: root.suffix.length > 0 ? 42 : 12
            background: Rectangle { color: Theme.input; border.color: Theme.border; border.width: 1 }
            Text { visible: root.suffix.length > 0; anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; text: root.suffix; color: Theme.textMuted; font.family: Theme.interfaceFont; font.pixelSize: Theme.caption }
        }
    }
    Component {
        id: comboComponent
        ComboBox {
            model: [root.value]
            font.family: Theme.monoFont; font.pixelSize: Theme.caption
            leftPadding: 12; rightPadding: 34
            contentItem: Text { text: root.value; color: Theme.textPrimary; font: parent.font; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
            indicator: Canvas { x: parent.width - width - 11; y: (parent.height-height)/2; width: 12; height: 8; onPaint:{var c=getContext("2d");c.reset();c.strokeStyle=Theme.textSecondary;c.beginPath();c.moveTo(2,2);c.lineTo(6,6);c.lineTo(10,2);c.stroke()} }
            background: Rectangle { color: Theme.input; border.color: Theme.border; border.width: 1 }
            popup: Popup { y: parent.height; width: parent.width; implicitHeight: 0 }
        }
    }
    Component {
        id: areaComponent
        TextArea {
            text: root.value
            color: Theme.textPrimary; selectionColor: Theme.live
            font.family: Theme.interfaceFont; font.pixelSize: Theme.caption
            wrapMode: TextEdit.Wrap; leftPadding: 12; rightPadding: 12; topPadding: 8; bottomPadding: 8
            background: Rectangle { color: Theme.input; border.color: Theme.border; border.width: 1 }
        }
    }
}
