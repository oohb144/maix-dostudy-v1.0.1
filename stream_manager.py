"""
MaixCAM2 人脸识别智能系统 - 推流管理模块

功能：
- HTTP JPEG 视频推流（支持推流处理后的画面）
- RTSP 视频推流（原始画面，用于监控）
- 推流启停控制
- 推流地址管理
- 网页端录制/截图/下载功能

使用方法：
- HTTP推流：通过浏览器访问推流地址查看实时画面
- RTSP推流：通过VLC/ffplay播放RTSP流
"""

from maix import http, network


class StreamManager:
    """
    推流管理器

    功能：
    - 管理 HTTP JPEG 流服务器
    - 控制推流启停
    - 获取推流地址
    - 推流带标注的人脸识别画面
    - 网页端支持录制视频、截图、下载
    """

    def __init__(self, jpeg_quality=75):
        """
        初始化推流管理器

        参数：
            jpeg_quality: JPEG 编码质量 (1-100)，默认 75
        """
        self._server = None
        self._is_streaming = False
        self._stream_url = ""
        self._jpeg_quality = jpeg_quality

        # 自定义网页界面（增强版 - 支持人脸检测自动录制/元数据显示/截图/下载）
        self._html = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MaixCAM2 人脸识别系统</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: #0f0f1a;
            color: #e0e0e0;
            min-height: 100vh;
        }
        .container {
            max-width: 960px;
            margin: 0 auto;
            padding: 16px;
        }

        /* ========== 头部 ========== */
        .header {
            text-align: center;
            padding: 24px 16px;
            background: linear-gradient(135deg, #1a1a3e 0%, #0d1b2a 100%);
            border-radius: 16px;
            margin-bottom: 16px;
            border: 1px solid rgba(99, 102, 241, 0.3);
        }
        .logo { font-size: 42px; margin-bottom: 6px; }
        .header h1 {
            font-size: 24px;
            font-weight: 700;
            background: linear-gradient(135deg, #818cf8, #6366f1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 4px;
        }
        .header p { color: #94a3b8; font-size: 13px; }

        /* ========== 视频卡片 ========== */
        .video-card {
            background: #1a1a2e;
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid rgba(99, 102, 241, 0.2);
            box-shadow: 0 4px 24px rgba(0,0,0,0.4);
        }
        .video-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            background: rgba(99, 102, 241, 0.1);
            border-bottom: 1px solid rgba(99, 102, 241, 0.2);
        }
        .video-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
            font-size: 14px;
        }
        .live-badge {
            background: #ef4444;
            color: white;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }

        /* 人脸检测状态角标 */
        .face-overlay {
            position: absolute;
            top: 12px;
            left: 12px;
            background: rgba(15, 15, 26, 0.85);
            color: #e0e0e0;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            display: none;
            align-items: center;
            gap: 8px;
            backdrop-filter: blur(4px);
            border: 1px solid rgba(99, 102, 241, 0.3);
            z-index: 10;
        }
        .face-overlay.active { display: flex; }
        .face-overlay .known { color: #22c55e; }
        .face-overlay .unknown { color: #ef4444; }

        /* 视频区域 */
        .video-wrapper {
            position: relative;
            background: #000;
            line-height: 0;
        }
        .video-wrapper img {
            display: block;
            width: 100%;
            height: auto;
            min-height: 240px;
            image-rendering: -webkit-optimize-contrast;
        }
        /* 隐藏的 canvas 用于截图/录制 */
        #captureCanvas { display: none; }

        /* 录制指示器 */
        .rec-indicator {
            position: absolute;
            top: 12px;
            right: 12px;
            background: rgba(239, 68, 68, 0.9);
            color: #fff;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            display: none;
            align-items: center;
            gap: 6px;
            backdrop-filter: blur(4px);
        }
        .rec-indicator.active { display: flex; }
        .rec-indicator .auto-label {
            background: rgba(255,255,255,0.25);
            padding: 1px 6px;
            border-radius: 4px;
            font-size: 10px;
            margin-left: 2px;
        }
        .rec-dot {
            width: 8px; height: 8px;
            background: #fff;
            border-radius: 50%;
            animation: blink 1s infinite;
        }
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }

        /* ========== 控制按钮栏 ========== */
        .controls {
            display: flex;
            gap: 10px;
            padding: 14px 16px;
            background: rgba(15, 15, 26, 0.6);
            border-top: 1px solid rgba(99, 102, 241, 0.15);
            flex-wrap: wrap;
            justify-content: center;
        }
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 10px 20px;
            border: none;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            font-family: inherit;
        }
        .btn:active { transform: scale(0.95); }
        .btn-record {
            background: linear-gradient(135deg, #ef4444, #dc2626);
            color: #fff;
        }
        .btn-record.recording {
            background: linear-gradient(135deg, #f59e0b, #d97706);
        }
        .btn-screenshot {
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            color: #fff;
        }
        .btn-download {
            background: linear-gradient(135deg, #10b981, #059669);
            color: #fff;
        }
        .btn-download:disabled {
            background: #374151;
            color: #6b7280;
            cursor: not-allowed;
        }
        .btn-clear {
            background: linear-gradient(135deg, #6b7280, #4b5563);
            color: #fff;
        }
        /* 自动录制开关按钮 */
        .btn-auto-rec {
            background: linear-gradient(135deg, #8b5cf6, #7c3aed);
            color: #fff;
            position: relative;
        }
        .btn-auto-rec.disabled {
            background: linear-gradient(135deg, #4b5563, #374151);
            color: #94a3b8;
        }
        .btn-auto-rec .toggle-dot {
            width: 8px; height: 8px;
            border-radius: 50%;
            background: #22c55e;
        }
        .btn-auto-rec.disabled .toggle-dot {
            background: #6b7280;
        }

        /* ========== 状态栏 ========== */
        .status-bar {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            padding: 14px;
            background: #1a1a2e;
            border-radius: 12px;
            margin-top: 16px;
            border: 1px solid rgba(99, 102, 241, 0.2);
        }
        .status-item { text-align: center; }
        .status-icon { font-size: 20px; margin-bottom: 4px; }
        .status-label { font-size: 10px; color: #94a3b8; margin-bottom: 2px; }
        .status-value { font-size: 13px; font-weight: 600; color: #818cf8; }

        /* ========== 人脸详情条 ========== */
        .face-detail-bar {
            background: #1a1a2e;
            border-radius: 8px;
            margin-top: 10px;
            padding: 10px 14px;
            border: 1px solid rgba(99, 102, 241, 0.2);
            display: none;
            font-size: 13px;
            line-height: 1.6;
        }
        .face-detail-bar.active { display: block; }
        .face-detail-bar .face-labels {
            font-size: 11px;
            color: #94a3b8;
            margin-top: 4px;
        }
        .face-detail-bar .known-count { color: #22c55e; font-weight: 700; }
        .face-detail-bar .unknown-count { color: #ef4444; font-weight: 700; }

        /* ========== 录制文件列表 ========== */
        .recordings-section {
            background: #1a1a2e;
            border-radius: 12px;
            margin-top: 16px;
            border: 1px solid rgba(99, 102, 241, 0.2);
            overflow: hidden;
        }
        .recordings-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            background: rgba(99, 102, 241, 0.08);
            border-bottom: 1px solid rgba(99, 102, 241, 0.15);
            font-weight: 600;
            font-size: 14px;
        }
        .recordings-count {
            background: rgba(99, 102, 241, 0.2);
            color: #818cf8;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
        }
        .recordings-list {
            max-height: 280px;
            overflow-y: auto;
            padding: 8px;
        }
        .recordings-list::-webkit-scrollbar { width: 6px; }
        .recordings-list::-webkit-scrollbar-track { background: transparent; }
        .recordings-list::-webkit-scrollbar-thumb {
            background: rgba(99, 102, 241, 0.3);
            border-radius: 3px;
        }
        .recording-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 12px;
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
            margin-bottom: 6px;
            transition: background 0.2s;
        }
        .recording-item:hover { background: rgba(99, 102, 241, 0.1); }
        .recording-info {
            display: flex;
            align-items: center;
            gap: 10px;
            flex: 1;
            min-width: 0;
        }
        .recording-icon { font-size: 20px; flex-shrink: 0; }
        .recording-name {
            font-size: 12px;
            color: #cbd5e1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .recording-meta {
            font-size: 11px;
            color: #64748b;
            margin-top: 2px;
        }
        .recording-meta .face-badge {
            display: inline-block;
            padding: 1px 6px;
            border-radius: 4px;
            font-size: 10px;
            margin-left: 4px;
        }
        .recording-meta .face-badge.auto {
            background: rgba(139, 92, 246, 0.2);
            color: #a78bfa;
        }
        .recording-meta .face-badge.known {
            background: rgba(34, 197, 94, 0.2);
            color: #22c55e;
        }
        .recording-meta .face-badge.unknown {
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
        }
        .recording-actions {
            display: flex;
            gap: 6px;
            flex-shrink: 0;
        }
        .btn-sm {
            padding: 5px 10px;
            font-size: 11px;
            border-radius: 6px;
            border: none;
            cursor: pointer;
            font-weight: 600;
            font-family: inherit;
            transition: all 0.2s;
        }
        .btn-sm:active { transform: scale(0.9); }
        .btn-play { background: #3b82f6; color: #fff; }
        .btn-delete { background: #ef4444; color: #fff; }
        .btn-download-sm { background: #10b981; color: #fff; }
        .empty-tip {
            text-align: center;
            padding: 30px;
            color: #64748b;
            font-size: 13px;
        }
        .empty-tip .icon { font-size: 36px; margin-bottom: 8px; }

        /* ========== 预览弹窗 ========== */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.85);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            padding: 20px;
        }
        .modal-overlay.active { display: flex; }
        .modal-content {
            background: #1a1a2e;
            border-radius: 16px;
            overflow: hidden;
            max-width: 800px;
            width: 100%;
            border: 1px solid rgba(99, 102, 241, 0.3);
        }
        .modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            background: rgba(99, 102, 241, 0.1);
            border-bottom: 1px solid rgba(99, 102, 241, 0.2);
        }
        .modal-title { font-weight: 600; font-size: 14px; }
        .btn-close {
            background: none;
            border: none;
            color: #94a3b8;
            font-size: 20px;
            cursor: pointer;
            padding: 4px;
        }
        .modal-body { padding: 16px; }
        .modal-body video {
            width: 100%;
            border-radius: 8px;
            background: #000;
        }
        .modal-body img {
            width: 100%;
            border-radius: 8px;
        }
        .face-summary {
            background: rgba(99, 102, 241, 0.08);
            border-radius: 8px;
            padding: 10px 14px;
            margin-top: 10px;
            font-size: 12px;
            color: #94a3b8;
        }
        .face-summary .known { color: #22c55e; font-weight: 600; }
        .face-summary .unknown { color: #ef4444; font-weight: 600; }

        /* ========== 页脚 ========== */
        .footer {
            text-align: center;
            padding: 16px;
            color: #475569;
            font-size: 11px;
            margin-top: 16px;
        }

        /* ========== Toast 提示 ========== */
        .toast {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%) translateY(-100px);
            background: rgba(30, 30, 50, 0.95);
            color: #e0e0e0;
            padding: 10px 20px;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 500;
            z-index: 2000;
            transition: transform 0.3s ease;
            border: 1px solid rgba(99, 102, 241, 0.3);
            backdrop-filter: blur(8px);
        }
        .toast.show { transform: translateX(-50%) translateY(0); }

        /* ========== 音频控制 ========== */
        .audio-controls {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 16px;
            background: rgba(15, 15, 26, 0.6);
            border-top: 1px solid rgba(99, 102, 241, 0.15);
        }
        .audio-label {
            font-size: 12px;
            color: #94a3b8;
            flex-shrink: 0;
        }
        .btn-audio {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 6px 12px;
            border: none;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            font-family: inherit;
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            color: #fff;
        }
        .btn-audio:active { transform: scale(0.95); }
        .btn-audio.muted {
            background: linear-gradient(135deg, #6b7280, #4b5563);
            color: #94a3b8;
        }
        .audio-status {
            font-size: 11px;
            color: #64748b;
            margin-left: auto;
        }
        .audio-status.connected { color: #22c55e; }
        .audio-status.disconnected { color: #f59e0b; }

        /* ========== 自动录制提示遮罩 ========== */
        .auto-rec-prompt {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.7);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 3000;
        }
        .auto-rec-prompt.active { display: flex; }
        .auto-rec-prompt-box {
            background: #1a1a2e;
            border-radius: 16px;
            padding: 32px 24px;
            text-align: center;
            max-width: 360px;
            border: 1px solid rgba(99, 102, 241, 0.3);
        }
        .auto-rec-prompt-box .icon { font-size: 48px; margin-bottom: 16px; }
        .auto-rec-prompt-box h3 {
            font-size: 16px;
            color: #e0e0e0;
            margin-bottom: 8px;
        }
        .auto-rec-prompt-box p {
            font-size: 13px;
            color: #94a3b8;
            margin-bottom: 20px;
        }
        .btn-enable-auto {
            background: linear-gradient(135deg, #8b5cf6, #7c3aed);
            color: #fff;
            border: none;
            padding: 12px 32px;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            font-family: inherit;
        }

        /* ========== 响应式 ========== */
        @media (max-width: 600px) {
            .container { padding: 10px; }
            .header h1 { font-size: 20px; }
            .header p { font-size: 12px; }
            .status-bar { grid-template-columns: repeat(3, 1fr); gap: 6px; }
            .controls { gap: 6px; }
            .btn { padding: 8px 12px; font-size: 12px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <div class="logo">🤖</div>
            <h1>MaixCAM2 人脸识别系统</h1>
            <p>实时视频流 · 智能人脸识别 · 自动录制</p>
        </div>

        <!-- 视频卡片 -->
        <div class="video-card">
            <div class="video-header">
                <div class="video-title">
                    <span>📹</span>
                    <span>实时监控画面</span>
                </div>
                <span class="live-badge">● LIVE</span>
            </div>
            <div class="video-wrapper">
                <img src="/stream" alt="Video Stream" id="stream" crossorigin="anonymous">
                <!-- 人脸检测状态角标 -->
                <div class="face-overlay" id="faceOverlay">
                    <span>👤</span>
                    <span id="faceOverlayText">0 人</span>
                </div>
                <!-- 录制指示器 -->
                <div class="rec-indicator" id="recIndicator">
                    <span class="rec-dot"></span>
                    <span>REC </span><span id="recTime">00:00</span>
                    <span class="auto-label" id="autoRecLabel" style="display:none">自动</span>
                </div>
            </div>
            <canvas id="captureCanvas"></canvas>
            <div class="controls">
                <button class="btn btn-auto-rec" id="btnAutoRec" onclick="toggleAutoRecord()">
                    <span class="toggle-dot"></span>
                    <span id="autoRecText">自动录制</span>
                </button>
                <button class="btn btn-record" id="btnRecord" onclick="toggleRecord()">
                    <span id="recordIcon">⏺</span>
                    <span id="recordText">开始录制</span>
                </button>
                <button class="btn btn-screenshot" onclick="takeScreenshot()">
                    📸 截图
                </button>
                <button class="btn btn-download" id="btnDownload" onclick="downloadRecording()" disabled>
                    💾 下载录制
                </button>
                <button class="btn btn-clear" onclick="clearRecordings()">
                    🗑️ 清空
                </button>
            </div>
            <!-- 音频控制行 -->
            <div class="audio-controls">
                <span class="audio-label">🔊 音频</span>
                <button class="btn-audio" id="btnAudio" onclick="toggleAudio()">
                    <span id="audioIcon">🔇</span>
                    <span id="audioText">点击开启</span>
                </button>
                <span class="audio-status" id="audioStatus">未连接</span>
            </div>
        </div>

        <!-- 状态栏 -->
        <div class="status-bar">
            <div class="status-item">
                <div class="status-icon">🎯</div>
                <div class="status-label">识别状态</div>
                <div class="status-value" id="detectStatus">待机中</div>
            </div>
            <div class="status-item">
                <div class="status-icon">👤</div>
                <div class="status-label">人脸数量</div>
                <div class="status-value" id="faceCount">0</div>
            </div>
            <div class="status-item">
                <div class="status-icon">📡</div>
                <div class="status-label">连接状态</div>
                <div class="status-value" id="connStatus" style="color:#22c55e">正常</div>
            </div>
        </div>

        <!-- 人脸详情条 -->
        <div class="face-detail-bar" id="faceDetails">
        </div>

        <!-- 录制文件列表 -->
        <div class="recordings-section">
            <div class="recordings-header">
                <span>📁 录制文件</span>
                <span class="recordings-count" id="recCount">0</span>
            </div>
            <div class="recordings-list" id="recordingsList">
                <div class="empty-tip">
                    <div class="icon">🎬</div>
                    <div>暂无录制文件</div>
                    <div style="margin-top:4px;font-size:11px">检测到人脸时将自动开始录制</div>
                </div>
            </div>
        </div>

        <!-- 页脚 -->
        <div class="footer">
            <p>MaixCAM2 Face Recognition System v2.1 · 智能检测录制版</p>
        </div>
    </div>

    <!-- 预览弹窗 -->
    <div class="modal-overlay" id="previewModal">
        <div class="modal-content">
            <div class="modal-header">
                <span class="modal-title" id="previewTitle">预览</span>
                <button class="btn-close" onclick="closePreview()">✕</button>
            </div>
            <div class="modal-body" id="previewBody"></div>
        </div>
    </div>

    <!-- 自动录制启用提示（浏览器策略要求） -->
    <div class="auto-rec-prompt" id="autoRecPrompt">
        <div class="auto-rec-prompt-box">
            <div class="icon">🎥</div>
            <h3>启用自动录制</h3>
            <p>浏览器要求用户交互才能录制视频。<br>点击下方按钮启用自动录制功能。</p>
            <button class="btn-enable-auto" onclick="enableAutoRecording()">点击启用</button>
        </div>
    </div>

    <!-- Toast 提示 -->
    <div class="toast" id="toast"></div>

    <script>
    // ==================== 配置 ====================
    const STATUS_SERVER_PORT = 8001;  // 状态服务器端口
    const AUTO_STOP_DELAY_MS = 3000;  // 人脸消失后延迟停止录制（毫秒）

    // ==================== 状态变量 ====================
    let isRecording = false;
    let mediaRecorder = null;
    let recordedChunks = [];
    let recordingStartTime = 0;
    let recTimerInterval = null;
    let recordings = [];  // {name, blob, url, size, duration, timestamp, autoRecorded, faceEvents}
    let lastRecordedBlob = null;

    // 自动录制相关
    let autoRecordingEnabled = true;   // 自动录制开关（默认开启）
    let autoRecording = false;         // 当前是否为自动录制模式
    let autoRecordTimeout = null;     // 自动停止延迟定时器
    let lastFaceState = false;        // 上一帧是否检测到人脸
    let recordingFaceEvents = [];     // 录制期间的人脸事件记录
    let lastFaceData = '';            // 上一帧的人脸数据（用于去重）
    let userInteracted = false;       // 用户是否已交互（解决浏览器策略）

    // 设备端状态
    let deviceState = {
        state: '空闲',
        has_face: false,
        face_count: 0,
        known_face_count: 0,
        unknown_face_count: 0,
        face_labels: [],
        recording: false,
        record_duration: 0
    };

    // DOM 元素缓存（避免每帧 getElementById 查询）
    let domCache = {};
    function getDom() {
        if (!domCache._init) {
            domCache.detectStatus = document.getElementById('detectStatus');
            domCache.faceCount = document.getElementById('faceCount');
            domCache.connStatus = document.getElementById('connStatus');
            domCache.faceOverlay = document.getElementById('faceOverlay');
            domCache.faceOverlayText = document.getElementById('faceOverlayText');
            domCache.faceDetails = document.getElementById('faceDetails');
            domCache.autoRecLabel = document.getElementById('autoRecLabel');
            domCache.btnRecord = document.getElementById('btnRecord');
            domCache.recordIcon = document.getElementById('recordIcon');
            domCache.recordText = document.getElementById('recordText');
            domCache.recIndicator = document.getElementById('recIndicator');
            domCache.btnDownload = document.getElementById('btnDownload');
            domCache.btnAutoRec = document.getElementById('btnAutoRec');
            domCache.autoRecTextEl = document.getElementById('autoRecText');
            domCache._init = true;
        }
        return domCache;
    }

    // ==================== 初始化 ====================
    const streamImg = document.getElementById('stream');
    const canvas = document.getElementById('captureCanvas');
    const ctx = canvas.getContext('2d');

    // 当图片加载后同步 canvas 尺寸
    streamImg.onload = function() {
        canvas.width = this.naturalWidth || this.width;
        canvas.height = this.naturalHeight || this.height;
    };

    // 图片加载错误处理
    streamImg.onerror = function() {
        this.src = 'data:image/svg+xml,' + encodeURIComponent(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">' +
            '<rect fill="#1a1a2e" width="400" height="300"/>' +
            '<text fill="#818cf8" font-family="Arial" font-size="18" x="50%" y="50%" text-anchor="middle">等待视频流...</text></svg>'
        );
    };

    // 用户首次点击标记（解决浏览器自动录制策略）
    document.addEventListener('click', function() { userInteracted = true; }, { once: false });
    document.addEventListener('touchstart', function() { userInteracted = true; }, { once: false });

    // ==================== 工具函数 ====================
    function showToast(msg, duration) {
        duration = duration || 2000;
        const t = document.getElementById('toast');
        t.textContent = msg;
        t.classList.add('show');
        setTimeout(() => t.classList.remove('show'), duration);
    }

    function formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    function formatDuration(ms) {
        const s = Math.floor(ms / 1000);
        const m = Math.floor(s / 60);
        const sec = s % 60;
        return (m < 10 ? '0' : '') + m + ':' + (sec < 10 ? '0' : '') + sec;
    }

    function getTimestamp() {
        const now = new Date();
        return now.getFullYear() +
            String(now.getMonth() + 1).padStart(2, '0') +
            String(now.getDate()).padStart(2, '0') + '_' +
            String(now.getHours()).padStart(2, '0') +
            String(now.getMinutes()).padStart(2, '0') +
            String(now.getSeconds()).padStart(2, '0');
    }

    // 将 MJPEG img 绘制到 canvas
    function drawToCanvas() {
        if (streamImg.naturalWidth > 0) {
            if (canvas.width !== streamImg.naturalWidth) {
                canvas.width = streamImg.naturalWidth;
                canvas.height = streamImg.naturalHeight;
            }
            ctx.drawImage(streamImg, 0, 0, canvas.width, canvas.height);
        }
    }

    // ==================== 状态轮询 ====================
    let pollFailCount = 0;  // 连续失败计数

    function pollStatus() {
        const ip = window.location.hostname;
        var controller = new AbortController();
        // 1.5秒超时，避免慢请求堆积
        var timeoutId = setTimeout(function() { controller.abort(); }, 1500);

        fetch('http://' + ip + ':' + STATUS_SERVER_PORT + '/status', {
            signal: controller.signal
        }).then(function(r) {
            clearTimeout(timeoutId);
            return r.json();
        }).then(function(data) {
            pollFailCount = 0;
            updateFaceStatus(data);
            var c = getDom();
            c.connStatus.textContent = '正常';
            c.connStatus.style.color = '#22c55e';
        }).catch(function(err) {
            clearTimeout(timeoutId);
            pollFailCount++;
            // 连续失败 3 次以上才显示离线，避免偶发超时就变色
            if (pollFailCount >= 3) {
                var c = getDom();
                c.connStatus.textContent = '离线';
                c.connStatus.style.color = '#f59e0b';
            }
        });
    }

    // 每 500ms 轮询状态（设备帧率约 15-30fps，500ms 足够）
    setInterval(pollStatus, 500);
    // 首次立即请求
    setTimeout(pollStatus, 100);

    // ==================== 人脸状态更新（带去抖） ====================
    let _lastStatusStr = '';  // 上次的状态 JSON 字符串，用于去抖

    function updateFaceStatus(data) {
        // 去抖：如果数据完全相同则跳过 DOM 更新
        var newStr = data.state + '|' + data.has_face + '|' + data.face_count +
            '|' + data.known_face_count + '|' + data.unknown_face_count +
            '|' + (data.face_labels ? data.face_labels.join(',') : '');
        if (newStr === _lastStatusStr) return;
        _lastStatusStr = newStr;

        // 保存完整状态
        deviceState = data;

        var c = getDom();

        // 更新状态栏
        c.detectStatus.textContent = data.state || '待机中';
        c.faceCount.textContent = data.face_count || 0;

        // 状态颜色
        if (data.state === '录制中') {
            c.detectStatus.style.color = '#ef4444';
        } else if (data.state === '识别中') {
            c.detectStatus.style.color = '#f59e0b';
        } else {
            c.detectStatus.style.color = '#818cf8';
        }

        // 更新人脸数显示
        c.faceCount.style.color = (data.face_count > 0) ? '#22c55e' : '#818cf8';

        // 更新人脸检测角标
        if (data.face_count > 0 && data.state !== '空闲') {
            c.faceOverlay.classList.add('active');
            var known = data.known_face_count || 0;
            var unknown = data.unknown_face_count || 0;
            c.faceOverlayText.innerHTML = '<span class="known">' + known + ' 熟人</span> · <span class="unknown">' + unknown + ' 陌生</span>';
        } else {
            c.faceOverlay.classList.remove('active');
        }

        // 更新人脸详情条
        if (data.face_count > 0 && data.state !== '空闲') {
            var known = data.known_face_count || 0;
            var unknown = data.unknown_face_count || 0;
            var html = '<strong>👤 检测到 ' + data.face_count + ' 张人脸</strong>　';
            html += '<span class="known-count">✓ ' + known + ' 熟人</span>　';
            html += '<span class="unknown-count">✗ ' + unknown + ' 陌生人</span>';
            if (data.face_labels && data.face_labels.length > 0) {
                html += '<div class="face-labels">标签: ' + data.face_labels.join(', ') + '</div>';
            }
            c.faceDetails.innerHTML = html;
            c.faceDetails.classList.add('active');
        } else {
            c.faceDetails.classList.remove('active');
        }

        // 自动录制逻辑
        handleAutoRecording(data);
    }

    // ==================== 自动录制逻辑 ====================
    function handleAutoRecording(data) {
        var hasFace = data.has_face && data.state !== '空闲';

        if (hasFace && !lastFaceState) {
            // 人脸刚出现 → 开始自动录制
            lastFaceState = true;
            // 清除任何待停止的定时器
            if (autoRecordTimeout) {
                clearTimeout(autoRecordTimeout);
                autoRecordTimeout = null;
            }
            if (autoRecordingEnabled && !isRecording) {
                startAutoRecording();
            }
        } else if (hasFace && lastFaceState) {
            // 人脸持续存在 → 取消待停止定时器
            if (autoRecordTimeout) {
                clearTimeout(autoRecordTimeout);
                autoRecordTimeout = null;
            }
        } else if (!hasFace && lastFaceState) {
            // 人脸刚消失 → 延迟停止录制
            lastFaceState = false;
            if (autoRecording && isRecording) {
                autoRecordTimeout = setTimeout(function() {
                    if (autoRecording && isRecording) {
                        stopRecording();
                        autoRecording = false;
                        showToast('👤 人脸消失，自动停止录制');
                    }
                    autoRecordTimeout = null;
                }, AUTO_STOP_DELAY_MS);
            }
        }

        // 录制期间记录人脸事件
        if (isRecording && data.face_labels) {
            var currentData = JSON.stringify({
                k: data.known_face_count,
                u: data.unknown_face_count,
                l: data.face_labels
            });
            if (currentData !== lastFaceData) {
                lastFaceData = currentData;
                recordingFaceEvents.push({
                    time: Date.now() - recordingStartTime,
                    faces: data.face_labels,
                    known: data.known_face_count,
                    unknown: data.unknown_face_count
                });
            }
        }
    }

    // 自动录制开关切换
    function toggleAutoRecord() {
        autoRecordingEnabled = !autoRecordingEnabled;
        updateAutoRecordButton();
        if (autoRecordingEnabled) {
            showToast('✅ 自动录制已开启');
        } else {
            showToast('⚠️ 自动录制已关闭');
            // 如果当前正在自动录制，不立即停止，让自然完成
        }
    }

    function updateAutoRecordButton() {
        var btn = document.getElementById('btnAutoRec');
        var text = document.getElementById('autoRecText');
        if (autoRecordingEnabled) {
            btn.classList.remove('disabled');
            text.textContent = '自动录制';
        } else {
            btn.classList.add('disabled');
            text.textContent = '手动录制';
        }
    }

    // 启动自动录制
    function startAutoRecording() {
        if (!userInteracted) {
            // 浏览器策略：需要用户交互才能录制
            document.getElementById('autoRecPrompt').classList.add('active');
            return;
        }
        autoRecording = true;
        startRecording();
        showToast('👤 检测到人脸，自动开始录制');
        document.getElementById('autoRecLabel').style.display = 'inline';
    }

    // 启用自动录制（用户点击确认后）
    function enableAutoRecording() {
        userInteracted = true;
        document.getElementById('autoRecPrompt').classList.remove('active');
        // 如果人脸还在，立即开始录制
        if (deviceState.has_face && deviceState.state !== '空闲') {
            startAutoRecording();
        }
    }

    // ==================== 录制功能 ====================
    function toggleRecord() {
        if (isRecording) {
            autoRecording = false;  // 手动停止时取消自动录制标记
            document.getElementById('autoRecLabel').style.display = 'none';
            stopRecording();
        } else {
            startRecording();
        }
    }

    function startRecording() {
        try {
            // 先绘制一帧到 canvas 确保尺寸正确
            drawToCanvas();

            // 从 canvas 获取流
            var stream = canvas.captureStream(15); // 15fps

            // 选择编码格式
            var mimeType = 'video/webm;codecs=vp9';
            if (!MediaRecorder.isTypeSupported(mimeType)) {
                mimeType = 'video/webm;codecs=vp8';
                if (!MediaRecorder.isTypeSupported(mimeType)) {
                    mimeType = 'video/webm';
                    if (!MediaRecorder.isTypeSupported(mimeType)) {
                        mimeType = '';
                    }
                }
            }

            var options = { videoBitsPerSecond: 2500000 };
            if (mimeType) options.mimeType = mimeType;

            mediaRecorder = new MediaRecorder(stream, options);
            recordedChunks = [];
            recordingFaceEvents = [];
            lastFaceData = '';

            mediaRecorder.ondataavailable = function(e) {
                if (e.data && e.data.size > 0) {
                    recordedChunks.push(e.data);
                }
            };

            mediaRecorder.onstop = function() {
                var blob = new Blob(recordedChunks, { type: 'video/webm' });
                lastRecordedBlob = blob;

                // 添加到录制列表
                var duration = Date.now() - recordingStartTime;
                var name = 'recording_' + getTimestamp() + '.webm';
                // 计算人脸统计摘要
                var faceSummary = computeFaceSummary(recordingFaceEvents);
                var rec = {
                    name: name,
                    blob: blob,
                    url: URL.createObjectURL(blob),
                    size: blob.size,
                    duration: duration,
                    timestamp: Date.now(),
                    autoRecorded: autoRecording,
                    faceEvents: recordingFaceEvents,
                    maxKnown: faceSummary.maxKnown,
                    maxUnknown: faceSummary.maxUnknown,
                    maxTotal: faceSummary.maxTotal,
                    labels: faceSummary.labels
                };
                recordings.unshift(rec);

                // 启用下载按钮
                document.getElementById('btnDownload').disabled = false;

                // 更新列表
                updateRecordingsList();
                showToast('✅ 录制完成: ' + name);

                // 重置自动录制标记
                if (autoRecording) {
                    autoRecording = false;
                    document.getElementById('autoRecLabel').style.display = 'none';
                }
            };

            // 开始录制
            mediaRecorder.start(100); // 每100ms收集一次数据
            isRecording = true;
            recordingStartTime = Date.now();

            // 更新 UI
            document.getElementById('btnRecord').classList.add('recording');
            document.getElementById('recordIcon').textContent = '⏹';
            document.getElementById('recordText').textContent = '停止录制';
            document.getElementById('recIndicator').classList.add('active');

            // 启动录制计时
            recTimerInterval = setInterval(function() {
                var elapsed = Date.now() - recordingStartTime;
                document.getElementById('recTime').textContent = formatDuration(elapsed);
            }, 200);

            // 持续绘制帧到 canvas（确保录制内容更新）
            startFrameCapture();

            if (!autoRecording) {
                showToast('🔴 开始录制');
            }
        } catch (err) {
            console.error('录制启动失败:', err);
            showToast('❌ 录制启动失败: ' + err.message);
        }
    }

    // 计算人脸统计摘要
    function computeFaceSummary(events) {
        var maxKnown = 0, maxUnknown = 0, maxTotal = 0;
        var labelsSet = {};
        for (var i = 0; i < events.length; i++) {
            var e = events[i];
            if (e.known > maxKnown) maxKnown = e.known;
            if (e.unknown > maxUnknown) maxUnknown = e.unknown;
            if ((e.known + e.unknown) > maxTotal) maxTotal = e.known + e.unknown;
            for (var j = 0; j < e.faces.length; j++) {
                labelsSet[e.faces[j]] = true;
            }
        }
        return {
            maxKnown: maxKnown,
            maxUnknown: maxUnknown,
            maxTotal: maxTotal,
            labels: Object.keys(labelsSet)
        };
    }

    let frameCaptureInterval = null;
    function startFrameCapture() {
        if (frameCaptureInterval) clearInterval(frameCaptureInterval);
        frameCaptureInterval = setInterval(function() {
            if (isRecording) drawToCanvas();
        }, 66); // ~15fps
    }

    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }
        isRecording = false;

        if (frameCaptureInterval) {
            clearInterval(frameCaptureInterval);
            frameCaptureInterval = null;
        }

        // 更新 UI
        document.getElementById('btnRecord').classList.remove('recording');
        document.getElementById('recordIcon').textContent = '⏺';
        document.getElementById('recordText').textContent = '开始录制';
        document.getElementById('recIndicator').classList.remove('active');

        if (recTimerInterval) {
            clearInterval(recTimerInterval);
            recTimerInterval = null;
        }
    }

    // ==================== 截图功能 ====================
    function takeScreenshot() {
        drawToCanvas();

        canvas.toBlob(function(blob) {
            if (!blob) {
                showToast('❌ 截图失败');
                return;
            }
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = 'screenshot_' + getTimestamp() + '.png';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            showToast('📸 截图已保存');
        }, 'image/png');
    }

    // ==================== 下载录制 ====================
    function downloadRecording() {
        if (recordings.length === 0) {
            showToast('⚠️ 没有可下载的录制');
            return;
        }
        // 下载最新的录制
        var rec = recordings[0];
        var a = document.createElement('a');
        a.href = rec.url;
        a.download = rec.name;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        showToast('💾 下载: ' + rec.name);
    }

    // ==================== 录制列表管理 ====================
    function updateRecordingsList() {
        var list = document.getElementById('recordingsList');
        var count = document.getElementById('recCount');
        count.textContent = recordings.length;

        if (recordings.length === 0) {
            list.innerHTML = '<div class="empty-tip">' +
                '<div class="icon">🎬</div>' +
                '<div>暂无录制文件</div>' +
                '<div style="margin-top:4px;font-size:11px">检测到人脸时将自动开始录制</div>' +
                '</div>';
            return;
        }

        var html = '';
        for (var i = 0; i < recordings.length; i++) {
            var rec = recordings[i];
            // 构建元数据信息
            var metaHtml = formatSize(rec.size) + ' · ' + formatDuration(rec.duration);

            // 人脸信息标签
            if (rec.maxTotal > 0) {
                metaHtml += ' · 👤' + rec.maxTotal;
            }
            if (rec.maxKnown > 0) {
                metaHtml += ' <span class="face-badge known">✓' + rec.maxKnown + '</span>';
            }
            if (rec.maxUnknown > 0) {
                metaHtml += ' <span class="face-badge unknown">✗' + rec.maxUnknown + '</span>';
            }
            if (rec.autoRecorded) {
                metaHtml += ' <span class="face-badge auto">自动</span>';
            }

            // 图标选择
            var icon = rec.autoRecorded ? '🤖' : '🎬';

            html += '<div class="recording-item">' +
                '<div class="recording-info">' +
                '<span class="recording-icon">' + icon + '</span>' +
                '<div>' +
                '<div class="recording-name">' + rec.name + '</div>' +
                '<div class="recording-meta">' + metaHtml + '</div>' +
                '</div></div>' +
                '<div class="recording-actions">' +
                '<button class="btn-sm btn-play" onclick="playRecording(' + i + ')">▶</button>' +
                '<button class="btn-sm btn-download-sm" onclick="downloadRecordingAt(' + i + ')">💾</button>' +
                '<button class="btn-sm btn-delete" onclick="deleteRecording(' + i + ')">✕</button>' +
                '</div></div>';
        }
        list.innerHTML = html;
    }

    function playRecording(idx) {
        var rec = recordings[idx];
        if (!rec) return;

        var modal = document.getElementById('previewModal');
        var body = document.getElementById('previewBody');
        var title = document.getElementById('previewTitle');

        // 构建标题（包含人脸信息）
        var titleText = '🎬 ' + rec.name;
        title.textContent = titleText;

        // 构建播放内容
        var contentHtml = '<video controls autoplay style="max-height:50vh;width:100%;border-radius:8px;background:#000">' +
            '<source src="' + rec.url + '" type="video/webm">' +
            '您的浏览器不支持播放此视频</video>';

        // 添加人脸检测摘要
        if (rec.maxTotal > 0) {
            contentHtml += '<div class="face-summary">';
            contentHtml += '👤 检测到 ' + rec.maxTotal + ' 张人脸　';
            if (rec.maxKnown > 0) {
                contentHtml += '<span class="known">✓ ' + rec.maxKnown + ' 熟人</span>　';
            }
            if (rec.maxUnknown > 0) {
                contentHtml += '<span class="unknown">✗ ' + rec.maxUnknown + ' 陌生人</span>';
            }
            if (rec.labels && rec.labels.length > 0) {
                contentHtml += '<br>识别: ' + rec.labels.join(', ');
            }
            contentHtml += '</div>';
        }

        body.innerHTML = contentHtml;
        modal.classList.add('active');
    }

    function downloadRecordingAt(idx) {
        var rec = recordings[idx];
        if (!rec) return;
        var a = document.createElement('a');
        a.href = rec.url;
        a.download = rec.name;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        showToast('💾 下载: ' + rec.name);
    }

    function deleteRecording(idx) {
        var rec = recordings[idx];
        if (!rec) return;
        URL.revokeObjectURL(rec.url);
        recordings.splice(idx, 1);
        updateRecordingsList();
        if (recordings.length === 0) {
            document.getElementById('btnDownload').disabled = true;
            lastRecordedBlob = null;
        }
        showToast('🗑️ 已删除');
    }

    function clearRecordings() {
        if (recordings.length === 0) return;
        if (!confirm('确定要清空所有录制文件吗？')) return;
        for (var i = 0; i < recordings.length; i++) {
            URL.revokeObjectURL(recordings[i].url);
        }
        recordings = [];
        lastRecordedBlob = null;
        document.getElementById('btnDownload').disabled = true;
        updateRecordingsList();
        showToast('🗑️ 已清空所有录制');
    }

    // ==================== 预览弹窗 ====================
    function closePreview() {
        var modal = document.getElementById('previewModal');
        var body = document.getElementById('previewBody');
        modal.classList.remove('active');
        // 停止视频播放
        var video = body.querySelector('video');
        if (video) { video.pause(); video.src = ''; }
        body.innerHTML = '';
    }

    // 点击遮罩关闭
    document.getElementById('previewModal').addEventListener('click', function(e) {
        if (e.target === this) closePreview();
    });

    // ESC 关闭
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') closePreview();
    });

    // ==================== 连接状态监测 ====================
    let reconnectTimer = null;
    streamImg.addEventListener('error', function() {
        document.getElementById('connStatus').textContent = '断开';
        document.getElementById('connStatus').style.color = '#ef4444';
        if (!reconnectTimer) {
            reconnectTimer = setInterval(function() {
                streamImg.src = '/stream?' + Date.now();
            }, 3000);
        }
    });

    streamImg.addEventListener('load', function() {
        if (reconnectTimer) {
            clearInterval(reconnectTimer);
            reconnectTimer = null;
        }
        // 注意：连接状态由状态轮询管理，这里只处理视频流重连
    });

    // ==================== WebSocket 音频播放 ====================
    const AUDIO_WS_PORT = 8002;  // WebSocket 音频端口
    const AUDIO_DEBUG_VERSION = 'audio-debug-20260608-2225-stable-fps';
    const AUDIO_GAIN = 1.0;
    const MAX_AUDIO_QUEUE_SECONDS = 2.8;
    let audioCtx = null;           // AudioContext 实例
    let audioScriptNode = null;     // PCM 播放节点
    let audioWs = null;             // WebSocket 连接
    let audioEnabled = false;       // 用户是否启用了音频
    let audioReconnectTimer = null; // 重连定时器
    let audioRetryCount = 0;        // 连续重试次数
    let audioSampleRate = 16000;
    let audioQueue = [];
    let audioQueuedSamples = 0;
    let currentAudioChunk = null;
    let currentAudioOffset = 0;
    let lastAudioPeak = 0;
    let highPassLastInput = 0;
    let highPassLastOutput = 0;

    function toggleAudio() {
        if (audioEnabled) {
            audioEnabled = false;
            stopAudioWebSocket();
            updateAudioUI();
            showToast('音频已关闭');
        } else {
            audioEnabled = true;
            startAudioPlayback();
            updateAudioUI();
        }
    }

    function updateAudioUI() {
        var btn = document.getElementById('btnAudio');
        var icon = document.getElementById('audioIcon');
        var text = document.getElementById('audioText');
        if (audioEnabled) {
            btn.classList.remove('muted');
            icon.textContent = 'ON';
            text.textContent = '播放中';
        } else {
            btn.classList.add('muted');
            icon.textContent = 'OFF';
            text.textContent = '点击开启';
        }
    }

    function startAudioPlayback() {
        if (!audioCtx) {
            try {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)({
                    sampleRate: audioSampleRate
                });
                createAudioOutputNode();
            } catch (err) {
                console.error('AudioContext 创建失败:', err);
                showToast('音频初始化失败');
                audioEnabled = false;
                updateAudioUI();
                return;
            }
        }

        if (!audioScriptNode) {
            createAudioOutputNode();
        }

        if (audioCtx.state === 'suspended') {
            audioCtx.resume().catch(function(err) {
                console.error('[音频] AudioContext resume 失败:', err);
            });
        }

        clearAudioQueue();
        connectAudioWebSocket();
    }

    function createAudioOutputNode() {
        if (!audioCtx || audioScriptNode) return;

        audioScriptNode = audioCtx.createScriptProcessor(2048, 0, 1);
        audioScriptNode.onaudioprocess = function(e) {
            var output = e.outputBuffer.getChannelData(0);
            for (var i = 0; i < output.length; i++) {
                if (!audioEnabled) {
                    output[i] = 0;
                    continue;
                }

                if (!currentAudioChunk || currentAudioOffset >= currentAudioChunk.length) {
                    currentAudioChunk = audioQueue.shift() || null;
                    currentAudioOffset = 0;
                    if (currentAudioChunk) {
                        audioQueuedSamples -= currentAudioChunk.length;
                    }
                }

                if (currentAudioChunk) {
                    output[i] = currentAudioChunk[currentAudioOffset++];
                } else {
                    output[i] = 0;
                }
            }
        };
        audioScriptNode.connect(audioCtx.destination);
        console.log('[音频] 输出节点已创建, ctx sampleRate=', audioCtx.sampleRate);
    }

    function clearAudioQueue() {
        audioQueue = [];
        audioQueuedSamples = 0;
        currentAudioChunk = null;
        currentAudioOffset = 0;
        lastAudioPeak = 0;
    }

    function resampleIfNeeded(samples, sourceRate, targetRate) {
        if (!targetRate || Math.abs(sourceRate - targetRate) < 1) return samples;

        var ratio = targetRate / sourceRate;
        var outLength = Math.max(1, Math.round(samples.length * ratio));
        var out = new Float32Array(outLength);
        for (var i = 0; i < outLength; i++) {
            var srcPos = i / ratio;
            var idx = Math.floor(srcPos);
            var frac = srcPos - idx;
            var s0 = samples[idx] || 0;
            var s1 = samples[idx + 1] || s0;
            out[i] = s0 + (s1 - s0) * frac;
        }
        return out;
    }

    function pushAudioChunk(samples) {
        audioQueue.push(samples);
        audioQueuedSamples += samples.length;

        var maxSamples = Math.floor((audioCtx ? audioCtx.sampleRate : audioSampleRate) * MAX_AUDIO_QUEUE_SECONDS);
        while (audioQueuedSamples > maxSamples && audioQueue.length > 1) {
            var dropped = audioQueue.shift();
            audioQueuedSamples -= dropped.length;
        }
    }

    function connectAudioWebSocket() {
        var ip = window.location.hostname;
        var wsUrl = 'ws://' + ip + ':' + AUDIO_WS_PORT;

        try {
            audioWs = new WebSocket(wsUrl);
            audioWs.binaryType = 'arraybuffer';

            audioWs.onopen = function() {
                audioRetryCount = 0;
                clearAudioQueue();
                document.getElementById('audioStatus').textContent = '已连接';
                document.getElementById('audioStatus').className = 'audio-status connected';
                console.log('[音频] WebSocket 已连接', AUDIO_DEBUG_VERSION);
            };

            audioWs.onmessage = function(event) {
                if (!audioEnabled) return;

                if (typeof event.data === 'string') {
                    try {
                        var info = JSON.parse(event.data);
                        if (info.sample_rate) audioSampleRate = info.sample_rate;
                        console.log('[音频] 收到参数:', info);
                    } catch (e) {}
                    return;
                }

                try {
                    var int16Array = new Int16Array(event.data);
                    var float32 = new Float32Array(int16Array.length);
                    var peak = 0;
                    for (var i = 0; i < int16Array.length; i++) {
                        var raw = int16Array[i] / 32768.0;
                        // 一阶高通去直流和低频底噪。
                        var hp = raw - highPassLastInput + 0.97 * highPassLastOutput;
                        highPassLastInput = raw;
                        highPassLastOutput = hp;

                        var sample = hp * AUDIO_GAIN;
                        // 轻微噪声门：小信号衰减，保留人声主体。
                        if (Math.abs(sample) < 0.018) {
                            sample *= 0.18;
                        }
                        // 软限幅减少爆音。
                        sample = Math.tanh(sample * 1.2) / Math.tanh(1.2);
                        sample = Math.max(-1, Math.min(1, sample));
                        float32[i] = sample;
                        var abs = Math.abs(sample);
                        if (abs > peak) peak = abs;
                    }
                    lastAudioPeak = peak;
                    float32 = resampleIfNeeded(float32, audioSampleRate, audioCtx ? audioCtx.sampleRate : audioSampleRate);
                    pushAudioChunk(float32);
                    document.getElementById('audioStatus').textContent = '已连接 ' + AUDIO_DEBUG_VERSION + ' 峰值 ' + peak.toFixed(3);
                } catch (e) {
                    console.error('[音频] PCM 处理失败:', e);
                }
            };

            audioWs.onclose = function() {
                document.getElementById('audioStatus').textContent = '已断开';
                document.getElementById('audioStatus').className = 'audio-status disconnected';
                console.log('[音频] WebSocket 已断开');

                if (audioEnabled) {
                    audioRetryCount++;
                    var delay = Math.min(audioRetryCount * 2, 10) * 1000;
                    audioReconnectTimer = setTimeout(function() {
                        connectAudioWebSocket();
                    }, delay);
                }
            };

            audioWs.onerror = function(err) {
                console.error('[音频] WebSocket 错误');
                audioWs.close();
            };

        } catch (err) {
            console.error('[音频] WebSocket 连接失败:', err);
            showToast('音频连接失败');
        }
    }

    function stopAudioWebSocket() {
        if (audioReconnectTimer) {
            clearTimeout(audioReconnectTimer);
            audioReconnectTimer = null;
        }
        if (audioWs) {
            audioWs.close();
            audioWs = null;
        }
        clearAudioQueue();
        document.getElementById('audioStatus').textContent = '未连接';
        document.getElementById('audioStatus').className = 'audio-status';
    }
    // 页面关闭时清理
    window.addEventListener('beforeunload', function() {
        stopAudioWebSocket();
        if (audioCtx) {
            audioCtx.close();
            audioCtx = null;
        }

    });
    </script>
</body>
</html>"""

        print("[推流] 推流管理器初始化完成")

    def _get_local_ip(self):
        """
        获取设备的本地 IP 地址

        返回：
            IP 地址字符串
        """
        try:
            w = network.wifi.Wifi()
            ip = w.get_ip()
            if ip and ip != "0.0.0.0":
                return ip
        except Exception as e:
            print(f"[推流] 获取 IP 失败: {e}")
        return "0.0.0.0"

    def start(self):
        """
        启动 HTTP JPEG 推流

        返回：
            True: 启动成功
            False: 启动失败
        """
        if self._is_streaming:
            print("[推流] 已在推流中")
            return True

        try:
            # 创建 HTTP JPEG 流服务器
            self._server = http.JpegStreamer()

            # 设置网页界面
            self._server.set_html(self._html)

            # 启动服务器
            self._server.start()

            # 获取推流地址（使用真实 IP）
            port = self._server.port()
            local_ip = self._get_local_ip()
            self._stream_url = f"http://{local_ip}:{port}"

            # 更新状态
            self._is_streaming = True

            print(f"[推流] HTTP 推流已启动")
            print(f"[推流] 推流地址: {self._stream_url}")
            print(f"[推流] 使用浏览器打开此地址查看")
            print(f"[推流] 支持功能: 录制视频 / 截图 / 下载")

            return True

        except Exception as e:
            print(f"[推流] 启动失败: {e}")
            self._cleanup()
            return False

    def write(self, img):
        """
        写入一帧图像进行推流

        参数：
            img: MaixPy Image 对象（带标注的画面）

        返回：
            True: 写入成功
            False: 写入失败或未推流
        """
        if not self._is_streaming or self._server is None:
            return False

        try:
            # 使用可配置的 JPEG 质量
            jpeg_img = img.to_jpeg(quality=self._jpeg_quality)
            self._server.write(jpeg_img)
            return True
        except Exception as e:
            # 如果转换失败，直接推流原始图像
            try:
                self._server.write(img)
            except:
                pass
            return False

    def stop(self):
        """
        停止 HTTP 推流

        返回：
            True: 停止成功
            False: 停止失败
        """
        if not self._is_streaming:
            return True

        try:
            self._cleanup()
            print("[推流] HTTP 推流已停止")
            return True

        except Exception as e:
            print(f"[推流] 停止失败: {e}")
            return False

    def _cleanup(self):
        """
        清理推流资源
        """
        self._server = None
        self._is_streaming = False
        self._stream_url = ""

    def is_streaming(self):
        """
        检查是否正在推流

        返回：
            True: 正在推流
            False: 未推流
        """
        return self._is_streaming

    def get_stream_url(self):
        """
        获取推流地址

        返回：
            HTTP 地址字符串，未推流时返回空字符串
        """
        return self._stream_url

    def destroy(self):
        """
        销毁推流管理器，释放资源
        """
        self.stop()
        print("[推流] 推流管理器已销毁")


class RtspStreamManager:
    """
    RTSP推流管理器

    功能：
    - 管理 RTSP 视频流服务器
    - 推流未经处理的原始画面（用于监控）
    - 支持 VLC/ffplay 播放

    注意事项：
    - RTSP模块只支持NV21格式（FMT_YVU420SP）
    - 绑定摄像头后，摄像头对象不能再被独立使用
    - RTSP服务启动后无法停止
    """

    def __init__(self):
        """
        初始化RTSP推流管理器
        """
        self._server = None
        self._cam = None
        self._audio_recorder = None
        self._is_streaming = False
        self._rtsp_url = ""

        print("[RTSP] RTSP推流管理器初始化完成")

    def _get_local_ip(self):
        """
        获取设备的本地 IP 地址

        返回：
            IP 地址字符串
        """
        try:
            w = network.wifi.Wifi()
            ip = w.get_ip()
            if ip and ip != "0.0.0.0":
                return ip
        except Exception as e:
            print(f"[RTSP] 获取 IP 失败: {e}")
        return "0.0.0.0"

    def start(self, width=640, height=480, enable_audio=True):
        """
        启动RTSP推流

        参数：
            width: 视频宽度
            height: 视频高度
            enable_audio: 是否启用音频推流

        返回：
            True: 启动成功
            False: 启动失败
        """
        if self._is_streaming:
            print("[RTSP] 已在推流中")
            return True

        try:
            from maix import rtsp, camera, image, audio

            # 创建独立的摄像头实例（YVU420SP格式）
            print(f"[RTSP] 初始化摄像头 ({width}x{height}, YVU420SP)...")
            self._cam = camera.Camera(width, height, image.Format.FMT_YVU420SP)

            # 创建RTSP服务器
            print("[RTSP] 创建RTSP服务器...")
            self._server = rtsp.Rtsp()

            # 绑定摄像头
            self._server.bind_camera(self._cam)

            # 绑定音频录制器（如果启用）
            if enable_audio:
                try:
                    print("[RTSP] 初始化音频录制器...")
                    self._audio_recorder = audio.Recorder()
                    self._server.bind_audio_recorder(self._audio_recorder)
                    print("[RTSP] 音频推流已启用")
                except Exception as e:
                    print(f"[RTSP] 音频初始化失败: {e}")
                    self._audio_recorder = None

            # 启动推流
            self._server.start()

            # 获取推流地址（从服务器获取，而不是自行拼接）
            self._rtsp_url = self._server.get_url()

            # 如果获取的地址包含0.0.0.0，尝试用真实IP替换
            if "0.0.0.0" in self._rtsp_url:
                real_ip = self._get_local_ip()
                if real_ip != "0.0.0.0":
                    self._rtsp_url = self._rtsp_url.replace("0.0.0.0", real_ip)

            # 更新状态
            self._is_streaming = True

            print("[RTSP] RTSP推流已启动")
            print(f"[RTSP] 播放地址: {self._rtsp_url}")
            print(f"[RTSP] VLC播放命令: vlc {self._rtsp_url}")
            print(f"[RTSP] ffplay播放命令: ffplay {self._rtsp_url}")

            return True

        except Exception as e:
            print(f"[RTSP] 启动失败: {e}")
            import traceback
            traceback.print_exc()
            self._cleanup()
            return False

    def is_streaming(self):
        """
        检查是否正在推流

        返回：
            True: 正在推流
            False: 未推流
        """
        return self._is_streaming

    def get_url(self):
        """
        获取RTSP推流地址

        返回：
            RTSP 地址字符串，未推流时返回空字符串
        """
        return self._rtsp_url

    def _cleanup(self):
        """
        清理推流资源
        """
        # 注意：RTSP没有stop方法，只能销毁引用
        self._audio_recorder = None
        self._cam = None
        self._server = None
        self._is_streaming = False
        self._rtsp_url = ""

    def destroy(self):
        """
        销毁RTSP推流管理器，释放资源
        """
        self._cleanup()
        print("[RTSP] RTSP推流管理器已销毁")







