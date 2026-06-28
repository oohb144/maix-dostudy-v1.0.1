# -*- coding: utf-8 -*-
"""
音频播放独立测试 —— 在板子上运行，隔离 wav 能否正常播放

用法：
    python test_audio_play.py
把完整输出贴回。
"""

import os
from maix import audio, time

# 待测文件（按 config.py 里的路径）
FILES = [
    "/root/error.wav",
    "/root/meldix-success.wav",
    "/root/melodix-success.wav",  # 备选拼写，万一文件名不同
]


def list_wav():
    """列出 /root 下所有 wav，确认真实文件名"""
    print("=" * 50)
    print("/root 下的 wav 文件：")
    try:
        for f in os.listdir("/root"):
            if f.lower().endswith(".wav"):
                full = "/root/" + f
                size = os.path.getsize(full)
                print(f"  {full}  ({size} 字节)")
    except Exception as e:
        print(f"  列目录失败: {e}")
    print("=" * 50)


def test_play(path):
    """尝试播放单个文件"""
    print(f"\n--- 测试: {path} ---")
    if not os.path.exists(path):
        print("  [跳过] 文件不存在")
        return
    try:
        player = audio.Player(path)
        player.volume(80)
        print("  开始播放（阻塞）...")
        player.play()
        print("  ✅ 播放调用完成")
        del player
        time.sleep_ms(300)
    except Exception as e:
        print(f"  ❌ 播放失败: {e}")


def main():
    list_wav()
    for path in FILES:
        test_play(path)
    print("\n测试结束。若听到声音=正常；若报错=贴回错误信息。")


if __name__ == "__main__":
    main()
