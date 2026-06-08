# MaixCAM2 人脸识别智能系统

## 项目简介

基于 MaixCAM2 开发的人脸识别智能系统，支持人脸识别、视频录制、人脸录入等功能。

## 功能特性

### 1. 人脸识别
- 使用 YOLO11 模型检测人脸
- 使用 SelfLearnClassifier 进行人脸比对
- 已录入人脸：LED 常亮 + 成功提示音
- 未录入人脸：LED 快闪 + 报警音

### 2. 视频录制
- 人脸识别时自动录制视频（MP4 格式）
- 同步录制音频（WAV 格式）
- 文件自动命名（带时间戳）

### 3. 人脸录入
- 长按 OK 键进入录入模式
- 自动拍摄 5 张人脸照片
- 自动训练分类器
- 进度条显示

### 4. 状态提示
- LED 闪烁指示不同状态
- 音频提示音区分不同事件
- 屏幕显示状态信息

## 硬件要求

- MaixCAM2 开发板
- 板载 LED（GPIOA6）
- 板载 PA 功放 + 1W 喇叭
- 板载摄像头
- 板载模拟硅麦

## 文件结构

```
dostudy/
├── main.py                 # 主程序入口
├── config.py               # 配置文件
├── state_machine.py        # 状态机模块
├── key_manager.py          # 按键管理模块
├── led_controller.py       # LED 控制模块
├── audio_controller.py     # 音频控制模块
├── face_detector.py        # 人脸识别模块（使用官方 nn.FaceRecognizer）
├── recorder_manager.py     # 录制管理模块
├── README.md               # 项目说明
└── data/
    ├── faces.bin           # 人脸数据库（运行后自动生成）
    ├── faces/              # 人脸数据存储（备用）
    └── recordings/         # 录制文件存储
```

## 使用方法

### 1. 上传项目到 MaixCAM2

将整个 `dostudy` 文件夹上传到 MaixCAM2 的 `/root/face_recognition_system/` 目录：

```bash
# 使用 scp 或其他方式上传
scp -r dostudy/ root@<maixcam_ip>:/root/face_recognition_system/
```

### 2. 确保模型文件存在

在 MaixCAM2 的 `/root/models/` 目录下需要有以下模型文件：

**必需模型：**
- `yolov8n_face.mud` - 人脸检测模型（官方推荐）
- `insghtface_webface_r50.mud` - 人脸特征提取模型（InsightFace ResNet50）

**可选模型（如果上面的特征模型不存在，可以使用这个）：**
- `face_feature.mud` - 备选特征提取模型

**模型下载地址：**
- 人脸检测模型：https://maixhub.com/model/zoo/407
- 特征提取模型：https://maixhub.com/model/zoo/462

**模型文件说明：**
- 使用官方 `nn.FaceRecognizer` 类，整合了检测和识别功能
- 支持人脸录入和保存（.bin 格式）
- 自动管理人脸数据库

### 3. 运行程序

```bash
cd /root/face_recognition_system
python main.py
```

## 操作说明

### 按键操作

| 操作 | 功能 | 状态转换 |
|------|------|----------|
| 短按 OK 键 | 触发人脸识别 | 空闲 → 识别 |
| 短按 OK 键 | 停止人脸识别 | 识别 → 空闲 |
| 长按 OK 键（1.5秒）| 进入人脸录入 | 空闲 → 录入 |
| 长按 OK 键 | 取消录入 | 录入 → 空闲 |
| 短按 OK 键 | 重置系统 | 错误 → 空闲 |

### 状态指示

#### LED 指示

| 状态 | LED 行为 | 说明 |
|------|----------|------|
| 空闲 | 超慢闪（1秒）| 系统待机 |
| 识别中 | 慢闪（500ms）| 正在识别 |
| 录制中 | 慢闪（500ms）| 正在录制 |
| 录入中 | 快闪（200ms）| 正在录入 |
| 检测到已知人脸 | 常亮 | 识别成功 |
| 检测到未知人脸 | 快闪（200ms）| 报警 |
| 错误 | 快闪（200ms）| 系统错误 |

