# -*- coding: utf-8 -*-
"""
MaixCAM2 人脸识别系统 - UI 页面定义

功能：
- 定义所有 UI 页面类
- 实现页面导航逻辑
- 整合触摸屏交互

页面结构：
- HomePage：主页，显示摄像头画面和功能入口
- SettingsPage：设置页，调节参数和功能开关
- EnrollPage：录入页，人脸录入管理
- RecordingsPage：录像页，录像文件管理
"""

from maix import image
import os
from config import STATE_NAMES, State
from ui import (Button, ButtonManager, Slider, SliderManager,
                Switch, SwitchManager, ResolutionAdapter, Page, UIManager,
                TouchKeyboard)


# ==================== 颜色常量 ====================
# 使用元组格式，由 UI 组件自动转换为 image.Color
C_WHITE = (255, 255, 255)
C_BLACK = (0, 0, 0)
C_RED = (200, 30, 30)
C_GREEN = (30, 200, 30)
C_BLUE = (0, 120, 220)
C_YELLOW = (220, 220, 30)
C_CYAN = (0, 200, 200)
C_GRAY = (100, 100, 100)
C_DARK_GRAY = (50, 50, 50)
C_LIGHT_GRAY = (180, 180, 180)

# 按钮颜色方案
BTN_PRIMARY = C_BLUE           # 主要按钮
BTN_PRIMARY_PRESSED = (0, 80, 160)  # 主要按钮按下
BTN_DANGER = C_RED             # 危险按钮
BTN_DANGER_PRESSED = (150, 20, 20)  # 危险按钮按下
BTN_SUCCESS = C_GREEN          # 成功按钮
BTN_SUCCESS_PRESSED = (20, 150, 20)  # 成功按钮按下
BTN_SECONDARY = C_GRAY        # 次要按钮
BTN_SECONDARY_PRESSED = (70, 70, 70)  # 次要按钮按下


# ==================== 子页面基类 ====================
class SubPage(Page):
    """
    通用子页面基类

    封装了返回按钮的处理逻辑，所有需要返回按钮的页面都应继承此类。
    """

    def __init__(self, ui_manager, ts, disp, adapter, on_back_callback=None):
        """
        初始化子页面

        参数：
            ui_manager: UIManager 实例
            ts: 触摸屏实例
            disp: 显示器实例
            adapter: ResolutionAdapter 实例
            on_back_callback: 返回按钮点击时的额外回调函数
        """
        super().__init__(ui_manager)
        self._ts = ts
        self._disp = disp
        self._adapter = adapter
        self._on_back_callback = on_back_callback

        # 创建返回按钮（640×480 图像坐标）
        self._back_btn = Button(
            rect=[10, 10, 70, 50],
            label='<',
            callback=self._on_back_click,
            bg_color=C_DARK_GRAY,
            pressed_color=C_GRAY,
            text_color=C_WHITE,
            border_thickness=1,
            text_scale=1.5
        )
        self._back_btn_manager = ButtonManager(ts, disp)
        self._back_btn_manager.add_button(self._back_btn)

    def _on_back_click(self):
        """返回按钮点击处理"""
        # 先执行额外的回调（如果有）
        if self._on_back_callback:
            self._on_back_callback()
        # 再弹出页面
        self.ui_manager.pop()

    def handle_back_button(self, img):
        """
        处理和绘制返回按钮

        参数：
            img: 图像对象
        """
        self._back_btn_manager.handle_events(img)

    def draw_title(self, img, title):
        """
        绘制页面标题

        参数：
            img: 图像对象
            title: 标题文字
        """
        img.draw_string(100, 18, title,
                       color=image.Color.from_rgb(*C_WHITE),
                       scale=2.0)


