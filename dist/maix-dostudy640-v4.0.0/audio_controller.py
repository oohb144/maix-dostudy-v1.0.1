"""
MaixCAM2 人脸识别智能系统 - 音频控制模块

功能：
- 报警音播放（未录入人脸时）
- 成功提示音播放（已录入人脸时）
- 状态切换提示音播放
- 欢迎音乐播放
- 播放用户上传的WAV文件

优化：
- 使用查表法生成音频，减少计算量
- 预生成常用音频并缓存
- 完全非阻塞播放
"""

from maix import audio, time
import math
import os
import _thread


class AudioController:
    """
    音频控制器

    功能：
    - 控制 MaixCAM2 板载喇叭播放提示音
    - 支持多种提示音类型
    - 完全非阻塞播放（使用线程）
    - 音频缓存优化
    """

    def __init__(self):
        """
        初始化音频控制器
        """
        # 音频播放器
        self._player = None
        self._player_initialized = False

        # 音频参数
        self._sample_rate = 16000  # 降低采样率，减少计算量

        # 播放状态
        self._is_playing = False
        self._lock = _thread.allocate_lock()  # 线程安全锁

        # 音频缓存
        self._cache = {}

        # 预生成常用音频
        self._pre_generate_audio()

        print("[音频] 音频控制器初始化完成（优化版）")

    def _init_player(self):
        """
        延迟初始化音频播放器
        """
        if not self._player_initialized:
            try:
                self._player = audio.Player(sample_rate=self._sample_rate)
                self._player_initialized = True
                print("[音频] 播放器初始化成功")
            except Exception as e:
                print(f"[音频] 播放器初始化失败: {e}")

    def _generate_tone_fast(self, freq, duration_ms, volume=0.5):
        """
        快速生成指定频率的 PCM 音频数据（使用查表法）

        参数：
            freq: 频率（Hz）
            duration_ms: 持续时间（毫秒）
            volume: 音量（0.0 ~ 1.0）

        返回：
            PCM 音频数据（bytes）
        """
        num_samples = int(self._sample_rate * duration_ms / 1000)

        # 使用查表法生成正弦波
        table_size = 256
        sin_table = []
        for i in range(table_size):
            sin_table.append(int(math.sin(2 * math.pi * i / table_size) * volume * 32767 * 0.7))

        # 计算相位增量
        phase_inc = int(freq * table_size / self._sample_rate)

        # 生成音频
        pcm_data = bytearray(num_samples * 2)
        phase = 0
        for i in range(num_samples):
            # 衰减包络
            envelope = 1.0 - (i / num_samples) * 0.3
            sample = int(sin_table[phase % table_size] * envelope)
            pcm_data[i*2] = sample & 0xFF
            pcm_data[i*2+1] = (sample >> 8) & 0xFF
            phase += phase_inc

        return bytes(pcm_data)

    def _pre_generate_audio(self):
        """
        预生成常用音频并缓存
        """
        try:
            # 报警音
            self._cache['alarm'] = self._generate_tone_fast(2700, 100, 0.6)

            # 成功提示音
            self._cache['success'] = self._generate_tone_fast(1500, 80, 0.4)

            # 状态切换提示音
            self._cache['transition'] = self._generate_tone_fast(2000, 60, 0.3)

            # 错误提示音
            self._cache['error'] = self._generate_tone_fast(500, 100, 0.5)

            # 双 beep 音
            pcm1 = self._generate_tone_fast(2000, 40, 0.4)
            silence = b'\x00' * (self._sample_rate * 30 // 1000 * 2)
            pcm2 = self._generate_tone_fast(2500, 40, 0.4)
            self._cache['double_beep'] = pcm1 + silence + pcm2

            # 欢迎音乐（简短版）
            melody = [
                (523, 80),   # C5
                (659, 80),   # E5
                (784, 80),   # G5
                (1047, 150), # C6
            ]
            music_pcm = b''
            for freq, duration in melody:
                pcm = self._generate_tone_fast(freq, duration, 0.4)
                music_pcm += pcm
                music_pcm += b'\x00' * (self._sample_rate * 15 // 1000 * 2)
            self._cache['welcome'] = music_pcm

            print("[音频] 音频缓存预生成完成")

        except Exception as e:
            print(f"[音频] 预生成失败: {e}")

    def _play_cached(self, key):
        """
        在线程中播放缓存的音频

        参数：
            key: 缓存键名
        """
        try:
            if key in self._cache:
                self._init_player()
                if self._player:
                    self._player.play(self._cache[key])
        except Exception as e:
            print(f"[音频] 播放失败: {e}")
        finally:
            with self._lock:
                self._is_playing = False

    def _play_async_cached(self, key):
        """
        异步播放缓存的音频（非阻塞）

        参数：
            key: 缓存键名
        """
        with self._lock:
            if self._is_playing:
                return
            self._is_playing = True
        try:
            _thread.start_new_thread(self._play_cached, (key,))
        except Exception as e:
            print(f"[音频] 启动播放线程失败: {e}")
            self._is_playing = False

    def play_alarm(self, freq=2700, duration=150):
        """
        播放报警音（未录入人脸时）
        """
        self._play_async_cached('alarm')

    def play_success(self, freq=1500, duration=100):
        """
        播放成功提示音（已录入人脸时）
        """
        self._play_async_cached('success')

    def play_transition(self, freq=2000, duration=80):
        """
        播放状态切换提示音
        """
        self._play_async_cached('transition')

    def play_double_beep(self):
        """
        播放双 beep 音（用于特殊状态提示）
        """
        self._play_async_cached('double_beep')

    def play_error(self):
        """
        播放错误提示音
        """
        self._play_async_cached('error')

    def play_welcome_music(self):
        """
        播放欢迎音乐（检测到已录入人脸时）
        """
        self._play_async_cached('welcome')

    def destroy(self):
        """
        销毁音频控制器，释放资源
        """
        while self._is_playing:
            time.sleep_ms(10)

        self._player = None
        self._player_initialized = False
        self._cache.clear()
        print("[音频] 音频控制器已销毁")

    # ==================== WAV文件播放功能 ====================

    def _play_wav_thread(self, file_path):
        """
        在线程中播放WAV文件

        参数：
            file_path: WAV文件路径
        """
        try:
            # 释放常驻 tone 播放器，避免占用音频设备导致文件播放器打不开
            if self._player is not None:
                try:
                    del self._player
                except Exception:
                    pass
                self._player = None
                self._player_initialized = False

            # 创建文件播放器（阻塞模式）
            player = audio.Player(file_path)
            player.volume(80)
            player.play()
            # 播放完成后释放，归还音频设备
            try:
                del player
            except Exception:
                pass
        except Exception as e:
            print(f"[音频] 播放WAV文件失败: {e}")
        finally:
            with self._lock:
                self._is_playing = False

    def play_wav_file(self, file_path):
        """
        非阻塞播放WAV文件

        参数：
            file_path: WAV文件路径

        返回：
            True: 开始播放成功
            False: 播放失败或正在播放
        """
        with self._lock:
            if self._is_playing:
                print("[音频] 正在播放中，忽略请求")
                return False
            self._is_playing = True

        if not os.path.exists(file_path):
            print(f"[音频] 文件不存在: {file_path}")
            with self._lock:
                self._is_playing = False
            return False

        try:
            _thread.start_new_thread(self._play_wav_thread, (file_path,))
            print(f"[音频] 开始播放: {file_path}")
            return True
        except Exception as e:
            print(f"[音频] 启动播放线程失败: {e}")
            with self._lock:
                self._is_playing = False
            return False

    def play_audio_by_name(self, audio_dir, filename):
        """
        根据文件名播放音频

        参数：
            audio_dir: 音频目录
            filename: 文件名（不含扩展名）

        返回：
            True: 开始播放成功
            False: 播放失败
        """
        # 尝试多种扩展名
        extensions = ['.wav', '.mp3', '.pcm']
        for ext in extensions:
            file_path = os.path.join(audio_dir, filename + ext)
            if os.path.exists(file_path):
                return self.play_wav_file(file_path)

        print(f"[音频] 未找到音频文件: {filename}")
        return False

    def get_audio_files(self, audio_dir):
        """
        获取目录中的音频文件列表

        参数：
            audio_dir: 音频目录

        返回：
            音频文件名列表（不含扩展名）
        """
        audio_files = []
        if not os.path.exists(audio_dir):
            return audio_files

        try:
            for filename in os.listdir(audio_dir):
                if filename.endswith(('.wav', '.mp3', '.pcm')):
                    name = os.path.splitext(filename)[0]
                    audio_files.append(name)
        except Exception as e:
            print(f"[音频] 获取音频文件列表失败: {e}")

        return audio_files

    def wait_for_completion(self, timeout_ms=800):
        """
        等待当前播放完成（用于录制前避免音频设备冲突）

        参数：
            timeout_ms: 最长等待毫秒数
        """
        waited = 0
        step = 20
        while self._is_playing and waited < timeout_ms:
            time.sleep_ms(step)
            waited += step

    def stop_playback(self):
        """
        停止当前播放（注意：MaixPy没有提供停止播放的方法，此方法仅重置状态）
        """
        self._is_playing = False
        print("[音频] 播放状态已重置")
