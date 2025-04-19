import os
import glob
import logging

short_cuts = ""

def get_desktop_shortcuts():
    # 获取用户桌面路径
    user_desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    # 获取公共桌面路径
    public_desktop_path = os.path.join(
        os.environ.get("PUBLIC", "C:\\Users\\Public"), "Desktop"
    )

    user_shortcuts = glob.glob(os.path.join(user_desktop_path, "*.lnk")) + glob.glob(
        os.path.join(user_desktop_path, "*.url")
    )
    public_shortcuts = glob.glob(
        os.path.join(public_desktop_path, "*.lnk")
    ) + glob.glob(os.path.join(public_desktop_path, "*.url"))

    return user_shortcuts + public_shortcuts


def start_program(query):
    """通过传入的字符串模糊匹配并启动对应程序"""
    global short_cuts
    for shortcut in short_cuts:
        # 获取快捷方式文件名
        file_name = os.path.basename(shortcut).lower()
        if query.lower() in file_name:
            os.startfile(shortcut)
            logging.info(f"启动程序：{file_name}")
            return
    logging.info(f"未找到程序：{query}")

def init(config):
    global short_cuts
    programs = ""
    short_cuts = get_desktop_shortcuts()
    for shortcut in short_cuts:
        file_name = os.path.basename(shortcut).lower()[0:-4]
        programs += f"{file_name}\n"

    return [start_program], "可用的程序列表：\n" + programs