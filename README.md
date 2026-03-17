# 多模态数字人系统全流程说明（Markdown版）

## 1. 核心交互场景：从“待机”到“多模态响应”的全过程

### 🎬 第一幕：静默守候 (The Silent Watcher)

**用户视角：**

* 数字人医生保持自然呼吸、眨眼（播放 `idle.mp4`）。
* 摄像头对着走廊，无弹窗干扰。

**后台逻辑：**

* **UI线程（modules/ui.py）**：以 30FPS 刷新，从 `idle.mp4` 读取帧。
* **视觉线程（modules/vision.py）**：后台每 0.2 秒读取一次摄像头。

**视觉识别场景：**

* YOLO 检测到“阿莫西林”。
* 悄悄更新：`GLOBAL_STATE["vision_label"] = "阿莫西林"`。

**听觉线程：**

* Whisper 一直监听环境声音，处于 VAD 静音检测状态，未触发识别。

---

### 🎬 第二幕：语音唤醒与意图识别 (The Intent Trigger)

**用户视角：**
“医生，我手里这个药一天吃几次？”

**后台逻辑：**

1. **STT 转写（audio.py）**：
   Whisper → 文本：`"我手里这个药一天吃几次"`

2. **主控回调（main.py/process）**：

   * 判断关键词：“手里”“这个药” → **需要视觉辅助**。

3. **跨模态融合：**

   * 读取 `GLOBAL_STATE["vision_label"]` → “阿莫西林”。
   * 重新生成实际问题：

     > “我现在手里拿着【阿莫西林】，请问阿莫西林一天吃几次？”

4. **异常情况（无视觉识别）**：

   * 返回：“请您将药盒举到摄像头前再问一次。”

---

### 🎬 第三幕：认知推理 (The Cognitive Reasoning)

1. **提问送入 brain.py**

2. **RAG 检索流程：**

   * embedding → 搜索向量库 `data/medical_vector_db`
   * 找到说明书内容：

     > “成人一次0.5g，每6~8小时1次。”

3. **LLM 生成（Ollama / Qwen2.5）**：
   输出：

   > “阿莫西林通常口服，成人一次0.5克，一日3到4次。建议饭后服用以减少胃肠刺激。”

---

### 🎬 第四幕：视听同步表达 (The Synchronized Expression)

**用户视角：**
数字人张嘴、发声、语音与口型同步。

**后台逻辑：**

* **TTS生成**：F5-TTS API 返回音频。

* **状态机切换：**

  * `is_speaking = True`
  * `new_sentence = True`

* **UI响应：**

  * 检测到说话 → 切换到 `talking.mp4`。
  * `new_sentence=True` → 视频跳到 0 秒，保证从“张嘴”开始。

* **阻塞音频播放**：`sd.wait()` 保证视听同步。

* **结束**：音频播放结束 → `is_speaking=False` → UI 切回 `idle.mp4`。

---

## 2. 系统架构设计

### 🏗️ 多线程异步架构

本系统采用**事件驱动的多线程架构**，通过全局状态黑板协调各模块：

```
┌─────────────────────────────────────────────────────────────┐
│                     GLOBAL_STATE (共享内存)                   │
│  { is_speaking, new_sentence, vision_label, subtitle }      │
└─────────────────────────────────────────────────────────────┘
         ↑                  ↑                   ↑
         │                  │                   │
    ┌────┴────┐       ┌─────┴──────┐      ┌────┴─────┐
    │ Vision  │       │   Audio    │      │    UI    │
    │ Thread  │       │   Thread   │      │  Thread  │
    │ (YOLO)  │       │ (Whisper)  │      │ (PyQt5)  │
    └────┬────┘       └─────┬──────┘      └────┬─────┘
         │                  │                   │
         └──────────┬───────┴───────────────────┘
                    ↓
            ┌───────────────┐
            │ SystemController│
            │  (main.py)     │
            │  - 意图识别    │
            │  - 跨模态融合  │
            └───────┬────────┘
                    ↓
            ┌───────────────┐
            │ MedicalBrain  │
            │  (RAG + LLM)  │
            └───────────────┘
```

### 🔄 数据流转示意

