# -*- coding: utf-8 -*-
"""
MaixCAM2 人脸识别智能系统 - 串口通信模块

功能：
- 接收外部语音开发板的命令
- 发送人脸识别结果（熟人/陌生人）
- 二进制协议通信

协议格式：
┌────────┬────────┬────────┬────────┬────────┬────────┐
│ 帧头   │ 命令ID │ 数据长度│ 数据   │ 校验和 │ 帧尾   │
│ 2字节  │ 1字节  │ 1字节  │ N字节  │ 1字节  │ 2字节  │
│ AA 55  │   XX   │   XX   │  ...   │   XX   │ 55 AA  │
└────────┴────────┴────────┴────────┴────────┴────────┘

接收命令（语音开发板 -> MaixCAM）：
- 0x01: 切换主页
- 0x02: 切换设置
- 0x03: 切换录入界面
- 0x04: 开始录入
- 0x05: 开始识别/录制
- 0x06: 停止识别/录制
- 0x07: 关闭推流
- 0x08: 打开推流

发送命令（MaixCAM -> 语音开发板）：
- 0x00: 熟人
- 0x09: 陌生人
"""

from maix import uart, pinmap, err, time
import _thread


# ==================== 协议常量 ====================
FRAME_HEAD = b'\xAA\x55'
FRAME_TAIL = b'\x55\xAA'

# 接收缓冲区最大大小（防止噪声数据导致缓冲区无限增长）
MAX_BUFFER_SIZE = 1024

# 接收命令定义
class RecvCmd:
    GO_HOME = 0x01          # 切换主页
    GO_SETTINGS = 0x02      # 切换设置
    GO_ENROLL_PAGE = 0x03   # 切换录入界面
    START_ENROLL = 0x05     # 开始录入
    START_RECOGNIZE = 0x04  # 开始识别/录制
    STOP_RECOGNIZE = 0x06   # 停止识别/录制
    CLOSE_STREAM = 0x07     # 关闭推流
    OPEN_STREAM = 0x08      # 打开推流

# 发送命令定义
class SendCmd:
    KNOWN_FACE = 0x00       # 熟人
    UNKNOWN_FACE = 0x09     # 陌生人

# 命令名称映射
RECV_CMD_NAMES = {
    RecvCmd.GO_HOME: "切换主页",
    RecvCmd.GO_SETTINGS: "切换设置",
    RecvCmd.GO_ENROLL_PAGE: "切换录入界面",
    RecvCmd.START_ENROLL: "开始录入",
    RecvCmd.START_RECOGNIZE: "开始识别/录制",
    RecvCmd.STOP_RECOGNIZE: "停止识别/录制",
    RecvCmd.CLOSE_STREAM: "关闭推流",
    RecvCmd.OPEN_STREAM: "打开推流",
}


