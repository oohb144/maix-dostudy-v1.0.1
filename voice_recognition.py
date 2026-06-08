# -*- coding: utf-8 -*-
"""
MaixCAM2 人脸识别智能系统 - 语音识别模块

功能：
- 关键词识别（KWS）
- 语音命令解析
- 非阻塞运行

使用方法：
- 通过语音命令切换界面、控制功能
- 支持自定义关键词

关键词格式：
- 使用带声调数字的拼音格式
- 例如：'xiao3 ai4 tong2 xue2' 表示 '小爱同学'
"""

from maix import nn, app, time
import _thread


class VoiceRecognition:
    """
    语音识别器

    功能：
    - 使用 nn.Speech 进行关键词识别
    - 支持自定义关键词和回调函数
    - 非阻塞运行（独立线程）
    """

    def __init__(self, model_path="/root/models/am_3332_192_int8.mud"):
        """
        初始化语音识别器

        参数：
            model_path: 语音模型路径
        """
        self._model_path = model_path
        self._speech = None
        self._is_running = False
        self._keywords = {}
        self._callback = None
        self._lock = _thread.allocate_lock()

        # 默认关键词配置（拼音声调格式）
        self._default_keywords = {
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

        print("[语音] 语音识别模块初始化完成")

    def _init_speech(self):
        """
        初始化语音识别引擎

        返回：
            True: 初始化成功
            False: 初始化失败
        """
        try:
            self._speech = nn.Speech(self._model_path)
            self._speech.init(nn.SpeechDevice.DEVICE_MIC)
            print("[语音] 语音识别引擎初始化成功")
            return True
        except Exception as e:
            print(f"[语音] 语音识别引擎初始化失败: {e}")
            return False

    def set_keywords(self, keywords):
        """
        设置关键词

        参数：
            keywords: 关键词字典 {拼音: 命令名}
        """
        self._keywords = keywords
        print(f"[语音] 设置关键词: {len(keywords)} 个")

    def set_callback(self, callback):
        """
        设置识别回调函数

        参数：
            callback: 回调函数，接收命令名作为参数
        """
        self._callback = callback
        print("[语音] 设置识别回调函数")

    def start(self, keywords=None, callback=None):
        """
        启动语音识别

        参数：
            keywords: 关键词字典（可选）
            callback: 回调函数（可选）

        返回：
            True: 启动成功
            False: 启动失败
        """
        if self._is_running:
            print("[语音] 语音识别已在运行")
            return True

        # 设置关键词和回调
        if keywords:
            self.set_keywords(keywords)
        if callback:
            self.set_callback(callback)

        # 如果没有设置关键词，使用默认关键词
        if not self._keywords:
            self._keywords = self._default_keywords.copy()

        # 初始化语音引擎
        if not self._init_speech():
            return False

        # 启动识别线程
        try:
            self._is_running = True
            _thread.start_new_thread(self._recognition_thread, ())
            print("[语音] 语音识别已启动")
            print("[语音] 支持的关键词:")
            for pinyin, command in self._keywords.items():
                print(f"  - {pinyin} -> {command}")
            return True
        except Exception as e:
            print(f"[语音] 启动语音识别失败: {e}")
            self._is_running = False
            return False

    def _recognition_thread(self):
        """
        语音识别线程
        """
        print("[语音] 识别线程启动")

        # 构建关键词表和阈值
        kw_tbl = list(self._keywords.keys())
        kw_gate = [0.1] * len(kw_tbl)  # 每个关键词的置信度门限

        # 识别回调函数
        def on_recognize(data, length):
            """
            识别结果回调

            参数：
                data: 置信度列表
                length: 结果数量
            """
            with self._lock:
                for i in range(length):
                    if data[i] > kw_gate[i]:
                        keyword = kw_tbl[i]
                        command = self._keywords.get(keyword, 'unknown')
                        print(f"[语音] 识别到: {keyword} -> {command} (置信度: {data[i]:.3f})")

                        # 调用用户回调
                        if self._callback:
                            try:
                                self._callback(command)
                            except Exception as e:
                                print(f"[语音] 回调执行失败: {e}")

        # 启用关键词识别
        self._speech.kws(kw_tbl, kw_gate, on_recognize, True)

        # 运行识别循环
        while self._is_running and not app.need_exit():
            try:
                frames = self._speech.run(1)
                if frames < 1:
                    time.sleep_ms(10)
            except Exception as e:
                print(f"[语音] 识别循环异常: {e}")
                time.sleep_ms(100)

        print("[语音] 识别线程退出")

    def stop(self):
        """
        停止语音识别
        """
        if not self._is_running:
            return

        self._is_running = False
        print("[语音] 语音识别已停止")

    def is_running(self):
        """
        检查是否正在运行

        返回：
            True: 正在运行
            False: 未运行
        """
        return self._is_running

    def destroy(self):
        """
        销毁语音识别器
        """
        self.stop()
        self._speech = None
        print("[语音] 语音识别器已销毁")
