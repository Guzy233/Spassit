import sys
import time
import Globals
import logging
import threading
from PyQt5 import QtCore
from PyQt5.QtGui import QColor, QPainter, QPen, QIcon
from PyQt5.QtCore import Qt, QPropertyAnimation, pyqtSignal, QObject
from PyQt5.QtWidgets import (
    QMenu,
    QLabel,
    QWidget,
    QLineEdit,
    QMessageBox,
    QHBoxLayout,
    QVBoxLayout,
    QApplication,
    QDesktopWidget,
    QPlainTextEdit,
    QSystemTrayIcon,
)


class LoadingIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0
        self.color = QColor(25, 25, 112)

        # 配置动画
        self.animation = QPropertyAnimation(self, b"angle")
        self.animation.setDuration(1500)
        self.animation.setStartValue(0)
        self.animation.setEndValue(360)
        self.animation.setLoopCount(-1)

    def getAngle(self):
        return self._angle

    def setAngle(self, value):
        self._angle = value
        self.update()  # 触发重绘

    angle = QtCore.pyqtProperty(int, getAngle, setAngle)

    def start(self):
        self.animation.start()

    def stop(self):
        self.animation.stop()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(self.color, 4, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)

        # 转换为整数坐标
        size = min(self.width(), self.height()) - 10
        x = int((self.width() - size) / 2)
        y = int((self.height() - size) / 2)

        # 使用QRect构造矩形区域
        rect = QtCore.QRect(x, y, size, size)
        # 绘制蓝色背景

        painter.drawArc(rect, self._angle * 16, 300 * 16)


class StatusWindow(QWidget):
    text_map = ["正在录音", "识别中", "处理中"]

    def __init__(self):
        super().__init__()
        self.current_state = 0
        self.initUI()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def initUI(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(50, 50, 50, 50)

        layout.addStretch(1)

        self.label = QLabel(text=self.text_map[self.current_state])
        self.label.setStyleSheet("color: #191970; font: bold 35px;")

        fm = self.label.fontMetrics()
        font_height = fm.height()
        self.loader = LoadingIndicator()
        self.loader.setFixedSize(int(font_height * 1.2), int(font_height * 1.2))
        self.loader.setStyleSheet(
            "background-color: rgba(173, 216, 230, 200); border-radius: 10px;"
        )

        layout.addWidget(self.label)
        layout.addWidget(self.loader)

        layout.addStretch(1)

        self.setLayout(layout)

    def update_position(self):
        screen = QDesktopWidget().screenGeometry()
        self.move(60, screen.height() - self.height() - 75)

    def showEvent(self, event):
        self.update_position()
        self.current_state = -1
        self.loader.start()
        super().showEvent(event)

    def next_state(self):
        self.current_state += 1
        if self.current_state >= len(self.text_map):
            self.loader.stop()
            return
        self.label.setText(self.text_map[self.current_state])
        self.layout().activate()
        self.update_position()  # 更新窗口位置

    def closeEvent(self, event):
        self.loader.stop()
        super().closeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(173, 216, 230, 150))  # 半透明的蓝色
        painter.setPen(Qt.NoPen)  # 无边框
        painter.drawRoundedRect(self.rect(), 10, 10)  # 圆角矩形
        super().paintEvent(event)


class StatusController(QObject):
    state_changed = pyqtSignal()
    create = pyqtSignal()
    close = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.window = None
        self.state_changed.connect(self.update_state)
        self.create.connect(self.create_window)
        self.close.connect(self.close_window)

    def create_window(self):
        self.window = StatusWindow()
        self.window.show()
        self.window.next_state()

    def update_state(self):
        if self.window is None:
            return
        self.window.next_state()
        if self.window.current_state == len(self.window.text_map):
            self.window.close()

    def close_window(self):
        if self.window is None:
            return
        self.window.close()


