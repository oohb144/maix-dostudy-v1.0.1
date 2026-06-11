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
from config import STATE_NAMES, State
from ui import (Button, ButtonManager, Slider, SliderManager,
                Switch, SwitchManager, ResolutionAdapter, Page, UIManager)


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

        # 创建返回按钮（直接用图像坐标）
        self._back_btn = Button(
            rect=[5, 5, 40, 30],
            label='<',
            callback=self._on_back_click,
            bg_color=C_DARK_GRAY,
            pressed_color=C_GRAY,
            text_color=C_WHITE,
            border_thickness=1,
            text_scale=1.2
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
        img.draw_string(55, 10, title,
                       color=image.Color.from_rgb(*C_WHITE),
                       scale=1.5)


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

        # 按钮布局（直接用 320x240 图像坐标，不缩放）
        # handle_event 会自动把图像坐标映射到显示器坐标来检测触摸
        btn_w, btn_h = 48, 50
        btn_y = 180
        btn_spacing = 5
        total_w = 6 * btn_w + 5 * btn_spacing
        start_x = (320 - total_w) // 2

        # 创建功能按钮
        self._btn_recognize = Button(
            rect=[start_x, btn_y, btn_w, btn_h],
            label='识别',
            callback=None,
            bg_color=BTN_PRIMARY,
            pressed_color=BTN_PRIMARY_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.0
        )

        self._btn_enroll = Button(
            rect=[start_x + btn_w + btn_spacing, btn_y, btn_w, btn_h],
            label='录入',
            callback=None,
            bg_color=BTN_SUCCESS,
            pressed_color=BTN_SUCCESS_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.0
        )

        self._btn_settings = Button(
            rect=[start_x + 2 * (btn_w + btn_spacing), btn_y, btn_w, btn_h],
            label='设置',
            callback=None,
            bg_color=BTN_SECONDARY,
            pressed_color=BTN_SECONDARY_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.0
        )

        self._btn_record = Button(
            rect=[start_x + 3 * (btn_w + btn_spacing), btn_y, btn_w, btn_h],
            label='录制',
            callback=None,
            bg_color=BTN_DANGER,
            pressed_color=BTN_DANGER_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.0
        )

        self._btn_stream = Button(
            rect=[start_x + 4 * (btn_w + btn_spacing), btn_y, btn_w, btn_h],
            label='推流',
            callback=None,
            bg_color=BTN_SECONDARY,
            pressed_color=BTN_SECONDARY_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.0
        )

        self._btn_fusion = Button(
            rect=[start_x + 5 * (btn_w + btn_spacing), btn_y, btn_w, btn_h],
            label='融合',
            callback=None,
            bg_color=BTN_SUCCESS,
            pressed_color=BTN_SUCCESS_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.0
        )

        # 添加按钮到管理器
        self._btn_manager.add_button(self._btn_recognize)
        self._btn_manager.add_button(self._btn_enroll)
        self._btn_manager.add_button(self._btn_settings)
        self._btn_manager.add_button(self._btn_record)
        self._btn_manager.add_button(self._btn_stream)
        self._btn_manager.add_button(self._btn_fusion)

    def set_callbacks(self, on_recognize, on_enroll, on_settings, on_record, on_stream, on_fusion):
        """
        设置按钮回调函数

        参数：
            on_recognize: 识别按钮回调
            on_enroll: 录入按钮回调（应跳转到录入页）
            on_settings: 设置按钮回调（应跳转到设置页）
            on_record: 纯录制按钮回调
            on_stream: 推流按钮回调
            on_fusion: 融合播放按钮回调
        """
        self._btn_recognize.callback = on_recognize
        self._btn_enroll.callback = on_enroll
        self._btn_settings.callback = on_settings
        self._btn_record.callback = on_record
        self._btn_stream.callback = on_stream
        self._btn_fusion.callback = on_fusion

    def update(self, img):
        """
        主页更新逻辑

        参数：
            img: 图像对象（320x240），disp.show() 会自动缩放到显示器
        """
        # 绘制状态背景条（直接在图像坐标系绘制）
        img.draw_rect(0, 0, img.width(), 20,
                     color=image.Color.from_rgb(*C_BLACK), thickness=-1)

        # 获取当前状态
        current_state = self._app_state.state
        state_name = STATE_NAMES.get(current_state, '未知')

        # 绘制状态文字（直接在图像坐标系绘制）
        img.draw_string(2, 3, f'状态:{state_name}',
                       color=image.Color.from_rgb(*C_WHITE),
                       scale=0.7)

        # 绘制已录入人数
        face_count = self._app_state.face_count
        img.draw_string(90, 3, f'录入:{face_count}',
                       color=image.Color.from_rgb(*C_GREEN),
                       scale=0.7)

        # 绘制底部信息栏
        img.draw_rect(0, img.height() - 16, img.width(), 16,
                     color=image.Color.from_rgb(*C_BLACK), thickness=-1)

        # 显示录制时长（如果正在录制）
        if current_state in (State.RECORDING, State.MANUAL_RECORDING):
            duration = self._app_state.record_duration
            img.draw_string(2, img.height() - 14, f'录制:{duration}s',
                           color=image.Color.from_rgb(*C_RED),
                           scale=0.6)

        # 显示推流地址（如果启用）
        if self._app_state.stream_enable:
            stream_url = self._app_state.stream_url
            if stream_url:
                img.draw_string(2, img.height() - 14, f'HTTP:{stream_url}',
                               color=image.Color.from_rgb(*C_CYAN),
                               scale=0.5)

        # 显示RTSP地址（如果启用）
        if self._app_state.rtsp_enable:
            rtsp_url = self._app_state.rtsp_url
            if rtsp_url:
                img.draw_string(2, img.height() - 7, f'RTSP:{rtsp_url}',
                               color=image.Color.from_rgb(*C_GREEN),
                               scale=0.5)

        # 处理按钮事件
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
        self._scroll_y = 0  # 当前滚动偏移
        self._max_scroll = 180  # 最大滚动距离（增大以容纳退出按钮）
        self._last_touch_y = 0
        self._is_dragging = False

        # 创建滑块管理器
        self._slider_manager = SliderManager(ts, disp)

        # 检测阈值滑块（直接用图像坐标）
        self._slider_conf = Slider(
            rect=[30, 60, 260, 20],
            label='检测阈值',
            min_val=10,
            max_val=90,
            default_val=int(app_state.conf_threshold * 100),
            scale=1.0,
            callback=lambda v: self._on_conf_threshold_change(v)
        )

        # 识别阈值滑块
        self._slider_recognize = Slider(
            rect=[30, 110, 260, 20],
            label='识别阈值',
            min_val=10,
            max_val=90,
            default_val=int(app_state.recognize_threshold * 100),
            scale=1.0,
            callback=lambda v: self._on_recognize_threshold_change(v)
        )

        # 添加滑块到管理器
        self._slider_manager.add_slider(self._slider_conf)
        self._slider_manager.add_slider(self._slider_recognize)

        # 创建开关管理器
        self._switch_manager = SwitchManager(ts, disp)

        # HTTP 推流开关
        self._switch_stream = Switch(
            position=[30, 155],
            scale=1.0,
            is_on=app_state.stream_enable,
            callback=lambda v: self._on_stream_toggle(v),
            on_color=C_GREEN,
            off_color=C_GRAY
        )

        # RTSP 推流开关
        self._switch_rtsp = Switch(
            position=[30, 195],
            scale=1.0,
            is_on=app_state.rtsp_enable,
            callback=lambda v: self._on_rtsp_toggle(v),
            on_color=C_GREEN,
            off_color=C_GRAY
        )

        # 音频提示开关
        self._switch_audio = Switch(
            position=[30, 235],
            scale=1.0,
            is_on=app_state.audio_enable,
            callback=lambda v: self._on_audio_toggle(v),
            on_color=C_GREEN,
            off_color=C_GRAY
        )

        # LED 指示开关
        self._switch_led = Switch(
            position=[30, 275],
            scale=1.0,
            is_on=app_state.led_enable,
            callback=lambda v: self._on_led_toggle(v),
            on_color=C_GREEN,
            off_color=C_GRAY
        )

        # 添加开关到管理器
        self._switch_manager.add_switch(self._switch_stream)
        self._switch_manager.add_switch(self._switch_rtsp)
        self._switch_manager.add_switch(self._switch_audio)
        self._switch_manager.add_switch(self._switch_led)

        # 创建按钮管理器
        self._btn_manager = ButtonManager(ts, disp)

        # 恢复默认按钮
        self._btn_reset = Button(
            rect=[30, 320, 120, 40],
            label='恢复默认',
            callback=lambda: self._on_reset(),
            bg_color=BTN_SECONDARY,
            pressed_color=BTN_SECONDARY_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=0.9
        )

        # 保存设置按钮
        self._btn_save = Button(
            rect=[170, 320, 120, 40],
            label='保存设置',
            callback=lambda: self._on_save(),
            bg_color=BTN_PRIMARY,
            pressed_color=BTN_PRIMARY_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=0.9
        )

        # 退出程序按钮
        self._btn_exit = Button(
            rect=[30, 370, 260, 40],
            label='退出程序',
            callback=lambda: self._on_exit(),
            bg_color=BTN_DANGER,
            pressed_color=BTN_DANGER_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=0.9
        )

        # 添加按钮到管理器
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
        """
        设置页更新逻辑

        参数：
            img: 图像对象
        """
        self._switch_stream.is_on = self._app_state.stream_enable
        self._switch_rtsp.is_on = self._app_state.rtsp_enable
        self._switch_audio.is_on = self._app_state.audio_enable
        self._switch_led.is_on = self._app_state.led_enable

        # 处理返回按钮
        self.handle_back_button(img)

        # 绘制标题
        self.draw_title(img, '系统设置')

        # 处理滚动
        self._handle_scroll()

        # 更新滑块和开关的位置（应用滚动偏移）
        self._update_component_positions()

        # 绘制开关标签（直接用图像坐标）
        y_stream = 160 - self._scroll_y
        if 40 < y_stream < img.height() - 60:
            img.draw_string(90, y_stream, 'HTTP 推流',
                           color=image.Color.from_rgb(*C_WHITE),
                           scale=1.0)

        y_rtsp = 200 - self._scroll_y
        if 40 < y_rtsp < img.height() - 60:
            img.draw_string(90, y_rtsp, 'RTSP 推流',
                           color=image.Color.from_rgb(*C_WHITE),
                           scale=1.0)

        y_audio = 240 - self._scroll_y
        if 40 < y_audio < img.height() - 60:
            img.draw_string(90, y_audio, '音频提示',
                           color=image.Color.from_rgb(*C_WHITE),
                           scale=1.0)

        y_led = 275 - self._scroll_y
        if 40 < y_led < img.height() - 60:
            img.draw_string(90, y_led, 'LED 指示',
                           color=image.Color.from_rgb(*C_WHITE),
                           scale=1.0)

        # 处理滑块事件
        self._slider_manager.handle_events(img)

        # 处理开关事件
        self._switch_manager.handle_events(img)

        # 处理按钮事件
        self._btn_manager.handle_events(img)

        # 绘制滚动条指示器
        self._draw_scrollbar(img)

    def _update_component_positions(self):
        """更新滑块和开关的位置（应用滚动偏移）"""
        # 计算滚动后的 Y 坐标（直接用图像坐标）
        y_conf = 60 - self._scroll_y
        y_recognize = 110 - self._scroll_y
        y_stream = 155 - self._scroll_y
        y_rtsp = 195 - self._scroll_y
        y_audio = 235 - self._scroll_y
        y_led = 275 - self._scroll_y
        y_btn_reset = 320 - self._scroll_y
        y_btn_save = 320 - self._scroll_y
        y_btn_exit = 370 - self._scroll_y

        # 更新滑块位置
        self._slider_conf.rect = [30, y_conf, 260, 20]
        self._slider_recognize.rect = [30, y_recognize, 260, 20]

        # 更新开关位置
        self._switch_stream.pos = [30, y_stream]
        self._switch_stream.rect = [30, y_stream,
                                     self._switch_stream.width, self._switch_stream.height]

        self._switch_rtsp.pos = [30, y_rtsp]
        self._switch_rtsp.rect = [30, y_rtsp,
                                   self._switch_rtsp.width, self._switch_rtsp.height]

        self._switch_audio.pos = [30, y_audio]
        self._switch_audio.rect = [30, y_audio,
                                    self._switch_audio.width, self._switch_audio.height]

        self._switch_led.pos = [30, y_led]
        self._switch_led.rect = [30, y_led,
                                  self._switch_led.width, self._switch_led.height]

        # 更新按钮位置
        self._btn_reset.rect = [30, y_btn_reset, 120, 40]
        self._btn_save.rect = [170, y_btn_save, 120, 40]
        self._btn_exit.rect = [30, y_btn_exit, 260, 40]

    def _handle_scroll(self):
        """处理触摸滚动"""
        try:
            x, y, pressed = self._ts.read()

            # 只在设置内容区域处理滚动（标题下方、退出按钮上方）
            content_top = 50
            content_bottom = 380

            if pressed:
                if not self._is_dragging:
                    # 开始拖动
                    if content_top < y < content_bottom:
                        self._is_dragging = True
                        self._last_touch_y = y
                else:
                    # 持续拖动
                    delta = self._last_touch_y - y
                    self._scroll_y = max(0, min(self._max_scroll, self._scroll_y + delta))
                    self._last_touch_y = y
            else:
                self._is_dragging = False
        except Exception:
            pass

    def _draw_scrollbar(self, img):
        """绘制滚动条指示器"""
        if self._max_scroll <= 0:
            return

        # 滚动条位置和大小
        bar_x = img.width() - 8
        bar_y = 50
        bar_height = img.height() - 100
        bar_width = 4

        # 绘制滚动条背景
        img.draw_rect(bar_x, bar_y, bar_width, bar_height,
                     color=image.Color.from_rgb(*C_DARK_GRAY), thickness=-1)

        # 计算滚动块位置和大小
        thumb_height = max(20, int(bar_height * (bar_height / (bar_height + self._max_scroll))))
        thumb_y = bar_y + int((bar_height - thumb_height) * (self._scroll_y / self._max_scroll))

        # 绘制滚动块
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

        # 创建按钮管理器
        self._btn_manager = ButtonManager(ts, disp)

        # 录入按钮（直接用图像坐标）
        self._btn_enroll = Button(
            rect=[30, 180, 80, 40],
            label='录入',
            callback=None,
            bg_color=BTN_SUCCESS,
            pressed_color=BTN_SUCCESS_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.0
        )

        # 删除选中按钮
        self._btn_delete = Button(
            rect=[120, 180, 80, 40],
            label='删除',
            callback=None,
            bg_color=BTN_DANGER,
            pressed_color=BTN_DANGER_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.0
        )

        # 清空全部按钮
        self._btn_clear = Button(
            rect=[210, 180, 80, 40],
            label='清空',
            callback=None,
            bg_color=BTN_DANGER,
            pressed_color=BTN_DANGER_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.0
        )

        # 添加按钮到管理器
        self._btn_manager.add_button(self._btn_enroll)
        self._btn_manager.add_button(self._btn_delete)
        self._btn_manager.add_button(self._btn_clear)

    def set_callbacks(self, on_enroll, on_delete, on_clear):
        """
        设置按钮回调函数

        参数：
            on_enroll: 录入按钮回调
            on_delete: 删除按钮回调
            on_clear: 清空按钮回调
        """
        self._btn_enroll.callback = on_enroll
        self._btn_delete.callback = on_delete
        self._btn_clear.callback = on_clear

    def update(self, img):
        """
        录入页更新逻辑

        参数：
            img: 图像对象
        """
        # 处理返回按钮
        self.handle_back_button(img)

        # 绘制标题
        self.draw_title(img, '人脸录入')

        # 绘制提示信息（直接用图像坐标）
        has_face = self._app_state.has_face
        if has_face:
            img.draw_string(30, 50, '检测到人脸，点击录入',
                           color=image.Color.from_rgb(*C_GREEN),
                           scale=1.0)
        else:
            img.draw_string(30, 50, '请正对摄像头',
                           color=image.Color.from_rgb(*C_YELLOW),
                           scale=1.0)

        # 调试：显示当前状态（直接用图像坐标）
        current_state = self._app_state.state
        state_name = STATE_NAMES.get(current_state, 'UNKNOWN')
        img.draw_string(200, 10, f'S:{state_name}',
                       color=image.Color.from_rgb(*C_GRAY),
                       scale=0.6)

        # 绘制已录入人脸列表
        face_list = self._app_state.face_list
        img.draw_string(30, 80, f'已录入 ({len(face_list)}):',
                       color=image.Color.from_rgb(*C_WHITE),
                       scale=0.9)

        # 显示人脸列表（最多显示 4 个）
        for i, name in enumerate(face_list[:4]):
            img.draw_string(30, 105 + i * 20, f'• {name}',
                           color=image.Color.from_rgb(*C_LIGHT_GRAY),
                           scale=0.8)

        if len(face_list) > 4:
            img.draw_string(30, 105 + 4 * 20, f'... 还有 {len(face_list) - 4} 人',
                           color=image.Color.from_rgb(*C_GRAY),
                           scale=0.8)

        # 处理按钮事件
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

        # 创建按钮管理器
        self._btn_manager = ButtonManager(ts, disp)

        # 刷新按钮（直接用图像坐标）
        self._btn_refresh = Button(
            rect=[30, 180, 60, 40],
            label='刷新',
            callback=None,
            bg_color=BTN_PRIMARY,
            pressed_color=BTN_PRIMARY_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=0.9
        )

        # 删除选中按钮
        self._btn_delete = Button(
            rect=[120, 180, 80, 40],
            label='删除',
            callback=None,
            bg_color=BTN_DANGER,
            pressed_color=BTN_DANGER_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.0
        )

        # 清空全部按钮
        self._btn_clear = Button(
            rect=[210, 180, 80, 40],
            label='清空',
            callback=None,
            bg_color=BTN_DANGER,
            pressed_color=BTN_DANGER_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=1.0
        )

        # 添加按钮到管理器
        self._btn_manager.add_button(self._btn_refresh)
        self._btn_manager.add_button(self._btn_delete)
        self._btn_manager.add_button(self._btn_clear)

    def set_callbacks(self, on_refresh, on_delete, on_clear):
        """
        设置按钮回调函数

        参数：
            on_refresh: 刷新按钮回调
            on_delete: 删除按钮回调
            on_clear: 清空按钮回调
        """
        self._btn_refresh.callback = on_refresh
        self._btn_delete.callback = on_delete
        self._btn_clear.callback = on_clear

    def update(self, img):
        """
        录像页更新逻辑

        参数：
            img: 图像对象
        """
        # 处理返回按钮
        self.handle_back_button(img)

        # 绘制标题
        self.draw_title(img, '录像管理')

        # 绘制录像文件列表（直接用图像坐标）
        recordings = self._app_state.recordings
        img.draw_string(30, 50, f'录像文件 ({len(recordings)}):',
                       color=image.Color.from_rgb(*C_WHITE),
                       scale=0.9)

        # 显示录像列表（最多显示 5 个）
        for i, rec in enumerate(recordings[:5]):
            name = rec.get('name', 'unknown')
            size = rec.get('size', 0)
            size_str = f'{size / 1024 / 1024:.1f}MB' if size > 1024*1024 else f'{size / 1024:.1f}KB'
            audio_size = rec.get('audio_size', 0)
            av_size = rec.get('av_size', 0)
            if av_size > 0:
                audio_mark = '+AV'
            elif audio_size > 0:
                audio_mark = '+WAV'
            else:
                audio_mark = '无音频'
            img.draw_string(30, 75 + i * 20, f'{name} {size_str} {audio_mark}',
                           color=image.Color.from_rgb(*C_LIGHT_GRAY),
                           scale=0.7)

        if len(recordings) == 0:
            img.draw_string(30, 75, '暂无录像文件',
                           color=image.Color.from_rgb(*C_GRAY),
                           scale=0.9)

        # 处理按钮事件
        self._btn_manager.handle_events(img)


# ==================== 融合播放页 ====================
class FusionPlayerPage(SubPage):
    """
    融合播放页

    功能：
    - 读取原始录像与已融合视频列表
    - 手动触发 MP4/WAV 融合
    - 选择已融合视频并播放
    """

    def __init__(self, ui_manager, ts, disp, adapter, app_state):
        """初始化融合播放页"""
        super().__init__(ui_manager, ts, disp, adapter)
        self._app_state = app_state
        self._selected_index = 0
        self._last_touch_pressed = False
        self._status_text = "等待读取"

        self._btn_manager = ButtonManager(ts, disp)

        self._btn_refresh = Button(
            rect=[30, 190, 60, 40],
            label='读取',
            callback=None,
            bg_color=BTN_PRIMARY,
            pressed_color=BTN_PRIMARY_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=0.9
        )

        self._btn_mux = Button(
            rect=[95, 190, 60, 40],
            label='融合',
            callback=None,
            bg_color=BTN_SUCCESS,
            pressed_color=BTN_SUCCESS_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=0.9
        )

        self._btn_play = Button(
            rect=[160, 190, 60, 40],
            label='播放',
            callback=None,
            bg_color=BTN_SUCCESS,
            pressed_color=BTN_SUCCESS_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=0.9
        )

        self._btn_back_home = Button(
            rect=[225, 190, 65, 40],
            label='返回',
            callback=self._on_back_click,
            bg_color=BTN_SECONDARY,
            pressed_color=BTN_SECONDARY_PRESSED,
            text_color=C_WHITE,
            border_thickness=0,
            text_scale=0.9
        )

        self._btn_manager.add_button(self._btn_refresh)
        self._btn_manager.add_button(self._btn_mux)
        self._btn_manager.add_button(self._btn_play)
        self._btn_manager.add_button(self._btn_back_home)

    def set_callbacks(self, on_refresh, on_mux, on_play):
        """设置按钮回调函数"""
        self._btn_refresh.callback = on_refresh
        self._btn_mux.callback = on_mux
        self._btn_play.callback = on_play

    def set_status(self, text):
        """设置页面状态提示"""
        self._status_text = text

    def get_selected_index(self):
        """获取当前选中的列表索引"""
        return self._selected_index

    def _handle_list_touch(self, img):
        """处理列表项触摸选择"""
        try:
            x, y, pressed = self._ts.read()
            img_w, img_h = img.width(), img.height()
            disp_w, disp_h = self._disp.width(), self._disp.height()
            if disp_w > 0 and disp_h > 0:
                x = int(x * img_w / disp_w)
                y = int(y * img_h / disp_h)
            if pressed and not self._last_touch_pressed:
                if 25 <= x <= 300 and 75 <= y <= 165:
                    index = (y - 75) // 22
                    muxed_items = self._app_state.muxed_videos
                    if 0 <= index < len(muxed_items[:4]):
                        self._selected_index = index
            self._last_touch_pressed = pressed
        except Exception:
            pass

    def update(self, img):
        """更新融合播放页"""
        self.handle_back_button(img)
        self.draw_title(img, '融合播放')
        self._handle_list_touch(img)

        raw_count = len(self._app_state.fusion_items)
        muxed_count = len(self._app_state.muxed_videos)
        img.draw_string(30, 45, f'原始:{raw_count}  已融合:{muxed_count}',
                       color=image.Color.from_rgb(*C_WHITE),
                       scale=0.9)
        img.draw_string(30, 62, self._status_text,
                       color=image.Color.from_rgb(*C_YELLOW),
                       scale=0.7)

        muxed_items = self._app_state.muxed_videos
        for i, item in enumerate(muxed_items[:4]):
            y = 78 + i * 22
            bg_color = C_DARK_GRAY if i == self._selected_index else C_BLACK
            img.draw_rect(25, y - 2, 270, 20,
                         color=image.Color.from_rgb(*bg_color),
                         thickness=-1)
            name = item.get('av_name') or item.get('name', 'unknown')
            size = item.get('av_size', 0)
            size_str = f'{size / 1024 / 1024:.1f}MB' if size > 1024 * 1024 else f'{size / 1024:.1f}KB'
            img.draw_string(30, y, f'{i + 1}. {name} {size_str}',
                           color=image.Color.from_rgb(*C_LIGHT_GRAY),
                           scale=0.65)

        if len(muxed_items) == 0:
            img.draw_string(30, 85, '暂无融合视频，点击“融合”生成',
                           color=image.Color.from_rgb(*C_GRAY),
                           scale=0.8)

        self._btn_manager.handle_events(img)
