"""
MaixCAM2 人脸识别智能系统 - 录制管理模块

功能：
- 视频录制（H265/MP4）
- 音频录制（WAV）
- 视频+音频同步录制
- 文件管理

修复：
- 使用非阻塞音频录制，实现音视频同步
"""

from maix import video, audio, time, image
import os
import _thread

class RecorderManager:
    """
    录制管理器

    功能：
    - 管理视频和音频录制
    - 生成带时间戳的文件名
    - 同步控制录制启停
    - 非阻塞音频录制
    """

    def __init__(self, record_dir, fps=25, sample_rate=16000, channel=1):
        """
        初始化录制管理器

        参数：
            record_dir: 录制文件保存目录
            fps: 视频帧率
            sample_rate: 音频采样率
            channel: 音频声道数
        """
        self._record_dir = record_dir
        self._fps = fps
        self._sample_rate = sample_rate
        self._channel = channel

        # 视频编码器
        self._video_encoder = None

        # 音频录制器（非阻塞模式）
        self._audio_recorder = None

        # 录制状态
        self._is_recording = False
        self._recording_start_time = 0

        # 当前录制文件路径
        self._current_video_path = ""
        self._current_audio_path = ""

        # 音频录制参数
        self._audio_chunk_ms = 50  # 每次读取50ms的音频数据
        self._last_audio_sync_time = 0
        self._audio_chunks = 0
        self._audio_empty_reads = 0
        self._audio_thread_running = False
        self._audio_thread_exit = True
        self._last_video_encode_time = 0
        self._video_frame_interval_ms = max(1, int(1000 / fps))
        self._video_frames = 0
        self._video_skip_frames = 0

        # 确保录制目录存在
        self._ensure_dir(record_dir)

        print(f"[录制] 录制管理器初始化完成，目录: {record_dir}")

    def _ensure_dir(self, dir_path):
        """
        确保目录存在，不存在则创建

        参数：
            dir_path: 目录路径
        """
        try:
            os.makedirs(dir_path, exist_ok=True)
        except Exception as e:
            print(f"[录制] 创建目录失败: {e}")

    def _generate_filename(self, prefix="record"):
        """
        生成带时间戳的文件名

        参数：
            prefix: 文件名前缀

        返回：
            文件名（不含路径和扩展名）
        """
        timestamp = time.ticks_ms()
        return f"{prefix}_{timestamp}"

    def start_recording(self, cam, with_audio=True):
        """
        开始录制视频+音频

        参数：
            cam: 摄像头对象
            with_audio: 是否同时录制音频

        返回：
            True: 录制启动成功
            False: 录制启动失败
        """
        if self._is_recording:
            print("[录制] 已在录制中")
            return False

        try:
            # 生成文件名
            filename = self._generate_filename()
            self._current_video_path = f"{self._record_dir}/{filename}.mp4"
            self._current_audio_path = f"{self._record_dir}/{filename}.wav"

            # 初始化视频编码器（优先设置文件帧率，固件不支持时回退旧构造方式）
            try:
                self._video_encoder = video.Encoder(
                    self._current_video_path,
                    cam.width(),
                    cam.height(),
                    framerate=self._fps
                )
            except Exception as e:
                print(f"[录制] 设置视频帧率失败，使用默认编码器参数: {e}")
                self._video_encoder = video.Encoder(
                    self._current_video_path,
                    cam.width(),
                    cam.height()
                )

            self._audio_chunks = 0
            self._audio_empty_reads = 0
            self._audio_thread_running = False
            self._audio_thread_exit = True

            if with_audio:
                # 使用非阻塞模式（block=False），避免 record() 持有 GIL 导致主线程卡顿
                self._audio_recorder = audio.Recorder(
                    self._current_audio_path,
                    sample_rate=self._sample_rate,
                    channel=self._channel,
                    block=False
                )
                self._audio_recorder.volume(100)
                self._audio_recorder.reset(True)  # 非阻塞模式必须调用 reset(True) 启动
                self._audio_thread_running = True
                self._audio_thread_exit = False
                _thread.start_new_thread(self._audio_record_thread, ())
            else:
                self._audio_recorder = None
                self._current_audio_path = ""

            # 更新状态
            self._is_recording = True
            self._recording_start_time = time.ticks_ms()
            self._last_video_encode_time = 0
            self._video_frames = 0
            self._video_skip_frames = 0

            print(f"[录制] 开始录制: {filename}")
            print(f"[录制] 视频: {self._current_video_path}")
            if self._current_audio_path:
                print(f"[录制] 音频: {self._current_audio_path}")
            else:
                print("[录制] 音频: 已禁用")

            return True

        except Exception as e:
            print(f"[录制] 录制启动失败: {e}")
            self._cleanup_recording()
            return False

    def encode_frame(self, img):
        """
        编码一帧视频并同步录制音频

        参数：
            img: MaixPy Image 对象（RGB888 格式）

        返回：
            True: 编码成功
            False: 编码失败或未在录制
        """
        if not self._is_recording:
            return False

        try:
            current_time = time.ticks_ms()
            if self._last_video_encode_time:
                elapsed = current_time - self._last_video_encode_time
                if elapsed < self._video_frame_interval_ms:
                    self._video_skip_frames += 1
                    return True
            self._last_video_encode_time = current_time

            # 编码视频帧
            # 若摄像头已是 YVU420SP（纯录制模式），直接编码，避免软件色彩转换
            if self._video_encoder:
                if img.format() == image.Format.FMT_YVU420SP:
                    self._video_encoder.encode(img)
                else:
                    self._video_encoder.encode(img.to_format(image.Format.FMT_YVU420SP))
                self._video_frames += 1

            return True

        except Exception as e:
            print(f"[录制] 编码异常: {e}")
            return False

    def _audio_record_thread(self):
        """
        独立音频录制线程（非阻塞模式）

        非阻塞 Recorder 立即返回缓冲区当前数据。
        先 sleep_ms(40) 让硬件积累约 40ms 音频，再 record(50) 取走，
        sleep_ms 会释放 GIL，主线程（摄像头/编码/UI）可自由运行。
        """
        print("[录制] 音频录制线程启动（非阻塞模式）")
        try:
            while self._audio_thread_running:
                if not self._audio_recorder:
                    break
                # 等待缓冲区积累足够数据，期间释放 GIL
                time.sleep_ms(40)
                data = self._audio_recorder.record(self._audio_chunk_ms)
                if data and len(data) > 0:
                    self._audio_chunks += 1
                    if self._audio_chunks % 20 == 0:
                        print(f"[录制] 音频已写入 {self._audio_chunks} 块，共约 {self._audio_chunks * self._audio_chunk_ms // 1000}s")
                else:
                    self._audio_empty_reads += 1
        except Exception as e:
            print(f"[录制] 音频录制线程异常: {e}")
        self._audio_thread_exit = True
        print("[录制] 音频录制线程退出")

    def stop_recording(self):
        """
        停止录制

        返回：
            (video_path, audio_path) - 录制文件路径
            None: 停止失败
        """
        if not self._is_recording:
            return None

        try:
            # 计算录制时长
            duration = time.ticks_ms() - self._recording_start_time

            # 停止音频录制
            if self._audio_recorder:
                try:
                    self._audio_thread_running = False
                    wait_start = time.ticks_ms()
                    while not self._audio_thread_exit and time.ticks_ms() - wait_start < 500:
                        time.sleep_ms(20)
                    self._audio_recorder.finish()
                except Exception as e:
                    print(f"[录制] 音频停止异常: {e}")
                self._audio_recorder = None

            # 清理视频编码器
            self._video_encoder = None

            # 保存路径
            video_path = self._current_video_path
            audio_path = self._current_audio_path

            if audio_path:
                try:
                    if (not os.path.exists(audio_path)) or os.path.getsize(audio_path) <= 44:
                        print("[录制] 音频文件未生成有效数据，本次仅保留视频")
                        audio_path = ""
                    else:
                        print(f"[录制] 音频块数: {self._audio_chunks}, 文件大小: {os.path.getsize(audio_path)} 字节")
                except Exception as e:
                    print(f"[录制] 检查音频文件失败: {e}")
                    audio_path = ""

            # 重置状态
            self._is_recording = False
            self._current_video_path = ""
            self._current_audio_path = ""

            print(f"[录制] 录制停止，时长: {duration}ms")
            print(f"[录制] 视频帧数: {self._video_frames}, 跳过帧数: {self._video_skip_frames}")
            print(f"[录制] 视频文件: {video_path}")
            print(f"[录制] 音频文件: {audio_path}")

            return (video_path, audio_path)

        except Exception as e:
            print(f"[录制] 录制停止失败: {e}")
            self._cleanup_recording()
            return None

    def _cleanup_recording(self):
        """
        清理录制资源
        """
        self._video_encoder = None
        if self._audio_recorder:
            try:
                self._audio_thread_running = False
                self._audio_recorder.finish()
            except Exception as e:
                print(f"[录制] 音频停止异常: {e}")
            self._audio_recorder = None
        self._audio_thread_exit = True
        self._is_recording = False

    def is_recording(self):
        """
        检查是否正在录制

        返回：
            True: 正在录制
            False: 未录制
        """
        return self._is_recording

    def get_recording_duration(self):
        """
        获取当前录制时长

        返回：
            录制时长（毫秒），未录制时返回 0
        """
        if not self._is_recording:
            return 0
        return time.ticks_ms() - self._recording_start_time

    def get_current_paths(self):
        """
        获取当前录制文件路径

        返回：
            (video_path, audio_path)
        """
        return (self._current_video_path, self._current_audio_path)

    def destroy(self):
        """
        销毁录制管理器，释放资源
        """
        if self._is_recording:
            self.stop_recording()
        print("[录制] 录制管理器已销毁")