#### 音频提示

| 事件 | 提示音 | 说明 |
|------|--------|------|
| 状态切换 | 单 beep | 切换成功 |
| 识别启动 | 双 beep | 进入识别模式 |
| 检测到已知人脸 | 上升音调 | 识别成功 |
| 检测到未知人脸 | 高频报警音 | 未录入人脸 |
| 录入成功 | 双 beep | 录入完成 |
| 错误 | 三声低沉音 | 系统错误 |

### 人脸识别流程

1. **启动系统**
   - 系统进入空闲状态
   - LED 超慢闪
   - 屏幕显示"空闲模式"
   - 显示已录入人脸数量

2. **触发识别**
   - 短按 OK 键
   - 进入识别状态
   - LED 快闪
   - 播放双 beep 提示音

3. **检测人脸**
   - 使用 YOLOv8-face 模型检测人脸
   - 使用 InsightFace 模型提取特征
   - 与人脸库比对识别身份

4. **识别人脸**
   - **已录入人脸**：绿框 + 关键点 + LED 常亮 + 成功音
   - **未录入人脸**：红框 + 关键点 + LED 快闪 + 报警音
   - 自动开始录制视频和音频

5. **停止识别**
   - 再次短按 OK 键
   - 或无人脸超过 5 秒自动停止
   - 停止录制并返回空闲状态

### 人脸录入流程

1. **进入录入模式**
   - 长按 OK 键（1.5秒）
   - 进入录入状态
   - LED 快闪
   - 播放切换提示音

2. **检测人脸**
   - 正对摄像头
   - 等待检测到人脸
   - 屏幕显示"检测到人脸，按下 OK 键录入"

3. **触发录入**
   - 短按 OK 键
   - 系统自动录入当前人脸
   - 生成标签（user_时间戳）

4. **完成录入**
   - 录入成功：快闪 5 次 + 双 beep
   - 保存到人脸数据库（faces.bin）
   - 显示已录入人数
   - 自动返回空闲状态

5. **取消录入**
   - 长按 OK 键取消
   - 返回空闲状态

### 人脸录入流程

1. **进入录入模式**
   - 长按 OK 键（1.5秒）
   - 进入录入状态
   - LED 快闪
   - 播放切换提示音

2. **拍摄照片**
   - 正对摄像头
   - 系统自动拍摄 5 张照片
   - 每张间隔 1.5 秒
   - 屏幕显示进度条

3. **完成录入**
   - 自动训练分类器
   - 录入成功：快闪 5 次 + 双 beep
   - 录入失败：错误提示音
   - 自动返回空闲状态

4. **取消录入**
   - 长按 OK 键取消
   - 返回空闲状态

## 配置说明

所有配置参数在 `config.py` 文件中定义：

### 硬件配置

```python
LED_PIN = "A6"              # LED 引脚
LED_GPIO = "GPIOA6"         # GPIO 名称
CAMERA_WIDTH = 320          # 摄像头宽度
CAMERA_HEIGHT = 240         # 摄像头高度
```

### 模型配置

```python
FACE_DETECT_MODEL = "/root/models/yolov8n_face.mud"
FACE_FEATURE_MODEL = "/root/models/insghtface_webface_r50.mud"
FACES_DB_PATH = "/root/face_recognition_system/data/faces.bin"
```

### 识别配置

```python
FACE_CONF_THRESHOLD = 0.4      # 检测置信度阈值
FACE_ENROLL_COUNT = 5          # 录入照片数量
FACE_ENROLL_INTERVAL = 1500    # 拍照间隔(ms)
RECOGNIZE_TIMEOUT = 5000       # 无人脸超时(ms)
```

### 录制配置

```python
RECORD_VIDEO_FPS = 25          # 视频帧率
RECORD_AUDIO_SAMPLE_RATE = 16000  # 音频采样率
```

### 按键配置

```python
LONG_PRESS_MS = 1500           # 长按阈值(ms)
```

