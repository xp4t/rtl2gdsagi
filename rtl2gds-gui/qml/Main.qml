import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."
import "components"
import "pages"

ApplicationWindow {
    id: window
    width: 1600
    height: 900
    minimumWidth: 1100
    minimumHeight: 700
    visible: true
    title: "RTL2GDSAGI — Operator Console"
    color: Theme.canvas

    AppSidebar {
        id: sidebar
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: implicitWidth
        currentPage: appController.currentPage
        onNavigate: function(route) { appController.navigate(route) }
        Behavior on width { NumberAnimation { duration: 100 } }
    }

    TopBar {
        id: topBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        runState: appController.runState
        z: 2
    }

    StackLayout {
        anchors.left: sidebar.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: Theme.topBarHeight + Theme.contentInset
        anchors.bottom: parent.bottom
        anchors.leftMargin: Theme.contentInset
        anchors.rightMargin: Theme.contentInset
        anchors.bottomMargin: Theme.contentInset
        currentIndex: {
            var pages = ["activeRun", "retuneReview", "runHistory", "checkpointRecovery", "newRun", "humanReview", "strategySweep"]
            return Math.max(0, pages.indexOf(appController.currentPage))
        }
        ActiveRunPage { }
        RetuneReviewPage { }
        RunHistoryPage { }
        CheckpointRecoveryPage { }
        NewRunPage { }
        HumanReviewPage { }
        StrategySweepPage { }
    }
}
