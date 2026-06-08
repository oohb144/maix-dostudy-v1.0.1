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

    def start_recording(self, cam):
        """
        开始录制视频+音频

        参数：
            cam: 摄像头对象

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

            # 初始化视频编码器（正确用法：文件路径作为第一个参数）
            self._video_encoder = video.Encoder(
                self._current_video_path,
                cam.width(),
                cam.height()
            )

            # 初始化音频录制器（非阻塞模式）
            self._audio_recorder = audio.Recorder(
                self._current_audio_path,
                block=False  # 非阻塞模式
            )
            self._audio_recorder.volume(100)
            self._audio_recorder.reset(True)  # 开始录制

            # 更新状态
            self._is_recording = True
            self._recording_start_time = time.ticks_ms()

            print(f"[录制] 开始录制: {filename}")
            print(f"[录制] 视频: {self._current_video_path}")
            print(f"[录制] 音频: {self._current_audio_path}")

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
            # 编码视频帧
            # 注意：video.Encoder 需要 YVU420SP 格式，需要先转换
            if self._video_encoder:
                # 将 RGB888 转换为 YVU420SP 格式
                img_yvu = img.to_format(image.Format.FMT_YVU420SP)
                self._video_encoder.encode(img_yvu)

            # 同步录制音频（非阻塞）
            if self._audio_recorder:
                self._sync_audio()

            return True

        except Exception as e:
            print(f"[录制] 编码异常: {e}")
            return False

    def _sync_audio(self):
        """
        同步录制音频数据

        功能：
        - 检查是否有足够的音频帧
        - 读取并保存音频数据
        """
        try:
            # 检查剩余帧数
            remaining_frames = self._audio_recorder.get_remaining_frames()
            need_frames = self._audio_chunk_ms * self._sample_rate // 1000

            # 如果有足够的帧，读取一部分
            if remaining_frames >= need_frames:
                data = self._audio_recorder.record(self._audio_chunk_ms)
                # 数据已经被录制到文件中

        except Exception as e:
            # 音频录制失败不影响视频录制
            print(f"[录制] 音频同步警告: {e}")

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
                    self._audio_recorder.finish()
                except Exception as e:
                    print(f"[录制] 音频停止异常: {e}")
                self._audio_recorder = None

            # 清理视频编码器
            self._video_encoder = None

            # 保存路径
            video_path = self._current_video_path
            audio_path = self._current_audio_path

            # 重置状态
            self._is_recording = False
            self._current_video_path = ""
            self._current_audio_path = ""

            print(f"[录制] 录制停止，时长: {duration}ms")
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
                self._audio_recorder.finish()
            except Exception as e:
                print(f"[录制] 音频停止异常: {e}")
            self._audio_recorder = None
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
