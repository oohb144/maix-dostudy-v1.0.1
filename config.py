"""
MaixCAM2 人脸识别智能系统 - 配置文件

功能：
- 定义硬件引脚配置
- 定义模型路径
- 定义系统参数
"""

from enum import IntEnum

# ==================== 硬件引脚配置 ====================
# 板载 LED 引脚（MaixCAM2）
LED_PIN = "A6"
LED_GPIO = "GPIOA6"

# ==================== 摄像头配置 ====================
# 降低分辨率以提高帧率（从 640x480 降到 320x240）
CAMERA_WIDTH = 320
CAMERA_HEIGHT = 240

# ==================== 模型路径配置 ====================
# 人脸检测模型（YOLOv8-face，官方推荐）
FACE_DETECT_MODEL = "/root/models/yolov8n_face.mud"

# 人脸特征提取模型（InsightFace ResNet50）
FACE_FEATURE_MODEL = "/root/models/insghtface_webface_r50.mud"

# 备选特征提取模型（如果上面的不存在）
FACE_FEATURE_MODEL_ALT = "/root/models/face_feature.mud"

# 人脸关键点模型（用于 478 关键点检测）
FACE_LANDMARKS_MODEL = "/root/models/face_landmarks.mud"

# ==================== 人脸识别配置 ====================
# 人脸检测置信度阈值（越大越严格，推荐 0.3-0.5）
# 降低阈值以提高检测率（可能会增加误检）
FACE_CONF_THRESHOLD = 0.25

# 人脸检测 IoU 阈值（过滤重叠框，推荐 0.3-0.5）
FACE_IOU_THRESHOLD = 0.4

# 人脸识别阈值（越大越严格，推荐 0.6-0.85）
# 降低阈值以提高识别率（可能会增加误识别）
FACE_RECOGNIZE_THRESHOLD = 0.72

# 人脸识别超时时间（毫秒）- 无人脸时停止识别并返回空闲
RECOGNIZE_TIMEOUT = 8000

# 录入结果显示时间（毫秒）
ENROLL_SHOW_TIME = 2000

# ==================== 录制配置 ====================
# 视频录制帧率
RECORD_VIDEO_FPS = 20

# 音频录制采样率
RECORD_AUDIO_SAMPLE_RATE = 16000

# 音频录制声道数
RECORD_AUDIO_CHANNEL = 1

# ==================== 文件路径配置 ====================
# 人脸数据库文件路径（.bin 格式）
FACES_DB_PATH = "/root/face_recognition_system/data/faces.bin"

# 人脸数据存储目录（备用）
FACE_DATA_DIR = "/root/face_recognition_system/data/faces"

# 录制文件存储目录
RECORD_DIR = "/root/face_recognition_system/data/recordings"

# ==================== 按键配置 ====================
# 长按阈值（毫秒）
LONG_PRESS_MS = 1500

# ==================== LED 闪烁配置 ====================
# 快闪间隔（毫秒）- 用于识别中
LED_BLINK_FAST = 200

# 慢闪间隔（毫秒）- 用于录制中
LED_BLINK_SLOW = 500

# 超慢闪间隔（毫秒）- 用于空闲状态
LED_BLINK_IDLE = 1000

# ==================== 音频配置 ====================
# 报警频率（Hz）- 未录入人脸
ALARM_FREQ = 2700

# 报警持续时间（毫秒）
ALARM_DURATION = 300

# 成功提示音频率（Hz）- 已录入人脸
SUCCESS_FREQ = 1500

# 成功提示音持续时间（毫秒）
SUCCESS_DURATION = 200

# 状态切换提示音频率（Hz）
TRANSITION_FREQ = 2000

# 状态切换提示音持续时间（毫秒）
TRANSITION_DURATION = 150

# ==================== 显示配置 ====================
# 文字颜色
TEXT_COLOR_WHITE = (255, 255, 255)
TEXT_COLOR_GREEN = (0, 255, 0)
TEXT_COLOR_RED = (255, 0, 0)
TEXT_COLOR_YELLOW = (255, 255, 0)
TEXT_COLOR_BLUE = (0, 128, 255)

# 文字大小
TEXT_SCALE = 1.2

# 状态提示文字位置
STATUS_TEXT_X = 10
STATUS_TEXT_Y = 10

# 人脸框颜色
FACE_BOX_COLOR_KNOWN = (0, 255, 0)    # 绿色 - 已知人脸
FACE_BOX_COLOR_UNKNOWN = (255, 0, 0)  # 红色 - 未知人脸

# 人脸框线宽
FACE_BOX_THICKNESS = 2

# ==================== 功能开关 ====================
# 是否启用音频提示
AUDIO_ENABLE = False

# 是否启用 LED 指示灯
LED_ENABLE = False

# 是否启用语音识别（需要语音模型文件）
VOICE_ENABLE = False

# 是否启用串口通信（接收外部语音开发板命令）
SERIAL_ENABLE = True

# ==================== 推流配置 ====================
# 是否启用 HTTP 推流（支持推流带标注的画面）
STREAM_ENABLE = True

# 推流分辨率（宽度）- 使用与摄像头相同的分辨率
STREAM_WIDTH = 320

# 推流分辨率（高度）- 使用与摄像头相同的分辨率
STREAM_HEIGHT = 240

# ==================== RTSP推流配置 ====================
# 是否启用 RTSP 推流（原始画面，用于监控）
RTSP_ENABLE = False

# RTSP 推流分辨率（宽度）- 降低分辨率以提高帧率
RTSP_WIDTH = 320

# RTSP 推流分辨率（高度）- 降低分辨率以提高帧率
RTSP_HEIGHT = 240

# RTSP 是否启用音频推流
RTSP_AUDIO_ENABLE = True

