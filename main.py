# -*- coding: utf-8 -*-
"""
MaixCAM2 人脸识别智能系统 - UI 版主程序

功能：
- 整合所有模块
- 实现 UI 界面切换
- 管理系统状态
- 实现主循环调度

使用方法：
1. 将整个项目上传到 MaixCAM2
2. 确保模型文件存在于 /root/models/
3. 运行 python main_ui.py

界面操作：
- 触摸屏点击按钮进行功能切换
- 物理按键仍可使用（短按识别、长按录入）
"""

from maix import camera, display, image, app, time, touchscreen
import os

# 导入自定义模块
from config import (
    # 硬件配置
    CAMERA_WIDTH, CAMERA_HEIGHT,
    LED_BLINK_FAST, LED_BLINK_SLOW, LED_BLINK_IDLE,
    LONG_PRESS_MS,
    # 模型配置
    FACE_DETECT_MODEL, FACE_FEATURE_MODEL, FACES_DB_PATH,
    FACE_CONF_THRESHOLD, FACE_IOU_THRESHOLD, FACE_RECOGNIZE_THRESHOLD,
    # 录制配置
    RECORD_DIR, RECORD_VIDEO_FPS, RECORD_AUDIO_SAMPLE_RATE, RECORD_AUDIO_CHANNEL,
    # 超时配置
    RECOGNIZE_TIMEOUT, ENROLL_SHOW_TIME,
    # 音频配置
    ALARM_FREQ, ALARM_DURATION,
    SUCCESS_FREQ, SUCCESS_DURATION,
    TRANSITION_FREQ, TRANSITION_DURATION,
    # 显示配置
    TEXT_SCALE, STATUS_TEXT_X, STATUS_TEXT_Y,
    # 功能开关
    AUDIO_ENABLE, LED_ENABLE, VOICE_ENABLE, SERIAL_ENABLE,
    # 推流配置
    STREAM_ENABLE, STREAM_WIDTH, STREAM_HEIGHT,
    # RTSP推流配置
    RTSP_ENABLE, RTSP_WIDTH, RTSP_HEIGHT, RTSP_AUDIO_ENABLE,
    # 语音识别配置
    VOICE_MODEL_PATH, AUDIO_DIR, VOICE_KEYWORDS,
    VOICE_PAUSE_WHEN_ACTIVE, VOICE_RUN_INTERVAL_MS,
    VOICE_PAUSE_SLEEP_MS, VOICE_KWS_GATE,
    # 串口通信配置
    SERIAL_PORT, SERIAL_BAUDRATE, SERIAL_TX_PIN, SERIAL_RX_PIN,
    # 状态定义
    State, STATE_NAMES,
    # 优化参数
    DETECT_FAST_THRESHOLD_SCALE, SUCCESS_COOLDOWN_MS, ALARM_COOLDOWN_MS,
    IDLE_SLEEP_MS, ACTIVE_SLEEP_MS, STREAM_JPEG_QUALITY,
    # 状态服务器配置
    STATUS_SERVER_PORT,
    # 性能优化参数
    STREAM_SKIP_FRAMES, STATUS_SKIP_FRAMES,
    # 音频推流配置
    AUDIO_STREAM_ENABLE, AUDIO_STREAM_PORT, AUDIO_STREAM_SAMPLE_RATE,
    AUDIO_STREAM_CHANNEL, AUDIO_STREAM_CHUNK_MS,
)
from state_machine import StateMachine
from key_manager import KeyManager
from led_controller import LedController
from audio_controller import AudioController
from face_detector import FaceDetector
from recorder_manager import RecorderManager
from video_player_manager import VideoPlayerManager
from stream_manager import StreamManager, RtspStreamManager
from audio_streamer import AudioStreamer
from status_server import StatusServer
from voice_recognition import VoiceRecognition
from serial_comm import SerialComm, RecvCmd, SendCmd

# 导入 UI 模块
from ui import UIManager, ResolutionAdapter
from ui_pages import HomePage, SettingsPage, EnrollPage, RecordingsPage, FusionPlayerPage


class AppState:
    """
    应用状态类

    使用属性代替字典，避免 key 拼写错误，提供类型安全
    """
    def __init__(self):
        self.state = State.IDLE
        self.face_count = 0
        self.face_list = []
        self.has_face = False
        self.known_face_count = 0       # 当前帧已知人脸数
        self.unknown_face_count = 0     # 当前帧未知人脸数
        self.face_labels = []           # 当前帧人脸标签列表
        self.record_duration = 0
        self.stream_enable = STREAM_ENABLE
        self.stream_url = ""
        self.rtsp_enable = RTSP_ENABLE
        self.rtsp_url = ""
        self.audio_enable = AUDIO_ENABLE
        self.led_enable = LED_ENABLE
        self.voice_enable = VOICE_ENABLE
        self.voice_status = "待机"
        self.serial_enable = SERIAL_ENABLE
        self.serial_status = "待机"
        self.conf_threshold = FACE_CONF_THRESHOLD
        self.recognize_threshold = FACE_RECOGNIZE_THRESHOLD
        self.recordings = []
        self.fusion_items = []
        self.muxed_videos = []
        self.need_save = False