# ==================== 主页 ====================
class HomePage(Page):
    """
    主页

    功能：
    - 显示摄像头实时画面 + 人脸框
    - 显示系统状态信息
    - 提供功能入口按钮
    """

    def __init__(self, ui_manager, ts, disp, adapter, app_state):
        """
        初始化主页

        参数：
            ui_manager: UIManager 实例
            ts: 触摸屏实例
            disp: 显示器实例
            adapter: ResolutionAdapter 实例
            app_state: 应用状态字典
        """
        super().__init__(ui_manager)
        self._ts = ts
        self._disp = disp
        self._adapter = adapter
        self._app_state = app_state

        # 创建按钮管理器
        self._btn_manager = ButtonManager(ts, disp)

        # 按钮布局（640×480 图像坐标）：5个按钮底部横排
        btn_w, btn_h = 110, 80
        btn_y = 385
        btn_spacing = 8
        total_w = 5 * btn_w + 4 * btn_spacing
        start_x = (640 - total_w) // 2

        # 创建功能按钮
        self._btn_recognize = Button(
            rect=[start_x, btn_y, btn_w, btn_h],
            label='识别',
            callback=None,
            bg_color=BTN_PRIMARY,
            pressed_color=BTN_PRIMARY_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.5
        )

        self._btn_enroll = Button(
            rect=[start_x + btn_w + btn_spacing, btn_y, btn_w, btn_h],
            label='录入',
            callback=None,
            bg_color=BTN_SUCCESS,
            pressed_color=BTN_SUCCESS_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.5
        )

        self._btn_settings = Button(
            rect=[start_x + 2 * (btn_w + btn_spacing), btn_y, btn_w, btn_h],
            label='设置',
            callback=None,
            bg_color=BTN_SECONDARY,
            pressed_color=BTN_SECONDARY_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.5
        )

        self._btn_record = Button(
            rect=[start_x + 3 * (btn_w + btn_spacing), btn_y, btn_w, btn_h],
            label='录制',
            callback=None,
            bg_color=BTN_DANGER,
            pressed_color=BTN_DANGER_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.5
        )

        self._btn_fusion = Button(
            rect=[start_x + 4 * (btn_w + btn_spacing), btn_y, btn_w, btn_h],
            label='融合',
            callback=None,
            bg_color=BTN_SUCCESS,
            pressed_color=BTN_SUCCESS_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.5
        )

        # 添加按钮到管理器
        self._btn_manager.add_button(self._btn_recognize)
        self._btn_manager.add_button(self._btn_enroll)
        self._btn_manager.add_button(self._btn_settings)
        self._btn_manager.add_button(self._btn_record)
        self._btn_manager.add_button(self._btn_fusion)

        # 语音识别开关按钮（右上角，独立管理器，避免与底部按钮布局冲突）
        self._btn_voice = Button(
            rect=[490, 4, 144, 30],
            label='语音:关',
            callback=None,
            bg_color=C_GRAY,
            pressed_color=C_DARK_GRAY,
            text_color=C_WHITE,
            border_thickness=1,
            text_scale=1.0
        )
        self._voice_btn_manager = ButtonManager(ts, disp)
        self._voice_btn_manager.add_button(self._btn_voice)

        # 自动录制开关按钮（右上角，语音按钮左侧）
        self._btn_auto_record = Button(
            rect=[340, 4, 144, 30],
            label='自动录制:开',
            callback=None,
            bg_color=image.Color.from_rgb(*C_GREEN),
            pressed_color=C_DARK_GRAY,
            text_color=C_WHITE,
            border_thickness=1,
            text_scale=1.0
        )
        self._auto_record_btn_manager = ButtonManager(ts, disp)
        self._auto_record_btn_manager.add_button(self._btn_auto_record)

    def set_callbacks(self, on_recognize, on_enroll, on_settings, on_record, on_fusion,
                      on_voice_toggle=None, on_auto_record_toggle=None):
        """设置按钮回调函数"""
        self._btn_recognize.callback = on_recognize
        self._btn_enroll.callback = on_enroll
        self._btn_settings.callback = on_settings
        self._btn_record.callback = on_record
        self._btn_fusion.callback = on_fusion
        self._btn_voice.callback = on_voice_toggle
        self._btn_auto_record.callback = on_auto_record_toggle

    def update(self, img):
        """主页更新逻辑（640×480 图像坐标）"""
        # 顶部状态栏
        img.draw_rect(0, 0, img.width(), 38,
                     color=image.Color.from_rgb(*C_BLACK), thickness=-1)

        current_state = self._app_state.state
        state_name = STATE_NAMES.get(current_state, '未知')

        img.draw_string(6, 8, f'状态:{state_name}',
                       color=image.Color.from_rgb(*C_WHITE),
                       scale=1.2)

        face_count = self._app_state.face_count
        img.draw_string(200, 8, f'录入:{face_count}人',
                       color=image.Color.from_rgb(*C_GREEN),
                       scale=1.2)

        # 动态更新语音按钮外观
        voice_active = getattr(self._app_state, 'voice_recognition_active', False)
        self._btn_voice.label = '语音:开' if voice_active else '语音:关'
        self._btn_voice.bg_color = image.Color.from_rgb(*C_GREEN) if voice_active else image.Color.from_rgb(*C_GRAY)

        # 动态更新自动录制按钮外观
        auto_record_on = getattr(self._app_state, 'auto_record_enable', True)
        self._btn_auto_record.label = '自动录制:开' if auto_record_on else '自动录制:关'
        self._btn_auto_record.bg_color = image.Color.from_rgb(*C_GREEN) if auto_record_on else image.Color.from_rgb(*C_GRAY)

        # 处理语音按钮事件（放在状态栏内）
        self._voice_btn_manager.handle_events(img)
        # 处理自动录制按钮事件
        self._auto_record_btn_manager.handle_events(img)

        # 底部信息栏
        img.draw_rect(0, img.height() - 30, img.width(), 30,
                     color=image.Color.from_rgb(*C_BLACK), thickness=-1)

        if current_state in (State.RECORDING, State.MANUAL_RECORDING):
            duration = self._app_state.record_duration
            img.draw_string(6, img.height() - 24, f'● 录制中 {duration}s',
                           color=image.Color.from_rgb(*C_RED),
                           scale=1.1)

        if self._app_state.rtsp_enable:
            rtsp_url = self._app_state.rtsp_url
            if rtsp_url:
                img.draw_string(6, img.height() - 24, f'RTSP:{rtsp_url}',
                               color=image.Color.from_rgb(*C_GREEN),
                               scale=0.9)

        # 处理底部功能按钮事件
        self._btn_manager.handle_events(img)


