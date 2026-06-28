# -*- coding: utf-8 -*-
"""
MaixCAM2 智能系统 - 在线语音识别模块（DashScope paraformer-realtime-v2）

功能：
- 通过麦克风实时采集 PCM 音频，经 WebSocket 流式上传阿里云 DashScope
- 使用 paraformer-realtime-v2 模型实时返回中文识别文本
- 对识别文本做关键词（中文子串）匹配，触发界面/功能切换回调

设计目标：
- 对外接口与离线版 VoiceRecognition 保持一致（start/stop/set_pause_callback/destroy）
- 非阻塞：识别在独立线程运行，不影响主视频循环
- 自动重连：会话断开/超时后自动重启
- 资源让渡：通过 pause 回调，在录像/识别等高负载状态暂停采集与上传

依赖（已在板子上确认可用）：
- websocket-client 1.9.0
- maix.audio
"""

import json
import uuid
import ssl
import _thread

import websocket  # websocket-client
from maix import audio, app, time


# ==================== 配置常量 ====================

# DashScope 实时识别 WebSocket 地址
WS_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/inference/"

# 识别模型
ASR_MODEL = "paraformer-realtime-v2"

# 音频参数（必须与采集一致）
SAMPLE_RATE = 16000          # 采样率 16kHz
AUDIO_CHANNEL = 1            # 单声道
AUDIO_CHUNK_MS = 100         # 每次采集/上传的音频块时长（毫秒）

# 同一条命令的去抖时间（毫秒）—— 防止一句话重复触发
TRIGGER_DEBOUNCE_MS = 1500


