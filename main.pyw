import os
import sys
import Gui
import json
import time
import logging
import inspect
import Globals
import keyboard
import importlib
import threading
import LLMService
import SpeechService
from datetime import datetime
from PyQt5.QtWidgets import QMessageBox

def init_logger():
    log_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    Globals.log_path = f"logs/{log_time}.log"
    if not os.path.exists("logs"):
        os.makedirs("logs")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(Globals.log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

def log_inlines(message, level=logging.INFO):
    for line in str(message).splitlines():
        logging.log(level, line)

def text_handler():
    if Globals.text is not None:
        Globals.reponse, time_cost = LLMService.call_llm_api(Globals.text)
        log_inlines(f"响应结果：\n{Globals.reponse}\n耗时:{time_cost:.2f}s")
        Gui.run_in_main_thread(Globals.controller.close_window)
        Gui.run_in_main_thread(Globals.reponse_handler)
Globals.text_handler = text_handler

def response_handler():
    Globals.modified = True

    pycode, pscode, note = "", "", ""

    if "```python" in Globals.reponse:
        pycode = Globals.reponse.split("```python")[1].split("```")[0].strip()

    if "```powershell" in Globals.reponse:
        pscode = Globals.reponse.split("```powershell")[1].split("```")[0].strip()

    if "```note" in Globals.reponse:
        note = Globals.reponse.split("```note")[1].split("```")[0].strip()

    if pycode or pscode or note:
        if note or Globals.always_ask:
            if Gui.info(f"提示：{note}\n将运行的代码:\n{pscode+pycode}") != QMessageBox.Ok:
                logging.info("取消操作")
                Globals.reponse = None
                return

        if pycode != "":
            try:
                exec(pycode)
            except Exception as e:
                logging.info(f"执行python失败:{e}", level=logging.ERROR)

        if pscode != "":
            try:
                os.system("powershell -Command " + pscode)
            except Exception as e:
                logging.info(f"执行powershell失败:{e}")

    if "```answer" in Globals.reponse:
        answer = Globals.reponse.split("```answer")[1].split("```")[0].strip()
        logging.info(f"answer:{answer}")
        Gui.info(answer, buttons=QMessageBox.Ok)

    if "```ambiguous```" in Globals.reponse:
        logging.info(f"ambiguous input")
        Gui.info(f"输入不明确：{Globals.text}", buttons=QMessageBox.Yes)
Globals.reponse_handler = response_handler


def hotkey_pressed_handler():
    if not Globals.is_recording:
        threading.Thread(target=Globals.speech_service.start_recording).start()
        logging.info("录音开始...")
        Gui.run_in_main_thread(Globals.controller.create_window)
        Globals.is_recording = True


def hotkey_released_handler(event):
    """按键松开时，开始识别"""
    if Globals.is_recording and event.name == Globals.hotkey:
        Globals.is_recording = False
        try:
            audio_data, time_last = Globals.speech_service.stop_recording()
            logging.info(f"录音结束，时长:{time_last:.2f}s")
            Gui.run_in_main_thread(Globals.controller.update_state)
            Globals.text, time_cost = Globals.speech_service.speech_to_text(audio_data)
            logging.info(f"识别结果：{Globals.text},耗时:{time_cost:.2f}s")
            Gui.run_in_main_thread(Globals.controller.update_state)
            text_handler()
        except Exception as e:
            logging.error(f"处理音频失败: {str(e)}")
            Gui.run_in_main_thread(Globals.controller.close_window)

    keyboard.release(Globals.hotkey)


def save_config(config):
    """保存配置"""
    while True:
        if not Globals.modified:
            time.sleep(30)
            continue
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        logging.info("配置已保存")
        Globals.modified = False


def register_function(config):
    """注册所有模块中的函数"""
    prompts = ""  # 生成提示语
    
    #判断是否在打包环境中
    if getattr(sys, 'frozen', False):
        dir="_internal/modules"
    else:
        dir="modules"

    for file in os.listdir(dir):
        if file.endswith(".py"):
            module_name = file[:-3]
            module = importlib.import_module(f"modules.{module_name}")
            logging.info(f"加载模块:{module_name}")
            functions,extra = module.init(config)
            for function in functions:
                sig = inspect.signature(function)
                logging.info(f"-注册函数:{module_name}.{function.__name__}{sig}")
                globals()[function.__name__] = function
                prompts += f"def {function.__name__}{sig}\n作用:{function.__doc__}\n"
            prompts += extra if extra else ""
            extra = None
    return prompts


def main():
    # 加载配置
    Globals.config = json.load(open("config.json", encoding="utf-8"))
    Globals.always_ask = Globals.config["always_ask"]
    Globals.hotkey = Globals.config["hotkey"]
    Globals.icon = Globals.config["icon"]

    # 初始化日志
    init_logger()

    # 启动配置保存线程
    threading.Thread(target=save_config, args=(Globals.config,), daemon=True).start()

    # 注册模块函数并初始化LLM服务
    funcs = register_function(Globals.config)
    LLMService.init(Globals.config, funcs)

    # 初始化语音服务
    Globals.speech_service = SpeechService.init(Globals.config["speech_services"])

    # 注册快捷键
    keyboard.add_hotkey(Globals.hotkey, hotkey_pressed_handler)
    keyboard.on_release(hotkey_released_handler)

    # 启动事件循环
    sys.exit(Gui.run_QtApp())

if __name__ == "__main__":
    main()
