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
    AUDIO_ENABLE, LED_ENABLE,
    # 推流配置
    STREAM_ENABLE, STREAM_WIDTH, STREAM_HEIGHT,
    # 状态定义
    State
)
from state_machine import StateMachine
from key_manager import KeyManager
from led_controller import LedController
from audio_controller import AudioController
from face_detector import FaceDetector
from recorder_manager import RecorderManager
from stream_manager import StreamManager

# 导入 UI 模块
from ui import UIManager, ResolutionAdapter
from ui_pages import HomePage, SettingsPage, EnrollPage, RecordingsPage


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
        self._cam = camera.Camera(
            CAMERA_WIDTH, CAMERA_HEIGHT,
            image.Format.FMT_RGB888
        )
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

        print("[系统] 初始化按键管理器...")
        self._key_manager = KeyManager(
            on_short_press=self._on_short_press,
            on_long_press=self._on_long_press,
            long_press_ms=LONG_PRESS_MS
        )

        # 初始化推流管理器
        self._stream_manager = StreamManager()
        if STREAM_ENABLE:
            print("[系统] 启动推流服务...")
            self._stream_manager.start()
            self._stream_url = self._stream_manager.get_stream_url()
        else:
            self._stream_url = ""

        # ==================== 初始化应用状态 ====================
        self._app_state = {
            'state': State.IDLE,
            'face_count': 0,
            'face_list': [],
            'has_face': False,
            'record_duration': 0,
            'stream_enable': STREAM_ENABLE,
            'stream_url': self._stream_url,
            'audio_enable': AUDIO_ENABLE,
            'led_enable': LED_ENABLE,
            'conf_threshold': FACE_CONF_THRESHOLD,
            'recognize_threshold': FACE_RECOGNIZE_THRESHOLD,
            'recordings': [],
            'need_save': False,
            'fps': 0,  # 帧率信息
        }

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

        self._enroll_page = EnrollPage(
            self._ui_manager, self._ts, self._disp,
            self._adapter, self._app_state
        )

        self._recordings_page = RecordingsPage(
            self._ui_manager, self._ts, self._disp,
            self._adapter, self._app_state
        )

        # 设置页面回调
        self._setup_page_callbacks()

        # 推入主页
        self._ui_manager.push(self._home_page)

        # ==================== 注册状态处理函数 ====================
        self._state_machine.register_handler(State.IDLE, self._handle_idle)
        self._state_machine.register_handler(State.RECOGNIZING, self._handle_recognizing)
        self._state_machine.register_handler(State.RECORDING, self._handle_recording)
        self._state_machine.register_handler(State.ENROLLING, self._handle_enrolling)
        self._state_machine.register_handler(State.ERROR, self._handle_error)

        # 注册状态进入回调
        self._state_machine.register_enter_callback(State.IDLE, self._on_enter_idle)
        self._state_machine.register_enter_callback(State.RECOGNIZING, self._on_enter_recognizing)
        self._state_machine.register_enter_callback(State.RECORDING, self._on_enter_recording)
        self._state_machine.register_enter_callback(State.ENROLLING, self._on_enter_enrolling)
        self._state_machine.register_enter_callback(State.ERROR, self._on_enter_error)

        # 注册状态退出回调
        self._state_machine.register_exit_callback(State.RECOGNIZING, self._on_exit_recognizing)
        self._state_machine.register_exit_callback(State.RECORDING, self._on_exit_recording)
        self._state_machine.register_exit_callback(State.ENROLLING, self._on_exit_enrolling)

        # ==================== 状态变量 ====================
        self._no_face_time = 0
        self._last_alarm_time = 0
        self._last_success_time = 0
        self._cached_faces = []
        self._cached_img = None
        self._enroll_show_time = 0
        self._enroll_success = False
        self._enroll_message = ""

        # 性能监控变量
        self._fps_counter = 0
        self._fps_start_time = time.ticks_ms()
        self._current_fps = 0

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
            on_stream=self._on_stream_click
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

    # ==================== 按钮回调函数 ====================
    def _on_recognize_click(self):
        """识别按钮点击"""
        current_state = self._state_machine.state
        if current_state == State.IDLE:
            self._state_machine.transition(State.RECOGNIZING)
        elif current_state in (State.RECOGNIZING, State.RECORDING):
            self._state_machine.transition(State.IDLE)

    def _on_enroll_click(self):
        """录入按钮点击 - 跳转到录入页"""
        self._ui_manager.push(self._enroll_page)

    def _on_settings_click(self):
        """设置按钮点击 - 跳转到设置页"""
        self._ui_manager.push(self._settings_page)

    def _on_stream_click(self):
        """推流按钮点击"""
        if self._stream_manager.is_streaming():
            self._stream_manager.stop()
            self._app_state['stream_enable'] = False
        else:
            self._stream_manager.start()
            self._app_state['stream_enable'] = True
            self._app_state['stream_url'] = self._stream_manager.get_stream_url()

    def _on_enroll_face_click(self):
        """录入人脸按钮点击"""
        self._do_enroll_face()

    def _on_delete_face_click(self):
        """删除人脸按钮点击"""
        # TODO: 实现删除选中人脸
        print("[UI] 删除人脸功能待实现")

    def _on_clear_faces_click(self):
        """清空人脸按钮点击"""
        # TODO: 实现清空所有人脸
        print("[UI] 清空人脸功能待实现")

    def _on_refresh_recordings(self):
        """刷新录像列表"""
        self._update_recordings_list()

    def _on_delete_recording(self):
        """删除录像"""
        # TODO: 实现删除选中录像
        print("[UI] 删除录像功能待实现")

    def _on_clear_recordings(self):
        """清空录像"""
        # TODO: 实现清空所有录像
        print("[UI] 清空录像功能待实现")

    # ==================== 辅助函数 ====================
    def _update_face_list(self):
        """更新已录入人脸列表"""
        try:
            # 获取人脸标签列表（排除 unknown）
            labels = self._face_detector.get_labels()
            face_list = [label for label in labels if label != 'unknown']
            class_count = self._face_detector.get_class_count()
            self._app_state['face_count'] = class_count
            self._app_state['face_list'] = face_list
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
                        path = os.path.join(RECORD_DIR, f)
                        size = os.path.getsize(path)
                        recordings.append({'name': f, 'size': size})
            # 按时间倒序排列
            recordings.sort(key=lambda x: x['name'], reverse=True)
            self._app_state['recordings'] = recordings
        except Exception as e:
            print(f"[系统] 更新录像列表失败: {e}")

    def _save_settings(self):
        """保存设置到应用配置"""
        try:
            app.set_app_config_kv('face_detect', 'conf_threshold',
                                  str(self._app_state['conf_threshold']), False)
            app.set_app_config_kv('face_detect', 'recognize_threshold',
                                  str(self._app_state['recognize_threshold']), False)
            app.set_app_config_kv('face_detect', 'stream_enable',
                                  str(self._app_state['stream_enable']), False)
            app.set_app_config_kv('face_detect', 'audio_enable',
                                  str(self._app_state['audio_enable']), False)
            app.set_app_config_kv('face_detect', 'led_enable',
                                  str(self._app_state['led_enable']), True)
            print("[系统] 设置已保存")
        except Exception as e:
            print(f"[系统] 保存设置失败: {e}")

    def _load_settings(self):
        """从应用配置加载设置"""
        try:
            val = app.get_app_config_kv('face_detect', 'conf_threshold', '', False)
            if val:
                self._app_state['conf_threshold'] = float(val)

            val = app.get_app_config_kv('face_detect', 'recognize_threshold', '', False)
            if val:
                self._app_state['recognize_threshold'] = float(val)

            val = app.get_app_config_kv('face_detect', 'stream_enable', '', False)
            if val:
                self._app_state['stream_enable'] = val.lower() == 'true'

            val = app.get_app_config_kv('face_detect', 'audio_enable', '', False)
            if val:
                self._app_state['audio_enable'] = val.lower() == 'true'

            val = app.get_app_config_kv('face_detect', 'led_enable', '', False)
            if val:
                self._app_state['led_enable'] = val.lower() == 'true'

            print("[系统] 设置已加载")
        except Exception as e:
            print(f"[系统] 加载设置失败: {e}")

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

    # ==================== 状态进入回调 ====================
    def _on_enter_idle(self):
        """进入空闲状态"""
        print("[状态] 进入空闲模式")
        self._app_state['state'] = State.IDLE
        self._led_blink(LED_BLINK_IDLE)
        self._audio_play('play_transition', freq=TRANSITION_FREQ, duration=TRANSITION_DURATION)
        self._no_face_time = 0
        self._cached_faces = []
        self._cached_img = None

    def _on_enter_recognizing(self):
        """进入识别状态"""
        print("[状态] 进入识别模式")
        self._app_state['state'] = State.RECOGNIZING
        self._led_blink(LED_BLINK_FAST)
        self._audio_play('play_double_beep')
        self._no_face_time = 0
        self._last_alarm_time = 0
        self._last_success_time = 0

    def _on_enter_recording(self):
        """进入录制状态"""
        print("[状态] 检测到人脸，开始录制")
        self._app_state['state'] = State.RECORDING
        self._led_blink(LED_BLINK_SLOW)
        self._recorder.start_recording(self._cam)

    def _on_enter_enrolling(self):
        """进入录入状态"""
        print("[状态] 进入录入模式")
        self._app_state['state'] = State.ENROLLING
        self._led_blink(LED_BLINK_FAST)
        self._audio_play('play_transition', freq=TRANSITION_FREQ, duration=TRANSITION_DURATION)
        self._cached_faces = []
        self._cached_img = None

    def _on_enter_error(self):
        """进入错误状态"""
        print("[状态] 进入错误状态")
        self._app_state['state'] = State.ERROR
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
            # 更新录像列表
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
        self._app_state['has_face'] = False
        self._app_state['record_duration'] = 0

        # 保存处理后的图像
        self._processed_img = img

        # 推流画面（如果启用）
        if self._stream_manager.is_streaming():
            self._stream_manager.write(img)

    def _handle_recognizing(self):
        """
        识别状态处理（优化版）：
        - 使用快速检测模式
        - 检测到人脸后转换到录制状态
        - 无人脸超时后返回空闲
        """
        img = self._cam.read()

        # 使用快速检测模式（仅检测位置，不进行身份识别）
        # 这样可以提高检测速度
        faces = self._face_detector.detect_faces_only(img)

        if faces:
            # 检测到人脸后，进行完整的识别
            recognized_faces = self._face_detector.detect_and_recognize(img)

            # 缓存人脸信息
            self._cached_faces = recognized_faces

            # 转换到录制状态
            self._state_machine.transition(State.RECORDING)
            return

        # 未检测到人脸
        current_time = time.ticks_ms()

        if self._no_face_time == 0:
            self._no_face_time = current_time

        # 检查超时
        no_face_duration = current_time - self._no_face_time
        if no_face_duration > RECOGNIZE_TIMEOUT:
            print("[系统] 无人脸超时，返回空闲状态")
            self._state_machine.transition(State.IDLE)
            return

        # 更新应用状态
        self._app_state['has_face'] = False

        # 推流画面
        if self._stream_manager.is_streaming():
            self._stream_manager.write(img)

    def _handle_recording(self):
        """
        录制状态处理（优化版）：
        - 使用快速检测模式
        - 编码视频帧
        - 无人脸超时后返回空闲
        """
        img = self._cam.read()

        # 使用快速检测模式
        faces = self._face_detector.detect_faces_only(img)

        if faces:
            # 检测到人脸，重置无人脸计时
            self._no_face_time = 0

            # 进行完整识别
            recognized_faces = self._face_detector.detect_and_recognize(img)

            # 编码视频帧
            self._recorder.encode_frame(img)

            # 处理每个人脸
            has_known_face = False
            for face in recognized_faces:
                if self._face_detector.is_known_face(face):
                    has_known_face = True
                    break

            for face in recognized_faces:
                self._process_face(img, face, has_known_face)

            # 更新应用状态
            self._app_state['has_face'] = True
            if self._recorder.is_recording():
                self._app_state['record_duration'] = self._recorder.get_recording_duration() // 1000

        else:
            # 未检测到人脸
            self._led_blink(LED_BLINK_SLOW)
            self._app_state['has_face'] = False

            current_time = time.ticks_ms()
            if self._no_face_time == 0:
                self._no_face_time = current_time

            # 检查超时
            no_face_duration = current_time - self._no_face_time
            if no_face_duration > RECOGNIZE_TIMEOUT:
                print("[系统] 无人脸超时，返回空闲状态")
                self._state_machine.transition(State.IDLE)
                return

        # 推流画面
        if self._stream_manager.is_streaming():
            self._stream_manager.write(img)

    def _process_face(self, img, face, has_known_face):
        """处理检测到的人脸"""
        label = self._face_detector.get_face_label(face)

        if self._face_detector.is_known_face(face):
            self._face_detector.draw_face(img, face,
                                         color=image.COLOR_GREEN,
                                         label=label)
            self._led_on()

            current_time = time.ticks_ms()
            if current_time - self._last_success_time > 3000:
                self._audio_play('play_welcome_music')
                self._last_success_time = current_time
        else:
            self._face_detector.draw_face(img, face,
                                         color=image.COLOR_RED,
                                         label="未知")

            if not has_known_face:
                current_time = time.ticks_ms()
                if current_time - self._last_alarm_time > 1000:
                    self._audio_play('play_alarm', freq=ALARM_FREQ, duration=ALARM_DURATION)
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
        self._app_state['has_face'] = len(faces) > 0

        # 检查是否需要显示录入结果
        if self._enroll_show_time > 0:
            current_time = time.ticks_ms()
            if current_time - self._enroll_show_time < ENROLL_SHOW_TIME:
                # 显示结果
                if self._enroll_success:
                    img.draw_string(10, 40, self._enroll_message,
                                   color=image.COLOR_GREEN, scale=1.5)
                else:
                    img.draw_string(10, 40, self._enroll_message,
                                   color=image.COLOR_RED, scale=1.5)
                # 推流画面
                if self._stream_manager.is_streaming():
                    self._stream_manager.write(img)
                return
            else:
                self._enroll_show_time = 0
                self._state_machine.transition(State.IDLE)
                return

        # 绘制人脸框
        for face in faces:
            self._face_detector.draw_face(img, face, color=image.COLOR_GREEN)

        # 推流画面
        if self._stream_manager.is_streaming():
            self._stream_manager.write(img)

    def _do_enroll_face(self):
        """执行人脸录入"""
        try:
            if not self._cached_faces or self._cached_img is None:
                print("[录入] 未检测到人脸，请调整位置")
                self._audio_play('play_error')
                return

            face = self._cached_faces[0]
            label = f"user_{time.ticks_ms() // 1000}"

            if self._face_detector.start_enrollment(label):
                success, message, count = self._face_detector.enroll_face(
                    self._cached_img)

                if success:
                    print(f"[录入] 成功: {message}")
                    self._audio_play('play_double_beep')
                    self._led_blink(100)

                    self._enroll_success = True
                    self._enroll_message = f"录入成功: {label}"
                    self._enroll_show_time = time.ticks_ms()

                    # 更新人脸列表
                    self._update_face_list()
                else:
                    print(f"[录入] 失败: {message}")
                    self._audio_play('play_error')

                    self._enroll_success = False
                    self._enroll_message = f"录入失败: {message}"
                    self._enroll_show_time = time.ticks_ms()

            self._cached_faces = []
            self._cached_img = None

        except Exception as e:
            print(f"[录入] 异常: {e}")
            self._audio_play('play_error')

    def _handle_error(self):
        """错误状态处理"""
        img = self._cam.read()

        # 推流画面
        if self._stream_manager.is_streaming():
            self._stream_manager.write(img)

    # ==================== 主循环 ====================
    def _update_fps(self):
        """更新帧率计算"""
        self._fps_counter += 1
        current_time = time.ticks_ms()
        elapsed = current_time - self._fps_start_time

        # 每秒更新一次帧率
        if elapsed >= 1000:
            self._current_fps = self._fps_counter * 1000 // elapsed
            self._fps_counter = 0
            self._fps_start_time = current_time
            # 更新应用状态中的帧率
            self._app_state['fps'] = self._current_fps

    def run(self):
        """运行主循环"""
        print("[系统] 开始运行主循环...")

        try:
            while not app.need_exit():
                # 1. 更新物理按键
                self._key_manager.update()

                # 2. 更新 LED
                self._led_update()

                # 3. 业务状态处理
                self._state_machine.update()

                # 4. 检查是否需要保存设置
                if self._app_state.get('need_save', False):
                    self._save_settings()
                    self._app_state['need_save'] = False

                # 5. 获取摄像头图像
                img = self._cam.read()

                # 6. 更新帧率计数
                self._update_fps()

                # 7. UI 页面绘制
                self._ui_manager.update(img)

                # 8. 显示图像
                self._disp.show(img)

                # 9. 短暂休眠（减少休眠时间以提高帧率）
                # 空闲状态可以休眠更长时间以节省资源
                if self._state_machine.state == State.IDLE:
                    time.sleep_ms(20)  # 空闲时休眠 20ms
                else:
                    time.sleep_ms(5)   # 活跃时休眠 5ms

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

        if self._stream_manager:
            self._stream_manager.destroy()

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
