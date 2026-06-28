"""
MaixCAM2 人脸识别智能系统 - 按键管理模块

功能：
- 检测短按事件（触发人脸识别）
- 检测长按事件（切换到人脸录入模式）
- 检测超长按事件（退出程序，≥3秒）
- 防抖处理
- 线程安全的事件回调
"""

from maix import key, time


class KeyManager:
    """
    按键管理器

    功能：
    - 封装 MaixPy 的 key 模块
    - 区分短按、长按和超长按事件
    - 提供防抖机制
    """

    # 超长按阈值（毫秒），超过此时间触发退出
    EXIT_PRESS_MS = 3000

    def __init__(self, on_short_press=None, on_long_press=None, on_exit_press=None, long_press_ms=1500):
        """
        初始化按键管理器

        参数：
            on_short_press: 短按回调函数
            on_long_press: 长按回调函数
            on_exit_press: 超长按回调函数（退出程序）
            long_press_ms: 长按阈值（毫秒），默认 1500ms
        """
        self._on_short_press = on_short_press
        self._on_long_press = on_long_press
        self._on_exit_press = on_exit_press
        self._long_press_ms = long_press_ms

        # 按键状态跟踪
        self._key_pressed = False
        self._press_start_time = 0
        self._long_press_triggered = False
        self._exit_press_triggered = False

        # 防抖参数
        self._last_release_time = 0
        self._debounce_ms = 200  # 200ms 防抖

        # 事件队列（线程安全）
        self._events = []

        # 创建按键对象
        self._key_obj = key.Key(self._key_callback)

        print("[按键] 按键管理器初始化完成")

    def _key_callback(self, key_id, state):
        """
        按键回调函数（在独立线程中执行）

        参数：
            key_id: 按键 ID
            state: 按键状态
        """
        if key_id != key.Keys.KEY_OK:
            return

        current_time = time.ticks_ms()

        if state == key.State.KEY_PRESSED:
            # 按键按下
            self._key_pressed = True
            self._press_start_time = current_time
            self._long_press_triggered = False
            self._exit_press_triggered = False

        elif state == key.State.KEY_RELEASED:
            # 按键释放
            if self._key_pressed:
                self._key_pressed = False
                press_duration = current_time - self._press_start_time

                # 防抖检查
                if current_time - self._last_release_time < self._debounce_ms:
                    return
                self._last_release_time = current_time

                # 如果超长按已经触发，不再触发其他事件
                if self._exit_press_triggered:
                    return

                # 如果长按已经触发，不再触发短按
                if self._long_press_triggered:
                    return

                # 判断短按（按下时间小于长按阈值）
                if press_duration < self._long_press_ms:
                    self._events.append('short_press')
                    print(f"[按键] 短按检测，持续 {press_duration}ms")

        elif state == key.State.KEY_LONG_PRESSED:
            # 长按检测（MaixPy 的长按事件）
            if self._key_pressed and not self._long_press_triggered and not self._exit_press_triggered:
                press_duration = current_time - self._press_start_time

                # 检查是否达到超长按阈值
                if press_duration >= self.EXIT_PRESS_MS:
                    # 超长按：退出程序
                    self._exit_press_triggered = True
                    self._events.append('exit_press')
                    print(f"[按键] 超长按检测（{press_duration}ms），退出程序")
                elif not self._long_press_triggered:
                    # 普通长按
                    self._long_press_triggered = True
                    self._events.append('long_press')
                    print("[按键] 长按检测")

    def update(self):
        """
        更新按键状态，处理待处理的事件

        功能：
        - 从事件队列中取出事件
        - 调用相应的回调函数
        """
        while self._events:
            event = self._events.pop(0)

            if event == 'short_press' and self._on_short_press:
                try:
                    self._on_short_press()
                except Exception as e:
                    print(f"[按键] 短按回调异常: {e}")

            elif event == 'long_press' and self._on_long_press:
                try:
                    self._on_long_press()
                except Exception as e:
                    print(f"[按键] 长按回调异常: {e}")

            elif event == 'exit_press' and self._on_exit_press:
                try:
                    self._on_exit_press()
                except Exception as e:
                    print(f"[按键] 超长按回调异常: {e}")

    def set_short_press_callback(self, callback):
        """
        设置短按回调函数

        参数：
            callback: 回调函数
        """
        self._on_short_press = callback

    def set_long_press_callback(self, callback):
        """
        设置长按回调函数

        参数：
            callback: 回调函数
        """
        self._on_long_press = callback

    def set_exit_press_callback(self, callback):
        """
        设置超长按回调函数（退出程序）

        参数：
            callback: 回调函数
        """
        self._on_exit_press = callback

    def is_pressed(self):
        """
        检查按键是否正在按下

        返回：
            True: 按键按下
            False: 按键释放
        """
        return self._key_pressed

    def destroy(self):
        """
        销毁按键管理器，释放资源
        """
        if self._key_obj:
            del self._key_obj
            self._key_obj = None
        print("[按键] 按键管理器已销毁")