# ==================== 设置页 ====================
class SettingsPage(SubPage):
    """
    设置页

    功能：
    - 调节检测参数（阈值）
    - 控制功能开关（推流、音频、LED）
    - 保存/加载配置
    - 支持触摸滚动查看所有设置项
    """

    def __init__(self, ui_manager, ts, disp, adapter, app_state):
        """
        初始化设置页

        参数：
            ui_manager: UIManager 实例
            ts: 触摸屏实例
            disp: 显示器实例
            adapter: ResolutionAdapter 实例
            app_state: 应用状态字典
        """
        super().__init__(ui_manager, ts, disp, adapter)
        self._app_state = app_state

        # 滚动相关
        self._scroll_y = 0
        self._max_scroll = 360
        self._last_touch_y = 0
        self._is_dragging = False

        # 创建滑块管理器
        self._slider_manager = SliderManager(ts, disp)

        # 检测阈值滑块（640×480 坐标）
        self._slider_conf = Slider(
            rect=[60, 120, 520, 40],
            label='检测阈值',
            min_val=10,
            max_val=90,
            default_val=int(app_state.conf_threshold * 100),
            scale=1.0,
            callback=lambda v: self._on_conf_threshold_change(v)
        )

        # 识别阈值滑块
        self._slider_recognize = Slider(
            rect=[60, 220, 520, 40],
            label='识别阈值',
            min_val=10,
            max_val=90,
            default_val=int(app_state.recognize_threshold * 100),
            scale=1.0,
            callback=lambda v: self._on_recognize_threshold_change(v)
        )

        self._slider_manager.add_slider(self._slider_conf)
        self._slider_manager.add_slider(self._slider_recognize)

        # 创建开关管理器
        self._switch_manager = SwitchManager(ts, disp)

        self._switch_stream = Switch(
            position=[60, 310],
            scale=2.0,
            is_on=app_state.stream_enable,
            callback=lambda v: self._on_stream_toggle(v),
            on_color=C_GREEN,
            off_color=C_GRAY
        )

        self._switch_rtsp = Switch(
            position=[60, 390],
            scale=2.0,
            is_on=app_state.rtsp_enable,
            callback=lambda v: self._on_rtsp_toggle(v),
            on_color=C_GREEN,
            off_color=C_GRAY
        )

        self._switch_audio = Switch(
            position=[60, 470],
            scale=2.0,
            is_on=app_state.audio_enable,
            callback=lambda v: self._on_audio_toggle(v),
            on_color=C_GREEN,
            off_color=C_GRAY
        )

        self._switch_led = Switch(
            position=[60, 550],
            scale=2.0,
            is_on=app_state.led_enable,
            callback=lambda v: self._on_led_toggle(v),
            on_color=C_GREEN,
            off_color=C_GRAY
        )

        self._switch_manager.add_switch(self._switch_stream)
        self._switch_manager.add_switch(self._switch_rtsp)
        self._switch_manager.add_switch(self._switch_audio)
        self._switch_manager.add_switch(self._switch_led)

        # 创建按钮管理器
        self._btn_manager = ButtonManager(ts, disp)

        self._btn_reset = Button(
            rect=[60, 640, 230, 70],
            label='恢复默认',
            callback=lambda: self._on_reset(),
            bg_color=BTN_SECONDARY,
            pressed_color=BTN_SECONDARY_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.3
        )

        self._btn_save = Button(
            rect=[350, 640, 230, 70],
            label='保存设置',
            callback=lambda: self._on_save(),
            bg_color=BTN_PRIMARY,
            pressed_color=BTN_PRIMARY_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.3
        )

        self._btn_exit = Button(
            rect=[60, 730, 520, 70],
            label='退出程序',
            callback=lambda: self._on_exit(),
            bg_color=BTN_DANGER,
            pressed_color=BTN_DANGER_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.3
        )

        self._btn_manager.add_button(self._btn_reset)
        self._btn_manager.add_button(self._btn_save)
        self._btn_manager.add_button(self._btn_exit)

    def _on_conf_threshold_change(self, value):
        """检测阈值变化回调"""
        self._app_state.conf_threshold = value / 100.0

    def _on_recognize_threshold_change(self, value):
        """识别阈值变化回调"""
        self._app_state.recognize_threshold = value / 100.0

    def _on_stream_toggle(self, is_on):
        """推流开关切换回调"""
        self._app_state.stream_enable = is_on

    def _on_rtsp_toggle(self, is_on):
        """RTSP 推流开关切换回调"""
        self._app_state.rtsp_enable = is_on

    def _on_audio_toggle(self, is_on):
        """音频开关切换回调"""
        self._app_state.audio_enable = is_on

    def _on_led_toggle(self, is_on):
        """LED 开关切换回调"""
        self._app_state.led_enable = is_on

    def _on_reset(self):
        """恢复默认设置"""
        self._app_state.conf_threshold = 0.3
        self._app_state.recognize_threshold = 0.6
        self._app_state.stream_enable = True
        self._app_state.rtsp_enable = False
        self._app_state.audio_enable = False
        self._app_state.led_enable = False

        # 更新 UI 组件
        self._slider_conf.value = 30
        self._slider_recognize.value = 60
        self._switch_stream.is_on = True
        self._switch_rtsp.is_on = False
        self._switch_audio.is_on = False
        self._switch_led.is_on = False

    def _on_save(self):
        """保存设置"""
        self._app_state.need_save = True

    def _on_exit(self):
        """退出程序"""
        from maix import app
        print("[设置] 用户点击退出程序按钮")
        app.set_exit_flag(True)

    def update(self, img):
        """设置页更新逻辑（640×480 坐标）"""
        self._switch_stream.is_on = self._app_state.stream_enable
        self._switch_rtsp.is_on = self._app_state.rtsp_enable
        self._switch_audio.is_on = self._app_state.audio_enable
        self._switch_led.is_on = self._app_state.led_enable

        self.handle_back_button(img)
        self.draw_title(img, '系统设置')
        self._handle_scroll()
        self._update_component_positions()

        # 开关标签
        y_stream = 320 - self._scroll_y
        if 80 < y_stream < img.height() - 80:
            img.draw_string(180, y_stream + 10, 'HTTP 推流',
                           color=image.Color.from_rgb(*C_WHITE), scale=1.5)

        y_rtsp = 400 - self._scroll_y
        if 80 < y_rtsp < img.height() - 80:
            img.draw_string(180, y_rtsp + 10, 'RTSP 推流',
                           color=image.Color.from_rgb(*C_WHITE), scale=1.5)

        y_audio = 480 - self._scroll_y
        if 80 < y_audio < img.height() - 80:
            img.draw_string(180, y_audio + 10, '音频提示',
                           color=image.Color.from_rgb(*C_WHITE), scale=1.5)

        y_led = 560 - self._scroll_y
        if 80 < y_led < img.height() - 80:
            img.draw_string(180, y_led + 10, 'LED 指示',
                           color=image.Color.from_rgb(*C_WHITE), scale=1.5)

        self._slider_manager.handle_events(img)
        self._switch_manager.handle_events(img)
        self._btn_manager.handle_events(img)
        self._draw_scrollbar(img)

    def _update_component_positions(self):
        """更新组件位置（应用滚动偏移）"""
        y_conf = 120 - self._scroll_y
        y_recognize = 220 - self._scroll_y
        y_stream = 310 - self._scroll_y
        y_rtsp = 390 - self._scroll_y
        y_audio = 470 - self._scroll_y
        y_led = 550 - self._scroll_y
        y_btn = 640 - self._scroll_y
        y_exit = 730 - self._scroll_y

        self._slider_conf.rect = [60, y_conf, 520, 40]
        self._slider_recognize.rect = [60, y_recognize, 520, 40]

        self._switch_stream.pos = [60, y_stream]
        self._switch_stream.rect = [60, y_stream, self._switch_stream.width, self._switch_stream.height]
        self._switch_rtsp.pos = [60, y_rtsp]
        self._switch_rtsp.rect = [60, y_rtsp, self._switch_rtsp.width, self._switch_rtsp.height]
        self._switch_audio.pos = [60, y_audio]
        self._switch_audio.rect = [60, y_audio, self._switch_audio.width, self._switch_audio.height]
        self._switch_led.pos = [60, y_led]
        self._switch_led.rect = [60, y_led, self._switch_led.width, self._switch_led.height]

        self._btn_reset.rect = [60, y_btn, 230, 70]
        self._btn_save.rect = [350, y_btn, 230, 70]
        self._btn_exit.rect = [60, y_exit, 520, 70]

    def _handle_scroll(self):
        """处理触摸滚动"""
        try:
            x, y, pressed = self._ts.read()
            if pressed:
                if not self._is_dragging:
                    if 80 < y < 760:
                        self._is_dragging = True
                        self._last_touch_y = y
                else:
                    delta = self._last_touch_y - y
                    self._scroll_y = max(0, min(self._max_scroll, self._scroll_y + delta))
                    self._last_touch_y = y
            else:
                self._is_dragging = False
        except Exception:
            pass

    def _draw_scrollbar(self, img):
        """绘制滚动条"""
        if self._max_scroll <= 0:
            return
        bar_x = img.width() - 14
        bar_y = 80
        bar_height = img.height() - 140
        bar_width = 8
        img.draw_rect(bar_x, bar_y, bar_width, bar_height,
                     color=image.Color.from_rgb(*C_DARK_GRAY), thickness=-1)
        thumb_height = max(40, int(bar_height * bar_height / (bar_height + self._max_scroll)))
        thumb_y = bar_y + int((bar_height - thumb_height) * (self._scroll_y / self._max_scroll))
        img.draw_rect(bar_x, thumb_y, bar_width, thumb_height,
                     color=image.Color.from_rgb(*C_GRAY), thickness=-1)