# ==================== 语音识别配置 ====================
# 语音模型路径
VOICE_MODEL_PATH = "/root/models/am_3332_192_int8.mud"

# 语音识别低占用模式：
# 注意：当前人脸检测 + 特征模型常驻后，MaixCAM2 剩余内存不足以再常驻 nn.Speech。
# 因此默认关闭本机语音模型，保留串口语音命令以保证帧率和稳定性。
# 如需单独测试本机语音模型，可临时打开 VOICE_ENABLE，并关闭人脸/推流等重负载功能。
VOICE_PAUSE_WHEN_ACTIVE = True
VOICE_RUN_INTERVAL_MS = 80
VOICE_PAUSE_SLEEP_MS = 150
VOICE_KWS_GATE = 0.25

# 音频文件目录
AUDIO_DIR = "/root/audio/"

# 关键词配置（拼音声调格式 -> 命令名）
VOICE_KEYWORDS = {
    # 界面切换命令
    'zhu3 jie4 mian4': 'home',           # 主界面
    'she4 zhi4': 'settings',              # 设置
    'lu4 ru4': 'enroll',                   # 录入
    'lu4 xiang4': 'recordings',            # 录像

    # 功能控制命令
    'shi2 bie2': 'recognize',              # 识别
    'ting2 zhi3': 'stop',                  # 停止
    'kai1 shi3': 'start',                  # 开始

    # 信息查询命令
    'du2 qu3 xin4 xi1': 'read_info',       # 读取信息
    'xian4 shi4 xin4 xi1': 'show_info',    # 显示信息

    # 音频播放命令
    'bo1 fang4 yin1 pin3': 'play_audio',   # 播放音频
    'ting2 zhi3 bo1 fang4': 'stop_audio',  # 停止播放
}

# ==================== 串口通信配置 ====================
# 串口设备路径
SERIAL_PORT = "/dev/ttyS4"

# 串口波特率
SERIAL_BAUDRATE = 115200

# 串口引脚配置
SERIAL_TX_PIN = "A21"
SERIAL_RX_PIN = "A22"

# ==================== 状态定义 ====================
class State(IntEnum):
    """系统状态枚举"""
    IDLE = 0           # 空闲状态
    RECOGNIZING = 1    # 人脸识别状态
    ENROLLING = 2      # 人脸录入状态
    RECORDING = 3      # 录制状态（与识别同时进行）
    MANUAL_RECORDING = 4  # 手动纯录制状态
    ERROR = 5          # 错误状态

# 状态名称映射（用于显示）
STATE_NAMES = {
    State.IDLE: "空闲",
    State.RECOGNIZING: "识别中",
    State.ENROLLING: "录入中",
    State.RECORDING: "录制中",
    State.MANUAL_RECORDING: "纯录制",
    State.ERROR: "错误"
}

# ==================== 状态服务器配置 ====================
# 状态服务器端口（人脸检测元数据 HTTP 端点）
# 用于向网页端推送人脸检测状态（与 JpegStreamer 的 8000 端口分开）
STATUS_SERVER_PORT = 8001

# 自动录制配置
# 人脸消失后延迟停止录制的毫秒数（避免短暂遮挡误停）
AUTO_STOP_DELAY_MS = 3000

# ==================== 性能优化参数 ====================
# 推流帧跳：每 N 帧推流一次（1=每帧推, 2=隔帧推, 3=每3帧推）
# 推流是 JPEG 编码+网络传输，非常耗时，隔帧推可以大幅提高帧率
STREAM_SKIP_FRAMES = 1

# 状态服务器推送帧跳：每 N 帧推送一次状态
# HTTP 状态轮询本身有去抖，不需要每帧都推送
STATUS_SKIP_FRAMES = 5

# 人脸检测阈值缩放因子（快速检测模式降低阈值以提高检测率）
DETECT_FAST_THRESHOLD_SCALE = 0.8

# 成功提示音冷却时间（毫秒）
SUCCESS_COOLDOWN_MS = 3000

# 陌生人报警冷却时间（毫秒）
ALARM_COOLDOWN_MS = 1000

# 主循环休眠时间（毫秒）
# 空闲状态可以休眠更长时间以节省资源
IDLE_SLEEP_MS = 5
ACTIVE_SLEEP_MS = 1

# 推流 JPEG 质量（降低质量可加快编码速度）
STREAM_JPEG_QUALITY = 45

# ==================== 音频推流配置 ====================
# 是否启用 WebSocket 音频推流（网页端实时听设备麦克风）
AUDIO_STREAM_ENABLE = False
# WebSocket 音频推流端口
AUDIO_STREAM_PORT = 8002
# 音频采样率（Hz）
AUDIO_STREAM_SAMPLE_RATE = 16000

# 更激进的识别降频配置：优先保证画面帧率。
RECOGNIZE_DETECT_INTERVAL_MS = 800
RECORD_RECOGNIZE_INTERVAL_MS = 1000
# 音频声道数（1=单声道）
AUDIO_STREAM_CHANNEL = 1
# 每次采集时长（毫秒）
AUDIO_STREAM_CHUNK_MS = 300


# ==================== 有效运行参数覆盖区 ====================
# 上方部分中文注释在当前文件编码下会和变量粘连，导致变量被注释吞掉。
# 这里集中重新定义主程序会导入的运行参数，保证上板后导入稳定。
DETECT_FAST_THRESHOLD_SCALE = 0.8
RECOGNIZE_DETECT_INTERVAL_MS = 800
RECORD_RECOGNIZE_INTERVAL_MS = 1000
SUCCESS_COOLDOWN_MS = 3000
ALARM_COOLDOWN_MS = 1000
STREAM_JPEG_QUALITY = 45
AUDIO_STREAM_ENABLE = False
AUDIO_STREAM_SAMPLE_RATE = 16000
