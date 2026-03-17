import threading
from modules.vision import MedicineDetector
from modules.brain import MedicalBrain
from modules.audio import AudioManager
from modules.ui import run_ui
from config import GLOBAL_STATE

class SystemController:
    def __init__(self):
        # 1. 初始化
        self.brain = MedicalBrain()
        self.audio = AudioManager()
        self.vision = MedicineDetector()
        
        # 2. 绑定回调
        self.audio.start_listen(self.process)
        self.vision.start(self.process)
        
        GLOBAL_STATE["subtitle"] = "医养通多模态系统就绪"

    def process(self, text):
        print(f"\n🔄 收到输入: {text}")

        # 【第一阶段】意图识别：判断是否为医疗相关
        is_medical = self.brain.is_medical_query(text)

        if not is_medical:
            # 判断是否为有意义的非医疗问题（如闲聊、问候）
            if len(text) >= 3 and any(kw in text for kw in ["你好", "您好", "谢谢", "再见", "天气", "时间", "几点"]):
                # 明确的非医疗问题，礼貌回应
                print("⚠️  非医疗相关问题，礼貌引导")
                self.audio.speak("我是医疗健康助手，请问您有什么医疗相关的问题吗？")
            else:
                # 无意义输入（噪音、漏网的干扰），静默忽略
                print("🔇 无意义输入，静默忽略")
            return

        # 【第二阶段】多模态融合 + 知识检索
        print("✅ 医疗相关问题，开始处理")
        GLOBAL_STATE["subtitle"] = "思考中..."
        answer = self.brain.think(text)
        self.audio.speak(answer)

if __name__ == "__main__":
    # 后台启动 AI
    threading.Thread(target=SystemController, daemon=True).start()
    # 前台启动 UI
    run_ui()