class OnlineVoiceRecognition:
    """
    在线语音识别器（DashScope 实时流式）

    用法：
        ovr = OnlineVoiceRecognition(api_key="sk-xxx")
        ovr.set_pause_callback(should_pause)
        ovr.start(keywords={'打开设置': 'settings'}, callback=on_command)
        ...
        ovr.destroy()
    """

    def __init__(self, api_key,
                 sample_rate=SAMPLE_RATE,
                 pause_sleep_ms=200,
                 reconnect_delay_ms=800):
        """
        初始化在线语音识别器

        参数：
            api_key: DashScope API Key
            sample_rate: 采样率，需与模型参数一致
            pause_sleep_ms: 暂停状态下的轮询睡眠时长
            reconnect_delay_ms: 会话断开后的重连等待时长
        """
        self._api_key = api_key
        self._sample_rate = sample_rate
        self._pause_sleep_ms = pause_sleep_ms
        self._reconnect_delay_ms = reconnect_delay_ms

        # 关键词字典 {中文文本: 命令名}
        self._keywords = {}
        # 识别命中回调（接收命令名）
        self._callback = None
        # 暂停判断回调（返回 True 时暂停采集上传）
        self._pause_callback = None

        # 运行状态
        self._is_running = False

        # 当前会话相关对象
        self._ws = None                 # 当前 WebSocketApp
        self._task_id = None            # 当前任务 ID
        self._task_started = False      # 服务端是否已就绪（可发送音频）
        self._session_active = False    # 当前会话是否存活
        self._recorder = None           # 麦克风录音对象

        # 命令去抖记录 {命令名: 上次触发时间ms}
        self._last_trigger = {}

        print("[在线语音] 模块初始化完成")

    # ==================== 配置接口 ====================

    def set_keywords(self, keywords):
        """设置关键词字典 {中文文本: 命令名}"""
        self._keywords = keywords or {}
        print(f"[在线语音] 设置关键词: {len(self._keywords)} 个")

    def set_callback(self, callback):
        """设置识别命中回调，回调接收命令名字符串"""
        self._callback = callback
        print("[在线语音] 设置识别回调")

    def set_pause_callback(self, callback):
        """设置暂停判断回调，返回 True 时暂停采集上传"""
        self._pause_callback = callback
        print("[在线语音] 设置暂停回调")

    def is_running(self):
        """是否正在运行"""
        return self._is_running

    # ==================== 启停控制 ====================

    def start(self, keywords=None, callback=None):
        """
        启动在线语音识别

        参数：
            keywords: 关键词字典（可选）
            callback: 识别回调（可选）

        返回：
            True 启动成功 / False 启动失败
        """
        if self._is_running:
            print("[在线语音] 已在运行")
            return True

        if keywords:
            self.set_keywords(keywords)
        if callback:
            self.set_callback(callback)

        if not self._keywords:
            print("[在线语音] 未设置关键词，启动失败")
            return False

        try:
            self._is_running = True
            _thread.start_new_thread(self._session_loop, ())
            print("[在线语音] 已启动，支持的关键词:")
            for text, cmd in self._keywords.items():
                print(f"  - {text} -> {cmd}")
            return True
        except Exception as e:
            print(f"[在线语音] 启动失败: {e}")
            self._is_running = False
            return False

    def stop(self):
        """停止在线语音识别"""
        if not self._is_running:
            return
        self._is_running = False
        self._close_session()
        print("[在线语音] 已停止")

    def destroy(self):
        """销毁识别器"""
        self.stop()
        self._teardown_recorder()
        print("[在线语音] 已销毁")

    # ==================== 会话主循环 ====================

    def _is_paused(self):
        """根据暂停回调判断当前是否应暂停"""
        if self._pause_callback:
            try:
                return bool(self._pause_callback())
            except Exception as e:
                print(f"[在线语音] 暂停回调异常: {e}")
        return False

    def _session_loop(self):
        """
        会话调度线程：
        - 暂停时释放麦克风并等待
        - 否则建立一次识别会话（阻塞运行），断开后自动重连
        """
        print("[在线语音] 会话线程启动")
        while self._is_running and not app.need_exit():
            # 暂停：释放麦克风，给主循环让出资源
            if self._is_paused():
                self._teardown_recorder()
                time.sleep_ms(self._pause_sleep_ms)
                continue

            try:
                self._run_one_session()
            except Exception as e:
                print(f"[在线语音] 会话异常: {e}")

            # 一次会话结束，稍等后重连（除非已停止/已暂停）
            if self._is_running and not app.need_exit():
                time.sleep_ms(self._reconnect_delay_ms)

        self._teardown_recorder()
        print("[在线语音] 会话线程退出")

    def _run_one_session(self):
        """建立并运行一次完整的识别会话（阻塞直到连接关闭）"""
        self._task_id = uuid.uuid4().hex
        self._task_started = False
        self._session_active = True

        # 创建 WebSocketApp，注册回调
        self._ws = websocket.WebSocketApp(
            WS_URL,
            header=["Authorization: bearer " + self._api_key],
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )

        # run_forever 阻塞运行，收到 close 后返回
        # 板子常缺 CA 根证书，跳过证书校验避免 CERTIFICATE_VERIFY_FAILED
        self._ws.run_forever(
            ping_interval=20,
            ping_timeout=10,
            sslopt={"cert_reqs": ssl.CERT_NONE},
        )

        # 会话收尾
        self._session_active = False
        self._ws = None

    def _close_session(self):
        """主动关闭当前会话"""
        self._session_active = False
        ws = self._ws
        if ws:
            try:
                ws.close()
            except Exception:
                pass

    # ==================== WebSocket 回调 ====================

    def _on_open(self, ws):
        """连接建立：发送 run-task 指令，并启动音频上传线程"""
        run_task = {
            "header": {
                "action": "run-task",
                "task_id": self._task_id,
                "streaming": "duplex",
            },
            "payload": {
                "task_group": "audio",
                "task": "asr",
                "function": "recognition",
                "model": ASR_MODEL,
                "parameters": {
                    "format": "pcm",
                    "sample_rate": self._sample_rate,
                    "language_hints": ["zh", "en"],
                },
                "input": {},
            },
        }
        try:
            ws.send(json.dumps(run_task))
            print("[在线语音] 已发送 run-task，等待服务端就绪...")
        except Exception as e:
            print(f"[在线语音] 发送 run-task 失败: {e}")
            self._close_session()
            return

        # 启动音频采集上传线程
        _thread.start_new_thread(self._audio_sender, (ws,))

    def _on_message(self, ws, message):
        """收到服务端消息（控制事件为 JSON 文本）"""
        try:
            msg = json.loads(message)
        except Exception:
            return

        header = msg.get("header", {})
        event = header.get("event", "")

        if event == "task-started":
            self._task_started = True
            print("[在线语音] 服务端就绪，开始上传音频")

        elif event == "result-generated":
            self._handle_result(msg.get("payload", {}))

        elif event == "task-finished":
            print("[在线语音] 任务完成")
            self._close_session()

        elif event == "task-failed":
            code = header.get("error_code", "")
            text = header.get("error_message", "")
            print(f"[在线语音] 任务失败: {code} {text}")
            self._close_session()

    def _on_error(self, ws, error):
        """连接错误"""
        print(f"[在线语音] WebSocket 错误: {error}")
        self._session_active = False

    def _on_close(self, ws, status_code, msg):
        """连接关闭"""
        self._session_active = False
        self._task_started = False

    # ==================== 结果处理与关键词匹配 ====================

    def _handle_result(self, payload):
        """解析识别结果，整句结束时做关键词匹配"""
        sentence = payload.get("output", {}).get("sentence", {})
        if not sentence:
            return

        text = sentence.get("text", "") or ""
        # sentence_end 为 True 表示一句话已说完（最终结果）
        is_end = sentence.get("sentence_end", False)

        if not text:
            return

        # 仅在整句结束时触发，避免中间结果重复命中
        if is_end:
            print(f"[在线语音] 识别: {text}")
            self._match_keywords(text)

    def _match_keywords(self, text):
        """在识别文本中匹配关键词并触发回调（带去抖）"""
        now = time.ticks_ms()
        for kw, command in self._keywords.items():
            if kw in text:
                last = self._last_trigger.get(command, 0)
                if now - last < TRIGGER_DEBOUNCE_MS:
                    continue
                self._last_trigger[command] = now
                print(f"[在线语音] 命中关键词: {kw} -> {command}")
                if self._callback:
                    try:
                        self._callback(command)
                    except Exception as e:
                        print(f"[在线语音] 回调执行失败: {e}")
                # 一句话只触发一个命令
                break

    # ==================== 音频采集与上传 ====================

    def _ensure_recorder(self):
        """惰性创建麦克风录音对象"""
        if self._recorder is None:
            self._recorder = audio.Recorder(
                sample_rate=self._sample_rate,
                channel=AUDIO_CHANNEL,
            )
            self._recorder.volume(100)
        return self._recorder

    def _teardown_recorder(self):
        """释放麦克风录音对象"""
        if self._recorder is not None:
            try:
                del self._recorder
            except Exception:
                pass
            self._recorder = None

    def _audio_sender(self, ws):
        """
        音频上传线程：
        - 等待服务端就绪
        - 持续采集小块 PCM 并以二进制帧上传
        - 暂停/停止/断开时退出，并发送 finish-task
        """
        # 等待 task-started（最多等约 5 秒）
        wait_ms = 0
        while (self._session_active and not self._task_started
               and self._is_running and wait_ms < 5000):
            time.sleep_ms(50)
            wait_ms += 50

        if not self._task_started:
            print("[在线语音] 等待服务端就绪超时")
            self._close_session()
            return

        try:
            recorder = self._ensure_recorder()
        except Exception as e:
            print(f"[在线语音] 麦克风初始化失败: {e}")
            self._close_session()
            return

        # 持续采集并上传
        while (self._session_active and self._is_running
               and not app.need_exit()):
            # 进入暂停状态：结束本次会话
            if self._is_paused():
                print("[在线语音] 进入暂停，结束当前会话")
                break

            try:
                pcm = recorder.record(AUDIO_CHUNK_MS)
                if pcm:
                    ws.send(pcm, opcode=websocket.ABNF.OPCODE_BINARY)
            except Exception as e:
                print(f"[在线语音] 音频上传异常: {e}")
                break

        # 通知服务端结束任务
        try:
            finish_task = {
                "header": {
                    "action": "finish-task",
                    "task_id": self._task_id,
                    "streaming": "duplex",
                },
                "payload": {"input": {}},
            }
            ws.send(json.dumps(finish_task))
        except Exception:
            pass

        # 关闭连接，触发会话循环重连/暂停处理
        self._close_session()


# ==================== 独立测试入口 ====================

if __name__ == "__main__":
    # 直接运行本文件可单独测试在线识别（打印识别结果与命中命令）
    API_KEY = "sk-dc4553ef7fe74c5283f05e4dc7d60adb"

    # 测试关键词：中文文本子串匹配
    TEST_KEYWORDS = {
        "主界面": "home",
        "回到主页": "home",
        "设置": "settings",
        "录入": "enroll",
        "录像": "recordings",
        "开始识别": "recognize",
        "停止": "stop",
        "开始": "start",
        "播放": "play_audio",
        "停止播放": "stop_audio",
    }

    def on_command(command):
        print(f"  >>> [测试] 触发命令: {command}")

    ovr = OnlineVoiceRecognition(api_key=API_KEY)
    ovr.start(keywords=TEST_KEYWORDS, callback=on_command)

    print("=" * 50)
    print("在线语音识别测试中，请对着麦克风说话...")
    print("（Ctrl+C 退出）")
    print("=" * 50)

    try:
        while not app.need_exit():
            time.sleep_ms(200)
    except KeyboardInterrupt:
        pass
    finally:
        ovr.destroy()