# ==================== 录入页 ====================
class EnrollPage(SubPage):
    """
    录入页

    功能：
    - 显示摄像头画面
    - 检测并显示人脸
    - 执行人脸录入操作
    """

    def __init__(self, ui_manager, ts, disp, adapter, app_state, on_back_callback=None):
        """
        初始化录入页

        参数：
            ui_manager: UIManager 实例
            ts: 触摸屏实例
            disp: 显示器实例
            adapter: ResolutionAdapter 实例
            app_state: 应用状态字典
            on_back_callback: 返回按钮点击时的额外回调函数
        """
        super().__init__(ui_manager, ts, disp, adapter, on_back_callback)
        self._app_state = app_state

        # 键盘状态
        self._keyboard = None          # 活跃时为 TouchKeyboard 实例
        self._on_enroll_with_name = None  # 带名字的录入回调（由 set_callbacks 设置）

        self._btn_manager = ButtonManager(ts, disp)

        # 录入按钮（640×480 坐标）
        self._btn_enroll = Button(
            rect=[60, 360, 150, 70],
            label='录入',
            callback=None,
            bg_color=BTN_SUCCESS,
            pressed_color=BTN_SUCCESS_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.5
        )

        self._btn_delete = Button(
            rect=[245, 360, 150, 70],
            label='删除',
            callback=None,
            bg_color=BTN_DANGER,
            pressed_color=BTN_DANGER_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.5
        )

        self._btn_clear = Button(
            rect=[430, 360, 150, 70],
            label='清空',
            callback=None,
            bg_color=BTN_DANGER,
            pressed_color=BTN_DANGER_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.5
        )

        self._btn_manager.add_button(self._btn_enroll)
        self._btn_manager.add_button(self._btn_delete)
        self._btn_manager.add_button(self._btn_clear)

    def set_callbacks(self, on_enroll, on_delete, on_clear):
        """
        设置按钮回调函数

        参数：
            on_enroll: 带 name 参数的录入回调 on_enroll(name: str)
            on_delete: 删除按钮回调
            on_clear: 清空按钮回调
        """
        self._on_enroll_with_name = on_enroll
        # 录入按钮触发键盘弹出，不直接调用业务回调
        self._btn_enroll.callback = self._open_keyboard
        self._btn_delete.callback = on_delete
        self._btn_clear.callback = on_clear

    def _open_keyboard(self):
        """弹出软键盘让用户输入姓名，同时锁住当前人脸缓存帧"""
        if self._app_state.has_face:
            self._app_state.keyboard_active = True  # 锁住 _cached_img/_cached_faces
            self._keyboard = TouchKeyboard(self._ts, self._disp, initial_text='')

    def update(self, img):
        """录入页更新逻辑（640×480 坐标）"""
        self.handle_back_button(img)
        self.draw_title(img, '人脸录入')

        has_face = self._app_state.has_face
        if has_face:
            img.draw_string(60, 80, '检测到人脸，点击录入',
                           color=image.Color.from_rgb(*C_GREEN), scale=1.5)
        else:
            img.draw_string(60, 80, '请正对摄像头',
                           color=image.Color.from_rgb(*C_YELLOW), scale=1.5)

        current_state = self._app_state.state
        state_name = STATE_NAMES.get(current_state, 'UNKNOWN')
        img.draw_string(440, 18, f'S:{state_name}',
                       color=image.Color.from_rgb(*C_GRAY), scale=1.0)

        face_list = self._app_state.face_list
        img.draw_string(60, 130, f'已录入 ({len(face_list)}):',
                       color=image.Color.from_rgb(*C_WHITE), scale=1.3)

        for i, name in enumerate(face_list[:7]):
            img.draw_string(60, 175 + i * 26, f'• {name}',
                           color=image.Color.from_rgb(*C_LIGHT_GRAY), scale=1.1)

        if len(face_list) > 7:
            img.draw_string(60, 175 + 7 * 26, f'... 还有 {len(face_list) - 7} 人',
                           color=image.Color.from_rgb(*C_GRAY), scale=1.0)

        # 键盘激活时叠加绘制，不响应底层按钮
        if self._keyboard is not None:
            done, text = self._keyboard.handle_events(img)
            if done is True:
                # 用户确认，执行录入
                name = text.strip()
                if not name:
                    name = None  # 空名字由业务层生成默认名
                self._keyboard = None
                self._app_state.keyboard_active = False  # 解锁缓存
                if self._on_enroll_with_name:
                    self._on_enroll_with_name(name)
            elif done is False:
                # 用户取消
                self._keyboard = None
                self._app_state.keyboard_active = False  # 解锁缓存
        else:
            self._btn_manager.handle_events(img)


