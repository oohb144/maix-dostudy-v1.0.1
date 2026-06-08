"""
MaixCAM2 人脸识别智能系统 - LED 控制模块

功能：
- LED 开/关控制
- LED 闪烁控制（快闪、慢闪、超慢闪）
- 非阻塞闪烁实现
"""

from maix import gpio, pinmap, time, err

class LedController:
    """
    LED 控制器

    功能：
    - 控制 MaixCAM2 板载 LED（GPIOA6）
    - 支持常亮、熄灭、闪烁模式
    - 非阻塞闪烁实现
    """

    def __init__(self):
        """
        初始化 LED 控制器

        功能：
        - 设置引脚功能
        - 创建 GPIO 输出对象
        """
        try:
            # 设置引脚功能
            err.check_raise(
                pinmap.set_pin_function("A6", "GPIOA6"),
                "LED 引脚设置失败"
            )

            # 创建 GPIO 输出对象
            self._led = gpio.GPIO("GPIOA6", gpio.Mode.OUT)

            # 闪烁控制参数
            self._blink_interval = 0      # 闪烁间隔（毫秒）
            self._blink_timer = 0         # 闪烁计时器
            self._blink_state = False     # 闪烁状态
            self._is_blinking = False     # 是否正在闪烁
            self._current_state = False   # 当前 LED 状态

            # 测试 LED：快速闪烁两次
            self._led.value(1)
            time.sleep_ms(100)
            self._led.value(0)
            time.sleep_ms(100)
            self._led.value(1)
            time.sleep_ms(100)
            self._led.value(0)

            print("[LED] LED 控制器初始化完成")

        except Exception as e:
            print(f"[LED] 初始化失败: {e}")
            self._led = None

    def on(self):
        """
        打开 LED（常亮）

        功能：
        - 熄灭闪烁模式
        - 点亮 LED
        """
        if self._led is None:
            return
        self._is_blinking = False
        self._current_state = True
        self._led.value(1)

    def off(self):
        """
        关闭 LED（熄灭）

        功能：
        - 熄灭闪烁模式
        - 关闭 LED
        """
        if self._led is None:
            return
        self._is_blinking = False
        self._current_state = False
        self._led.value(0)

    def blink(self, interval_ms):
        """
        启动 LED 闪烁

        参数：
            interval_ms: 闪烁间隔（毫秒）
                        - 200ms: 快闪（识别中）
                        - 500ms: 慢闪（录制中）
                        - 1000ms: 超慢闪（空闲）
        """
        if self._led is None:
            return
        if not self._is_blinking or self._blink_interval != interval_ms:
            self._blink_interval = interval_ms
            self._blink_timer = time.ticks_ms()
            self._blink_state = False
            self._is_blinking = True
            self._led.value(0)

    def update(self):
        """
        更新 LED 状态

        功能：
        - 非阻塞闪烁实现
        - 需要在主循环中调用
        """
        if self._led is None or not self._is_blinking:
            return

        current_time = time.ticks_ms()
        if current_time - self._blink_timer >= self._blink_interval:
            self._blink_timer = current_time
            self._blink_state = not self._blink_state
            self._current_state = self._blink_state
            self._led.value(1 if self._blink_state else 0)

    def flash(self, times=3, interval_ms=100):
        """
        LED 闪烁指定次数（阻塞）

        参数：
            times: 闪烁次数
            interval_ms: 闪烁间隔（毫秒）
        """
        for _ in range(times):
            self._led.value(1)
            time.sleep_ms(interval_ms)
            self._led.value(0)
            time.sleep_ms(interval_ms)

    def is_blinking(self):
        """
        检查是否正在闪烁

        返回：
            True: 正在闪烁
            False: 未闪烁
        """
        return self._is_blinking

    def get_blink_interval(self):
        """
        获取当前闪烁间隔

        返回：
            闪烁间隔（毫秒），未闪烁时返回 0
        """
        return self._blink_interval if self._is_blinking else 0

    def is_on(self):
        """
        检查 LED 是否亮着

        返回：
            True: LED 亮
            False: LED 灭
        """
        return self._current_state

    def destroy(self):
        """
        销毁 LED 控制器，释放资源
        """
        self.off()
        print("[LED] LED 控制器已销毁")
