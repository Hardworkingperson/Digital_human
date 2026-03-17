import uvicorn
from fastapi import FastAPI, Body, HTTPException
from fastapi.responses import StreamingResponse
import torch
import soundfile as sf
import io
import os
import traceback

# F5-TTS 核心组件导入
from f5_tts.model import DiT
from f5_tts.infer.utils_infer import (
    load_vocoder,
    load_model,
    infer_process,
)

app = FastAPI()

# ==============================================================================
# 1. 路径配置
# ==============================================================================
CKPT_PATH = "/home/admin1108/weitiao/models/F5-TTS/model_1250000.safetensors"
VOCAB_PATH = "/home/admin1108/weitiao/models/F5-TTS/vocab.txt"
VOCODER_PATH = "/home/admin1108/weitiao/models/vocos-mel-24khz"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ==============================================================================
# 2. 全局模型加载
# ==============================================================================
print("\n🚀 [F5-TTS API] 正在启动...")

# --- 加载声码器 ---
print(f"⏳ 加载声码器: {VOCODER_PATH}")
vocoder = load_vocoder(is_local=True, local_path=VOCODER_PATH)

# --- 加载主模型 ---
print(f"⏳ 加载 DiT 模型: {CKPT_PATH}")
model_cfg = dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4)
model = load_model(
    model_cls=DiT,
    model_cfg=model_cfg,
    ckpt_path=CKPT_PATH,
    mel_spec_type="vocos",
    vocab_file=VOCAB_PATH,
    ode_method="euler",
    use_ema=True,
    device=DEVICE,
)
print("✅ 服务启动完成")

# ==============================================================================
# 3. API 接口
# ==============================================================================

@app.post("/tts")
async def text_to_speech(
    text: str = Body(..., embed=True),
    ref_audio_path: str = Body(..., embed=True),
    ref_text: str = Body(..., embed=True),
):
    print(f"\n📩 收到请求: '{text[:20]}...'")

    # 校验文件
    if not os.path.exists(ref_audio_path):
        raise HTTPException(status_code=404, detail=f"参考音频文件未找到: {ref_audio_path}")

    try:
        # =================================================================
        # 核心修正：完全复刻 Windows 成功逻辑
        # 1. 不手动调用 preprocess_ref_audio_text (让 infer_process 内部处理)
        # 2. 只有前3个参数按位置传 (路径, 参考文本, 生成文本)
        # =================================================================

        audio, sample_rate, _ = infer_process(
            ref_audio_path,   # [位置1] 参考音频路径 (直接传路径字符串)
            ref_text,         # [位置2] 参考文本
            text,             # [位置3] 生成文本
            model,            # [位置4] 模型对象
            vocoder,          # [位置5] 声码器
            # 下面是配置参数,通常用关键字没问题
            mel_spec_type="vocos",
            speed=1.0,
            nfe_step=32,
            cfg_strength=2.0,
            sway_sampling_coef=-1.0,
            device=DEVICE
        )

        # 序列化为音频流
        buffer = io.BytesIO()
        sf.write(buffer, audio, sample_rate, format='wav')
        buffer.seek(0)

        print(f"✅ 生成成功: {len(buffer.getvalue())/1024:.1f} KB")
        return StreamingResponse(buffer, media_type="audio/wav")

    except Exception as e:
        print(f"❌ 生成错误: {e}")
        # 打印完整堆栈以便调试
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)