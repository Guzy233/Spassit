import time
import threading
from pynput import mouse
import logging

# 连点状态
left_clicking = False
right_clicking = False

# 连点间隔时间（秒）
click_interval = 0.003 

config=None

def left_clicker():
    while True:
        if left_clicking:
            mouse.Controller().click(mouse.Button.left)
        time.sleep(click_interval)


def right_clicker():
    while True:
        if right_clicking:
            mouse.Controller().click(mouse.Button.right)
        time.sleep(click_interval)


def on_click(x, y, button, pressed):
    global left_clicking, right_clicking

    if button == mouse.Button.x1:
        right_clicking = pressed
        logging.info(f"右键连点 {'开启' if pressed else '关闭'}")
    elif button == mouse.Button.x2:
        left_clicking = pressed
        logging.info(f"左键连点 {'开启' if pressed else '关闭'}")


left_click_thread = None
right_click_thread = None
listener = None  # 添加全局监听器变量

def start_autoclick():
    """启动自动连点"""
    global left_click_thread, right_click_thread, listener
    left_click_thread = threading.Thread(target=left_clicker)
    right_click_thread = threading.Thread(target=right_clicker)
    left_click_thread.daemon = True
    right_click_thread.daemon = True
    left_click_thread.start()
    right_click_thread.start()

    listener = mouse.Listener(on_click=on_click)
    listener.start()


def stop_autoclick():
    """停止自动连点"""
    global left_clicking, right_clicking, left_click_thread, right_click_thread, listener
    left_clicking = False
    right_clicking = False
    if listener:
        listener.stop()
    if left_click_thread:
        del left_click_thread
    if right_click_thread:
        del right_click_thread

def set_interval(interval):
    """设置连点间隔/频率"""
    global click_interval
    click_interval=interval
    logging.info(f"设置连点间隔为{click_interval}秒")
    config["autoclick"]["interval"]=click_interval


def init(_config:dict):
    global click_interval,config
    config=_config
    if "autoclick" in _config:
        click_interval=_config["autoclick"]["interval"]
    else:
        logging.info("配置文件中未找到autoclick配置,将使用默认配置")
        # 保存配置
        _config["autoclick"]={
            "interval":click_interval
        }

    return [start_autoclick,stop_autoclick,set_interval],None