# ==================== 录像页 ====================
class RecordingsPage(SubPage):
    """
    录像页

    功能：
    - 显示录像文件列表
    - 管理录像文件
    """

    def __init__(self, ui_manager, ts, disp, adapter, app_state):
        """
        初始化录像页

        参数：
            ui_manager: UIManager 实例
            ts: 触摸屏实例
            disp: 显示器实例
            adapter: ResolutionAdapter 实例
            app_state: 应用状态字典
        """
        super().__init__(ui_manager, ts, disp, adapter)
        self._app_state = app_state

        self._btn_manager = ButtonManager(ts, disp)

        # 刷新按钮（640×480 坐标）
        self._btn_refresh = Button(
            rect=[60, 390, 150, 70],
            label='刷新',
            callback=None,
            bg_color=BTN_PRIMARY,
            pressed_color=BTN_PRIMARY_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.5
        )

        self._btn_delete = Button(
            rect=[245, 390, 150, 70],
            label='删除',
            callback=None,
            bg_color=BTN_DANGER,
            pressed_color=BTN_DANGER_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.5
        )

        self._btn_clear = Button(
            rect=[430, 390, 150, 70],
            label='清空',
            callback=None,
            bg_color=BTN_DANGER,
            pressed_color=BTN_DANGER_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.5
        )

        self._btn_manager.add_button(self._btn_refresh)
        self._btn_manager.add_button(self._btn_delete)
        self._btn_manager.add_button(self._btn_clear)

    def set_callbacks(self, on_refresh, on_delete, on_clear):
        """设置按钮回调函数"""
        self._btn_refresh.callback = on_refresh
        self._btn_delete.callback = on_delete
        self._btn_clear.callback = on_clear

    def update(self, img):
        """录像页更新逻辑（640×480 坐标）"""
        self.handle_back_button(img)
        self.draw_title(img, '录像管理')

        recordings = self._app_state.recordings
        img.draw_string(60, 80, f'录像文件 ({len(recordings)}):',
                       color=image.Color.from_rgb(*C_WHITE), scale=1.3)

        for i, rec in enumerate(recordings[:8]):
            name = rec.get('name', 'unknown')
            size = rec.get('size', 0)
            size_str = f'{size / 1024 / 1024:.1f}MB' if size > 1024*1024 else f'{size / 1024:.1f}KB'
            av_size = rec.get('av_size', 0)
            audio_size = rec.get('audio_size', 0)
            if av_size > 0:
                mark = '+AV'
            elif audio_size > 0:
                mark = '+WAV'
            else:
                mark = ''
            img.draw_string(60, 115 + i * 32, f'{name} {size_str} {mark}',
                           color=image.Color.from_rgb(*C_LIGHT_GRAY), scale=1.0)

        if len(recordings) == 0:
            img.draw_string(60, 115, '暂无录像文件',
                           color=image.Color.from_rgb(*C_GRAY), scale=1.3)

        self._btn_manager.handle_events(img)


