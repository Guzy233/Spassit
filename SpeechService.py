import time
import numpy as np
import sounddevice as sd
# import speech_recognition as sr
import aip.speech as aip
import logging


class SpeechService:
    def __init__(self):
        self.is_recording = False
        self.audio_buffer = []
        self.sample_rate = 16000
        self.channels = 1
        self.stime = 0

    def start_recording(self):
        self.is_recording = True
        self.audio_buffer = []
        self.stime = time.time()

        def callback(indata, frames, time, status):
            if self.is_recording:
                self.audio_buffer.append(indata.copy())

        with sd.InputStream(
            callback=callback,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
        ):
            while self.is_recording:
                sd.sleep(100)

    def stop_recording(self):
        """返回录音数据和录音时长"""
        self.is_recording = False
        if not self.audio_buffer:
            return None
        audio_data = np.concatenate(self.audio_buffer)
        return audio_data, time.time() - self.stime

    def speech_to_text(self, audio_data):
        """将音频数据转换为文本"""
        raise NotImplementedError("子类必须实现此方法")


# class GoogleASR(SpeechService):
#     def __init__(self):
#         super().__init__()
#         self.recognizer = sr.Recognizer()
#         logging.info("使用GoogleASR初始化完成")

#     def speech_to_text(self, audio_data):
#         stime = time.time()
#         audio_bytes = audio_data.tobytes()

#         audio_data_sr = sr.AudioData(
#             frame_data=audio_bytes,
#             sample_rate=self.sample_rate,
#             sample_width=2,  # int16类型对应2字节
#         )
#         text = self.recognizer.recognize_google(audio_data_sr, language="zh-CN")
#         return text, time.time() - stime


class BaiduASR(SpeechService):
    def __init__(self, config):
        super().__init__()
        self.APP_ID = config["app_id"]
        self.API_KEY = config["api_key"]
        self.SECRET_KEY = config["secret_key"]
        self.client = aip.AipSpeech(self.APP_ID, self.API_KEY, self.SECRET_KEY)
        logging.info("语音服务初始化完成,服务商:BaiduASR")
        logging.info(f"-APP_ID:{self.APP_ID}")
        logging.info(f"-API_KEY:{self.API_KEY[:5] +  "*" * (len(self.API_KEY) - 8) + self.API_KEY[-3:]}")
        logging.info(f"-SECRET_KEY:{self.SECRET_KEY[:5] + "*" * (len(self.SECRET_KEY) - 8) + self.SECRET_KEY[-3:]}")

    def speech_to_text(self, audio_data):
        stime = time.time()
        audio_bytes = audio_data.tobytes()
        result = self.client.asr(
            audio_bytes,
            "pcm",
            self.sample_rate,
            {
                "dev_pid": 1537,  # 中文普通话识别
            },
        )
        if "result" in result:
            text = result["result"][0]
        else:
            text = ""
            logging.error(f"BaiduASR返回错误:{result}")
        return text, time.time() - stime


def init(config):
    # 将config中的值按照priority排序，返回优先级最高的ASR对象
    config = sorted(config, key=lambda x: x["Priority"], reverse=True)[0]

    # if config["name"] == "Google":
    #     return GoogleASR()
    if config["name"] == "Baidu":
        return BaiduASR(config)
