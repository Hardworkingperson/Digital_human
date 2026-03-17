import os

# --- 1. 动态获取项目根目录 ---
# 无论你把文件夹拷到哪里，BASE_DIR 都会自动定位到当前文件夹
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- 2. 资源路径配置 ---
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
VIDEO_IDLE = os.path.join(ASSETS_DIR, "idle.mp4")
VIDEO_TALKING = os.path.join(ASSETS_DIR, "talking.mp4")

# --- 3. 模型与数据路径 (全部指向内部 models 文件夹) ---
MODELS_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")

# YOLO 模型路径
YOLO_MODEL_PATH = os.path.join(MODELS_DIR, "yolo", "best.pt")

# STT (Whisper) 模型路径
STT_MODEL_PATH = os.path.join(MODELS_DIR, "stt") 
# 注意：如果你的模型文件直接散在 stt 里，就写 stt；
# 如果 stt 下面还有个 fast_model_int8 文件夹，就写 os.path.join(MODELS_DIR, "stt", "fast_model_int8")

# 向量数据库路径
DB_PATH = os.path.join(DATA_DIR, "medical_vector_db")

# --- 4. 硬件配置 ---
MIC_DEVICE_ID = 7
CAMERA_ID = 0
WINDOW_WIDTH = 1080
WINDOW_HEIGHT = 1920
FPS = 30

# --- 5. API 配置 (F5-TTS 保持独立) ---
TTS_API_URL = "http://127.0.0.1:8000/tts"
# 参考音频建议也放进 assets，这里暂时指向绝对路径或 assets
TTS_REF_AUDIO = "/home/admin1108/weitiao/data/test.wav" 
TTS_REF_TEXT = "您好，我是医养通智能助手。"

OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "qwen3:14b"

# --- 6. 全局状态 (通信黑板) ---
GLOBAL_STATE = {
    "is_speaking": False,         # 视频控制
    "new_sentence": False,        # 视频重置
    "running": True,              # 程序开关
    "subtitle": "系统初始化...",   # 字幕
    "vision_label": "",           # 视觉结果
}