class FaceRecognitionUI:
    """
    人脸识别智能系统 UI 版

    架构：
    - UI 页面层：UIManager + Page（视觉界面和页面导航）
    - 业务状态层：StateMachine（业务逻辑和硬件操作）
    """

    def __init__(self):
        """
        初始化系统
        """
        print("=" * 50)
        print("MaixCAM2 人脸识别智能系统 - UI 版")
        print("=" * 50)

        # ==================== 初始化硬件 ====================
        print("[系统] 初始化摄像头...")
        # 使用 RGB888 格式，支持绘图操作
        # 注：RTSP 推流有独立的摄像头实例，使用 YVU420SP 格式
        self._cam = camera.Camera(
            CAMERA_WIDTH, CAMERA_HEIGHT,
            image.Format.FMT_RGB888
        )
        # 跳过启动帧，提高稳定性
        self._cam.skip_frames(10)

        print("[系统] 初始化显示器...")
        self._disp = display.Display()

        print("[系统] 初始化触摸屏...")
        self._ts = touchscreen.TouchScreen()

        # 加载中文字体
        print("[系统] 加载中文字体...")
        try:
            image.load_font("chinese", "/maixapp/share/font/SourceHanSansCN-Regular.otf", size=24)
            image.set_default_font("chinese")
            print("[系统] 中文字体加载成功")
        except Exception as e:
            print(f"[系统] 中文字体加载失败: {e}")

        # 创建分辨率适配器
        self._adapter = ResolutionAdapter(
            self._disp.width(), self._disp.height(),
            base_width=320, base_height=240
        )

        # ==================== 初始化功能模块 ====================
        print("[系统] 初始化状态机...")
        self._state_machine = StateMachine(initial_state=State.IDLE)

        # LED 控制器
        if LED_ENABLE:
            print("[系统] 初始化 LED 控制器...")
            self._led = LedController()
        else:
            self._led = None
            print("[系统] LED 已禁用")

        # 音频控制器
        if AUDIO_ENABLE:
            print("[系统] 初始化音频控制器...")
            self._audio = AudioController()
        else:
            self._audio = None
            print("[系统] 音频已禁用")

        # 语音识别器
        self._voice_recognition = None
        if VOICE_ENABLE:
            print("[系统] 初始化语音识别器...")
            self._voice_recognition = VoiceRecognition(
                VOICE_MODEL_PATH,
                run_interval_ms=VOICE_RUN_INTERVAL_MS,
                pause_sleep_ms=VOICE_PAUSE_SLEEP_MS,
                kws_gate=VOICE_KWS_GATE
            )
            self._voice_recognition.set_pause_callback(
                self._should_pause_voice_recognition
            )
        else:
            print("[系统] 语音识别已禁用")

        # 串口通信（接收外部语音开发板命令）
        self._serial_comm = None
        if SERIAL_ENABLE:
            print("[系统] 初始化串口通信...")
            self._serial_comm = SerialComm(
                port=SERIAL_PORT,
                baudrate=SERIAL_BAUDRATE,
                tx_pin=SERIAL_TX_PIN,
                rx_pin=SERIAL_RX_PIN
            )
        else:
            print("[系统] 串口通信已禁用")

        print("[系统] 初始化人脸识别器...")
        self._face_detector = FaceDetector(
            FACE_DETECT_MODEL,
            FACE_FEATURE_MODEL,
            FACES_DB_PATH,
            conf_th=FACE_CONF_THRESHOLD,
            iou_th=FACE_IOU_THRESHOLD,
            recognize_th=FACE_RECOGNIZE_THRESHOLD
        )

        print("[系统] 初始化录制管理器...")
        self._recorder = RecorderManager(
            RECORD_DIR,
            fps=RECORD_VIDEO_FPS,
            sample_rate=RECORD_AUDIO_SAMPLE_RATE,
            channel=RECORD_AUDIO_CHANNEL
        )
        self._video_player = VideoPlayerManager(self._disp, RECORD_DIR)

        print("[系统] 初始化按键管理器...")
        self._key_manager = KeyManager(
            on_short_press=self._on_short_press,
            on_long_press=self._on_long_press,
            on_exit_press=self._on_exit_press,
            long_press_ms=LONG_PRESS_MS
        )

        # 初始化推流管理器
        self._stream_manager = StreamManager(jpeg_quality=STREAM_JPEG_QUALITY)
        if STREAM_ENABLE:
            print("[系统] 启动推流服务...")
            self._stream_manager.start()
            self._stream_url = self._stream_manager.get_stream_url()
        else:
            self._stream_url = ""

        # 初始化RTSP推流管理器（不在此启动，延迟到run()中）
        self._rtsp_manager = RtspStreamManager()
        self._rtsp_url = ""

        # 初始化状态服务器（推送人脸检测元数据到网页端）
        print("[系统] 初始化状态服务器...")
        self._status_server = StatusServer(port=STATUS_SERVER_PORT)
        self._status_server.start()

        # 初始化音频推流管理器（不在此启动，延迟到run()中）
        self._audio_streamer = None
        if AUDIO_STREAM_ENABLE:
            self._audio_streamer = AudioStreamer(
                port=AUDIO_STREAM_PORT,
                sample_rate=AUDIO_STREAM_SAMPLE_RATE,
                channel=AUDIO_STREAM_CHANNEL,
                chunk_ms=AUDIO_STREAM_CHUNK_MS
            )

        # ==================== 初始化应用状态 ====================
        self._app_state = AppState()
        # 设置运行时才能获取的值
        self._app_state.stream_url = self._stream_url
        self._app_state.rtsp_url = self._rtsp_url

        # ==================== 初始化 UI 框架 ====================
        print("[系统] 初始化 UI 框架...")
        self._ui_manager = UIManager()

        # 创建页面
        self._home_page = HomePage(
            self._ui_manager, self._ts, self._disp,
            self._adapter, self._app_state
        )

        self._settings_page = SettingsPage(
            self._ui_manager, self._ts, self._disp,
            self._adapter, self._app_state
        )

        # 录入页需要返回回调，退出录入状态
        self._enroll_page = EnrollPage(
            self._ui_manager, self._ts, self._disp,
            self._adapter, self._app_state,
            on_back_callback=self._on_enroll_back
        )

        self._recordings_page = RecordingsPage(
            self._ui_manager, self._ts, self._disp,
            self._adapter, self._app_state
        )

        self._fusion_player_page = FusionPlayerPage(
            self._ui_manager, self._ts, self._disp,
            self._adapter, self._app_state
        )

        # 设置页面回调
        self._setup_page_callbacks()

        # 推入主页
        self._ui_manager.push(self._home_page)

        # 启动语音识别
        if self._voice_recognition:
            print("[系统] 启动语音识别...")
            self._voice_recognition.start(
                keywords=VOICE_KEYWORDS,
                callback=self._on_voice_command
            )

        # 启动串口通信
        if self._serial_comm:
            print("[系统] 启动串口通信...")
            self._serial_comm.start(callback=self._on_serial_command)

        # ==================== 注册状态处理函数 ====================
        self._state_machine.register_handler(State.IDLE, self._handle_idle)
        self._state_machine.register_handler(State.RECOGNIZING, self._handle_recognizing)
        self._state_machine.register_handler(State.RECORDING, self._handle_recording)
        self._state_machine.register_handler(State.MANUAL_RECORDING, self._handle_manual_recording)
        self._state_machine.register_handler(State.ENROLLING, self._handle_enrolling)
        self._state_machine.register_handler(State.ERROR, self._handle_error)

        # 注册状态进入回调
        self._state_machine.register_enter_callback(State.IDLE, self._on_enter_idle)
        self._state_machine.register_enter_callback(State.RECOGNIZING, self._on_enter_recognizing)
        self._state_machine.register_enter_callback(State.RECORDING, self._on_enter_recording)
        self._state_machine.register_enter_callback(State.MANUAL_RECORDING, self._on_enter_manual_recording)
        self._state_machine.register_enter_callback(State.ENROLLING, self._on_enter_enrolling)
        self._state_machine.register_enter_callback(State.ERROR, self._on_enter_error)

        # 注册状态退出回调
        self._state_machine.register_exit_callback(State.RECOGNIZING, self._on_exit_recognizing)
        self._state_machine.register_exit_callback(State.RECORDING, self._on_exit_recording)
        self._state_machine.register_exit_callback(State.MANUAL_RECORDING, self._on_exit_manual_recording)
        self._state_machine.register_exit_callback(State.ENROLLING, self._on_exit_enrolling)

        # ==================== 状态变量 ====================
        self._no_face_time = 0
        self._last_alarm_time = 0
        self._last_success_time = 0
        self._last_recognize_detect_time = 0
        self._last_record_recognize_time = 0
        self._cached_faces = []
        self._cached_identity_label = "未知"
        self._cached_identity_known = False
        self._cached_img = None
        self._enroll_show_time = 0
        self._enroll_success = False
        self._enroll_message = ""
        self._last_face_type = 'none'  # 'none', 'known', 'unknown'

        # 当前处理后的图像（包含人脸框）
        self._processed_img = None

        # 帧跳计数器（用于降低推流和状态推送频率）
        self._frame_count = 0

        # 阈值变化检测（避免 hasattr 反模式）
        self._last_conf_threshold = FACE_CONF_THRESHOLD
        self._last_recognize_threshold = FACE_RECOGNIZE_THRESHOLD

        # 录入帧计数
        self._enroll_frame_count = 0

        # 加载已录入人脸列表
        self._update_face_list()

        # 加载录像列表
        self._update_recordings_list()

        print("[系统] 初始化完成！")
        print("=" * 50)

    # ==================== 页面回调设置 ====================
    def _setup_page_callbacks(self):
        """设置各页面的回调函数"""

        # 主页按钮回调
        self._home_page.set_callbacks(
            on_recognize=self._on_recognize_click,
            on_enroll=self._on_enroll_click,
            on_settings=self._on_settings_click,
            on_record=self._on_record_click,
            on_stream=self._on_stream_click,
            on_fusion=self._on_fusion_click
        )

        # 录入页按钮回调
        self._enroll_page.set_callbacks(
            on_enroll=self._on_enroll_face_click,
            on_delete=self._on_delete_face_click,
            on_clear=self._on_clear_faces_click
        )

        # 录像页按钮回调
        self._recordings_page.set_callbacks(
            on_refresh=self._on_refresh_recordings,
            on_delete=self._on_delete_recording,
            on_clear=self._on_clear_recordings
        )

        # 融合播放页按钮回调
        self._fusion_player_page.set_callbacks(
            on_refresh=self._on_fusion_refresh,
            on_mux=self._on_fusion_mux,
            on_play=self._on_fusion_play
        )

    # ==================== 按钮回调函数 ====================
    def _on_recognize_click(self):
        """识别按钮点击"""
        current_state = self._state_machine.state
        if current_state == State.IDLE:
            self._state_machine.transition(State.RECOGNIZING)
        elif current_state in (State.RECOGNIZING, State.RECORDING, State.MANUAL_RECORDING):
            self._state_machine.transition(State.IDLE)

    def _on_enroll_click(self):
        """录入按钮点击 - 跳转到录入页并进入录入状态"""
        # 先停止当前状态（如果正在识别或录制）
        current_state = self._state_machine.state
        if current_state in (State.RECOGNIZING, State.RECORDING, State.MANUAL_RECORDING):
            self._state_machine.transition(State.IDLE)

        # 更新人脸列表（确保显示最新数据）
        self._update_face_list()

        # 进入录入状态
        self._state_machine.transition(State.ENROLLING)

        # 跳转到录入页
        self._ui_manager.push(self._enroll_page)

    def _on_settings_click(self):
        """设置按钮点击 - 跳转到设置页"""
        self._ui_manager.push(self._settings_page)

    def _on_record_click(self):
        """纯录制按钮点击"""
        current_state = self._state_machine.state
        if current_state == State.MANUAL_RECORDING:
            self._state_machine.transition(State.IDLE)
            return

        if current_state in (State.RECOGNIZING, State.RECORDING, State.ENROLLING):
            self._state_machine.transition(State.IDLE)

        if self._state_machine.state == State.IDLE:
            self._state_machine.transition(State.MANUAL_RECORDING)

    def _on_stream_click(self):
        """推流按钮点击"""
        self._app_state.stream_enable = not self._app_state.stream_enable
        self._sync_stream_settings()

    def _on_fusion_click(self):
        """融合播放按钮点击"""
        current_state = self._state_machine.state
        if current_state in (State.RECOGNIZING, State.RECORDING, State.MANUAL_RECORDING):
            self._state_machine.transition(State.IDLE)
        self._refresh_fusion_items("已读取融合列表")
        self._ui_manager.push(self._fusion_player_page)

    def _on_enroll_face_click(self):
        """录入人脸按钮点击"""
        print(f"[录入] 点击录入按钮，当前状态: {self._state_machine.state}")
        # 只有在 ENROLLING 状态下才允许录入
        if self._state_machine.state == State.ENROLLING:
            self._do_enroll_face()
        else:
            print(f"[录入] 当前不在录入模式，忽略点击")

    def _on_enroll_back(self):
        """从录入页返回时的回调"""
        # 退出录入状态
        current_state = self._state_machine.state
        if current_state == State.ENROLLING:
            self._state_machine.transition(State.IDLE)

    # ==================== 语音命令回调 ====================

    def _should_pause_voice_recognition(self):
        """判断是否暂停语音识别，避免影响视频帧率"""
        if not VOICE_PAUSE_WHEN_ACTIVE:
            return False

        return self._state_machine.state in (
            State.RECOGNIZING,
            State.RECORDING,
            State.MANUAL_RECORDING,
            State.ENROLLING,
        )

    def _on_voice_command(self, command):
        """
        语音命令回调函数

        参数：
            command: 命令名
        """
        print(f"[语音] 收到命令: {command}")

        current_state = self._state_machine.state

        # 界面切换命令
        if command == 'home':
            # 返回主页
            while len(self._ui_manager.page_stack) > 1:
                self._ui_manager.pop()
            if current_state not in (State.IDLE,):
                self._state_machine.transition(State.IDLE)
            print("[语音] 切换到主页")

        elif command == 'settings':
            # 切换到设置页
            if len(self._ui_manager.page_stack) == 1:
                self._ui_manager.push(self._settings_page)
            print("[语音] 切换到设置页")

        elif command == 'enroll':
            # 切换到录入页
            if current_state == State.IDLE:
                self._state_machine.transition(State.ENROLLING)
                if len(self._ui_manager.page_stack) == 1:
                    self._ui_manager.push(self._enroll_page)
            print("[语音] 切换到录入页")

        elif command == 'recordings':
            # 切换到录像页
            if len(self._ui_manager.page_stack) == 1:
                self._ui_manager.push(self._recordings_page)
            print("[语音] 切换到录像页")

        # 功能控制命令
        elif command == 'recognize':
            # 开始识别
            if current_state == State.IDLE:
                self._state_machine.transition(State.RECOGNIZING)
            print("[语音] 开始识别")

        elif command == 'stop':
            # 停止当前操作
            if current_state in (State.RECOGNIZING, State.RECORDING, State.MANUAL_RECORDING):
                self._state_machine.transition(State.IDLE)
            elif current_state == State.ENROLLING:
                self._state_machine.transition(State.IDLE)
            print("[语音] 停止操作")

        elif command == 'start':
            # 开始识别
            if current_state == State.IDLE:
                self._state_machine.transition(State.RECOGNIZING)
            print("[语音] 开始识别")

        # 信息查询命令
        elif command in ('read_info', 'show_info'):
            # 读取系统信息
            face_count = self._face_detector.get_class_count()
            state_name = STATE_NAMES.get(current_state, '未知')

            info = f"当前状态: {state_name}, 已录入人脸: {face_count}人"
            print(f"[语音] 系统信息: {info}")

            # 播放提示音
            if self._audio:
                self._audio.play_transition()

        # 音频播放命令
        elif command == 'play_audio':
            # 播放音频文件
            if self._audio:
                audio_files = self._audio.get_audio_files(AUDIO_DIR)
                if audio_files:
                    # 播放第一个音频文件
                    self._audio.play_audio_by_name(AUDIO_DIR, audio_files[0])
                    print(f"[语音] 播放音频: {audio_files[0]}")
                else:
                    print("[语音] 没有找到音频文件")

        elif command == 'stop_audio':
            # 停止音频播放
            if self._audio:
                self._audio.stop_playback()
            print("[语音] 停止音频播放")

        else:
            print(f"[语音] 未知命令: {command}")

    # ==================== 串口命令回调 ====================

    def _on_serial_command(self, cmd_id, data):
        """
        串口命令回调函数

        参数：
            cmd_id: 命令ID
            data: 命令数据
        """
        from serial_comm import RecvCmd

        current_state = self._state_machine.state

        # 切换主页 (0x01)
        if cmd_id == RecvCmd.GO_HOME:
            while len(self._ui_manager.page_stack) > 1:
                self._ui_manager.pop()
            if current_state not in (State.IDLE,):
                self._state_machine.transition(State.IDLE)
            print("[串口] 切换到主页")

        # 切换设置 (0x02)
        elif cmd_id == RecvCmd.GO_SETTINGS:
            if len(self._ui_manager.page_stack) == 1:
                self._ui_manager.push(self._settings_page)
            print("[串口] 切换到设置页")

        # 切换录入界面 (0x03)
        elif cmd_id == RecvCmd.GO_ENROLL_PAGE:
            if current_state in (State.RECOGNIZING, State.RECORDING, State.MANUAL_RECORDING):
                self._state_machine.transition(State.IDLE)
            if len(self._ui_manager.page_stack) == 1:
                self._ui_manager.push(self._enroll_page)
            print("[串口] 切换到录入界面")

        # 开始录入 (0x04)
        elif cmd_id == RecvCmd.START_ENROLL:
            if current_state == State.IDLE:
                self._state_machine.transition(State.ENROLLING)
                if len(self._ui_manager.page_stack) == 1:
                    self._ui_manager.push(self._enroll_page)
            print("[串口] 开始录入")

        # 开始识别/录制 (0x05)
        elif cmd_id == RecvCmd.START_RECOGNIZE:
            if current_state == State.IDLE:
                self._state_machine.transition(State.RECOGNIZING)
            print("[串口] 开始识别/录制")

        # 停止识别/录制 (0x06)
        elif cmd_id == RecvCmd.STOP_RECOGNIZE:
            if current_state in (State.RECOGNIZING, State.RECORDING, State.MANUAL_RECORDING):
                self._state_machine.transition(State.IDLE)
            elif current_state == State.ENROLLING:
                self._state_machine.transition(State.IDLE)
            print("[串口] 停止识别/录制")

        # 关闭推流 (0x07)
        elif cmd_id == RecvCmd.CLOSE_STREAM:
            if self._stream_manager and self._stream_manager.is_streaming():
                self._stream_manager.stop()
                self._app_state.stream_enable = False
                print("[串口] 关闭推流")

        # 打开推流 (0x08)
        elif cmd_id == RecvCmd.OPEN_STREAM:
            if self._stream_manager and not self._stream_manager.is_streaming():
                self._stream_manager.start()
                self._app_state.stream_enable = True
                self._app_state.stream_url = self._stream_manager.get_stream_url()
                print("[串口] 打开推流")

        else:
            print(f"[串口] 未知命令: {cmd_id:#04x}")

    def _on_delete_face_click(self):
        """删除人脸按钮点击"""
        # TODO: 实现删除选中人脸
        print("[UI] 删除人脸功能待实现")

    def _on_clear_faces_click(self):
        """清空所有人脸"""
        self._face_detector.clear_all_faces()
        self._update_face_list()

    def _on_refresh_recordings(self):
        """刷新录像列表"""
        self._update_recordings_list()

    def _on_delete_recording(self):
        """删除录像"""
        # TODO: 实现删除选中录像
        print("[UI] 删除录像功能待实现")

    def _refresh_fusion_items(self, status_text="已刷新"):
        """刷新融合播放页面列表"""
        items = self._video_player.list_video_items()
        self._app_state.fusion_items = items
        self._app_state.muxed_videos = [item for item in items if item.get('av_size', 0) > 0]
        self._fusion_player_page.set_status(status_text)
        print(f"[融合] 原始视频: {len(items)}, 已融合: {len(self._app_state.muxed_videos)}")

    def _on_fusion_refresh(self):
        """读取融合页面文件列表"""
        self._refresh_fusion_items("读取完成")

    def _on_fusion_mux(self):
        """手动融合所有可融合录像"""
        self._fusion_player_page.set_status("正在融合，请稍候")
        success_count, total_count = self._video_player.mux_all()
        self._refresh_fusion_items(f"融合完成 {success_count}/{total_count}")
        self._update_recordings_list()

    def _on_fusion_play(self):
        """播放选中的融合视频"""
        muxed_videos = self._app_state.muxed_videos
        if not muxed_videos:
            self._fusion_player_page.set_status("暂无融合视频可播放")
            print("[融合] 暂无融合视频可播放")
            return

        index = self._fusion_player_page.get_selected_index()
        if index >= len(muxed_videos):
            index = 0
        item = muxed_videos[index]
        av_path = item.get('av_path', '')
        self._fusion_player_page.set_status(f"播放: {item.get('av_name', '')}")
        self._video_player.play(av_path)
        self._refresh_fusion_items("播放结束")

    def _on_clear_recordings(self):
        """清空所有录像"""
        try:
            for rec in self._app_state.recordings:
                path = os.path.join(RECORD_DIR, rec.get('name', ''))
                if os.path.exists(path):
                    os.remove(path)
                audio_name = rec.get('audio_name', '')
                if audio_name:
                    audio_path = os.path.join(RECORD_DIR, audio_name)
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
                av_name = rec.get('av_name', '')
                if av_name:
                    av_path = os.path.join(RECORD_DIR, av_name)
                    if os.path.exists(av_path):
                        os.remove(av_path)
            self._app_state.recordings = []
            self._update_recordings_list()
            print("[UI] 已清空所有录像")
        except Exception as e:
            print(f"[UI] 清空录像失败: {e}")

    # ==================== 辅助函数 ====================
    def _update_face_list(self):
        """更新已录入人脸列表"""
        try:
            # 获取人脸标签列表（排除 unknown）
            labels = self._face_detector.get_labels()
            face_list = [label for label in labels if label != 'unknown']
            class_count = self._face_detector.get_class_count()
            self._app_state.face_count = class_count
            self._app_state.face_list = face_list
            print(f"[系统] 更新人脸列表: {class_count} 人, 标签: {face_list}")
        except Exception as e:
            print(f"[系统] 更新人脸列表失败: {e}")

    def _update_recordings_list(self):
        """更新录像文件列表"""
        try:
            recordings = []
            if os.path.exists(RECORD_DIR):
                for f in os.listdir(RECORD_DIR):
                    if f.endswith('.mp4'):
                        if f.endswith('_av.mp4'):
                            continue
                        path = os.path.join(RECORD_DIR, f)
                        size = os.path.getsize(path)
                        base = f[:-4]
                        audio_name = base + '.wav'
                        audio_path = os.path.join(RECORD_DIR, audio_name)
                        audio_size = os.path.getsize(audio_path) if os.path.exists(audio_path) else 0
                        av_name = base + '_av.mp4'
                        av_path = os.path.join(RECORD_DIR, av_name)
                        av_size = os.path.getsize(av_path) if os.path.exists(av_path) else 0
                        recordings.append({
                            'name': f,
                            'size': size,
                            'audio_name': audio_name if audio_size > 0 else '',
                            'audio_size': audio_size,
                            'av_name': av_name if av_size > 0 else '',
                            'av_size': av_size,
                        })
                    elif f.endswith('.wav'):
                        base = f[:-4]
                        video_name = base + '.mp4'
                        video_path = os.path.join(RECORD_DIR, video_name)
                        if os.path.exists(video_path):
                            continue
                        path = os.path.join(RECORD_DIR, f)
                        recordings.append({
                            'name': f,
                            'size': os.path.getsize(path),
                            'audio_name': f,
                            'audio_size': os.path.getsize(path),
                        })
            recordings.sort(key=lambda x: x['name'], reverse=True)
            self._app_state.recordings = recordings
        except Exception as e:
            print(f"[系统] 更新录像列表失败: {e}")

    def _check_threshold_update(self):
        """检查阈值是否变化，实时更新检测器"""
        current_conf = self._app_state.conf_threshold
        current_recognize = self._app_state.recognize_threshold

        if (abs(current_conf - self._last_conf_threshold) > 0.01 or
            abs(current_recognize - self._last_recognize_threshold) > 0.01):
            # 阈值变化了，更新检测器
            self._face_detector.set_detect_threshold(
                conf_th=current_conf,
                iou_th=0.45,
                recognize_th=current_recognize
            )
            self._last_conf_threshold = current_conf
            self._last_recognize_threshold = current_recognize

    def _sync_stream_settings(self):
        """同步设置页推流开关到实际服务"""
        try:
            if self._app_state.stream_enable:
                if self._stream_manager and not self._stream_manager.is_streaming():
                    if self._stream_manager.start():
                        self._app_state.stream_url = self._stream_manager.get_stream_url()
                    else:
                        self._app_state.stream_enable = False
                        self._app_state.stream_url = ""
            else:
                if self._stream_manager and self._stream_manager.is_streaming():
                    self._stream_manager.stop()
                self._app_state.stream_url = ""

            if self._app_state.rtsp_enable:
                if self._rtsp_manager and not self._rtsp_manager.is_streaming():
                    if self._rtsp_manager.start(RTSP_WIDTH, RTSP_HEIGHT, RTSP_AUDIO_ENABLE):
                        self._rtsp_url = self._rtsp_manager.get_url()
                        self._app_state.rtsp_url = self._rtsp_url
                    else:
                        self._app_state.rtsp_enable = False
                        self._app_state.rtsp_url = ""
            else:
                if self._rtsp_manager and self._rtsp_manager.is_streaming():
                    self._rtsp_manager.stop()
                self._rtsp_url = ""
                self._app_state.rtsp_url = ""
        except Exception as e:
            print(f"[系统] 同步推流设置失败: {e}")

    def _save_settings(self):
        """保存设置到应用配置"""
        try:
            app.set_app_config_kv('face_detect', 'conf_threshold',
                                  str(self._app_state.conf_threshold), False)
            app.set_app_config_kv('face_detect', 'recognize_threshold',
                                  str(self._app_state.recognize_threshold), False)
            app.set_app_config_kv('face_detect', 'stream_enable',
                                  str(self._app_state.stream_enable), False)
            app.set_app_config_kv('face_detect', 'rtsp_enable',
                                  str(self._app_state.rtsp_enable), False)
            app.set_app_config_kv('face_detect', 'audio_enable',
                                  str(self._app_state.audio_enable), False)
            app.set_app_config_kv('face_detect', 'led_enable',
                                  str(self._app_state.led_enable), True)
            print("[系统] 设置已保存")
        except Exception as e:
            print(f"[系统] 保存设置失败: {e}")

    # ==================== 安全调用封装 ====================
    def _led_blink(self, interval):
        """安全调用 LED 闪烁"""
        if self._led:
            self._led.blink(interval)

    def _led_on(self):
        """安全调用 LED 常亮"""
        if self._led:
            self._led.on()

    def _led_update(self):
        """安全调用 LED 更新"""
        if self._led:
            self._led.update()

    def _audio_play(self, method_name, **kwargs):
        """安全调用音频播放"""
        if self._audio:
            method = getattr(self._audio, method_name, None)
            if method:
                method(**kwargs)

    # ==================== 按键回调函数 ====================
    def _on_short_press(self):
        """短按 OK 键回调"""
        current_state = self._state_machine.state
        print(f"[按键] 短按，当前状态: {current_state}")

        if current_state == State.IDLE:
            self._state_machine.transition(State.RECOGNIZING)
        elif current_state == State.RECOGNIZING:
            self._state_machine.transition(State.IDLE)
        elif current_state == State.RECORDING:
            self._state_machine.transition(State.IDLE)
        elif current_state == State.MANUAL_RECORDING:
            self._state_machine.transition(State.IDLE)
        elif current_state == State.ENROLLING:
            self._do_enroll_face()
        elif current_state == State.ERROR:
            self._state_machine.transition(State.IDLE)

    def _on_long_press(self):
        """长按 OK 键回调"""
        current_state = self._state_machine.state
        print(f"[按键] 长按，当前状态: {current_state}")

        if current_state == State.IDLE:
            self._state_machine.transition(State.ENROLLING)
        elif current_state == State.ENROLLING:
            self._state_machine.transition(State.IDLE)

    def _on_exit_press(self):
        """超长按 OK 键回调（≥3秒）—— 退出程序"""
        print("[按键] 超长按，退出程序...")
        app.set_exit_flag(True)

    # ==================== 状态进入回调 ====================
    def _on_enter_idle(self):
        """进入空闲状态"""
        print("[状态] 进入空闲模式")
        self._app_state.state = State.IDLE
        self._led_blink(LED_BLINK_IDLE)
        self._no_face_time = 0
        self._cached_faces = []
        self._cached_identity_label = "未知"
        self._cached_identity_known = False
        self._cached_img = None
        self._last_face_type = 'none'  # 重置人脸类型

    def _on_enter_recognizing(self):
        """进入识别状态"""
        print("[状态] 进入识别模式")
        self._app_state.state = State.RECOGNIZING
        self._led_blink(LED_BLINK_FAST)
        self._audio_play('play_double_beep')
        self._no_face_time = 0
        self._last_alarm_time = 0
        self._last_success_time = 0
        self._last_recognize_detect_time = 0
        self._cached_faces = []
        self._cached_identity_label = "未知"
        self._cached_identity_known = False

    def _on_enter_recording(self):
        """进入录制状态"""
        print("[状态] 检测到人脸，开始录制")
        self._app_state.state = State.RECORDING
        self._led_blink(LED_BLINK_SLOW)
        self._last_record_recognize_time = 0
        self._recorder.start_recording(self._cam, with_audio=True)

    def _on_enter_manual_recording(self):
        """进入手动纯录制状态"""
        print("[状态] 进入纯录制模式")
        self._app_state.state = State.MANUAL_RECORDING
        self._led_blink(LED_BLINK_SLOW)
        self._app_state.has_face = False
        self._app_state.face_count = 0
        self._app_state.known_face_count = 0
        self._app_state.unknown_face_count = 0
        self._app_state.face_labels = []
        self._cached_faces = []
        self._cached_identity_label = "未知"
        self._cached_identity_known = False
        self._recorder.start_recording(self._cam, with_audio=True)

    def _on_enter_enrolling(self):
        """进入录入状态"""
        print("[状态] 进入录入模式，state=ENROLLING(2)")
        self._app_state.state = State.ENROLLING
        self._led_blink(LED_BLINK_FAST)
        self._audio_play('play_transition', freq=TRANSITION_FREQ, duration=TRANSITION_DURATION)
        self._cached_faces = []
        self._cached_img = None

    def _on_enter_error(self):
        """进入错误状态"""
        print("[状态] 进入错误状态")
        self._app_state.state = State.ERROR
        self._led_blink(LED_BLINK_FAST)
        self._audio_play('play_error')

    # ==================== 状态退出回调 ====================
    def _on_exit_recognizing(self):
        """退出识别状态"""
        print("[状态] 退出识别模式")

    def _on_exit_recording(self):
        """退出录制状态"""
        print("[状态] 退出录制模式，停止录制")
        if self._recorder.is_recording():
            video_path, audio_path = self._recorder.stop_recording()
            print(f"[录制] 视频文件: {video_path}")
            print(f"[录制] 音频文件: {audio_path}")
            self._update_recordings_list()

    def _on_exit_manual_recording(self):
        """退出手动纯录制状态"""
        print("[状态] 退出纯录制模式，停止录制")
        if self._recorder.is_recording():
            result = self._recorder.stop_recording()
            if result:
                video_path, audio_path = result
                print(f"[录制] 视频文件: {video_path}")
                print(f"[录制] 音频文件: {audio_path}")
            self._update_recordings_list()

    def _on_exit_enrolling(self):
        """退出录入状态"""
        print("[状态] 退出录入模式")
        if self._face_detector.is_enrolling():
            self._face_detector.cancel_enrollment()

    # ==================== 状态处理函数 ====================
    def _handle_idle(self):
        """
        空闲状态处理（优化版）：
        - 只读取摄像头图像，不进行人脸识别
        - 空闲状态用于提高帧率，减少 CPU 负载
        - 只在需要时（进入识别或录入状态）才进行人脸识别
        """
        img = self._cam.read()

        # 空闲状态不进行人脸识别，保持低负载
        # 人脸检测只在 RECOGNIZING 和 ENROLLING 状态进行
        self._app_state.has_face = False
        self._app_state.face_count = 0
        self._app_state.known_face_count = 0
        self._app_state.unknown_face_count = 0
        self._app_state.face_labels = []
        self._app_state.record_duration = 0

        # 保存处理后的图像
        self._processed_img = img

    def _handle_recognizing(self):
        """
        识别状态处理（优化版）：
        - 使用快速检测模式
        - 检测到人脸后转换到录制状态
        - 无人脸超时后返回空闲
        """
        img = self._cam.read()
        faces = self._face_detector.detect_faces_only(img)

        if faces:
            # 检测到人脸后，进行完整的识别
            recognized_faces = self._face_detector.detect_and_recognize(img)

            # 绘制人脸框
            for face in recognized_faces:
                color = image.COLOR_GREEN if self._face_detector.is_known_face(face) else image.COLOR_RED
                label = self._face_detector.get_face_label(face) if self._face_detector.is_known_face(face) else "未知"
                self._face_detector.draw_face(img, face, color=color, label=label)

            # 保存处理后的图像（包含人脸框）
            self._processed_img = img

            # 缓存人脸信息
            self._cached_faces = recognized_faces
            self._cached_identity_known = any(
                self._face_detector.is_known_face(face) for face in recognized_faces
            )
            if self._cached_identity_known:
                for face in recognized_faces:
                    if self._face_detector.is_known_face(face):
                        self._cached_identity_label = self._face_detector.get_face_label(face)
                        break
            else:
                self._cached_identity_label = "未知"

            # 更新人脸详情数据
            known = sum(1 for f in recognized_faces if self._face_detector.is_known_face(f))
            unknown = len(recognized_faces) - known
            labels = [self._face_detector.get_face_label(f) for f in recognized_faces]
            self._app_state.face_count = len(recognized_faces)
            self._app_state.known_face_count = known
            self._app_state.unknown_face_count = unknown
            self._app_state.face_labels = labels

            # 转换到录制状态
            self._state_machine.transition(State.RECORDING)
            return

        # 未检测到人脸
        current_time = time.ticks_ms()
        if self._no_face_time == 0:
            self._no_face_time = current_time

        no_face_duration = current_time - self._no_face_time
        if no_face_duration > RECOGNIZE_TIMEOUT:
            print("[系统] 无人脸超时，返回空闲状态")
            self._state_machine.transition(State.IDLE)
            return

        # 显示等待信息
        remaining = (RECOGNIZE_TIMEOUT - no_face_duration) // 1000
        img.draw_string(10, 40, f"等待人脸... {remaining}s",
                       color=image.COLOR_YELLOW, scale=TEXT_SCALE)

        # 更新应用状态
        self._app_state.has_face = False
        self._app_state.face_count = 0
        self._app_state.known_face_count = 0
        self._app_state.unknown_face_count = 0
        self._app_state.face_labels = []

        # 保存处理后的图像
        self._processed_img = img

    def _handle_recording(self):
        """
        录制状态处理（优化版）：
        - 直接完整识别（不再做双重推理）
        - 编码视频帧
        - 无人脸超时后返回空闲
        """
        img = self._cam.read()
        current_time = time.ticks_ms()
        recognized_faces = self._face_detector.detect_and_recognize(img)

        if recognized_faces:
            # 检测到人脸，重置无人脸计时
            self._no_face_time = 0

            # 处理每个人脸
            has_known_face = False
            for face in recognized_faces:
                if self._face_detector.is_known_face(face):
                    has_known_face = True
                    break

            for face in recognized_faces:
                self._process_face(img, face, has_known_face)

            # 更新应用状态
            self._app_state.has_face = True

            # 更新人脸详情数据
            known = sum(1 for f in recognized_faces if self._face_detector.is_known_face(f))
            unknown = len(recognized_faces) - known
            labels = [self._face_detector.get_face_label(f) for f in recognized_faces]
            self._app_state.face_count = len(recognized_faces)
            self._app_state.known_face_count = known
            self._app_state.unknown_face_count = unknown
            self._app_state.face_labels = labels

            if self._recorder.is_recording():
                self._app_state.record_duration = self._recorder.get_recording_duration() // 1000

        else:
            # 未检测到人脸
            self._led_blink(LED_BLINK_SLOW)
            self._app_state.has_face = False
            self._app_state.face_count = 0
            self._app_state.known_face_count = 0
            self._app_state.unknown_face_count = 0
            self._app_state.face_labels = []

            if self._no_face_time == 0:
                self._no_face_time = current_time

            # 检查超时
            no_face_duration = current_time - self._no_face_time
            if no_face_duration > RECOGNIZE_TIMEOUT:
                print("[系统] 无人脸超时，返回空闲状态")
                self._state_machine.transition(State.IDLE)
                return

            # 显示等待信息
            remaining = (RECOGNIZE_TIMEOUT - no_face_duration) // 1000
            img.draw_string(10, 40, f"等待人脸... {remaining}s",
                           color=image.COLOR_YELLOW, scale=TEXT_SCALE)

        # 编码当前录制画面。放在末尾可保存带标注/等待提示的画面，并避免短暂无人脸时视频缺帧。
        self._recorder.encode_frame(img)

        # 保存处理后的图像（关键：必须在return之前保存）
        self._processed_img = img

    def _handle_manual_recording(self):
        """
        手动纯录制状态处理：
        - 不运行任何 AI 人脸识别
        - 仅采集当前画面并编码音视频
        - 更新录制时长用于 UI 显示
        """
        img = self._cam.read()

        self._app_state.has_face = False
        self._app_state.face_count = 0
        self._app_state.known_face_count = 0
        self._app_state.unknown_face_count = 0
        self._app_state.face_labels = []

        if self._recorder.is_recording():
            self._recorder.encode_frame(img)
            self._app_state.record_duration = self._recorder.get_recording_duration() // 1000
        else:
            self._app_state.record_duration = 0

        self._processed_img = img

    def _process_face(self, img, face, has_known_face):
        """处理检测到的人脸"""
        label = self._face_detector.get_face_label(face)

        if self._face_detector.is_known_face(face):
            self._face_detector.draw_face(img, face,
                                         color=image.COLOR_GREEN,
                                         label=label)
            self._led_on()

            # 串口发送熟人通知（只在状态变化时发送一次）
            if self._serial_comm and self._serial_comm.is_running():
                if self._last_face_type != 'known':
                    self._serial_comm.send_known_face()
                    self._last_face_type = 'known'

            current_time = time.ticks_ms()
            if current_time - self._last_success_time > SUCCESS_COOLDOWN_MS:
                self._last_success_time = current_time
        else:
            self._face_detector.draw_face(img, face,
                                         color=image.COLOR_RED,
                                         label="未知")

            # 串口发送陌生人通知（只在状态变化时发送一次）
            if self._serial_comm and self._serial_comm.is_running():
                if self._last_face_type != 'unknown':
                    self._serial_comm.send_unknown_face()
                    self._last_face_type = 'unknown'

            if not has_known_face:
                current_time = time.ticks_ms()
                if current_time - self._last_alarm_time > ALARM_COOLDOWN_MS:
                    self._last_alarm_time = current_time
                    self._led_blink(LED_BLINK_FAST)

    def _handle_enrolling(self):
        """
        录入状态处理（优化版）：
        - 使用快速检测模式
        - 检测人脸并缓存结果
        - 显示引导信息
        """
        img = self._cam.read()
        self._cached_img = img

        # 使用快速检测模式
        faces = self._face_detector.detect_faces_only(img)
        self._cached_faces = faces

        # 更新应用状态
        self._app_state.has_face = len(faces) > 0

        # 调试信息（每10帧打印一次，避免刷屏）
        self._enroll_frame_count += 1

        if self._enroll_frame_count % 10 == 0:
            if len(faces) > 0:
                print(f"[录入] 检测到 {len(faces)} 张人脸，has_face=True")
            else:
                print(f"[录入] 未检测到人脸，has_face=False")

        # 检查是否需要显示录入结果
        if self._enroll_show_time > 0:
            current_time = time.ticks_ms()
            if current_time - self._enroll_show_time < ENROLL_SHOW_TIME:
                if self._enroll_success:
                    img.draw_string(10, 40, self._enroll_message,
                                   color=image.COLOR_GREEN, scale=1.5)
                else:
                    img.draw_string(10, 40, self._enroll_message,
                                   color=image.COLOR_RED, scale=1.5)
                self._processed_img = img
                return
            else:
                self._enroll_show_time = 0
                self._state_machine.transition(State.IDLE)
                return

        # 绘制人脸框
        for face in faces:
            self._face_detector.draw_face(img, face, color=image.COLOR_GREEN)

        # 保存处理后的图像
        self._processed_img = img

    def _do_enroll_face(self):
        """执行人脸录入"""
        try:
            face_count = len(self._cached_faces) if self._cached_faces else 0
            has_img = self._cached_img is not None
            print("[录入] 开始录入，缓存人脸数:", face_count)
            print("[录入] 缓存图像:", has_img)

            if not self._cached_faces or self._cached_img is None:
                print("[录入] 未检测到人脸，请调整位置")
                self._enroll_success = False
                self._enroll_message = "未检测到人脸"
                self._enroll_show_time = time.ticks_ms()
                return

            face = self._cached_faces[0]
            label = f"user_{time.ticks_ms() // 1000}"
            print(f"[录入] 生成标签: {label}")
            print(f"[录入] 人脸信息: x={face.x}, y={face.y}, w={face.w}, h={face.h}")

            # 先取消之前的录入状态（如果有）
            if self._face_detector.is_enrolling():
                self._face_detector.cancel_enrollment()

            # 开始新的录入
            start_result = self._face_detector.start_enrollment(label)
            print(f"[录入] start_enrollment 结果: {start_result}")

            if start_result:
                print(f"[录入] 开始录入流程...")
                success, message, count = self._face_detector.enroll_face(
                    self._cached_img)
                print(f"[录入] enroll_face 结果: success={success}, message={message}, count={count}")

                if success:
                    print(f"[录入] 成功: {message}")
                    self._audio_play('play_double_beep')
                    self._led_blink(100)

                    self._enroll_success = True
                    self._enroll_message = f"录入成功: {label}"
                    self._enroll_show_time = time.ticks_ms()

                    self._update_face_list()
                else:
                    print(f"[录入] 失败: {message}")
                    self._audio_play('play_error')

                    self._enroll_success = False
                    self._enroll_message = f"录入失败: {message}"
                    self._enroll_show_time = time.ticks_ms()
            else:
                print("[录入] start_enrollment 失败")
                self._enroll_success = False
                self._enroll_message = "无法开始录入"
                self._enroll_show_time = time.ticks_ms()

            # 清除缓存
            self._cached_faces = []
            self._cached_img = None

        except Exception as e:
            print(f"[录入] 异常: {e}")
            import traceback
            traceback.print_exc()

            self._enroll_success = False
            self._enroll_message = f"录入异常: {str(e)[:20]}"
            self._enroll_show_time = time.ticks_ms()

            # 确保清除缓存
            self._cached_faces = []
            self._cached_img = None

    def _handle_error(self):
        """错误状态处理"""
        img = self._cam.read()
        self._processed_img = img

    # ==================== 主循环 ====================
    def run(self):
        """运行主循环"""
        print("[系统] 开始运行主循环...")

        # 延迟启动 RTSP 推流（避免在 __init__ 中与 display 冲突）
        if self._app_state.rtsp_enable and self._rtsp_manager:
            print("[系统] 延迟启动 RTSP 推流服务...")
            try:
                self._rtsp_manager.start(RTSP_WIDTH, RTSP_HEIGHT, RTSP_AUDIO_ENABLE)
                self._rtsp_url = self._rtsp_manager.get_url()
                self._app_state.rtsp_url = self._rtsp_url
                self._app_state.rtsp_enable = self._rtsp_manager.is_streaming()
            except Exception as e:
                print(f"[系统] RTSP 启动失败: {e}")
                self._app_state.rtsp_enable = False

        # 延迟启动音频推流（避免在 __init__ 中与音频录制器冲突）
        if self._audio_streamer:
            print("[系统] 延迟启动音频推流服务...")
            try:
                self._audio_streamer.start()
                audio_url = self._audio_streamer.get_url()
                print(f"[系统] 音频推流地址: {audio_url}")
            except Exception as e:
                print(f"[系统] 音频推流启动失败: {e}")

        try:
            while not app.need_exit():
                try:
                    # 帧计数器递增
                    self._frame_count += 1

                    # 1. 更新物理按键
                    self._key_manager.update()

                    # 2. 更新 LED
                    self._led_update()

                    # 3. 检查是否需要保存设置
                    if self._app_state.need_save:
                        self._save_settings()
                        self._app_state.need_save = False

                    # 4. 检查阈值是否变化，实时更新检测器
                    self._check_threshold_update()

                    # 5. 同步设置页中的 HTTP/RTSP 推流开关
                    self._sync_stream_settings()

                    # 6. 业务状态处理（会更新 self._processed_img）
                    self._state_machine.update()

                    audio_client_count = 0
                    if self._audio_streamer:
                        audio_client_count = self._audio_streamer.get_client_count()

                    # 5.5 状态推送（音频开启时进一步降频，避免 JSON 序列化抢占主循环）
                    status_skip = STATUS_SKIP_FRAMES
                    if audio_client_count > 0:
                        status_skip = max(status_skip, 10)
                    if self._frame_count % status_skip == 0:
                        self._status_server.update_status({
                            'state': STATE_NAMES.get(self._state_machine.state, '未知'),
                            'has_face': self._app_state.has_face,
                            'face_count': self._app_state.face_count,
                            'known_face_count': self._app_state.known_face_count,
                            'unknown_face_count': self._app_state.unknown_face_count,
                            'face_labels': self._app_state.face_labels,
                            'recording': self._recorder.is_recording(),
                            'record_duration': self._app_state.record_duration,
                        })

                    # 7. 使用处理后的图像（包含人脸框）
                    if self._processed_img is not None:
                        img = self._processed_img
                    else:
                        img = self._cam.read()

                    # 8. UI 页面绘制（叠加按钮、状态栏等）
                    self._ui_manager.update(img)

                    # 9. 显示图像
                    self._disp.show(img)

                    # 10. 推流（保持配置帧跳，避免音频开启时网页视频帧率突降）
                    stream_skip = STREAM_SKIP_FRAMES
                    if self._stream_manager.is_streaming() and (self._frame_count % stream_skip == 0):
                        self._stream_manager.write(img)

                    # 11. 短暂休眠（减少休眠时间以提高帧率）
                    if self._state_machine.state == State.IDLE:
                        time.sleep_ms(IDLE_SLEEP_MS)
                    else:
                        time.sleep_ms(ACTIVE_SLEEP_MS)

                except KeyboardInterrupt:
                    raise  # 重新抛出 KeyboardInterrupt
                except Exception as e:
                    print(f"[系统] 主循环异常: {e}")
                    import traceback
                    traceback.print_exc()
                    time.sleep_ms(100)  # 异常后短暂休眠

        except KeyboardInterrupt:
            print("[系统] 用户中断")
        except Exception as e:
            print(f"[系统] 异常: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._cleanup()

    def _cleanup(self):
        """清理资源"""
        print("[系统] 清理资源...")

        # 停止状态服务器
        if hasattr(self, '_status_server') and self._status_server:
            self._status_server.stop()

        # 停止音频推流
        if self._audio_streamer:
            self._audio_streamer.stop()

        # 销毁串口通信
        if self._serial_comm:
            self._serial_comm.destroy()

        # 销毁语音识别器
        if self._voice_recognition:
            self._voice_recognition.destroy()

        if self._stream_manager:
            self._stream_manager.destroy()

        if self._rtsp_manager:
            self._rtsp_manager.destroy()

        if self._recorder.is_recording():
            self._recorder.stop_recording()

        self._key_manager.destroy()
        if self._led:
            self._led.destroy()
        if self._audio:
            self._audio.destroy()
        self._recorder.destroy()

        print("[系统] 资源清理完成")


# ==================== 程序入口 ====================
def main():
    """主函数"""
    try:
        system = FaceRecognitionUI()
        system.run()
    except Exception as e:
        print(f"[系统] 启动失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
