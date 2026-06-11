# -*- coding: utf-8 -*-
"""
MaixCAM2 人脸识别系统 - 视频融合与播放管理模块

功能：
- 将同名 MP4 视频和 WAV 音频融合为带音频 MP4
- 使用 MaixPy video.Decoder 播放视频画面
- 在 decode_video 仅输出视频帧时，使用非阻塞音频流同步播放 WAV
- 保留原始录制文件，融合产物使用 _av.mp4 后缀
"""

from maix import video, audio, time, app
import os
import _thread


class WavStreamPlayer:
    """按块播放 WAV 数据，尽量与视频画面同步启动"""

    def __init__(self, file_path, volume=80, chunk_bytes=8192):
        self._file_path = file_path
        self._volume = volume
        self._chunk_bytes = chunk_bytes
        self._player = None
        self._thread_started = False
        self._finished = False
        self._start_failed = False
        self._data_offset = 44
        self._sample_rate = 16000
        self._channel = 1
        self._bits_per_sample = 16

    def start(self):
        """启动后台音频流播放"""
        if self._thread_started or not self._prepare():
            return False
        self._thread_started = True
        try:
            _thread.start_new_thread(self._play_thread, ())
            return True
        except Exception as e:
            self._start_failed = True
            print(f"[播放器] 启动音频流线程失败: {e}")
            return False

    def is_finished(self):
        """音频是否已播放完成"""
        return self._finished

    def wait_finish(self, timeout_ms=1500):
        """等待音频尾部尽量播完，避免刚结束就退出"""
        deadline = time.ticks_ms() + timeout_ms
        while not app.need_exit() and not self._finished:
            if time.ticks_ms() >= deadline:
                break
            time.sleep_ms(10)

    def _prepare(self):
        """读取 WAV 头，初始化播放器参数"""
        if not self._file_path or not os.path.exists(self._file_path):
            return False

        try:
            with open(self._file_path, "rb") as f:
                header = f.read(44)

            if len(header) < 44 or header[0:4] != b"RIFF" or header[8:12] != b"WAVE":
                print(f"[播放器] WAV 头无效，无法流式播放: {self._file_path}")
                return False

            self._channel = int.from_bytes(header[22:24], "little") or 1
            self._sample_rate = int.from_bytes(header[24:28], "little") or 16000
            self._bits_per_sample = int.from_bytes(header[34:36], "little") or 16
            self._data_offset = self._find_data_offset(header)

            if self._bits_per_sample != 16:
                print(f"[播放器] 当前仅验证过 16bit WAV，实际为 {self._bits_per_sample}bit")

            self._player = audio.Player(
                sample_rate=self._sample_rate,
                channel=self._channel,
                block=False
            )
            self._player.volume(self._volume)

            # 先灌一小段静音，尽量减少首包启动抖动
            self._player.play(bytes([0] * 4096))
            return True
        except Exception as e:
            print(f"[播放器] 初始化 WAV 流播放器失败: {e}")
            self._player = None
            return False

    def _find_data_offset(self, header):
        """尽量从标准 WAV 头中找到 data 块偏移"""
        if len(header) < 44:
            return 44
        if header[36:40] == b"data":
            return 44
        for idx in range(12, max(12, len(header) - 8)):
            if header[idx:idx + 4] == b"data":
                return idx + 8
        return 44

    def _wait_idle_size(self, size):
        """等待播放器内部缓冲有足够空闲再写入"""
        if not self._player or not hasattr(self._player, "get_remaining_frames"):
            return

        while not app.need_exit():
            try:
                idle_frames = self._player.get_remaining_frames()
                frame_size = self._player.frame_size()
                write_frames = int((size + frame_size - 1) / frame_size)
                if idle_frames >= write_frames:
                    break
            except Exception:
                break
            time.sleep_ms(4)

    def _align_chunk_size(self, chunk):
        """按采样位宽和声道对齐块大小，避免拆到半帧"""
        if not chunk:
            return chunk
        bytes_per_sample = max(1, self._bits_per_sample // 8)
        align = max(1, self._channel * bytes_per_sample)
        valid_len = (len(chunk) // align) * align
        return chunk[:valid_len]

    def _play_thread(self):
        """后台按块读 WAV 并喂给非阻塞播放器"""
        try:
            with open(self._file_path, "rb") as f:
                f.seek(self._data_offset)
                while not app.need_exit():
                    chunk = f.read(self._chunk_bytes)
                    if not chunk:
                        break

                    chunk = self._align_chunk_size(chunk)
                    if not chunk:
                        continue

                    self._wait_idle_size(len(chunk))
                    self._player.play(chunk)

            # 等待底层缓冲尽量输出完成
            if self._player and hasattr(self._player, "period_count") and hasattr(self._player, "period_size"):
                try:
                    total_frames = self._player.period_count() * self._player.period_size()
                    while not app.need_exit():
                        idle_frames = self._player.get_remaining_frames()
                        if idle_frames >= total_frames:
                            break
                        time.sleep_ms(10)
                except Exception:
                    pass
        except Exception as e:
            self._start_failed = True
            print(f"[播放器] WAV 流播放失败: {e}")
        finally:
            self._finished = True


class VideoPlayerManager:
    """视频播放器管理器"""

    def __init__(self, disp, record_dir, volume=80):
        """
        初始化视频播放器

        参数:
            disp: MaixPy 显示对象
            record_dir: 录像文件目录
            volume: 播放音量
        """
        self._disp = disp
        self._record_dir = record_dir
        self._volume = volume
        self._ensure_dir(record_dir)
        print(f"[播放器] 初始化完成，目录: {record_dir}")

    def _ensure_dir(self, dir_path):
        """确保目录存在"""
        try:
            os.makedirs(dir_path, exist_ok=True)
        except Exception as e:
            print(f"[播放器] 创建目录失败: {e}")

    def get_muxed_path(self, video_path):
        """获取融合后的视频路径"""
        if not video_path:
            return ""
        base, ext = os.path.splitext(video_path)
        if base.endswith("_av"):
            return video_path
        return f"{base}_av{ext or '.mp4'}"

    def find_audio_path(self, video_path):
        """查找与视频对应的 WAV 音频文件"""
        if not video_path:
            return ""
        base, _ = os.path.splitext(video_path)
        if base.endswith("_av"):
            base = base[:-3]
        audio_path = base + ".wav"
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 44:
            return audio_path
        return ""

    def list_video_items(self):
        """
        读取录像目录中的原始视频和已融合视频

        返回:
            录像信息列表，每项包含原始 MP4、WAV、融合 MP4 的路径和大小
        """
        items = []
        try:
            if not os.path.exists(self._record_dir):
                return items

            for name in os.listdir(self._record_dir):
                if (not name.endswith(".mp4")) or name.endswith("_av.mp4"):
                    continue

                video_path = os.path.join(self._record_dir, name)
                base = name[:-4]
                audio_name = base + ".wav"
                av_name = base + "_av.mp4"
                audio_path = os.path.join(self._record_dir, audio_name)
                av_path = os.path.join(self._record_dir, av_name)
                audio_size = os.path.getsize(audio_path) if os.path.exists(audio_path) else 0
                av_size = os.path.getsize(av_path) if os.path.exists(av_path) else 0

                items.append({
                    "name": name,
                    "video_path": video_path,
                    "video_size": os.path.getsize(video_path),
                    "audio_name": audio_name if audio_size > 44 else "",
                    "audio_path": audio_path if audio_size > 44 else "",
                    "audio_size": audio_size if audio_size > 44 else 0,
                    "av_name": av_name if av_size > 0 else "",
                    "av_path": av_path if av_size > 0 else "",
                    "av_size": av_size,
                })

            items.sort(key=lambda item: item.get("name", ""), reverse=True)
        except Exception as e:
            print(f"[播放器] 读取录像列表失败: {e}")
        return items

    def count_muxed(self):
        """统计已融合视频数量"""
        count = 0
        for item in self.list_video_items():
            if item.get("av_size", 0) > 0:
                count += 1
        return count

    def mux_all(self):
        """
        批量融合所有已有 MP4/WAV 文件

        返回:
            (成功数量, 总数量)
        """
        success_count = 0
        total_count = 0
        for item in self.list_video_items():
            if not item.get("audio_path"):
                continue
            total_count += 1
            output_path = self.mux(item.get("video_path", ""), item.get("audio_path", ""))
            if output_path and output_path.endswith("_av.mp4") and os.path.exists(output_path):
                success_count += 1
        print(f"[播放器] 批量融合完成: {success_count}/{total_count}")
        return success_count, total_count

    def mux(self, video_path, audio_path=""):
        """
        合成 MP4 + WAV 为带音频 MP4

        返回:
            合成后视频路径；失败时返回原视频路径或空字符串
        """
        if not video_path or not os.path.exists(video_path):
            print(f"[播放器] 视频不存在: {video_path}")
            return ""

        if video_path.endswith("_av.mp4"):
            return video_path

        if not audio_path:
            audio_path = self.find_audio_path(video_path)
        if not audio_path:
            print("[播放器] 未找到有效 WAV，使用原视频播放")
            return video_path

        output_path = self.get_muxed_path(video_path)
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception as e:
                print(f"[播放器] 删除旧融合文件失败: {e}")
                return output_path

        commands = [
            (
                "ffmpeg -y -i \"{}\" -i \"{}\" "
                "-c:v libx264 -pix_fmt yuv420p -x264opts \"bframes=0\" "
                "-c:a aac -b:a 96k -shortest \"{}\""
            ).format(video_path, audio_path, output_path),
            (
                "ffmpeg -y -i \"{}\" -i \"{}\" "
                "-c:v copy -c:a aac -b:a 96k -shortest \"{}\""
            ).format(video_path, audio_path, output_path),
        ]

        print(f"[播放器] 开始合成: {output_path}")
        ret = -1
        for idx, cmd in enumerate(commands):
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except Exception:
                    pass
            ret = os.system(cmd)
            if ret == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                if idx == 0:
                    print(f"[播放器] H264 合成完成: {output_path}")
                else:
                    print(f"[播放器] 回退方案合成完成: {output_path}")
                return output_path
            print(f"[播放器] 合成尝试 {idx + 1} 失败，返回码: {ret}")

        return video_path

    def play(self, video_path):
        """
        播放视频文件

        参数:
            video_path: MP4 文件路径

        返回:
            True: 播放完成
            False: 播放失败
        """
        if not video_path or not os.path.exists(video_path):
            print(f"[播放器] 播放文件不存在: {video_path}")
            return False

        decoder = None
        pcm_player = None
        stream_player = None
        audio_started = False
        try:
            decoder = video.Decoder(video_path)
            print(f"[播放器] 开始播放: {video_path}")
            print(f"[播放器] 分辨率: {decoder.width()}x{decoder.height()} fps={decoder.fps()}")

            if hasattr(decoder, "seek"):
                decoder.seek(0)

            last_us = time.ticks_us()
            while not app.need_exit():
                if hasattr(decoder, "decode_video"):
                    ctx = decoder.decode_video()
                    if not ctx:
                        break

                    img = self._get_ctx_image(ctx)
                    if img:
                        if not audio_started:
                            audio_started = True
                            stream_player = self._create_stream_player(video_path)

                        while time.ticks_us() - last_us < self._get_ctx_duration_us(ctx):
                            time.sleep_ms(1)
                        last_us = time.ticks_us()
                        self._disp.show(img)
                    else:
                        print("[播放器] 解码到视频上下文，但未取到图像")
                    continue

                if pcm_player is None:
                    sample_rate, channel = self._get_audio_params(decoder)
                    try:
                        pcm_player = audio.Player(sample_rate=sample_rate, channel=channel, block=False)
                        pcm_player.volume(self._volume)
                    except Exception as e:
                        print(f"[播放器] PCM 音频播放器初始化失败，仅播放画面: {e}")
                        pcm_player = None

                ctx = decoder.decode()
                if not ctx:
                    break

                if self._is_video_ctx(ctx):
                    img = self._get_ctx_image(ctx)
                    if img:
                        self._disp.show(img)
                        delay_ms = max(1, int(self._get_ctx_duration_us(ctx) / 1000))
                        time.sleep_ms(delay_ms)
                elif self._is_audio_ctx(ctx):
                    pcm = self._get_ctx_pcm(ctx)
                    if pcm and pcm_player:
                        self._wait_pcm_idle_size(pcm_player, len(pcm))
                        pcm_player.play(pcm)

            if stream_player:
                stream_player.wait_finish()

            print("[播放器] 播放结束")
            return True

        except Exception as e:
            print(f"[播放器] 播放失败: {e}")
            return False
        finally:
            try:
                if decoder:
                    decoder.close()
            except Exception:
                pass
            try:
                if pcm_player:
                    pcm_player.finish()
            except Exception:
                pass

    def _create_stream_player(self, video_path):
        """为 decode_video 路径创建流式音频播放器"""
        audio_path = self.find_audio_path(video_path)
        if not audio_path:
            print("[播放器] 未找到可播放的 WAV 音频文件，本次仅播放画面")
            return None

        player = WavStreamPlayer(audio_path, volume=self._volume)
        if not player.start():
            print("[播放器] 启动流式音频失败，本次仅播放画面")
            return None

        print(f"[播放器] 启动流式音频播放: {audio_path}")
        return player

    def _wait_pcm_idle_size(self, player, size):
        """等待 PCM 播放器有足够空闲缓冲"""
        if not player or not hasattr(player, "get_remaining_frames"):
            return

        while not app.need_exit():
            try:
                idle_frames = player.get_remaining_frames()
                frame_size = player.frame_size()
                write_frames = int((size + frame_size - 1) / frame_size)
                if idle_frames >= write_frames:
                    break
            except Exception:
                break
            time.sleep_ms(4)

    def _get_audio_params(self, decoder):
        """读取解码器音频参数，失败时使用录制默认值"""
        sample_rate = 16000
        channel = 1
        try:
            if hasattr(decoder, "audio_sample_rate"):
                sample_rate = decoder.audio_sample_rate() or sample_rate
        except Exception:
            pass
        try:
            if hasattr(decoder, "audio_channels"):
                channel = decoder.audio_channels() or channel
        except Exception:
            pass
        return sample_rate, channel

    def _get_ctx_image(self, ctx):
        """兼容不同固件的视频帧接口"""
        if hasattr(ctx, "image"):
            return ctx.image()
        if hasattr(ctx, "get_image"):
            return ctx.get_image()
        return None

    def _get_ctx_pcm(self, ctx):
        """兼容不同固件的音频 PCM 接口"""
        if hasattr(ctx, "get_pcm"):
            return ctx.get_pcm()
        if hasattr(ctx, "pcm"):
            return ctx.pcm()
        return None

    def _get_ctx_duration_us(self, ctx):
        """获取帧持续时间"""
        try:
            if hasattr(ctx, "duration_us"):
                return ctx.duration_us() or 40000
        except Exception:
            pass
        return 40000

    def _get_ctx_media_name(self, ctx):
        """读取媒体类型名称用于兼容判断"""
        try:
            media_type = ctx.media_type()
            return str(media_type)
        except Exception:
            return ""

    def _is_video_ctx(self, ctx):
        """判断当前解码上下文是否为视频帧"""
        try:
            if hasattr(video, "MediaType"):
                return ctx.media_type() == video.MediaType.MEDIA_TYPE_VIDEO
        except Exception:
            pass
        return "VIDEO" in self._get_ctx_media_name(ctx).upper()

    def _is_audio_ctx(self, ctx):
        """判断当前解码上下文是否为音频帧"""
        try:
            if hasattr(video, "MediaType"):
                return ctx.media_type() == video.MediaType.MEDIA_TYPE_AUDIO
        except Exception:
            pass
        return "AUDIO" in self._get_ctx_media_name(ctx).upper()