```
用户说话 → Whisper(STT) → 意图识别 → 是否医疗相关？
                                         ↓ 是
                          是否需要视觉辅助？("这个药")
                                         ↓ 是
                          读取 vision_label → 跨模态融合
                                         ↓
                          RAG检索 → LLM生成 → F5-TTS
                                         ↓
                          音频播放 + 视频同步 → 用户感知
```

### 🎯 核心设计理念

1. **解耦设计**：各模块独立运行，通过 GLOBAL_STATE 松耦合通信
2. **异步并行**：视觉、听觉、UI 同时工作，互不阻塞
3. **状态驱动**：UI 根据 is_speaking 自动切换视频
4. **智能过滤**：噪音词过滤 + 意图识别 + 静默机制

---

## 3. Python 文件功能拆解（File by File）

### 🛠️ 1. config.py —— 全局神经中枢

**功能：** 全局共享内存、基础路径。

**关键内容：**

* `GLOBAL_STATE`：跨线程通信黑板。
* `BASE_DIR`：自动定位项目根目录。

---

### 🛠️ 2. main.py —— 大脑皮层（总控）

**功能：**

* 决策中心，不负责看/听，只负责“判断与分发”。

**关键逻辑：**

* `SystemController` 初始化所有模块。
* `process()` 根据意图决定是否使用视觉信息。

---

### 🛠️ 3. modules/vision.py —— 沉默的观察者

**功能：** YOLOv8 目标检测后台线程。

**关键逻辑：**

* Daemon Thread 循环识别。
* **只写不读**：仅修改 `GLOBAL_STATE["vision_label"]`。
* 避免说话时推理：`if not GLOBAL_STATE["is_speaking"]`。

---

### 🛠️ 4. modules/audio.py —— 耳与口（ASR + TTS）

**功能：** Whisper + F5-TTS。

**关键逻辑：**

* Whisper 在 `is_speaking=True` 时停止监听（避免听到自己）。
* sounddevice 阻塞播放用于视听同步。

---

### 🛠️ 5. modules/brain.py —— 海马体（RAG）

**功能：** LangChain RAG 推理。

**关键逻辑：**

* Embedding 模型与 create_db.py 完全一致。
* Prompt 限制：严格基于知识库、字数限制确保医疗合规。

---

### 🛠️ 6. modules/ui.py —— 面部表情层

**功能：** PyQt5 + OpenCV 渲染视频。

**关键逻辑：**

* 用 cv2 解码帧 → 转为 Qt 图片。
* 每 33ms 检查 `is_speaking` 决定播放 idle 或 talking。

---

### 🛠️ 7. create_db.py —— 知识工厂

**功能：** 构建与更新医疗向量数据库。

**关键流程：**

* 文档清洗 → 分块 → 向量化 → 入库。
* 比赛中可展示"数据工程"能力。

---

### 🛠️ 8. f5-tts.py —— 独立 TTS API 服务

**功能：** FastAPI 实现的文本转语音 HTTP 服务。

**关键逻辑：**

* 加载 F5-TTS 模型与 Vocos 声码器。
* 提供 `/tts` POST 端点，接收文本返回 WAV 音频流。
* 支持参考音频克隆，实现个性化音色。

**部署方式：**

```bash
python f5-tts.py
# 监听 http://127.0.0.1:8000
```

**API 调用示例：**

```python
payload = {
    "text": "阿莫西林通常一日三次",
    "ref_audio_path": "assets/ref.wav",
    "ref_text": "参考音频的文本内容"
}
requests.post("http://127.0.0.1:8000/tts", json=payload)
```

---

## 4. 技术栈详解

### 🤖 AI 模型层

| 模块 | 模型 | 用途 | 推理设备 |
|------|------|------|----------|
| 视觉识别 | YOLOv8 | 药物目标检测 | CUDA |
| 语音识别 | Whisper (faster-whisper) | 中文语音转文本 | CUDA |
| 文本嵌入 | text2vec-base-chinese | 向量化检索 | CUDA |
| 大语言模型 | Qwen2.5:14b (Ollama) | 医疗知识问答 | CUDA |
| 语音合成 | F5-TTS + Vocos | 文本转自然语音 | CUDA |

### 🔧 框架与库

| 类别 | 技术选型 |
|------|----------|
| Web 框架 | FastAPI (TTS 服务) |
| AI 框架 | LangChain, HuggingFace Transformers |
| 向量数据库 | Chroma |
| GUI | PyQt5 |
| 视频处理 | OpenCV (cv2) |
| 音频处理 | sounddevice, soundfile |
| 模型推理 | Ollama, ONNX Runtime |

