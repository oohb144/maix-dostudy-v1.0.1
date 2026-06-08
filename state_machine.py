"""
MaixCAM2 人脸识别智能系统 - 状态机模块

功能：
- 管理系统状态（空闲、识别、录入、录制、错误）
- 处理状态转换
- 执行状态回调函数
- 提供超时保护
"""

from maix import time

class StateMachine:
    """
    轻量级状态机

    特点：
    - 无外部依赖
    - 内存占用小
    - 支持进入/退出回调
    - 支持状态超时检测
    """

    def __init__(self, initial_state=0):
        """
        初始化状态机

        参数：
            initial_state: 初始状态值，默认为 0（IDLE）
        """
        # 当前状态
        self._state = initial_state
        # 上一个状态
        self._prev_state = initial_state
        # 状态处理函数字典
        self._handlers = {}
        # 进入状态回调字典
        self._enter_callbacks = {}
        # 退出状态回调字典
        self._exit_callbacks = {}
        # 状态进入时间戳
        self._state_time = time.ticks_ms()
        # 是否正在转换中（防止重入）
        self._transitioning = False

    @property
    def state(self):
        """获取当前状态"""
        return self._state

    @property
    def prev_state(self):
        """获取上一个状态"""
        return self._prev_state

    @property
    def state_duration(self):
        """获取当前状态持续时间（毫秒）"""
        return time.ticks_ms() - self._state_time

    def register_handler(self, state, handler):
        """
        注册状态处理函数

        参数：
            state: 状态值
            handler: 处理函数，无参数
        """
        self._handlers[state] = handler

    def register_enter_callback(self, state, callback):
        """
        注册进入状态回调

        参数：
            state: 状态值
            callback: 回调函数，无参数
        """
        self._enter_callbacks[state] = callback

    def register_exit_callback(self, state, callback):
        """
        注册退出状态回调

        参数：
            state: 状态值
            callback: 回调函数，无参数
        """
        self._exit_callbacks[state] = callback

    def transition(self, new_state):
        """
        状态转换

        参数：
            new_state: 目标状态值

        返回：
            True: 转换成功
            False: 转换失败（相同状态或正在转换中）
        """
        # 防止重入
        if self._transitioning:
            return False

        # 相同状态不转换
        if new_state == self._state:
            return False

        self._transitioning = True

        try:
            # 执行退出回调
            if self._state in self._exit_callbacks:
                try:
                    self._exit_callbacks[self._state]()
                except Exception as e:
                    print(f"[状态机] 退出回调异常: {e}")

            # 保存上一个状态
            self._prev_state = self._state

            # 更新状态
            self._state = new_state
            self._state_time = time.ticks_ms()

            # 执行进入回调
            if new_state in self._enter_callbacks:
                try:
                    self._enter_callbacks[new_state]()
                except Exception as e:
                    print(f"[状态机] 进入回调异常: {e}")

            print(f"[状态机] {self._prev_state} -> {new_state}")
            return True

        finally:
            self._transitioning = False

    def update(self):
        """
        更新状态机

        功能：
        - 执行当前状态的处理函数
        - 捕获异常并处理
        """
        if self._state in self._handlers:
            try:
                self._handlers[self._state]()
            except Exception as e:
                print(f"[状态机] 处理函数异常: {e}")
                # 可以选择转入错误状态
                # self.transition(State.ERROR)

    def is_state(self, state):
        """
        检查是否为指定状态

        参数：
            state: 要检查的状态值

        返回：
            True: 当前是该状态
            False: 当前不是该状态
        """
        return self._state == state

    def get_state_duration(self):
        """
        获取当前状态持续时间

        返回：
            持续时间（毫秒）
        """
        return self.state_duration

    def reset(self):
        """
        重置状态机到初始状态
        """
        self.transition(0)  # 转到 IDLE 状态