# 托盘图标
class TrayIcon(QSystemTrayIcon):
    response_signal = pyqtSignal()

    def __init__(self, icon_path):
        super().__init__()
        self.setIcon(QIcon(icon_path))

        menu = QMenu()
        exit_action = menu.addAction("退出")
        exit_action.triggered.connect(QApplication.quit)

        self.setContextMenu(menu)
        self.activated.connect(self.on_activate)
        self.response_signal.connect(Globals.reponse_handler)

    def on_activate(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            show_command_interface()


class QtLogHandler(logging.Handler, QObject):
    log_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        logging.Handler.__init__(self)
        QObject.__init__(self, parent)
        self.formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        self.log_signal.connect(self._handle_log)

    def emit(self, record):
        """重写emit方法(自动处理多线程)"""
        msg = self.format(record)
        self.log_signal.emit(msg)

    def _handle_log(self, msg):
        """实际处理日志的方法"""
        if hasattr(self, "output_widget"):
            self.output_widget.appendPlainText(msg)

    def attach_widget(self, widget):
        """关联GUI输出组件"""
        self.output_widget = widget


class CLIWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.init_handler()
        self.append_initial_output()

    def init_ui(self):
        self.setWindowTitle("Spassit")
        self.layout = QVBoxLayout()
        self.setWindowIcon(QIcon(Globals.icon))

        # 输出显示区域
        self.output_area = QPlainTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setStyleSheet(
            "QPlainTextEdit { background-color: #282c34; color: #abb2bf; }"
            "QPlainTextEdit { font-family: 'Consolas'; font-size: 28px; }"
            "QPlainTextEdit { border: none; }"
        )
        self.layout.addWidget(self.output_area)

        # 输入区域
        self.input_line = QLineEdit()
        self.input_line.returnPressed.connect(self.process_input)
        self.input_line.setStyleSheet(
            "QLineEdit { background-color: #282c34; color: #abb2bf; }"
            "QLineEdit { font-family: 'Consolas'; font-size: 28px; }"
            "QLineEdit { border: none; }"
        )
        self.input_line.setPlaceholderText("输入提示词......")
        self.input_line.setFocus()
        self.layout.addWidget(self.input_line)

        self.setLayout(self.layout)
        self.setStyleSheet(
            "background-color: #282c34; color: #abb2bf; font-family: 'Consolas'; font-size: 28px;"
        )
        self.resize(1600, 800)

    def init_handler(self):
        self.qt_handler = QtLogHandler()
        self.qt_handler.attach_widget(self.output_area)
        logging.getLogger().addHandler(self.qt_handler)

    def append_initial_output(self):
        content = open(Globals.log_path, "r", encoding="utf-8").read()
        content = content.rstrip("\n")
        self.output_area.appendPlainText(content)

    def append_output(self, text):
        self.output_area.appendPlainText(text.rstrip("\n"))

    def process_input(self):
        input_text = self.input_line.text()
        self.input_line.clear()
        Globals.text = input_text
        self.append_output(f">>> {input_text}")
        threading.Thread(target=Globals.text_handler).start()

    def closeEvent(self, event):
        logging.getLogger().removeHandler(self.qt_handler)
        super().closeEvent(event)


class FuncCaller(QObject):
    func_called = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.func_called.connect(self.handler)
        self.target_func = None

    def handler(self):
        self.target_func()
        self.target_func = None


def run_in_main_thread(func):
    while Globals.caller.target_func is not None:
        time.sleep(0.05)
    Globals.caller.target_func = func
    QtCore.QMetaObject.invokeMethod(
        Globals.caller, "func_called", QtCore.Qt.QueuedConnection
    )


def show_command_interface():
    window = CLIWindow()
    window.show()
    Globals.gui = window


def info(str, buttons=QMessageBox.Ok | QMessageBox.Cancel):
    msgBox = QMessageBox()
    msgBox.setWindowTitle("警告")
    msgBox.setIcon(QMessageBox.Question)
    msgBox.setWindowFlags(Qt.WindowStaysOnTopHint)
    msgBox.setText(str)
    msgBox.setStandardButtons(buttons)

    return msgBox.exec_()


def run_QtApp():
    # 初始化PyQt5
    app = QApplication(sys.argv)
    QApplication.setQuitOnLastWindowClosed(False)

    # 初始化状态控制器
    Globals.controller = StatusController()
    # 初始化系统托盘
    Globals.tray = TrayIcon(Globals.icon)
    Globals.tray.show()
    Globals.caller = FuncCaller()
    return app.exec_()