### LED 配置

```python
LED_BLINK_FAST = 200           # 快闪间隔(ms)
LED_BLINK_SLOW = 500           # 慢闪间隔(ms)
LED_BLINK_IDLE = 1000          # 超慢闪间隔(ms)
```

## 常见问题

### Q1: 模型文件在哪里？

A1: 模型文件通常在 `/root/models/` 目录下，使用 `.mud` 格式。需要两个模型：
- `yolov8n_face.mud` - 人脸检测模型
- `insghtface_webface_r50.mud` - 特征提取模型

### Q2: 模型文件从哪里下载？

A2: 可以从 MaixHub 下载：
- 人脸检测：https://maixhub.com/model/zoo/407
- 特征提取：https://maixhub.com/model/zoo/462

### Q3: 如何查看设备型号？

A3: 使用 `sys.device_id()` 返回 `"maixcam"` 或 `"maixcam2"`。

### Q4: 程序如何退出？

A4: 按 `Ctrl+C` 或通过 `app.need_exit()` 触发退出。

### Q5: 录制的文件在哪里？

A5: 录制文件保存在 `/root/face_recognition_system/data/recordings/` 目录下，格式为 MP4 和 WAV。

### Q6: 人脸数据库在哪里？

A6: 人脸数据库保存在 `/root/face_recognition_system/data/faces.bin`，自动创建和更新。

### Q7: 如何调整人脸识别灵敏度？

A7: 修改 `config.py` 中的阈值参数：
- `FACE_CONF_THRESHOLD` - 检测置信度（越大越严格）
- `FACE_IOU_THRESHOLD` - IoU 阈值（过滤重叠框）
- `FACE_RECOGNIZE_THRESHOLD` - 识别阈值（越大越严格）

也可以在运行时调用 `face_detector.set_detect_threshold()` 修改。

### Q8: 如何修改长按时间？

A8: 修改 `config.py` 中的 `LONG_PRESS_MS` 值，单位为毫秒，默认 1500ms。

### Q9: 如何删除已录入的人脸？

A9: 删除 `/root/face_recognition_system/data/faces.bin` 文件，重新运行程序即可。

### Q10: 支持多少人同时识别？

A10: 理论上无人数限制，但建议不超过 10 人以保证识别速度。

## 开发说明

### 技术架构

本项目使用 MaixPy 官方 API，主要技术栈：

1. **人脸识别**：`nn.FaceRecognizer` 类
   - 整合人脸检测和特征提取
   - 支持人脸库管理（.bin 格式）
   - 官方文档：https://wiki.sipeed.com/maixpy/doc/zh/vision/face_recognition.html

2. **状态机**：自定义轻量级状态机
   - 无外部依赖
   - 支持进入/退出回调
   - 支持超时保护

3. **硬件控制**：GPIO/PWM/Audio API
   - LED 控制：`gpio.GPIO`
   - 音频播放：`audio.Player`
   - 视频录制：`video.Encoder`

### 添加新功能

1. 在 `config.py` 中添加配置参数
2. 创建新的模块类
3. 在 `main.py` 中初始化和注册
4. 添加状态处理函数

### 调试技巧

1. 查看串口输出的调试信息
2. 使用 `print()` 输出变量值
3. 检查模型文件是否正确加载
4. 验证硬件引脚配置
5. 查看 MaixPy 官方文档：https://wiki.sipeed.com/maixpy/doc/zh/

## 版本历史

- v1.1.0 (2026-06-02)
  - 使用官方 nn.FaceRecognizer 类
  - 支持人脸数据库持久化（.bin 格式）
  - 优化人脸录入流程（按键触发）
  - 更新模型文件要求（yolov8n_face + insightface）

- v1.0.0 (2026-06-02)
  - 初始版本
  - 实现基本人脸识别功能
  - 实现视频录制功能
  - 实现人脸录入功能

## 许可证

本项目仅供学习和研究使用。

## 联系方式

如有问题，请联系开发者。