# ==================== 融合播放页 ====================
class FusionPlayerPage(SubPage):
    '''
    融合播放页

    功能：
    - 读取原始录像与已融合视频列表
    - 手动触发 MP4/WAV 融合
    - 选择已融合视频播放/删除
    - 支持翻页浏览
    '''

    ITEMS_PER_PAGE = 5  # 每页显示条数
    ITEM_H = 52         # 每条目高度
    LIST_TOP = 110      # 列表起始 Y

    def __init__(self, ui_manager, ts, disp, adapter, app_state):
        '''初始化融合播放页'''
        super().__init__(ui_manager, ts, disp, adapter)
        self._app_state = app_state
        self._selected_index = 0   # 全局选中索引
        self._page = 0             # 当前页
        self._last_touch_pressed = False
        self._status_text = '等待读取'

        self._btn_manager = ButtonManager(ts, disp)

        # 第一行按钮：读取 / 融合 / 播放（各120宽，间距20）
        self._btn_refresh = Button(
            rect=[30, 390, 130, 60],
            label='读取',
            callback=None,
            bg_color=BTN_PRIMARY,
            pressed_color=BTN_PRIMARY_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.4
        )
        self._btn_mux = Button(
            rect=[180, 390, 130, 60],
            label='融合',
            callback=None,
            bg_color=BTN_SUCCESS,
            pressed_color=BTN_SUCCESS_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.4
        )
        self._btn_play = Button(
            rect=[330, 390, 130, 60],
            label='播放',
            callback=None,
            bg_color=BTN_SUCCESS,
            pressed_color=BTN_SUCCESS_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.4
        )
        self._btn_delete = Button(
            rect=[480, 390, 130, 60],
            label='删除',
            callback=self._on_delete_click,
            bg_color=BTN_DANGER,
            pressed_color=BTN_DANGER_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.4
        )

        # 翻页按钮（右上角，返回按钮右侧）
        self._btn_prev = Button(
            rect=[460, 10, 80, 50],
            label='< 上页',
            callback=self._on_prev_page,
            bg_color=BTN_SECONDARY,
            pressed_color=BTN_SECONDARY_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=0.9
        )
        self._btn_next = Button(
            rect=[550, 10, 80, 50],
            label='下页 >',
            callback=self._on_next_page,
            bg_color=BTN_SECONDARY,
            pressed_color=BTN_SECONDARY_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=0.9
        )

        self._btn_manager.add_button(self._btn_refresh)
        self._btn_manager.add_button(self._btn_mux)
        self._btn_manager.add_button(self._btn_play)
        self._btn_manager.add_button(self._btn_delete)
        self._btn_manager.add_button(self._btn_prev)
        self._btn_manager.add_button(self._btn_next)

    def set_callbacks(self, on_refresh, on_mux, on_play):
        '''设置按钮回调函数'''
        self._btn_refresh.callback = on_refresh
        self._btn_mux.callback = on_mux
        self._btn_play.callback = on_play

    def set_status(self, text):
        '''设置页面状态提示'''
        self._status_text = text

    def get_selected_index(self):
        '''获取当前选中的全局索引'''
        return self._selected_index

    def _on_prev_page(self):
        '''上一页'''
        if self._page > 0:
            self._page -= 1

    def _on_next_page(self):
        '''下一页'''
        muxed = self._app_state.muxed_videos
        max_page = max(0, (len(muxed) - 1) // self.ITEMS_PER_PAGE)
        if self._page < max_page:
            self._page += 1

    def _on_delete_click(self):
        '''删除选中的融合视频文件'''
        muxed = self._app_state.muxed_videos
        if not muxed or self._selected_index >= len(muxed):
            self._status_text = '无可删除项'
            return
        item = muxed[self._selected_index]
        deleted = []
        try:
            for key in ('av_path', 'path', 'audio_path'):
                p = item.get(key, '')
                if p and os.path.exists(p):
                    os.remove(p)
                    deleted.append(p)
            self._status_text = f'已删除 {len(deleted)} 个文件'
        except Exception as e:
            self._status_text = f'删除失败: {e}'
        # 刷新列表
        items = self._app_state.fusion_items
        try:
            items = [i for i in items if i.get('av_path') != item.get('av_path')]
        except Exception:
            pass
        self._app_state.fusion_items = items
        self._app_state.muxed_videos = [i for i in items if i.get('av_size', 0) > 0]
        # 调整选中位置
        if self._selected_index >= len(self._app_state.muxed_videos):
            self._selected_index = max(0, len(self._app_state.muxed_videos) - 1)
        max_page = max(0, (len(self._app_state.muxed_videos) - 1) // self.ITEMS_PER_PAGE)
        if self._page > max_page:
            self._page = max_page

    def _handle_list_touch(self, img):
        '''处理列表项触摸选择'''
        try:
            x, y, pressed = self._ts.read()
            img_w, img_h = img.width(), img.height()
            disp_w, disp_h = self._disp.width(), self._disp.height()
            if disp_w > 0 and disp_h > 0:
                tx = int(x * img_w / disp_w)
                ty = int(y * img_h / disp_h)
            else:
                tx, ty = x, y
            if pressed and not self._last_touch_pressed:
                list_bottom = self.LIST_TOP + self.ITEMS_PER_PAGE * self.ITEM_H
                if 20 <= tx <= 620 and self.LIST_TOP <= ty <= list_bottom:
                    row = (ty - self.LIST_TOP) // self.ITEM_H
                    global_idx = self._page * self.ITEMS_PER_PAGE + row
                    muxed = self._app_state.muxed_videos
                    if 0 <= global_idx < len(muxed):
                        self._selected_index = global_idx
            self._last_touch_pressed = pressed
        except Exception:
            pass

    def update(self, img):
        '''更新融合播放页（640×480 坐标）'''
        self.handle_back_button(img)
        self.draw_title(img, '融合播放')
        self._handle_list_touch(img)

        muxed = self._app_state.muxed_videos
        total = len(muxed)
        max_page = max(0, (total - 1) // self.ITEMS_PER_PAGE) if total > 0 else 0

        # 统计行
        raw_count = len(self._app_state.fusion_items)
        img.draw_string(30, 68, f'原始:{raw_count}  已融合:{total}  第{self._page+1}/{max_page+1}页',
                       color=image.Color.from_rgb(*C_WHITE), scale=1.1)
        img.draw_string(30, 90, self._status_text,
                       color=image.Color.from_rgb(*C_YELLOW), scale=1.0)

        # 列表区背景
        img.draw_rect(20, self.LIST_TOP - 4, 600, self.ITEMS_PER_PAGE * self.ITEM_H + 8,
                     color=image.Color.from_rgb(*C_DARK_GRAY), thickness=-1)

        # 列表项
        start = self._page * self.ITEMS_PER_PAGE
        page_items = muxed[start:start + self.ITEMS_PER_PAGE]
        for i, item in enumerate(page_items):
            global_idx = start + i
            y = self.LIST_TOP + i * self.ITEM_H
            # 选中高亮
            bg = (0, 80, 160) if global_idx == self._selected_index else (40, 40, 40)
            img.draw_rect(22, y, 596, self.ITEM_H - 2,
                         color=image.Color.from_rgb(*bg), thickness=-1)
            name = item.get('av_name') or item.get('name', 'unknown')
            size = item.get('av_size', 0)
            size_str = f'{size/1024/1024:.1f}MB' if size > 1024*1024 else f'{size/1024:.1f}KB'
            marker = '▶ ' if global_idx == self._selected_index else '  '
            img.draw_string(30, y + 14, f'{marker}{global_idx+1}. {name}  {size_str}',
                           color=image.Color.from_rgb(*C_WHITE), scale=1.0)

        if total == 0:
            img.draw_string(30, self.LIST_TOP + 20, '暂无融合视频，点击融合生成',
                           color=image.Color.from_rgb(*C_GRAY), scale=1.1)

        # 操作按钮行（4个横排，列表下方）
        self._btn_refresh.rect = [30,  400, 120, 55]
        self._btn_mux.rect     = [170, 400, 120, 55]
        self._btn_play.rect    = [310, 400, 120, 55]
        self._btn_delete.rect  = [450, 400, 120, 55]

       
        self._btn_manager.handle_events(img)
