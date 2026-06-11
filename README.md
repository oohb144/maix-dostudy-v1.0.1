# 🤖 MaixCAM2 人脸识别智能系统

[![版本](https://img.shields.io/badge/版本-2.0.0-blue.svg)](https://github.com/your-username/maix-dostudy/releases)
[![平台](https://img.shields.io/badge/平台-MaixCAM2-green.svg)](https://wiki.sipeed.com/maixcam2)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 基于 MaixCAM2 的人脸识别智能系统，支持人脸识别、视频录制、实时推流、语音交互等功能，分辨率升级至 **640×480** 高清模式。

## 📋 功能特性

### 🎯 核心功能

| 功能 | 描述 |
|------|------|
| **人脸识别** | YOLOv8-face + InsightFace 双模型，实时检测和识别已录入人脸 |
| **视频录制** | 自动录制 MP4 视频 + WAV 音频，支持音视频融合播放 |
| **人脸录入** | 触摸屏操作，一键录入人脸，支持批量管理 |
| **UI 界面** | 5 页触摸屏 UI（主页/设置/录入/录像/融合播放） |
| **实时推流** | HTTP + RTSP 推流，支持网页端监控 |
| **状态同步** | WebSocket 实时推送人脸检测状态到网页端 |
| **语音控制** | 支持本地语音识别和串口语音命令 |
| **高清显示** | 分辨率升级至 640×480，画面更清晰 |

### 📊 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    MaixCAM2 人脸识别系统                      │
├─────────────────────────────────────────────────────────────┤
│  UI 层      │  UIManager + Pages（主页/设置/录入/录像/融合）    │
│  业务层     │  StateMachine + FaceDetector + Recorder         │
│  硬件层     │  Camera + Display + Audio + GPIO + UART         │
│  网络层     │  HTTP Streamer + RTSP + WebSocket + StatusServer │
│  AI 层      │  YOLOv8-face + InsightFace Feature Extractor    │
└─────────────────────────────────────────────────────────────┘
```

### 🖥️ UI 界面

**主页 (640×480)**
- 实时摄像头画面 + 人脸标注框
- 顶部状态栏：系统状态、已录入人数
- 底部功能按钮：识别 / 录入 / 设置 / 录制 / 融合

**设置页**
- 检测阈值滑块（可调灵敏度）
- 识别阈值滑块
- HTTP 推流开关
- RTSP 推流开关
- 音频提示开关
- LED 指示灯开关

**录入页**
- 实时人脸检测显示
- 已录入人脸列表
- 操作按钮：录入 / 删除 / 清空

**录像页**
- 录像文件列表（显示大小、音视频状态）
- 操作按钮：刷新 / 删除 / 清空

**融合播放页**
- 读取原始录像
- 一键融合音视频
- 选择播放已融合视频
- 支持翻页浏览

## 🚀 快速开始

### 📦 安装步骤

#### 1️⃣ 上传项目到 MaixCAM2

```bash
# 使用 SCP 上传（替换 <maixcam_ip> 为实际 IP 地址）
scp -r ./* root@<maixcam_ip>:/root/face_recognition_system/

# 或使用 MaixCDT 工具上传
```

#### 2️⃣ 准备模型文件

在 MaixCAM2 的 `/root/models/` 目录下放置以下模型：

| 模型文件 | 用途 | 下载地址 |
|---------|------|---------|
| `yolov8n_face.mud` | 人脸检测（YOLOv8） | [MaixHub](https://maixhub.com/model/zoo/407) |
| `insghtface_webface_r50.mud` | 人脸特征提取（InsightFace ResNet50） | [MaixHub](https://maixhub.com/model/zoo/462) |
| `face_feature.mud` | 备选特征提取模型（可选） | - |
| `am_3332_192_int8.mud` | 语音识别模型（可选） | - |

#### 3️⃣ 创建必要目录

```bash
# SSH 登录 MaixCAM2
ssh root@<maixcam_ip>

# 创建目录结构
mkdir -p /root/face_recognition_system/data/faces
mkdir -p /root/face_recognition_system/data/recordings
mkdir -p /root/models
mkdir -p /root/audio
```

#### 4️⃣ 运行程序

```bash
cd /root/face_recognition_system
python main.py
```

### 🎮 操作指南

#### 触摸屏操作（推荐）

| 操作 | 功能 |
|------|------|
| 点击 **识别** | 进入人脸识别模式，检测到人脸后自动录制 |
| 点击 **录入** | 进入人脸录入页面，点击录入按钮录入人脸 |
| 点击 **设置** | 打开设置页面，调节参数 |
| 点击 **录制** | 进入纯录制模式（不进行人脸识别） |
| 点击 **融合** | 进入融合播放页面，合并音视频 |
| 点击 **返回** | 返回主页 |

#### 物理按键操作

| 操作 | 功能 | 状态转换 |
|------|------|---------|
| **短按 OK 键** | 开始/停止人脸识别 | 空闲 ⇄ 识别 |
| **长按 OK 键**（1.5秒） | 进入人脸录入模式 | 空闲 → 录入 |
| **超长按 OK 键**（3秒） | 退出程序 | 任意 → 退出 |

#### 语音控制（需启用）

| 语音命令 | 功能 |
|---------|------|
| "主界面" | 返回主页 |
| "设置" | 打开设置页 |
| "录入" | 进入录入页 |
| "录像" | 查看录像列表 |
| "识别" / "开始" | 开始人脸识别 |
| "停止" | 停止当前操作 |
| "读取信息" | 读取系统状态 |

#### 串口命令（需外部语音板）

| 命令 ID | 功能 |
|---------|------|
| `0x01` | 切换到主页 |
| `0x02` | 切换到设置页 |
| `0x03` | 切换到录入页 |
| `0x04` | 开始录入 |
| `0x05` | 开始识别/录制 |
| `0x06` | 停止识别/录制 |
| `0x07` | 关闭推流 |
| `0x08` | 打开推流 |

## ⚙️ 配置说明

### 配置文件：`config.py`

#### 硬件配置

```python
# 摄像头分辨率
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# LED 引脚
LED_PIN = "A6"
LED_GPIO = "GPIOA6"

# 串口配置
SERIAL_PORT = "/dev/ttyS4"
SERIAL_BAUDRATE = 115200
SERIAL_TX_PIN = "A21"
SERIAL_RX_PIN = "A22"
```

#### 人脸识别配置

```python
# 模型路径
FACE_DETECT_MODEL = "/root/models/yolov8n_face.mud"
FACE_FEATURE_MODEL = "/root/models/insghtface_webface_r50.mud"

# 检测阈值（越大越严格，推荐 0.2-0.5）
FACE_CONF_THRESHOLD = 0.25

# IoU 阈值（过滤重叠框）
FACE_IOU_THRESHOLD = 0.4

# 识别阈值（越大越严格，推荐 0.6-0.85）
FACE_RECOGNIZE_THRESHOLD = 0.72
```

#### 录制配置

```python
RECORD_VIDEO_FPS = 30
RECORD_AUDIO_SAMPLE_RATE = 16000
RECORD_AUDIO_CHANNEL = 1
```

#### 推流配置

```python
# HTTP 推流
STREAM_ENABLE = True
STREAM_WIDTH = 640
STREAM_HEIGHT = 480

# RTSP 推流
RTSP_ENABLE = False
RTSP_WIDTH = 640
RTSP_HEIGHT = 480
RTSP_AUDIO_ENABLE = True

# 音频推流（WebSocket）
AUDIO_STREAM_ENABLE = False
AUDIO_STREAM_PORT = 8002
```

#### 功能开关

```python
AUDIO_ENABLE = False      # 音频提示音
LED_ENABLE = False        # LED 指示灯
VOICE_ENABLE = False      # 本地语音识别（内存不足时建议关闭）
SERIAL_ENABLE = True      # 串口语音命令
```

## 📂 文件结构

```
maix-dostudy-v2.0.0/
├── main.py                    # 主程序入口
├── main_k.py                  # 备用主程序
├── config.py                  # 配置文件
├── app.yaml                   # 应用配置（MaixCDT 打包用）
├── app.png                    # 应用图标
│
├── UI 模块
│   ├── ui.py                  # UI 框架（Button/Slider/Switch/Page）
│   └── ui_pages.py            # UI 页面定义（主页/设置/录入/录像/融合）
│
├── 核心业务模块
│   ├── state_machine.py       # 状态机模块
│   ├── face_detector.py       # 人脸识别模块
│   ├── recorder_manager.py    # 视频录制管理
│   ├── video_player_manager.py # 视频播放和音视频融合
│   └── key_manager.py         # 按键管理
│
├── 硬件控制模块
│   ├── led_controller.py      # LED 控制器
│   ├── audio_controller.py    # 音频控制器（提示音 + 音频播放）
│   └── voice_recognition.py   # 语音识别模块
│
├── 网络模块
│   ├── stream_manager.py      # HTTP + RTSP 推流管理
│   ├── audio_streamer.py      # WebSocket 音频推流
│   ├── status_server.py       # 状态服务器（HTTP JSON API）
│   └── serial_comm.py         # 串口通信模块
│
├── 文档
│   ├── README.md              # 项目说明（本文件）
│   └── OPTIMIZATION_README.md # 性能优化说明
│
└── dist/                      # 打包输出目录
    ├── maix-dostudy640-v2.0.0.zip
    ├── maix-dostudy2-v1.3.0.zip
    ├── maix-dostudy2-v1.2.0.zip
    └── maix-dostudy2-v1.0.3.zip
```

## 🔧 高级配置

### 推流服务地址

| 服务 | 端口 | 地址格式 |
|------|------|---------|
| HTTP 推流 | 8000 | `http://<ip>:8000` |
| 状态服务器 | 8001 | `http://<ip>:8001/status` |
| RTSP 推流 | 554 | `rtsp://<ip>:554/live` |
| 音频推流 | 8002 | `ws://<ip>:8002` |

### 网页端接入

**获取实时状态**
```javascript
// 轮询状态
fetch('http://<maixcam_ip>:8001/status')
  .then(res => res.json())
  .then(data => {
    console.log('系统状态:', data.state);
    console.log('人脸数:', data.face_count);
    console.log('已知人脸:', data.known_face_count);
    console.log('未知人脸:', data.unknown_face_count);
  });

// 获取实时视频流
const img = document.getElementById('video');
img.src = 'http://<maixcam_ip>:8000';
```

**状态数据结构**
```json
{
  "state": "识别中",
  "has_face": true,
  "face_count": 2,
  "known_face_count": 1,
  "unknown_face_count": 1,
  "face_labels": ["张三", "未知"],
  "recording": true,
  "record_duration": 5
}
```

### 性能优化参数

```python
# 帧率优化
IDLE_SLEEP_MS = 5           # 空闲状态休眠时间
ACTIVE_SLEEP_MS = 1         # 活跃状态休眠时间
STREAM_SKIP_FRAMES = 1      # 推流帧跳（1=每帧，2=隔帧）
STATUS_SKIP_FRAMES = 5      # 状态推送帧跳

# 识别优化
RECOGNIZE_DETECT_INTERVAL_MS = 800   # 识别模式检测间隔
RECORD_RECOGNIZE_INTERVAL_MS = 1000  # 录制模式识别间隔

# 推流质量
STREAM_JPEG_QUALITY = 45    # JPEG 压缩质量（0-100）
```

## 🐛 故障排除

### Q1: 程序无法启动？

**可能原因：**
1. 模型文件缺失
2. 摄像头初始化失败
3. 磁盘空间不足

**解决方法：**
```bash
# 检查模型文件
ls /root/models/*.mud

# 检查磁盘空间
df -h

# 查看启动日志
python main.py 2>&1 | tee startup.log
```

### Q2: 人脸识别不准确？

**调整方法：**
1. 在设置页面调节 **检测阈值**（降低以提高检测率）
2. 调节 **识别阈值**（降低以提高识别率）
3. 重新录入人脸（确保光线充足，正对摄像头）

**参数调整：**
```python
# 降低检测阈值（更敏感，但可能误检）
FACE_CONF_THRESHOLD = 0.2  # 默认 0.25

# 降低识别阈值（更容易识别，但可能误认）
FACE_RECOGNIZE_THRESHOLD = 0.65  # 默认 0.72
```

### Q3: 帧率太低怎么办？

**优化建议：**
1. 关闭不必要的推流（HTTP/RTSP）
2. 增加推流帧跳
3. 降低推流质量
4. 关闭音频推流

```python
# 优化配置
STREAM_SKIP_FRAMES = 2           # 隔帧推流
STREAM_JPEG_QUALITY = 30         # 降低质量
AUDIO_STREAM_ENABLE = False      # 关闭音频推流
RTSP_ENABLE = False              # 关闭 RTSP
```

### Q4: 内存不足？

**解决方法：**
```python
# 关闭语音识别（占用大量内存）
VOICE_ENABLE = False

# 关闭不必要的推流
RTSP_ENABLE = False
AUDIO_STREAM_ENABLE = False
```

### Q5: 录像文件在哪里？

**文件位置：**
```
/root/face_recognition_system/data/recordings/
├── 20240611_123456.mp4      # 视频文件
├── 20240611_123456.wav      # 音频文件
└── 20240611_123456_av.mp4   # 融合后的文件
```

### Q6: 如何删除人脸数据？

**方法一：UI 操作**
1. 进入录入页
2. 点击"清空"按钮

**方法二：手动删除**
```bash
rm /root/face_recognition_system/data/faces.bin
```

### Q7: 如何远程调试？

```bash
# SSH 登录
ssh root@<maixcam_ip>

# 查看实时日志
tail -f /tmp/maixcam.log

# 查看进程状态
ps aux | grep python
```

## 📊 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| AI 模型 | YOLOv8-face | 人脸检测 |
| AI 模型 | InsightFace ResNet50 | 人脸特征提取 |
| 图像处理 | MaixPy Image API | 图像绘制和格式转换 |
| 视频录制 | MaixPy Video Encoder | MP4 编码 |
| 音频录制 | MaixPy Audio Recorder | WAV 录制 |
| 推流服务 | JpegStreamer + RTSP | HTTP/RTSP 推流 |
| UI 框架 | 自研 UI 系统 | Button/Slider/Switch/Page |
| 状态机 | 自研轻量状态机 | 无外部依赖 |
| 通信协议 | UART + WebSocket | 串口和网络通信 |

## 🎯 性能指标

| 指标 | 值 | 说明 |
|------|-----|------|
| 分辨率 | 640×480 | v2.0.0 升级 |
| 空闲帧率 | ~25 FPS | 无 AI 负载 |
| 识别帧率 | ~15 FPS | 含人脸检测+识别 |
| 录制帧率 | ~20 FPS | 含视频编码 |
| 推流帧率 | ~15 FPS | JPEG 编码+网络传输 |
| 检测延迟 | ~30ms | YOLOv8-face 单次推理 |
| 识别延迟 | ~50ms | InsightFace 特征提取 |

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m 'Add some feature'`
4. 推送到分支：`git push origin feature/your-feature`
5. 提交 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [Sipeed](https://wiki.sipeed.com/) - MaixCAM2 硬件支持
- [MaixPy](https://github.com/sipeed/MaixPy) - MaixPy 开发框架
- [MaixHub](https://maixhub.com/) - AI 模型资源
- [YOLOv8](https://github.com/ultralytics/ultralytics) - 目标检测框架
- [InsightFace](https://github.com/deepinsight/insightface) - 人脸识别框架

## 📞 联系方式

- **作者**: oohb144
- **邮箱**: your-email@example.com
- **GitHub**: [github.com/your-username](https://github.com/your-username)

## 📝 更新日志

### v2.0.0 (2024-06-11) 🎉

**重大更新：**
- ⬆️ **分辨率升级** - 从 320×240 升级至 640×480 高清模式
- 🎨 **全新 UI 系统** - 5 页触摸屏 UI，支持滑动、翻页
- 🎬 **融合播放功能** - 音视频自动融合，一键播放
- 🔊 **音频推流** - WebSocket 实时音频推流到网页端
- 📡 **状态同步** - HTTP 实时推送人脸检测元数据

**新功能：**
- 融合播放页面（读取/融合/播放/删除）
- 录像管理页面（列表/删除/清空）
- 设置页面（阈值调节/功能开关）
- 串口语音命令支持
- HTTP 状态服务器（端口 8001）

**优化：**
- 高帧率模式：轻量检测+间隔重识别
- 推流帧跳优化，音频开启时自动降频
- 阈值变化实时生效，无需重启
- 内存优化，关闭语音识别释放资源

**修复：**
- 修复音频推流导致帧率下降的问题
- 修复 RTSP 推流与 Display 冲突
- 修复阈值参数编码问题
- 修复录像文件列表排序问题

---

### v1.3.0 (2024-06-11)

- 新增 HTTP 状态推送服务器
- 新增音频推流功能
- 优化识别帧节流策略
- 修复推流质量调节问题

---

### v1.2.0 (2024-06-11)

- 新增 RTSP 推流支持
- 新增网页端状态同步
- 优化推流帧率和质量
- 修复音频录制与推流冲突

---

### v1.0.3 (2024-06-07)

- 初始发布版本
- 实现基本人脸识别功能
- 实现视频录制功能
- 实现人脸录入管理

---

**Made with ❤️ for MaixCAM2**

![MaixCAM2](https://img.shields.io/badge/MaixCAM2-Embedded_AI-blueviolet?style=for-the-badge&logo=hardware)
