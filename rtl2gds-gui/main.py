from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from backend.app_controller import AppController


def main() -> int:
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("RTL2GDSAGI")
    app.setOrganizationName("RTL2GDSAGI")

    font_dir = Path(__file__).resolve().parent / "assets" / "fonts"
    for font_name in (
        "FiraSans-Regular.ttf",
        "FiraSans-Medium.ttf",
        "FiraSans-SemiBold.ttf",
        "FiraCode-Variable.ttf",
    ):
        if QFontDatabase.addApplicationFont(str(font_dir / font_name)) < 0:
            raise RuntimeError(f"Unable to load bundled font: {font_name}")

    controller = AppController()
    app.aboutToQuit.connect(controller.shutdown)
    initial_page = os.environ.get("RTL2GDS_PAGE")
    if initial_page:
        controller.navigate(initial_page)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", controller)
    qml_path = Path(__file__).resolve().parent / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(qml_path))
    if not engine.rootObjects():
        return 1
    requested_size = os.environ.get("RTL2GDS_SIZE")
    if requested_size:
        width, height = (int(part) for part in requested_size.lower().split("x", 1))
        engine.rootObjects()[0].setWidth(width)
        engine.rootObjects()[0].setHeight(height)
    screenshot_path = os.environ.get("RTL2GDS_SCREENSHOT")
    if screenshot_path:
        def capture() -> None:
            window = engine.rootObjects()[0]
            window.screen().grabWindow(window.winId()).save(screenshot_path)
            app.quit()

        QTimer.singleShot(1200, capture)
    exit_code = app.exec()
    del engine
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
