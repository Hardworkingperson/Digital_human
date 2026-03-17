# modules/ui.py
import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QStackedLayout
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap, QFont
from config import WINDOW_WIDTH, WINDOW_HEIGHT, FPS, VIDEO_IDLE, VIDEO_TALKING, GLOBAL_STATE

# =========================================================================
# 1. 视频播放器适配器 (OpenCV -> Qt)
# =========================================================================
class SeamlessPlayer:
    def __init__(self, path):
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            print(f"❌ [UI] 无法加载视频: {path}")
            
    def get_frame_pixmap(self):
        """读取一帧并转换为 QPixmap"""
        ret, frame = self.cap.read()
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # 循环播放
            ret, frame = self.cap.read()
            
        # 1. 调整大小
        frame = cv2.resize(frame, (WINDOW_WIDTH, WINDOW_HEIGHT))
        
        # 2. 颜色转换 BGR -> RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 3. 如果是竖屏视频在横屏显示，可能需要旋转
        # frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        
        # 4. 转换为 Qt 图像格式
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        # PyQt5 写法
        qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        return QPixmap.fromImage(qt_image)

    def reset(self):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

# =========================================================================
# 2. 主窗口界面
# =========================================================================
class DigitalHumanWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("医养通 · 智能医疗座舱 (Qt5版)")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        # 设置黑色背景
        self.setStyleSheet("background-color: black;")
        
        # --- 布局管理器 ---
        # 使用 QStackedLayout 实现图层叠加 (视频在底，文字在顶)
        self.main_layout = QStackedLayout(self)
        self.main_layout.setStackingMode(QStackedLayout.StackAll)

        # --- 图层 1: 视频层 ---
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setScaledContents(True) # 让视频自适应窗口
        self.main_layout.addWidget(self.video_label)

        # --- 图层 2: UI 覆盖层 (HUD) ---
        self.hud_widget = QWidget(self)
        self.hud_layout = QVBoxLayout(self.hud_widget)
        # PyQt5 设置背景透明
        self.hud_widget.setAttribute(Qt.WA_TranslucentBackground)
        
        # 1. 顶部：视觉识别状态
        self.vision_label = QLabel("")
        # 字体设置
        font = QFont("Microsoft YaHei", 18)
        font.setBold(True)
        self.vision_label.setFont(font)
        self.vision_label.setStyleSheet("color: #00FF00; background: rgba(0, 0, 0, 0.5); padding: 10px; border-radius: 5px;")
        self.vision_label.hide() # 默认隐藏
        self.hud_layout.addWidget(self.vision_label, alignment=Qt.AlignLeft | Qt.AlignTop)
        
        self.hud_layout.addStretch() # 弹簧

        # 2. 底部：字幕条
        self.subtitle_label = QLabel("系统初始化完成...")
        self.subtitle_label.setFont(QFont("Microsoft YaHei", 24))
        self.subtitle_label.setWordWrap(True) # 自动换行
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        # 样式：半透明黑底 + 青色文字 + 荧光效果
        self.subtitle_label.setStyleSheet("""
            QLabel {
                color: #00FFFF;
                background-color: rgba(0, 20, 40, 0.7);
                border-top: 2px solid #00FFFF;
                padding: 20px;
                border-radius: 10px;
            }
        """)
        self.hud_layout.addWidget(self.subtitle_label)
        
        self.main_layout.addWidget(self.hud_widget)

        # --- 初始化视频资源 ---
        print("⏳ [UI] 正在加载视频资源...")
        self.player_idle = SeamlessPlayer(VIDEO_IDLE)
        self.player_talk = SeamlessPlayer(VIDEO_TALKING)

        # --- 启动定时器 (30 FPS 刷新) ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(int(1000 / FPS))

    def update_ui(self):
        """核心渲染循环"""
        if not GLOBAL_STATE["running"]:
            self.close()
            return

        # 1. 视频重置逻辑
        if GLOBAL_STATE["new_sentence"]:
            self.player_talk.reset()
            GLOBAL_STATE["new_sentence"] = False

        # 2. 获取当前视频帧
        if GLOBAL_STATE["is_speaking"]:
            pixmap = self.player_talk.get_frame_pixmap()
        else:
            pixmap = self.player_idle.get_frame_pixmap()
        
        self.video_label.setPixmap(pixmap)

        # 3. 更新字幕
        current_text = GLOBAL_STATE["subtitle"]
        if self.subtitle_label.text() != current_text:
            self.subtitle_label.setText(current_text)

        # 4. 更新视觉识别状态
        vision_text = GLOBAL_STATE["vision_label"]
        if vision_text:
            self.vision_label.setText(f"👁️ 视觉感知: {vision_text}")
            self.vision_label.show()
        else:
            self.vision_label.hide()

    def closeEvent(self, event):
        """窗口关闭时触发"""
        GLOBAL_STATE["running"] = False
        event.accept()

# =========================================================================
# 3. 启动函数 (main.py 调用)
# =========================================================================
def run_ui_loop():
    # 创建 Qt 应用实例
    app = QApplication(sys.argv)
    
    # 创建并显示窗口
    window = DigitalHumanWindow()
    # 全屏显示效果更震撼 (按 Alt+F4 退出)
    # window.showFullScreen() 
    window.show() # 窗口模式
    
    # PyQt5 推荐使用 exec_() (为了兼容 Python2 关键字，虽然 Python3 用 exec() 也可以，但 exec_() 最稳)
    sys.exit(app.exec_())