### 💾 数据存储

```
data/
└── medical_vector_db/        # Chroma 向量数据库
    ├── chroma.sqlite3        # 元数据
    └── embeddings/           # 向量索引
```

---

## 5. 环境配置与部署

### 📋 系统要求

* **操作系统**：Windows 10/11, Linux (Ubuntu 20.04+)
* **GPU**：NVIDIA RTX 3060 及以上（推荐 RTX 3090）
* **显存**：≥ 12GB
* **内存**：≥ 16GB
* **Python**：3.9 ~ 3.11

### 🚀 快速部署

#### 1. 安装依赖

```bash
# 创建虚拟环境
conda create -n yiynagtong python=3.10
conda activate yiynagtong

# 安装 PyTorch (CUDA 11.8)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 安装项目依赖
pip install -r requirements.txt
```

#### 2. 安装 Ollama 并拉取模型

```bash
# 安装 Ollama (https://ollama.com)
# Windows: 下载安装包
# Linux: curl -fsSL https://ollama.com/install.sh | sh

# 拉取 Qwen2.5 模型
ollama pull qwen2.5:14b
```

#### 3. 下载模型权重

```bash
# 自动下载脚本（需联网）
python download_models.py

# 或手动下载到 models/ 目录：
# - YOLOv8: yolo/best.pt
# - Whisper: stt/faster-whisper-large-v3
# - F5-TTS: F5-TTS/
# - Vocos: vocos-mel-24khz/
```

#### 4. 构建向量数据库

```bash
python create_db.py
# 生成 data/medical_vector_db/
```

#### 5. 启动系统

```bash
# 终端1: 启动 TTS 服务
python f5-tts.py

# 终端2: 启动主程序
python main.py
```

---

## 6. 使用说明

### 🎮 基本操作

1. **启动系统**：运行 `python main.py`
2. **数字人待机**：系统自动播放 idle.mp4（自然呼吸）
3. **药物识别**：将药盒举到摄像头前，YOLO 自动识别
4. **语音提问**：对着麦克风说话（如"这个药一天吃几次？"）
5. **系统回答**：数字人切换到 talking.mp4，口型同步播放答案

### 📝 支持的问题类型

**医疗相关**（会正常回答）：
* "感冒了怎么办？"
* "阿莫西林的用法用量"
* "头疼吃什么药？"
* "这个药有副作用吗？"（需配合视觉识别）

**非医疗问题**（礼貌引导）：
* "你好" → "我是医疗健康助手，请问您有什么医疗相关的问题吗？"
* "今天天气怎么样？" → 礼貌引导

**噪音干扰**（静默忽略）：
* 环境噪音、语气词（"嗯"、"啊"）等会被自动过滤

### ⚙️ 配置调整

在 `config.py` 中可修改：

```python
# 硬件配置
MIC_DEVICE_ID = 1          # 麦克风设备 ID
CAMERA_ID = 0              # 摄像头 ID
WINDOW_WIDTH = 1080        # 窗口宽度
WINDOW_HEIGHT = 1920       # 窗口高度

# API 配置
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:14b"
TTS_API_URL = "http://127.0.0.1:8000/tts"
```

---

## 7. 核心优化亮点

### ✨ 优化1：智能意图识别过滤

**问题**：系统会响应任何声音，包括噪音和非医疗问题。

**解决方案**：
* 在 `brain.py` 添加 `is_medical_query()` 方法
* 使用 Ollama 判断问题是否与医疗相关
* 非医疗问题礼貌拒绝，提升专业性

**实现位置**：`modules/brain.py:28-43`, `main.py:24-36`

### ✨ 优化2：噪音词过滤机制

**问题**：Whisper 在静音时会误识别"点点点"、"嗯"等无意义文本，导致系统无故回复。

**解决方案**：
* 在 `audio.py` 添加噪音词黑名单
* 三层过滤：长度过滤 + 黑名单过滤 + 纯标点过滤
* 对无意义输入静默处理，避免突兀回复

**实现位置**：`modules/audio.py:19-24`, `modules/audio.py:49-56`

**效果对比**：