class SerialComm:
    """
    串口通信管理器
    """

    def __init__(self, port="/dev/ttyS4", baudrate=115200, tx_pin="A21", rx_pin="A22"):
        """
        初始化串口通信管理器

        参数：
            port: 串口设备路径
            baudrate: 波特率
            tx_pin: 发送引脚
            rx_pin: 接收引脚
        """
        self._port = port
        self._baudrate = baudrate
        self._tx_pin = tx_pin
        self._rx_pin = rx_pin

        self._serial = None
        self._is_running = False
        self._callback = None

        # 接收缓冲区
        self._buffer = bytearray()

        print(f"[串口] 串口通信模块初始化完成 (端口: {port}, 波特率: {baudrate})")

    def _init_serial(self):
        """初始化串口"""
        try:
            err.check_raise(pinmap.set_pin_function(self._tx_pin, "UART4_TX"), "set pin failed")
            err.check_raise(pinmap.set_pin_function(self._rx_pin, "UART4_RX"), "set pin failed")
            self._serial = uart.UART(self._port, self._baudrate)
            print(f"[串口] 串口初始化成功 ({self._port})")
            return True
        except Exception as e:
            print(f"[串口] 串口初始化失败: {e}")
            return False

    def set_callback(self, callback):
        """设置命令回调函数"""
        self._callback = callback

    def start(self, callback=None):
        """启动串口通信"""
        if self._is_running:
            print("[串口] 串口通信已在运行")
            return True

        if callback:
            self.set_callback(callback)

        if not self._init_serial():
            return False

        try:
            self._is_running = True
            _thread.start_new_thread(self._receive_thread, ())
            print("[串口] 串口通信已启动")
            print("[串口] 等待外部语音开发板发送命令...")
            return True
        except Exception as e:
            print(f"[串口] 启动串口通信失败: {e}")
            self._is_running = False
            return False

    def _calculate_checksum(self, cmd_id, data_length, data):
        """计算校验和"""
        checksum = cmd_id ^ data_length
        for byte in data:
            checksum ^= byte
        return checksum & 0xFF

    def _parse_packet(self, packet):
        """解析数据包"""
        if len(packet) < 3:
            return None

        cmd_id = packet[0]
        data_length = packet[1]

        if len(packet) < 3 + data_length:
            return None

        data = packet[2:2+data_length]
        checksum = packet[2+data_length]

        expected_checksum = self._calculate_checksum(cmd_id, data_length, data)
        if checksum != expected_checksum:
            print(f"[串口] 校验和错误: 期望={expected_checksum:#04x}, 实际={checksum:#04x}")
            return None

        return (cmd_id, bytes(data))

    def _process_buffer(self):
        """处理接收缓冲区"""
        commands = []

        # 限制缓冲区大小，防止噪声数据导致无限增长
        if len(self._buffer) > MAX_BUFFER_SIZE:
            self._buffer = self._buffer[-(MAX_BUFFER_SIZE // 2):]

        while True:
            head_pos = self._buffer.find(FRAME_HEAD)
            if head_pos == -1:
                if len(self._buffer) > 1:
                    self._buffer = self._buffer[-1:]
                break

            if head_pos > 0:
                self._buffer = self._buffer[head_pos:]

            tail_pos = self._buffer.find(FRAME_TAIL, len(FRAME_HEAD))
            if tail_pos == -1:
                break

            packet_data = self._buffer[len(FRAME_HEAD):tail_pos]
            result = self._parse_packet(packet_data)
            if result:
                commands.append(result)

            self._buffer = self._buffer[tail_pos + len(FRAME_TAIL):]

        return commands

    def _receive_thread(self):
        """接收线程"""
        print("[串口] 接收线程启动")

        while self._is_running:
            try:
                if self._serial:
                    data = self._serial.read()
                    if data:
                        self._buffer.extend(data)
                        commands = self._process_buffer()
                        for cmd_id, cmd_data in commands:
                            self._handle_command(cmd_id, cmd_data)
                else:
                    time.sleep_ms(10)
            except Exception as e:
                print(f"[串口] 接收异常: {e}")
                time.sleep_ms(100)

        print("[串口] 接收线程退出")

    def _handle_command(self, cmd_id, data):
        """处理接收到的命令"""
        cmd_name = RECV_CMD_NAMES.get(cmd_id, f"未知命令({cmd_id:#04x})")
        print(f"[串口] 收到命令: {cmd_name} (ID: {cmd_id:#04x})")

        if self._callback:
            try:
                self._callback(cmd_id, data)
            except Exception as e:
                print(f"[串口] 回调执行失败: {e}")

    def send_command(self, cmd_id, data=b''):
        """
        发送命令

        参数：
            cmd_id: 命令ID
            data: 数据

        返回：
            True: 发送成功
            False: 发送失败
        """
        if not self._serial:
            return False

        try:
            data_length = len(data)
            checksum = self._calculate_checksum(cmd_id, data_length, data)

            packet = bytearray()
            packet.extend(FRAME_HEAD)
            packet.append(cmd_id)
            packet.append(data_length)
            packet.extend(data)
            packet.append(checksum)
            packet.extend(FRAME_TAIL)

            self._serial.write(bytes(packet))
            return True
        except Exception as e:
            print(f"[串口] 发送失败: {e}")
            return False

    def send_known_face(self):
        """发送熟人通知"""
        print("[串口] 发送: 熟人")
        return self.send_command(SendCmd.KNOWN_FACE)

    def send_unknown_face(self):
        """发送陌生人通知"""
        print("[串口] 发送: 陌生人")
        return self.send_command(SendCmd.UNKNOWN_FACE)

    def stop(self):
        """停止串口通信"""
        self._is_running = False

    def is_running(self):
        """检查是否正在运行"""
        return self._is_running

    def destroy(self):
        """销毁串口通信管理器"""
        self.stop()
        self._serial = None
        print("[串口] 串口通信管理器已销毁")
