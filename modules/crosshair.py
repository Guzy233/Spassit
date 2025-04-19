from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QPoint, QSize
from PyQt5.QtGui import QPainter, QPen, QColor
import logging
from typing import Dict, List, Callable

# 全局变量存储状态
_overlay_window = None
_config = None
_logger = logging.getLogger("crosshair")

class CrosshairWindow(QWidget):
    """准星绘制窗口"""
    def __init__(self):
        super().__init__()
        self._setup_window()

    def _setup_window(self):
        """初始化窗口属性"""
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint  # 始终置顶
            | Qt.FramelessWindowHint  # 无边框
            | Qt.WindowTransparentForInput  # 不接收输入
            | Qt.Tool  # 隐藏任务栏图标
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(0, 0, QApplication.desktop().screenGeometry().width(),
                         QApplication.desktop().screenGeometry().height())

    def paintEvent(self, event):
        """绘制准星"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 从全局配置获取参数
        pen = QPen()
        pen.setColor(QColor(_config["color"]))
        pen.setWidth(_config["line_width"])
        painter.setPen(pen)

        center = self.rect().center()
        size = QSize(_config["size"], _config["size"])

        # 绘制水平线
        painter.drawLine(
            center.x() - size.width()//2,
            center.y(),
            center.x() + size.width()//2,
            center.y()
        )
        # 绘制垂直线
        painter.drawLine(
            center.x(),
            center.y() - size.height()//2,
            center.x(),
            center.y() + size.height()//2
        )

def init(config: Dict, logger: logging.Logger = None) -> List[Callable]:
    """
    初始化准星模块
    Args:
        config: 全局配置字典，会自动添加/读取 module_name 为 "crosshair" 的配置
        logger: 日志记录器实例
    Returns:
        list: 包含所有接口函数的列表
    """
    global _config, _logger
    module_name = "crosshair"
    
    # 设置日志记录器
    _logger = logger or logging.getLogger("crosshair")
    
    # 初始化配置
    default_config = {
        "color": "#FF0000",
        "size": 20,
        "line_width": 2,
        "visible": False
    }
    
    if module_name not in config:
        config[module_name] = default_config
        _logger.info("Using default crosshair configuration")
    else:
        # 合并配置
        config[module_name] = {**default_config, **config[module_name]}
    
    _config = config[module_name]
    
    return [start_crosshair, stop_crosshair, update_config],None

def start_crosshair():
    """启动/显示屏幕准星"""
    global _overlay_window
    if not _overlay_window:
        _overlay_window = CrosshairWindow()
    _overlay_window.show()
    _config["visible"] = True
    _logger.info("Crosshair started")

def stop_crosshair():
    """关闭/隐藏屏幕准星"""
    global _overlay_window
    if _overlay_window:
        _overlay_window.hide()
        _overlay_window.deleteLater()
        _overlay_window = None
    _config["visible"] = False
    _logger.info("Crosshair stopped")

def update_config(new_config: Dict):
    """
    更新准星配置
    Args:
        new_config: 需要更新的配置项字典（支持部分更新）
        格式：{"color": "#00FF00", "size": 30, "line_width": 3, "visible": True}
    """
    global _config
    _config.update(new_config)
    
    # 立即应用配置
    if _overlay_window and _config["visible"]:
        _overlay_window.update()
    
    _logger.info(f"Config updated: {new_config}")