| 场景 | 优化前 | 优化后 |
|------|--------|--------|
| 环境噪音 | ❌ 播放引导话术 | ✅ 静默忽略 |
| 语气词（"嗯"） | ❌ 播放引导话术 | ✅ 静默忽略 |
| 有意义闲聊 | ❌ 播放引导话术 | ✅ 播放引导话术 |
| 医疗问题 | ✅ 正常处理 | ✅ 正常处理 |

### ✨ 优化3：跨模态融合

**特色**：当用户说"这个药"时，自动结合视觉识别结果理解指代。

**实现**：
* 检测关键词（"手里"、"这个药"）
* 从 `GLOBAL_STATE["vision_label"]` 读取 YOLO 识别结果
* 重组问题："这个药一天吃几次？" → "阿莫西林一天吃几次？"

---

## 8. 项目特色与创新点

### 🌟 技术创新

1. **多模态理解**：视觉 + 语音信息深度融合
2. **实时视听同步**：口型与音频毫秒级同步
3. **智能过滤机制**：三层过滤 + 意图识别，避免误触发
4. **医疗合规设计**：RAG 严格基于知识库，防止 LLM 幻觉

### 🎯 应用场景

* **智能医疗座舱**：医院、药房、健康小屋
* **药物咨询机器人**：患者自助式查询
* **医疗辅助助手**：个性化用药指导

### 🏆 竞赛优势

* **完整性**：从感知到表达的全链路实现
* **实用性**：真实医疗场景可直接部署
* **可扩展性**：模块化设计，易于添加新功能
* **技术深度**：涉及 CV、NLP、语音、多模态等前沿技术

---

## 9. 常见问题 (FAQ)

### Q1: 如何查看麦克风设备 ID？

```python
import sounddevice as sd
print(sd.query_devices())
```

### Q2: 向量数据库如何更新？

修改 `create_db.py` 中的 `RAW_DATA`，然后重新运行：

```bash
python create_db.py
```

### Q3: 如何更换数字人视频？

替换 `assets/idle.mp4` 和 `assets/talking.mp4`，保持分辨率一致。

### Q4: 如何调整 LLM 回答长度？

修改 `modules/brain.py:19` 的 Prompt：

```python
template="基于资料回答：{context}\n问题：{question}\n要求：简练专业，100字内。"
```

### Q5: 系统无响应怎么办？

检查日志输出：
* `👂 [Audio] 听到: xxx` - 确认语音识别是否正常
* `🔍 [Brain] 意图识别: xxx` - 确认意图识别结果
* `🤖 [Audio] 播放: xxx` - 确认 TTS 是否正常

---

## 10. 未来优化方向

### 🚀 功能扩展

* [ ] 支持多轮对话上下文记忆
* [ ] 添加表情识别（情绪分析）
* [ ] 集成体征监测（心率、血压）
* [ ] 支持多语言问答

### ⚡ 性能优化

* [ ] 模型量化（INT8）降低显存占用
* [ ] 流式 TTS 减少延迟
* [ ] 向量检索加速（FAISS 替代 Chroma）

### 🎨 体验优化

* [ ] 更自然的数字人动作（手势、眼神）
* [ ] 背景音乐与环境音效
* [ ] 移动端适配（Web 版本）

---

## 11. 致谢与参考

### 📚 技术参考

* [YOLOv8](https://github.com/ultralytics/ultralytics) - 目标检测
* [Whisper](https://github.com/openai/whisper) - 语音识别
* [F5-TTS](https://github.com/SWivid/F5-TTS) - 语音合成
* [LangChain](https://github.com/langchain-ai/langchain) - RAG 框架
* [Ollama](https://ollama.com) - 本地 LLM 推理

---

## 12. 项目总结

**医养通多模态数字人系统**是一个集成了**视觉识别、语音交互、知识推理、数字人渲染**的完整 AI 解决方案。通过**智能过滤、意图识别、跨模态融合**等创新设计，实现了自然流畅的人机交互体验。

系统采用**模块化设计**，各组件独立运行、松耦合通信，易于扩展和维护。在医疗健康领域具有广阔的应用前景，可直接部署于医院、药房等实际场景。

**核心竞争力**：
* ✅ 真实场景可用的完整系统
* ✅ 多模态深度融合
* ✅ 医疗合规的知识推理
* ✅ 自然流畅的交互体验

---

**项目开发者**：[您的名字/团队名称]
**最后更新**：2025-12-14
**版本**：v1.0.0
