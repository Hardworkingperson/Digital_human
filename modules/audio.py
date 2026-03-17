import sounddevice as sd
import soundfile as sf
import speech_recognition as sr
import io
import requests
import threading
import time
import numpy as np
from faster_whisper import WhisperModel
from config import STT_MODEL_PATH, MIC_DEVICE_ID, TTS_API_URL, TTS_REF_AUDIO, TTS_REF_TEXT, GLOBAL_STATE

class AudioManager:
    def __init__(self):
        print(f"👂 [Audio] 加载 Whisper: {STT_MODEL_PATH}")
        self.stt_model = WhisperModel(STT_MODEL_PATH, device="cuda", compute_type="float16", local_files_only=True)
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 1000

        # 噪音词黑名单（Whisper 常见的误识别结果）
        self.noise_words = {
            "点点点", "。。。", "...", "嗯", "啊", "呃", "哦", "嗯嗯",
            "啊啊", "呵呵", "哈哈", "嘿", "唉", "诶", "额", "嘛",
            "字幕", "谢谢观看", "请关注", "订阅", "点赞", "下集", "下一集"
        }

    def start_listen(self, callback):
        threading.Thread(target=self._listen_loop, args=(callback,), daemon=True).start()

    def _listen_loop(self, callback):
        try:
            mic = sr.Microphone(device_index=MIC_DEVICE_ID, sample_rate=48000)
        except:
            print("❌ 麦克风打开失败")
            return
        
        with mic as source:
            self.recognizer.adjust_for_ambient_noise(source)
            while GLOBAL_STATE["running"]:
                if GLOBAL_STATE["is_speaking"]:
                    time.sleep(0.5)
                    continue
                try:
                    audio = self.recognizer.listen(source, phrase_time_limit=8)
                    raw = audio.get_raw_data()
                    np_data = np.frombuffer(raw, np.int16).flatten().astype(np.float32) / 32768.0
                    segs, _ = self.stt_model.transcribe(np_data, language="zh")
                    text = "".join([s.text for s in segs]).strip()

                    # 多层过滤
                    if len(text) < 2:  # 太短
                        continue
                    if text in self.noise_words:  # 噪音词
                        print(f"🔇 [Audio] 过滤噪音: {text}")
                        continue
                    if all(c in "。，、？！…—·~" for c in text):  # 纯标点
                        continue

                    print(f"👂 [Audio] 听到: {text}")
                    callback(text)
                except:
                    pass

    def speak(self, text):
        print(f"🤖 [Audio] 播放: {text}")
        GLOBAL_STATE["subtitle"] = text
        try:
            payload = {"text": text, "ref_audio_path": TTS_REF_AUDIO, "ref_text": TTS_REF_TEXT}
            resp = requests.post(TTS_API_URL, json=payload, timeout=10)
            
            if resp.status_code == 200:
                audio, sr = sf.read(io.BytesIO(resp.content))
                
                # --- 视频切换核心逻辑 ---
                GLOBAL_STATE["new_sentence"] = True
                GLOBAL_STATE["is_speaking"] = True
                
                sd.play(audio, sr)
                sd.wait() # 阻塞至播完
                
                GLOBAL_STATE["is_speaking"] = False
                GLOBAL_STATE["subtitle"] = "倾听中..."
            else:
                print("❌ TTS API Error")
        except Exception as e:
            print(f"❌ TTS Fail: {e}")
            GLOBAL_STATE["is_speaking"] = False