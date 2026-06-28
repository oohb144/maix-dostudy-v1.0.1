#!/bin/bash
# ============================================================
#  固定语音 WAV 生成脚本（Linux / macOS / WSL / Git Bash）
#  用 edge-tts 生成 17 条中文语音到 dist/voice/
#  生成后将 dist/voice/ 整目录拷到板子 /root/voice/
# ============================================================
set -e

VOICE="zh-CN-XiaoxiaoNeural"
OUT="dist/voice"

mkdir -p "$OUT"

echo "[1/3] 安装 edge-tts ..."
python -m pip install --quiet edge-tts

echo "[2/3] 生成 17 条语音到 $OUT ..."

# ---- A. 状态切换播报 ----
edge-tts --voice "$VOICE" --text "系统已就绪"               --write-media "$OUT/sys_ready.wav"
edge-tts --voice "$VOICE" --text "开始识别"                 --write-media "$OUT/start_recognize.wav"
edge-tts --voice "$VOICE" --text "请正对摄像头录入"         --write-media "$OUT/start_enroll.wav"
edge-tts --voice "$VOICE" --text "系统异常，请稍后"         --write-media "$OUT/error_alert.wav"

# ---- B. 识别结果反馈 ----
edge-tts --voice "$VOICE" --text "欢迎回来"                 --write-media "$OUT/known_face.wav"
edge-tts --voice "$VOICE" --text "检测到陌生人"             --write-media "$OUT/stranger.wav"

# ---- C. 命令回声确认（按界面分组）----
edge-tts --voice "$VOICE" --text "已返回主页"               --write-media "$OUT/cmd_home.wav"
edge-tts --voice "$VOICE" --text "已进入设置"               --write-media "$OUT/cmd_settings.wav"
edge-tts --voice "$VOICE" --text "已进入录入"               --write-media "$OUT/cmd_enroll.wav"
edge-tts --voice "$VOICE" --text "已打开录像"               --write-media "$OUT/cmd_recordings.wav"
edge-tts --voice "$VOICE" --text "开始识别"                 --write-media "$OUT/cmd_start.wav"
edge-tts --voice "$VOICE" --text "已停止"                   --write-media "$OUT/cmd_stop.wav"

# ---- D. 录入与录制结果反馈 ----
edge-tts --voice "$VOICE" --text "录入成功"                 --write-media "$OUT/enroll_ok.wav"
edge-tts --voice "$VOICE" --text "录入失败，请重试"         --write-media "$OUT/enroll_fail.wav"
edge-tts --voice "$VOICE" --text "录制已保存"               --write-media "$OUT/record_saved.wav"

# ---- E. 信息查询播报 ----
edge-tts --voice "$VOICE" --text "请查看屏幕上的系统信息"   --write-media "$OUT/read_info_hint.wav"

echo "[3/3] 完成。已生成 $(ls "$OUT"/*.wav | wc -l) 个 wav 于 $OUT"
echo "下一步：用 SCP 或 U 盘把 $OUT 拷到板子 /root/voice/"