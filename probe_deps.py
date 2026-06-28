# -*- coding: utf-8 -*-
"""
依赖探测脚本 —— 在 MaixCAM 板子上运行
目的：确认实现 DashScope 实时语音识别(WebSocket)所需的库是否可用

用法（在板子终端）：
    python probe_deps.py
把完整输出贴回给我，据此决定 WebSocket 用现成库还是 socket+ssl 手写。
"""

# DashScope 实时识别 WebSocket 地址（仅用于连通性测试）
WS_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/inference/"
API_KEY = "sk-dc4553ef7fe74c5283f05e4dc7d60adb"


def check_import(name):
    """尝试导入一个模块，返回 (是否成功, 版本或错误信息)"""
    try:
        mod = __import__(name)
        ver = getattr(mod, "__version__", "未知版本")
        return True, ver
    except Exception as e:
        return False, str(e)


def main():
    print("=" * 50)
    print("MaixCAM 依赖探测")
    print("=" * 50)

    # 1. Python 版本
    try:
        import sys
        print(f"[Python] {sys.version}")
    except Exception as e:
        print(f"[Python] 读取版本失败: {e}")

    # 2. 逐个探测关键库
    libs = [
        "json",            # JSON 解析（标准库，应有）
        "ssl",             # TLS（HTTPS/WSS 必需）
        "socket",          # 裸 socket（手写 HTTP/WS 的底座）
        "threading",       # 线程（也可用 maix 的 _thread）
        "websocket",       # websocket-client 库（首选，pip 包名 websocket-client）
        "requests",        # HTTP 客户端（文件转写方案会用）
        "urllib",          # 标准库 HTTP
        "hashlib",         # 签名用
        "hmac",            # 签名用
        "base64",          # 编码用
    ]
    print("-" * 50)
    print("库可用性：")
    results = {}
    for name in libs:
        ok, info = check_import(name)
        results[name] = ok
        flag = "✅" if ok else "❌"
        print(f"  {flag} {name:12s} {info}")

    # 3. maix 音频录制能力
    print("-" * 50)
    try:
        from maix import audio
        print("  ✅ maix.audio 可用（用于麦克风采集）")
    except Exception as e:
        print(f"  ❌ maix.audio 不可用: {e}")

    # 4. 如果有 websocket 库，做一次真实连接测试
    print("-" * 50)
    if results.get("websocket"):
        print("尝试用 websocket-client 连接 DashScope ...")
        try:
            import websocket
            ws = websocket.create_connection(
                WS_URL,
                header=["Authorization: bearer " + API_KEY],
                timeout=10,
            )
            print("  ✅ WebSocket 连接成功！实时方案可用 websocket-client 实现")
            ws.close()
        except Exception as e:
            print(f"  ⚠️ WebSocket 连接失败: {e}")
            print("     （可能是网络/鉴权问题，也可能需 socket+ssl 手写）")
    else:
        print("无 websocket-client 库 —— 将改用 socket+ssl 手写 WebSocket")

    print("=" * 50)
    print("探测完成，请把以上完整输出贴回")
    print("=" * 50)


if __name__ == "__main__":
    main()
