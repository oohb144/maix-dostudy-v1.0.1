"""
MaixCAM2 人脸识别智能系统 - WebSocket 音频推流模块

功能：
- 通过 WebSocket 实时推送麦克风采集的 PCM 音频到浏览器
- 支持多客户端同时监听
- 独立线程运行，不阻塞主循环
- 浏览器端使用 Web Audio API 播放

音频格式：
- 采样率：16000 Hz（可配置）
- 声道：单声道
- 位深度：16-bit signed little-endian (PCM_S16LE)
- 每帧：约 50ms ≈ 1600 字节

使用方法：
- 创建 AudioStreamer 实例并调用 start()
- 浏览器通过 WebSocket 连接到 ws://<设备IP>:<port>
- 接收二进制 PCM 数据，用 AudioContext 播放
"""

import _thread
import asyncio


class AudioStreamer:
    """
    WebSocket 音频推流器

    功能：
    - 在独立线程中运行 asyncio WebSocket 服务器
    - 在另一个独立线程中采集麦克风音频
    - 将 PCM 音频数据实时推送给所有连接的浏览器客户端
    - 支持多客户端同时连接
    """

    def __init__(self, port=8002, sample_rate=16000, channel=1, chunk_ms=50):
        """
        初始化音频推流器

        参数：
            port: WebSocket 端口号，默认 8002
            sample_rate: 音频采样率，默认 16000
            channel: 声道数，默认 1（单声道）
            chunk_ms: 每次采集时长（毫秒），默认 50
        """
        self._port = port
        self._sample_rate = sample_rate
        self._channel = channel
        self._chunk_ms = chunk_ms
        self._running = False
        self._recorder = None
        self._clients = set()
        self._lock = _thread.allocate_lock()
        self._event_loop = None
        self._server = None
        self._client_busy = {}
        self._dropped_chunks = 0
        self._sent_chunks = 0
        self._empty_reads = 0
        self._client_pending = {}
        self._need_frames = int(self._chunk_ms * self._sample_rate / 1000)
        self._max_buffer_frames = self._need_frames * 4

        # 音频参数描述（发送给客户端的初始信息）
        self._audio_info = {
            "type": "info",
            "sample_rate": sample_rate,
            "channel": channel,
            "chunk_ms": chunk_ms,
            "format": "pcm_s16le"
        }

        print(f"[音频推流] 初始化完成，端口: {port}, 采样率: {sample_rate}Hz")
        print("[音频推流] 版本: audio-debug-20260608-2238-adaptive-video")

    def start(self):
        """
        启动音频推流器（WebSocket 服务 + 音频采集线程）

        返回：
            True: 启动成功
            False: 启动失败
        """
        if self._running:
            print("[音频推流] 已在运行中")
            return True

        self._running = True

        # 启动 WebSocket 服务线程
        try:
            _thread.start_new_thread(self._serve_websocket, ())
            print(f"[音频推流] WebSocket 服务已启动，端口: {self._port}")
        except Exception as e:
            print(f"[音频推流] WebSocket 服务启动失败: {e}")
            self._running = False
            return False

        # 启动音频采集线程
        try:
            _thread.start_new_thread(self._capture_audio, ())
            print("[音频推流] 音频采集已启动")
        except Exception as e:
            print(f"[音频推流] 音频采集启动失败: {e}")
            # WebSocket 仍然可以运行，只是没有音频数据

        return True

    def stop(self):
        """
        停止音频推流器
        """
        self._running = False

        # 关闭音频录制器
        if self._recorder:
            try:
                self._recorder.finish()
            except Exception:
                pass
            self._recorder = None

        # 关闭所有 WebSocket 客户端
        with self._lock:
            for ws in self._clients:
                try:
                    asyncio.run_coroutine_threadsafe(
                        ws.close(), self._event_loop
                    )
                except Exception:
                    pass
            self._clients.clear()
            self._client_busy.clear()

        # 停止 asyncio 事件循环
        if self._event_loop and self._event_loop.is_running():
            self._event_loop.call_soon_threadsafe(self._event_loop.stop)

        print("[音频推流] 已停止")

    def _serve_websocket(self):
        """
        运行 asyncio WebSocket 服务器（在独立线程中）

        功能：
        - 监听指定端口
        - 接受浏览器 WebSocket 连接
        - 将客户端添加到广播列表
        - 客户端断开时从列表中移除
        """
        try:
            import websockets
        except ImportError:
            print("[音频推流] websockets 库未安装，尝试加载...")
            try:
                # MaixPy 可能使用不同的导入方式
                from maix import websockets
            except ImportError:
                print("[音频推流] 错误：websockets 库不可用，音频推流功能无法使用")
                self._running = False
                return

        async def handle_client(websocket, path=None):
            """处理单个 WebSocket 客户端连接"""
            # 发送音频参数信息
            try:
                import json
                await websocket.send(json.dumps(self._audio_info))
            except Exception:
                pass

            # 添加到客户端列表
            with self._lock:
                self._clients.add(websocket)
                self._client_busy[websocket] = False
            client_count = len(self._clients)
            print(f"[音频推流] 客户端连接，当前连接数: {client_count}")

            try:
                # 保持连接（等待客户端断开）
                async for message in websocket:
                    # 目前不处理客户端消息
                    pass
            except Exception:
                pass
            finally:
                # 从客户端列表中移除
                with self._lock:
                    self._clients.discard(websocket)
                    self._client_busy.pop(websocket, None)
                client_count = len(self._clients)
                print(f"[音频推流] 客户端断开，当前连接数: {client_count}")

        async def process_request(connection, request):
            """
            处理 WebSocket 握手前的 HTTP 请求

            如果请求不是 WebSocket 升级请求（例如浏览器直接访问 8002 端口），
            返回友好的 HTTP 响应页面，避免报 InvalidUpgrade 错误。
            WebSocket 升级请求则正常放行。
            """
            # 检查是否为有效的 WebSocket 升级请求
            upgrade = request.headers.get("Upgrade", "")
            if upgrade.lower() != "websocket":
                # 浏览器直接访问此端口，返回友好提示
                html = (
                    "<html><body style='font-family:sans-serif;padding:40px;text-align:center'>"
                    "<h2>MaixCAM2 音频推流服务</h2>"
                    "<p>此端口 (8002) 用于 WebSocket 音频数据传输</p>"
                    "<p>请访问 <a href='http://{}:8000'>主页面</a> 并点击 🔊 按钮开启音频</p>"
                    "</body></html>"
                )
                # 尝试获取设备 IP 填入链接
                try:
                    from maix import network
                    w = network.wifi.Wifi()
                    ip = w.get_ip()
                except Exception:
                    ip = "设备IP"
                body = html.format(ip).encode("utf-8")
                headers = {"Content-Type": "text/html; charset=utf-8"}
                await connection.respond(200, "OK", headers=headers, body=body)
                return connection  # 返回非 None 表示已处理，不再进行 WebSocket 升级
            # 是 WebSocket 升级请求，返回 None 放行
            return None

        async def run_server():
            """启动 WebSocket 服务器（兼容不同版本的 websockets 库）"""
            # 先尝试带 process_request 参数（websockets 12+），失败则回退
            try:
                self._server = await websockets.serve(
                    handle_client,
                    "0.0.0.0",
                    self._port,
                    max_size=None,
                    process_request=process_request
                )
                print(f"[音频推流] WebSocket 服务器正在监听端口 {self._port}")
            except TypeError:
                # 旧版 websockets 不支持 process_request 参数，回退
                print("[音频推流] 不支持 process_request，使用兼容模式")
                self._server = await websockets.serve(
                    handle_client,
                    "0.0.0.0",
                    self._port,
                    max_size=None
                )
                print(f"[音频推流] WebSocket 服务器正在监听端口 {self._port}")

            try:
                # 保持事件循环运行
                await asyncio.Future()  # 永不完成，直到 stop() 调用
            except Exception as e:
                print(f"[音频推流] 服务器异常: {e}")
            finally:
                if self._server:
                    self._server.close()
                    await self._server.wait_closed()

        # 创建并运行事件循环
        self._event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._event_loop)

        try:
            self._event_loop.run_until_complete(run_server())
        except Exception as e:
            if self._running:  # 只在运行中才报告错误
                print(f"[音频推流] 事件循环异常: {e}")
        finally:
            self._event_loop.close()
            print("[音频推流] WebSocket 服务线程已退出")

    def _capture_audio(self):
        """
        音频采集循环（在独立线程中运行）

        功能：
        - 初始化音频录制器（无文件模式，非阻塞）
        - 持续采集 PCM 音频数据
        - 将数据广播给所有 WebSocket 客户端

        优化：
        - 先检查缓冲区是否有足够数据再读取，避免返回空数据
        - 没有客户端时跳过采集，释放 CPU
        - 每次采集后主动让出 CPU 时间片
        """
        from maix import audio, time

        # 等待 WebSocket 服务就绪
        time.sleep_ms(500)

        try:
            # 初始化音频录制器（无文件路径 = 原始 PCM 模式）。采集线程独立运行，使用阻塞读取避免空读。
            self._recorder = audio.Recorder(
                sample_rate=self._sample_rate,
                channel=self._channel,
                block=True
            )
            self._recorder.volume(100)
            self._recorder.reset(True)  # 启动音频流

            # 计算每次需要的帧数
            self._need_frames = int(self._chunk_ms * self._sample_rate / 1000)
            self._max_buffer_frames = self._need_frames * 4

            print(f"[音频推流] 录制器初始化成功，采样率: {self._sample_rate}Hz")
            print(f"[音频推流] 每帧: {self._chunk_ms}ms, 需 {self._need_frames} 帧")

        except Exception as e:
            print(f"[音频推流] 录制器初始化失败: {e}")
            self._recorder = None
            return

        # 音频采集主循环
        while self._running:
            try:
                # 检查是否有客户端连接
                with self._lock:
                    client_count = len(self._clients)

                if client_count == 0:
                    # 没有客户端时不读取麦克风，避免 block=True 占用多媒体资源。
                    time.sleep_ms(200)
                    continue

                # 阻塞读取一块音频。此处在独立线程中运行，不会阻塞主 UI 循环。
                pcm_data = self._recorder.record(self._chunk_ms)

                if not pcm_data or len(pcm_data) == 0:
                    self._empty_reads += 1
                    if self._empty_reads % 10 == 0:
                        print(f"[音频推流] 空读 {self._empty_reads} 次, block=True, chunk_ms={self._chunk_ms}")
                    time.sleep_ms(5)
                    continue

                if pcm_data and len(pcm_data) > 0:
                    # MaixPy 返回值可能不是标准 bytes，WebSocket 发送前统一转为二进制字节串。
                    try:
                        pcm_data = bytes(pcm_data)
                    except Exception as e:
                        print(f"[音频推流] PCM 转换失败: {e}")
                        continue

                    self._sent_chunks += 1
                    if self._sent_chunks % 40 == 0:
                        peak = self._calc_pcm_peak(pcm_data)
                        print(f"[音频推流] 已发送 {self._sent_chunks} 块, len={len(pcm_data)}, peak={peak}, dropped={self._dropped_chunks}")

                    # 广播给所有客户端
                    self._broadcast(pcm_data)

                # 让出 CPU 时间片，避免和主循环抢资源
                time.sleep_ms(1)

            except Exception as e:
                if self._running:
                    print(f"[音频推流] 采集异常: {e}")
                    time.sleep_ms(100)

        # 清理录制器
        if self._recorder:
            try:
                self._recorder.finish()
            except Exception:
                pass
            self._recorder = None

        print("[音频推流] 音频采集线程已退出")

    def _drain_audio_buffer(self, target_frames, max_reads=8):
        """
        丢弃旧音频，直到缓冲接近目标帧数。
        """
        if not self._recorder:
            return

        dropped = 0
        for _ in range(max_reads):
            try:
                remaining = self._recorder.get_remaining_frames()
                if remaining <= target_frames or remaining < self._need_frames:
                    break
                self._recorder.record(self._chunk_ms)
                dropped += 1
            except Exception:
                break

        if dropped > 0:
            self._dropped_chunks += dropped

    def _calc_pcm_peak(self, data):
        """
        计算 PCM_S16LE 数据的峰值，用于判断麦克风是否采到有效声音。
        """
        peak = 0
        limit = min(len(data) - 1, 512)
        for i in range(0, limit, 2):
            sample = data[i] | (data[i + 1] << 8)
            if sample >= 32768:
                sample -= 65536
            if sample < 0:
                sample = -sample
            if sample > peak:
                peak = sample
        return peak

    def _broadcast(self, data):
        """
        向所有连接的客户端广播音频数据

        参数：
            data: PCM 音频字节串
        """
        with self._lock:
            clients = list(self._clients)

        if not clients or not self._event_loop or not self._event_loop.is_running():
            return

        # 异步发送到所有客户端；允许少量在途包，避免网络轻微抖动造成音频打洞。
        for ws in clients:
            try:
                with self._lock:
                    pending = self._client_pending.get(ws, 0)
                    if pending >= 3:
                        self._dropped_chunks += 1
                        continue
                    self._client_pending[ws] = pending + 1
                    self._client_busy[ws] = True

                future = asyncio.run_coroutine_threadsafe(
                    self._send_chunk(ws, data), self._event_loop
                )
                future.add_done_callback(
                    lambda fut, client=ws: self._on_send_done(client, fut)
                )
            except Exception:
                # 发送失败，移除客户端
                with self._lock:
                    self._clients.discard(ws)
                    self._client_busy.pop(ws, None)
                    self._client_pending.pop(ws, None)

    async def _send_chunk(self, ws, data):
        """
        发送单个音频块。
        """
        await ws.send(data)

    def _on_send_done(self, ws, future):
        """
        音频块发送结束后的状态清理。
        """
        remove_client = False
        try:
            future.result()
        except Exception as e:
            print(f"[音频推流] 发送失败，移除客户端: {e}")
            remove_client = True

        with self._lock:
            if ws not in self._clients:
                self._client_busy.pop(ws, None)
                self._client_pending.pop(ws, None)
                return

            pending = max(0, self._client_pending.get(ws, 1) - 1)
            self._client_pending[ws] = pending
            self._client_busy[ws] = pending > 0
            if remove_client:
                self._clients.discard(ws)
                self._client_busy.pop(ws, None)
                self._client_pending.pop(ws, None)

    def is_running(self):
        """
        检查是否正在运行

        返回：
            True: 正在运行
            False: 已停止
        """
        return self._running

    def get_url(self):
        """
        获取 WebSocket 地址

        返回：
            WebSocket URL 字符串
        """
        from maix import network
        try:
            w = network.wifi.Wifi()
            ip = w.get_ip()
            if ip and ip != "0.0.0.0":
                return f"ws://{ip}:{self._port}"
        except Exception:
            pass
        return f"ws://0.0.0.0:{self._port}"

    def get_client_count(self):
        """
        获取当前连接的客户端数量

        返回：
            客户端数量
        """
        with self._lock:
            return len(self._clients)

    def destroy(self):
        """
        销毁音频推流器，释放所有资源
        """
        self.stop()
        print("[音频推流] 音频推流器已销毁")



















