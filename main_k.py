"""
MaixCAM2 人脸识别智能系统 - 主程序

功能：
- 整合所有模块
- 管理系统状态
- 实现主循环调度
- 处理异常情况

使用方法：
1. 将整个项目上传到 MaixCAM2
2. 确保模型文件存在于 /root/models/
3. 运行 python main.py

按键操作：
- 短按 OK 键：开始/停止人脸识别和录制
- 长按 OK 键（1.5秒）：进入/退出人脸录入模式
"""

from maix import camera, display, image, app, time

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


class FaceRecognitionSystem:
    """
    人脸识别智能系统

    状态流转：
    - IDLE（空闲）：等待用户操作
    - RECOGNIZING（识别中）：人脸识别，检测到人脸后进入录制
    - RECORDING（录制中）：人脸识别 + 视频音频录制
    - ENROLLING（录入中）：人脸录入模式
    - ERROR（错误）：异常状态
    """

    def __init__(self):
        """
        初始化系统
        """
        print("=" * 50)
        print("MaixCAM2 人脸识别智能系统")
        print("=" * 50)

        # ==================== 初始化硬件 ====================
        print("[系统] 初始化摄像头...")

        # 使用 RGB888 格式，支持绘图操作
        # 视频录制时会自动处理格式转换
        self._cam = camera.Camera(
            CAMERA_WIDTH, CAMERA_HEIGHT,
            image.Format.FMT_RGB888  # RGB888 格式，支持绘图和显示
        )
        self._cam.skip_frames(10)  # 跳过启动帧

        print("[系统] 初始化显示器...")
        self._disp = display.Display()

        # 加载中文字体（必须！否则中文显示乱码）
        print("[系统] 加载中文字体...")
        try:
            image.load_font("chinese", "/maixapp/share/font/SourceHanSansCN-Regular.otf", size=24)
            image.set_default_font("chinese")
            print("[系统] 中文字体加载成功")
        except Exception as e:
            print(f"[系统] 中文字体加载失败: {e}")

        # ==================== 初始化模块 ====================
        print("[系统] 初始化状态机...")
        self._state_machine = StateMachine(initial_state=State.IDLE)

        # LED 控制器（可选）
        if LED_ENABLE:
            print("[系统] 初始化 LED 控制器...")
            self._led = LedController()
        else:
            self._led = None
            print("[系统] LED 已禁用")

        # 音频控制器（可选）
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
        self._no_face_time = 0          # 无人脸时间
        self._last_alarm_time = 0       # 上次报警时间
        self._last_success_time = 0     # 上次成功提示时间
        self._cached_faces = []         # 缓存的人脸检测结果
        self._cached_img = None         # 缓存的当前帧
        self._enroll_show_time = 0      # 录入结果显示时间
        self._enroll_success = False    # 录入是否成功
        self._enroll_message = ""       # 录入结果消息

        print("[系统] 初始化完成！")
        print("=" * 50)

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
        """
        短按 OK 键回调：
        - IDLE → RECOGNIZING（开始识别和录制）
        - RECOGNIZING/RECORDING → IDLE（停止识别和录制）
        - ENROLLING → 执行人脸录入
        - ERROR → IDLE（重置）
        """
        current_state = self._state_machine.state
        print(f"[按键] 短按，当前状态: {current_state}")

        if current_state == State.IDLE:
            # 开始识别
            self._state_machine.transition(State.RECOGNIZING)

        elif current_state == State.RECOGNIZING:
            # 停止识别（尚未检测到人脸，未开始录制）
            self._state_machine.transition(State.IDLE)

        elif current_state == State.RECORDING:
            # 停止录制和识别
            self._state_machine.transition(State.IDLE)

        elif current_state == State.ENROLLING:
            # 执行人脸录入
            self._do_enroll_face()

        elif current_state == State.ERROR:
            # 重置
            self._state_machine.transition(State.IDLE)

    def _on_long_press(self):
        """
        长按 OK 键回调：
        - IDLE → ENROLLING（进入录入模式）
        - ENROLLING → IDLE（退出录入模式）
        """
        current_state = self._state_machine.state
        print(f"[按键] 长按，当前状态: {current_state}")

        if current_state == State.IDLE:
            # 进入录入模式
            self._state_machine.transition(State.ENROLLING)

        elif current_state == State.ENROLLING:
            # 退出录入模式
            self._state_machine.transition(State.IDLE)

    # ==================== 状态进入回调 ====================
    def _on_enter_idle(self):
        """进入空闲状态"""
        print("[状态] 进入空闲模式")
        self._led_blink(LED_BLINK_IDLE)
        self._audio_play('play_transition', freq=TRANSITION_FREQ, duration=TRANSITION_DURATION)
        # 重置状态变量
        self._no_face_time = 0
        self._cached_faces = []
        self._cached_img = None

    def _on_enter_recognizing(self):
        """进入识别状态（尚未开始录制）"""
        print("[状态] 进入识别模式，等待检测到人脸后开始录制")
        self._led_blink(LED_BLINK_FAST)
        self._audio_play('play_double_beep')
        self._no_face_time = 0
        self._last_alarm_time = 0
        self._last_success_time = 0

    def _on_enter_recording(self):
        """进入录制状态（检测到人脸，开始录制）"""
        print("[状态] 检测到人脸，开始录制")
        self._led_blink(LED_BLINK_SLOW)
        # 启动录制
        self._recorder.start_recording(self._cam)

    def _on_enter_enrolling(self):
        """进入录入状态"""
        print("[状态] 进入录入模式")
        self._led_blink(LED_BLINK_FAST)
        self._audio_play('play_transition', freq=TRANSITION_FREQ, duration=TRANSITION_DURATION)
        self._cached_faces = []
        self._cached_img = None

    def _on_enter_error(self):
        """进入错误状态"""
        print("[状态] 进入错误状态")
        self._led_blink(LED_BLINK_FAST)
        self._audio_play('play_error')

    # ==================== 状态退出回调 ====================
    def _on_exit_recognizing(self):
        """退出识别状态"""
        print("[状态] 退出识别模式")

    def _on_exit_recording(self):
        """退出录制状态"""
        print("[状态] 退出录制模式，停止录制")
        # 停止录制
        if self._recorder.is_recording():
            video_path, audio_path = self._recorder.stop_recording()
            print(f"[录制] 视频文件: {video_path}")
            print(f"[录制] 音频文件: {audio_path}")

    def _on_exit_enrolling(self):
        """退出录入状态"""
        print("[状态] 退出录入模式")
        if self._face_detector.is_enrolling():
            self._face_detector.cancel_enrollment()

    # ==================== 状态处理函数 ====================
    def _handle_idle(self):
        """
        空闲状态处理：
        - 读取摄像头图像
        - 显示状态信息
        - 显示已录入人脸数量
        - 推流画面
        """
        img = self._cam.read()

        # 显示状态信息
        self._draw_status(img, "空闲模式 - 短按识别/长按录入")

        # 显示已录入人脸数量
        class_count = self._face_detector.get_class_count()
        if class_count > 0:
            img.draw_string(10, 40, f"已录入: {class_count} 人",
                          color=image.COLOR_GREEN, scale=TEXT_SCALE)

        # 显示推流地址
        if self._stream_url:
            # 使用自定义青色 (0, 255, 255)
            cyan_color = image.Color.from_rgb(0, 255, 255)
            img.draw_string(10, img.height() - 25, f"推流: {self._stream_url}",
                          color=cyan_color, scale=0.8)

        self._disp.show(img)

        # 推流画面
        if self._stream_manager.is_streaming():
            self._stream_manager.write(img)

    def _handle_recognizing(self):
        """
        识别状态处理（尚未开始录制）：
        - 检测人脸
        - 检测到人脸后转换到 RECORDING 状态
        - 无人脸超时后返回 IDLE
        """
        img = self._cam.read()

        # 检测并识别人脸
        faces = self._face_detector.detect_and_recognize(img)

        if faces:
            # 检测到人脸，转换到录制状态
            self._cached_faces = faces
            self._state_machine.transition(State.RECORDING)
            return

        # 未检测到人脸
        current_time = time.ticks_ms()

        # 更新无人脸时间
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

        # 显示状态信息
        self._draw_status(img, "识别中 - 短按停止")

        self._disp.show(img)

        # 推流画面
        if self._stream_manager.is_streaming():
            self._stream_manager.write(img)

    def _handle_recording(self):
        """
        录制状态处理：
        - 持续检测人脸
        - 编码视频帧
        - 处理人脸识别结果
        - 无人脸超时后返回 IDLE
        """
        img = self._cam.read()

        # 检测并识别人脸
        faces = self._face_detector.detect_and_recognize(img)

        if faces:
            # 检测到人脸，重置无人脸计时
            self._no_face_time = 0

            # 编码视频帧
            self._recorder.encode_frame(img)

            # 处理每个人脸（优先判断是否有已知人脸）
            has_known_face = False
            for face in faces:
                if self._face_detector.is_known_face(face):
                    has_known_face = True
                    break

            # 处理人脸
            for face in faces:
                self._process_face(img, face, has_known_face)

            # 如果有已知人脸，LED 常亮（在 _process_face 中已设置）
            # 如果只有未知人脸，LED 快闪（在 _process_face 中已设置）

        else:
            # 未检测到人脸，LED 慢闪
            self._led_blink(LED_BLINK_SLOW)

            # 未检测到人脸
            current_time = time.ticks_ms()

            # 更新无人脸时间
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

        # 显示状态信息
        self._draw_status(img, "录制中 - 短按停止")

        # 显示已录入人脸数量（左下角）
        class_count = self._face_detector.get_class_count()
        img.draw_string(10, img.height() - 45, f"已录入: {class_count} 人",
                       color=image.COLOR_GREEN, scale=TEXT_SCALE)

        # 显示录制时长（左下角）
        if self._recorder.is_recording():
            duration = self._recorder.get_recording_duration() // 1000
            img.draw_string(10, img.height() - 20, f"录制: {duration}s",
                           color=image.COLOR_RED, scale=TEXT_SCALE)

        self._disp.show(img)

        # 推流画面（带人脸标注）
        if self._stream_manager.is_streaming():
            self._stream_manager.write(img)

    def _process_face(self, img, face, has_known_face):
        """
        处理检测到的人脸

        参数：
            img: 图像对象
            face: 人脸对象
            has_known_face: 画面中是否有已知人脸
        """
        # 获取人脸标签
        label = self._face_detector.get_face_label(face)

        if self._face_detector.is_known_face(face):
            # 已知人脸：绿框 + LED 常亮
            self._face_detector.draw_face(img, face,
                                         color=image.COLOR_GREEN,
                                         label=label)
            # LED 常亮
            self._led_on()

            # 播放欢迎音乐（每3秒一次，避免重复播放）
            current_time = time.ticks_ms()
            if current_time - self._last_success_time > 3000:
                self._audio_play('play_welcome_music')
                self._last_success_time = current_time

        else:
            # 未知人脸：红框
            self._face_detector.draw_face(img, face,
                                         color=image.COLOR_RED,
                                         label="未知")

            # 只有画面中没有已知人脸时才报警
            if not has_known_face:
                # 报警提示（每1秒一次）
                current_time = time.ticks_ms()
                if current_time - self._last_alarm_time > 1000:
                    self._audio_play('play_alarm', freq=ALARM_FREQ, duration=ALARM_DURATION)
                    self._last_alarm_time = current_time
                    # LED 快闪
                    self._led_blink(LED_BLINK_FAST)

    def _handle_enrolling(self):
        """
        录入状态处理：
        - 检测人脸并缓存结果
        - 显示引导信息
        - 等待按键触发录入
        """
        # 读取摄像头图像并缓存
        img = self._cam.read()
        self._cached_img = img

        # 检测人脸并缓存结果
        faces = self._face_detector.detect_and_recognize(img)
        self._cached_faces = faces

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
                self._disp.show(img)
                return
            else:
                # 显示时间结束，返回空闲状态
                self._enroll_show_time = 0
                self._state_machine.transition(State.IDLE)
                return

        if faces:
            # 检测到人脸，显示提示
            img.draw_string(10, 40, "检测到人脸，按下 OK 键录入",
                           color=image.COLOR_GREEN, scale=TEXT_SCALE)

            # 绘制人脸框
            for face in faces:
                self._face_detector.draw_face(img, face, color=image.COLOR_GREEN)
        else:
            # 未检测到人脸
            img.draw_string(10, 40, "请正对摄像头",
                           color=image.COLOR_YELLOW, scale=TEXT_SCALE)

        # 显示状态信息
        self._draw_status(img,
                         f"录入模式 - 已录入 {self._face_detector.get_class_count()} 人")

        self._disp.show(img)

        # 推流画面
        if self._stream_manager.is_streaming():
            self._stream_manager.write(img)

    def _do_enroll_face(self):
        """
        执行人脸录入（使用缓存的检测结果）

        修复问题6：使用缓存的人脸检测结果，避免重复检测
        """
        try:
            # 检查缓存
            if not self._cached_faces or self._cached_img is None:
                print("[录入] 未检测到人脸，请调整位置")
                self._audio_play('play_error')
                return

            # 取第一个检测到的人脸
            face = self._cached_faces[0]

            # 生成标签（使用时间戳）
            label = f"user_{time.ticks_ms() // 1000}"

            # 开始录入
            if self._face_detector.start_enrollment(label):
                success, message, count = self._face_detector.enroll_face(
                    self._cached_img)

                if success:
                    print(f"[录入] 成功: {message}")
                    self._audio_play('play_double_beep')
                    # LED 快闪（非阻塞）
                    self._led_blink(100)

                    # 设置显示时间和消息
                    self._enroll_success = True
                    self._enroll_message = f"录入成功: {label}"
                    self._enroll_show_time = time.ticks_ms()
                else:
                    print(f"[录入] 失败: {message}")
                    self._audio_play('play_error')

                    # 设置显示时间和消息
                    self._enroll_success = False
                    self._enroll_message = f"录入失败: {message}"
                    self._enroll_show_time = time.ticks_ms()

            # 清除缓存
            self._cached_faces = []
            self._cached_img = None

        except Exception as e:
            print(f"[录入] 异常: {e}")
            self._audio_play('play_error')

    def _handle_error(self):
        """
        错误状态处理
        """
        img = self._cam.read()
        img.draw_string(10, 30, "系统错误", color=image.COLOR_RED, scale=2.0)
        img.draw_string(10, 70, "短按 OK 键重置", color=image.COLOR_WHITE, scale=TEXT_SCALE)
        self._disp.show(img)

        # 推流画面
        if self._stream_manager.is_streaming():
            self._stream_manager.write(img)

    # ==================== 辅助函数 ====================
    def _draw_status(self, img, status_text):
        """
        绘制状态信息

        参数：
            img: 图像对象
            status_text: 状态文字
        """
        # 绘制状态背景（使用 image.COLOR_BLACK）
        img.draw_rect(0, 0, img.width(), 25, color=image.COLOR_BLACK, thickness=-1)
        # 绘制状态文字（使用 image.COLOR_WHITE）
        img.draw_string(STATUS_TEXT_X, 5, status_text,
                        color=image.COLOR_WHITE, scale=TEXT_SCALE)

    # ==================== 主循环 ====================
    def run(self):
        """
        运行主循环
        """
        print("[系统] 开始运行主循环...")

        try:
            while not app.need_exit():
                # 更新按键状态
                self._key_manager.update()

                # 更新 LED 状态
                self._led_update()

                # 更新状态机
                self._state_machine.update()

                # 短暂休眠，释放 CPU
                time.sleep_ms(10)

        except KeyboardInterrupt:
            print("[系统] 用户中断")
        except Exception as e:
            print(f"[系统] 异常: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._cleanup()

    def _cleanup(self):
        """
        清理资源
        """
        print("[系统] 清理资源...")

        # 停止推流
        if self._stream_manager:
            self._stream_manager.destroy()

        # 停止录制
        if self._recorder.is_recording():
            self._recorder.stop_recording()

        # 销毁模块
        self._key_manager.destroy()
        if self._led:
            self._led.destroy()
        if self._audio:
            self._audio.destroy()
        self._recorder.destroy()

        print("[系统] 资源清理完成")


# ==================== 程序入口 ====================
def main():
    """
    主函数
    """
    try:
        system = FaceRecognitionSystem()
        system.run()
    except Exception as e:
        print(f"[系统] 启动失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
