# 🎉 MaixCAM2 人脸识别智能系统 v2.0.0

**重大版本更新！** 分辨率升级至 640×480，全新 UI 系统，音视频融合播放！

---

## 📥 下载

| 文件 | 大小 | 说明 |
|------|------|------|
| [maix-dostudy640-v2.0.0.zip](https://github.com/your-username/maix-dostudy/releases/download/v2.0.0/maix-dostudy640-v2.0.0.zip) | 122 KB | **推荐** 高清 640×480 版本 |
| [maix-dostudy2-v1.3.0.zip](https://github.com/your-username/maix-dostudy/releases/download/v2.0.0/maix-dostudy2-v1.3.0.zip) | 121 KB | 标清 320×240 版本 |

---

## ✨ 亮点特性

### 🖥️ 全新 UI 系统
- 5 页触摸屏界面（主页/设置/录入/录像/融合）
- 支持触摸滑动、翻页浏览
- 实时状态显示

### 🎬 音视频融合播放
- 一键融合 MP4 + WAV 文件
- 融合后视频直接播放
- 列表管理和批量操作

### 📡 实时状态同步
- HTTP 状态服务器（端口 8001）
- WebSocket 音频推流（端口 8002）
- 网页端实时监控人脸状态

### 🎤 语音控制
- 本地语音识别（实验性）
- 串口语音命令支持
- 12 种语音指令

### ⚡ 性能优化
- 轻量检测 + 间隔重识别
- 音频开启时自动降频
- 阈值实时生效

---

## 🚀 快速开始

```bash
# 1. 上传到 MaixCAM2
scp -r maix-dostudy640-v2.0.0/* root@<ip>:/root/face_recognition_system/

# 2. 准备模型文件
# 下载模型: https://maixhub.com/model/zoo/407
# 放置到: /root/models/

# 3. 运行
cd /root/face_recognition_system
python main.py
```

---

## 🎮 操作指南

**触摸屏操作：**
- 点击"识别" → 人脸识别 + 自动录制
- 点击"录入" → 人脸录入管理
- 点击"设置" → 参数调节
- 点击"录制" → 纯录制模式
- 点击"融合" → 音视频融合播放

**物理按键：**
- 短按 OK：开始/停止识别
- 长按 OK (1.5s)：进入录入模式
- 超长按 OK (3s)：退出程序

---

## 📊 性能指标

| 指标 | 值 |
|------|-----|
| 分辨率 | 640×480 |
| 空闲帧率 | ~25 FPS |
| 识别帧率 | ~15 FPS |
| 录制帧率 | ~20 FPS |
| 推流帧率 | ~15 FPS |
| 检测延迟 | ~30ms |

---

## 🐛 问题修复

- ✅ 修复音频推流导致帧率下降
- ✅ 修复 RTSP 推流与 Display 冲突
- ✅ 修复阈值参数编码问题
- ✅ 修复录像文件列表排序
- ✅ 修复纯录制模式状态重置
- ✅ 修复识别状态反复提示音
- ✅ 修复陌生人报警冷却问题

---

## 📚 完整文档

- 📖 [项目说明](README.md) - 完整使用文档
- 📋 [版本日志](CHANGELOG.md) - 详细更新说明
- 🔧 [性能优化](OPTIMIZATION_README.md) - 优化指南

---

## 🔧 配置示例

```python
# config.py 主要配置

# 分辨率
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# 人脸识别
FACE_CONF_THRESHOLD = 0.25       # 检测阈值
FACE_RECOGNIZE_THRESHOLD = 0.72  # 识别阈值

# 推流
STREAM_ENABLE = True             # HTTP 推流
RTSP_ENABLE = False              # RTSP 推流
AUDIO_STREAM_ENABLE = False      # 音频推流

# 语音
VOICE_ENABLE = False             # 本地语音识别
SERIAL_ENABLE = True             # 串口语音命令
```

---

## 📦 文件结构

```
maix-dostudy640-v2.0.0/
├── main.py                    # 主程序
├── config.py                  # 配置文件
├── ui.py                      # UI 框架
├── ui_pages.py                # UI 页面
├── face_detector.py           # 人脸识别
├── recorder_manager.py        # 视频录制
├── video_player_manager.py    # 视频播放
├── stream_manager.py          # 推流管理
├── audio_streamer.py          # 音频推流
├── status_server.py           # 状态服务器
├── serial_comm.py             # 串口通信
├── voice_recognition.py       # 语音识别
├── state_machine.py           # 状态机
├── key_manager.py             # 按键管理
├── led_controller.py          # LED 控制
├── audio_controller.py        # 音频控制
├── README.md                  # 项目说明
└── CHANGELOG.md               # 版本日志
```

---

## 🎯 推流服务

| 服务 | 端口 | 地址 |
|------|------|------|
| HTTP 推流 | 8000 | `http://<ip>:8000` |
| 状态服务器 | 8001 | `http://<ip>:8001/status` |
| RTSP 推流 | 554 | `rtsp://<ip>:554/live` |
| 音频推流 | 8002 | `ws://<ip>:8002` |

**网页端接入示例：**
```javascript
// 获取实时视频
const img = document.getElementById('video');
img.src = 'http://<maixcam_ip>:8000';

// 获取状态
async function getStatus() {
  const res = await fetch('http://<maixcam_ip>:8001/status');
  const data = await res.json();
  console.log('状态:', data.state);
  console.log('人脸数:', data.face_count);
}
```

---

## ⚠️ 注意事项

1. **内存限制**: 关闭语音识别可释放内存
2. **模型文件**: 确保 `/root/models/` 下有必需的 `.mud` 文件
3. **网络配置**: 确保 MaixCAM2 与电脑在同一网络
4. **光线条件**: 良好光线可提高识别准确率
5. **人脸录入**: 建议在光线充足时录入人脸

---

## 🔗 相关链接

- [MaixCAM2 官网](https://wiki.sipeed.com/maixcam2)
- [MaixPy 文档](https://wiki.sipeed.com/maixpy/doc/zh/)
- [MaixHub 模型下载](https://maixhub.com/)
- [项目 GitHub](https://github.com/your-username/maix-dostudy)

---

## 🙏 致谢

感谢所有贡献者和开源社区的支持！

---

## 📞 联系方式

- **Issues**: [提交问题](https://github.com/your-username/maix-dostudy/issues)
- **Email**: your-email@example.com

---

**Full Changelog**: https://github.com/your-username/maix-dostudy/compare/v1.3.0...v2.0.0

---

Made with ❤️ for MaixCAM2 🤖
