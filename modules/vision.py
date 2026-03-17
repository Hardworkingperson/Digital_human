import cv2
import threading
import time
from config import YOLO_MODEL_PATH, CAMERA_ID, GLOBAL_STATE

class MedicineDetector:
    def __init__(self):
        print(f"👁️ [Vision] 加载模型: {YOLO_MODEL_PATH}")
        try:
            from ultralytics import YOLO
            self.model = YOLO(YOLO_MODEL_PATH)
            self.names = self.model.names
            print("✅ [Vision] 模型加载成功")
        except Exception as e:
            print(f"⚠️ [Vision] 加载失败: {e}")
            self.model = None

    def start(self, callback_func):
        threading.Thread(target=self._loop, args=(callback_func,), daemon=True).start()

    def _loop(self, callback):
        cap = cv2.VideoCapture(CAMERA_ID)
        last_time = 0
        while GLOBAL_STATE["running"]:
            ret, frame = cap.read()
            if not ret:
                time.sleep(1)
                continue

            # 说话时暂停识别
            if not GLOBAL_STATE["is_speaking"] and self.model:
                # 5秒识别一次
                if time.time() - last_time > 5.0:
                    results = self.model(frame, verbose=False, conf=0.6)
                    for r in results:
                        for box in r.boxes:
                            label = self.names[int(box.cls[0])]
                            GLOBAL_STATE["vision_label"] = label
                            print(f"📸 [Vision] 捕捉到: {label}")
                            
                            # 触发智能体
                            query = f"我手里拿的是{label}，请介绍它的功效和用法。"
                            callback(query)
                            last_time = time.time()
                            break
            time.sleep(0.2)
        cap.release()