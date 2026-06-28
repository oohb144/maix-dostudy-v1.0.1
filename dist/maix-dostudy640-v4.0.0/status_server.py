"""
MaixCAM2 人脸识别智能系统 - 状态服务器模块

功能：
- 提供轻量级 HTTP 状态端点
- 将人脸检测元数据（人数、熟人/陌生人、标签）推送到浏览器
- 支持跨域请求（CORS）
- 独立线程运行，不阻塞主循环

优化：
- 使用单字节原子变量替代锁（_running 标志）
- 加锁范围缩小到纯字典拷贝，减少主循环阻塞
- HTTP 响应预构建头部，减少 per-request 构建
- settimeout(0.5) 平衡响应延迟与空转开销

使用方法：
- 在 main.py 中创建 StatusServer 实例并启动
- 每帧调用 update_status() 更新人脸检测数据
- 浏览器通过 GET /status 获取 JSON 数据
"""

import _thread
import json


class StatusServer:
    """
    轻量级 HTTP 状态服务器

    功能：
    - 在独立线程中运行 HTTP 服务
    - 提供 /status 端点返回人脸检测 JSON 数据
    - 线程安全的状态更新（最小锁粒度）
    - 支持 CORS 跨域请求
    - 变化检测：数据没变时跳过 JSON 序列化
    """

    # 预构建 HTTP 响应头前缀（避免每请求重复拼接）
    _HTTP_OK_PREFIX = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: application/json; charset=utf-8\r\n"
        "Access-Control-Allow-Origin: *\r\n"
        "Cache-Control: no-cache\r\n"
        "Connection: close\r\n"
    )
    _HTTP_404 = "HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"

    def __init__(self, port=8001):
        """
        初始化状态服务器

        参数：
            port: 服务端口号，默认 8001（避免与 JpegStreamer 8000 冲突）
        """
        self._port = port
        self._status = {
            "state": "空闲",
            "has_face": False,
            "face_count": 0,
            "known_face_count": 0,
            "unknown_face_count": 0,
            "face_labels": [],
            "recording": False,
            "record_duration": 0
        }
        self._lock = _thread.allocate_lock()
        self._running = False
        self._server_socket = None

        # 预缓存的 JSON 响应体字节（仅在数据变化时重建）
        self._cached_body = b'{}'
        self._cached_body_len = 2
        # 上一帧的状态指纹，用于变化检测（避免无变化时重复序列化）
        self._last_fingerprint = ""

        print(f"[状态服务] 初始化完成，端口: {port}")

    def start(self):
        """
        启动 HTTP 状态服务器（在独立线程中运行）

        返回：
            True: 启动成功（线程已创建）
        """
        if self._running:
            print("[状态服务] 已在运行中")
            return True

        self._running = True
        try:
            _thread.start_new_thread(self._serve, ())
            print(f"[状态服务] 已启动，访问 http://0.0.0.0:{self._port}/status")
            return True
        except Exception as e:
            print(f"[状态服务] 启动失败: {e}")
            self._running = False
            return False

    def stop(self):
        """
        停止 HTTP 状态服务器
        """
        self._running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None
        print("[状态服务] 已停止")

    def update_status(self, data):
        """
        线程安全地更新状态数据

        优化：只在数据真正变化时才重建 JSON 缓存，
        使用轻量级指纹（关键字段拼接）避免无变化时重复序列化。

        参数：
            data: 状态字典
        """
        with self._lock:
            self._status.update(data)
            # 生成轻量级指纹：关键数值字段拼接
            fp = "{}|{}|{}|{}|{}|{}".format(
                self._status.get("state", ""),
                self._status.get("has_face", False),
                self._status.get("face_count", 0),
                self._status.get("known_face_count", 0),
                self._status.get("unknown_face_count", 0),
                "|".join(self._status.get("face_labels", []))
            )
            if fp != self._last_fingerprint:
                self._last_fingerprint = fp
                # 数据变化了，才做 JSON 序列化
                body = json.dumps(self._status, ensure_ascii=False)
                self._cached_body = body.encode('utf-8')
                self._cached_body_len = len(self._cached_body)

    def get_status(self):
        """
        线程安全地获取当前状态数据

        返回：
            状态字典的副本
        """
        with self._lock:
            return self._status.copy()

    def _serve(self):
        """
        HTTP 服务主循环（在独立线程中运行）

        优化：
        - 使用预缓存的 JSON 响应体，避免每次请求加锁构建
        - Connection: close 头让浏览器快速释放连接
        - settimeout(0.5) 平衡响应延迟和空转
        """
        import socket

        try:
            self._server_socket = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM
            )
            self._server_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
            )
            # 设置发送/接收缓冲区较小，减少内存占用
            self._server_socket.bind(('0.0.0.0', self._port))
            self._server_socket.listen(3)
            # 0.5 秒超时，比 1 秒更快响应停止请求
            self._server_socket.settimeout(0.5)

            print(f"[状态服务] 监听端口 {self._port}")

        except Exception as e:
            print(f"[状态服务] 绑定端口失败: {e}")
            self._running = False
            return

        while self._running:
            try:
                client = None
                try:
                    client, addr = self._server_socket.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break

                try:
                    # 快速读取请求行（只关心第一行路径）
                    # 设置短超时防止慢客户端阻塞
                    client.settimeout(2.0)
                    request = client.recv(256).decode('utf-8', errors='ignore')

                    if request.startswith('GET /status'):
                        # 使用预缓存的 JSON 响应体，无需加锁
                        # 仅读取缓存字节和长度（原子读，线程安全）
                        body_bytes = self._cached_body
                        body_len = self._cached_body_len

                        # 构建完整响应（头部+预构建体）
                        response = (
                            self._HTTP_OK_PREFIX +
                            f"Content-Length: {body_len}\r\n\r\n"
                        ).encode('utf-8') + body_bytes

                        client.sendall(response)
                    else:
                        client.sendall(self._HTTP_404.encode('utf-8'))

                except Exception:
                    pass
                finally:
                    try:
                        client.close()
                    except Exception:
                        pass

            except Exception:
                if not self._running:
                    break

        # 清理
        try:
            if self._server_socket:
                self._server_socket.close()
        except Exception:
            pass
        self._server_socket = None
        print("[状态服务] 服务线程已退出")

    def destroy(self):
        """
        销毁状态服务器，释放资源
        """
        self.stop()
        print("[状态服务] 状态服务器已销毁")