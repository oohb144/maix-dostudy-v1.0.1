# -*- coding: utf-8 -*-
"""
固定语音 WAV 生成脚本（跨平台，调用 edge-tts 库 API）

用法：
    python scripts/gen_voice.py            # 默认女声 zh-CN-XiaoxiaoNeural
    python scripts/gen_voice.py --voice zh-CN-YunxiNeural   # 换男声
    python scripts/gen_voice.py --out dist/voice

生成后把输出目录整目录拷到板子 /root/voice/
"""
import argparse
import asyncio
import os
import sys
import wave

try:
    import edge_tts
except ImportError:
    print("[错误] 未安装 edge-tts，正在自动安装 ...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "edge-tts"])
    import edge_tts

# edge-tts 只能输出 MP3，需解码成 PCM 写成真 WAV 给板子用
try:
    import miniaudio
except ImportError:
    print("[错误] 未安装 miniaudio（MP3->WAV 解码用），正在自动安装 ...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "miniaudio"])
    import miniaudio


def mp3_bytes_to_wav_bytes(mp3_bytes):
    """把 MP3 字节流解码成 16bit PCM，按原始采样率/声道如实包成 WAV 返回字节流。

    板子 play_wav_thread 会读 WAV 头里的 sample_rate / channel 重建 Player，
    所以无需强制重采样到 16kHz——保持解码原参数即可正常播放。
    """
    decoded = miniaudio.decode(mp3_bytes, output_format=miniaudio.SampleFormat.SIGNED16)
    # decoded.samples 是 array.array('h')，转 bytes
    import array
    raw = array.array('h', decoded.samples).tobytes()

    import io
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(decoded.nchannels)
        w.setsampwidth(2)
        w.setframerate(decoded.sample_rate)
        w.writeframes(raw)
    return buf.getvalue()


# (文件名, 文本) —— 与 config.py 的 VOICE_* 常量一一对应
PHRASES = [
    # A. 状态切换播报
    ("sys_ready.wav",        "系统已就绪"),
    ("start_recognize.wav",  "开始识别"),
    ("start_enroll.wav",     "请正对摄像头录入"),
    ("error_alert.wav",      "系统异常，请稍后"),
    # B. 识别结果反馈
    ("known_face.wav",       "欢迎回来"),
    ("stranger.wav",         "检测到陌生人"),
    # C. 命令回声确认（按界面分组）
    ("cmd_home.wav",         "已返回主页"),
    ("cmd_settings.wav",     "已进入设置"),
    ("cmd_enroll.wav",       "已进入录入"),
    ("cmd_recordings.wav",  "已打开录像"),
    ("cmd_start.wav",        "开始识别"),
    ("cmd_stop.wav",         "已停止"),
    # D. 录入与录制结果反馈
    ("enroll_ok.wav",        "录入成功"),
    ("enroll_fail.wav",      "录入失败，请重试"),
    ("record_saved.wav",     "录制已保存"),
    # E. 信息查询播报
    ("read_info_hint.wav",   "请查看屏幕上的系统信息"),
]


async def synthesize(voice, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    ok, fail = 0, 0
    for name, text in PHRASES:
        path = os.path.join(out_dir, name)
        try:
            # 1) edge-tts 合成 MP3 到内存
            communicate = edge_tts.Communicate(text, voice)
            mp3_data = b''
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_data += chunk["data"]
            # 2) MP3 -> 真 WAV（保持原采样率/声道），写盘
            wav_data = mp3_bytes_to_wav_bytes(mp3_data)
            with open(path, 'wb') as f:
                f.write(wav_data)
            ok += 1
            print(f"[OK]  {name}  <-  {text}")
        except Exception as e:
            fail += 1
            print(f"[失败] {name}  <-  {text}  : {e}")
    print(f"\n完成：成功 {ok} / 失败 {fail}，输出目录 {out_dir}")
    return fail


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", default="zh-CN-XiaoxiaoNeural",
                        help="edge-tts 音色（默认 zh-CN-XiaoxiaoNeural 女声；男声用 zh-CN-YunxiNeural）")
    parser.add_argument("--out", default=os.path.join("dist", "voice"),
                        help="输出目录（默认 dist/voice）")
    args = parser.parse_args()

    print(f"音色: {args.voice}")
    print(f"输出: {args.out}")
    print(f"共 {len(PHRASES)} 条语音\n")

    fail = asyncio.run(synthesize(args.voice, args.out))
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()