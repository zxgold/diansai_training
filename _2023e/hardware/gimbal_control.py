import threading
import gpiod
import numpy as np
import time
from dataclasses import dataclass

from config import (
    RED_GIMBAL_X_ENA,
    RED_GIMBAL_X_PWM,
    RED_GIMBAL_X_DIR,
    RED_GIMBAL_X_COUNTER_PIN,
    RED_GIMBAL_Y_ENA,
    RED_GIMBAL_Y_PWM,
    RED_GIMBAL_Y_DIR,
    RED_GIMBAL_Y_COUNTER_PIN
)

# PWM输出引脚：GPIO12,连接到PUL+端
# 环回连接：从GPIO12引出一根杜邦线，连接到一个未使用的GPIO口，
# 计数输入引脚：GPIO5
# PWM子系统驱动GPIO12，gpiod子系统监听GPIO5
@dataclass
class MotorConfig:
    chip_name: str = 'gpiochip0'
    # --- gpiod Pins ---
    dir_pin: int
    
    # --- PWM Output Pin (for sysfs) ---
    pul_pin: int
    
    # --- gpiod Counter Pin (for loopback) ---
    counter_pin: int

    # --- sysfs PWM Controller Info ---
    # 在树莓派5上，你需要找到step_pin对应的pwmchip。
    # 常用: GPIO12 -> pwmchip2, GPIO13 -> pwmchip0
    # 可通过 `ls /sys/class/pwm` 查看
    pwm_chip: str
    pwm_channel: int

    # --- Motor/Driver Specs ---
    motor_steps_per_rev: int = 200
    driver_microsteps: int = 16

    @property
    def steps_per_degree(self) -> float:
        """计算每度需要多少步（包括微步）"""
        return (self.motor_steps_per_rev * self.driver_microsteps) / 360.0
    
# --- 辅助类: 用于控制 sysfs PWM ---
class HardwarePWM:
    """一个封装了 sysfs PWM 接口的辅助类"""
    def __init__(self, chip: str, channel: int):
        self.chip_path = f'/sys/class/pwm/{chip}/'
        self.channel_path = f'{self.chip_path}pwm{channel}/'
        self.channel_str = str(channel)
        self._period_ns = 0

        # 在初始化时就确保通道被导出，并等待其就绪
        self._export_and_wait()

    def _export_and_wait(self, timeout_sec=0.5):
        """导出PWM通道并等待其sysfs节点创建完成。"""
        import os # 引入os模块用于检查文件
        
        # 检查是否已经导出，如果period文件已存在，则认为已就绪
        if os.path.exists(self.channel_path + 'period'):
            print(f"Info: PWM channel {self.channel_str} already exported and ready.")
            return

        # 如果未导出，则执行导出操作
        try:
            with open(self.chip_path + 'export', 'w') as f:
                f.write(self.channel_str)
        except IOError:
            # 如果导出失败（例如权限问题），这里会立即抛出异常
            # 如果是因为已导出而失败，上面的os.path.exists会处理
            print(f"Warning: Failed to write to export file. Assuming already exported.")

        # 使用重试循环等待period文件出现
        start_time = time.monotonic()
        while not os.path.exists(self.channel_path + 'period'):
            if time.monotonic() - start_time > timeout_sec:
                raise TimeoutError(
                    f"PWM channel {self.channel_str} did not become ready "
                    f"within {timeout_sec} seconds."
                )
            time.sleep(0.001) # 短暂休眠，避免CPU空转

    def set_params(self, freq_hz: int, duty_percent: int = 50):
        if freq_hz <= 0: return
        self._period_ns = int(1_000_000_000 / freq_hz)
        duty_ns = int(self._period_ns * (duty_percent / 100.0))
        
        # 由于我们在__init__中已经等待了文件创建，这里通常可以直接写入
        # 不再需要 try-except-sleep 块
        try:
            with open(self.channel_path + 'period', 'w') as f: f.write(str(self._period_ns))
            with open(self.channel_path + 'duty_cycle', 'w') as f: f.write(str(duty_ns))
        except FileNotFoundError as e:
            # 添加一个健壮性后备，以防万一
            print(f"Error: PWM sysfs files disappeared unexpectedly: {e}")
            raise e

    def start(self):
        with open(self.channel_path + 'enable', 'w') as f: f.write('1')

    def stop(self):
        # 增加文件存在性检查，使停止操作更健壮
        import os
        enable_path = self.channel_path + 'enable'
        if os.path.exists(enable_path):
            with open(enable_path, 'w') as f: f.write('0')

    def unexport(self):
        self.stop()
        try:
            with open(self.chip_path + 'unexport', 'w') as f:
                f.write(self.channel_str)
        except IOError as e:
            # 这种情况很常见，比如程序崩溃后重启，通道可能已经被内核清理
            print(f"Warning: Could not unexport PWM channel. It might have been already unexported. {e}")


class Motor:
    '''
    使用gpio和sysfs PWM在树莓派5上控制步进电机
    '''
    FORWARD = 1
    BACKWARD = 0

    def __init__(self, config: MotorConfig):
        self._config = config
        self._is_moving = False
        self._target_step = 0
        self._steps_counted = 0
        self._direction = self.FORWARD

         # --- PWM 初始化 ---
        self._pwm = HardwarePWM(config.pwm_chip, config.pwm_channel)
        
        # --- gpiod 初始化 ---
        self._chip = gpiod.Chip(self._config.chip_name)
        self._dir_line = self._chip.get_line(config.dir_pin)
        # self._enable_line = self._chip.get_line(config.enable_pin) # 我们不使用enable
        self._counter_line = self._chip.get_line(config.counter_pin)
        
        # 请求输出线路
        self._dir_line.request(consumer="stepper-dir", type=gpiod.LINE_REQ_DIR_OUT)
        self._enable_line.request(consumer="stepper-enable", type=gpiod.LINE_REQ_DIR_OUT)
        
        # 请求输入线路并配置边沿检测
        self._counter_line.request(
            consumer="stepper-counter",
            type=gpiod.LINE_REQ_EV_RISING_EDGE
        )
        
        # 默认禁用驱动器 (ENA+ 高电平)
        # self._enable_line.set_value(1)
        self.setDir(self.FORWARD)

        # --- 回调监控线程 ---
        self._monitor_thread = threading.Thread(target=self._event_monitor_loop, daemon=True)
        self._running = True
        self._monitor_thread.start()

    def _event_monitor_loop(self):
        """在后台线程中等待并处理边沿事件"""
        while self._running:
            # 等待事件，超时1秒以允许线程退出检查
            if self._counter_line.event_wait(sec=1):
                event = self._counter_line.event_read()
                if self._is_moving:
                    self._steps_counted += 1
                    if self._steps_counted >= self._target_steps:
                        # 在回调中自动停止
                        self.stop()
    
    def setDir(self, direction: int):
        self._direction = direction
        self._dir_line.set_value(self._direction)
        
    def setStep(self, steps: int, speed_hz: int):
        if self._is_moving:
            print("Warning: Motor is moving. Call stop() first.")
            return
        if steps <= 0:
            print("Warning: Steps must be positive.")
            return
        
        self._target_steps = steps
        self._steps_counted = 0
        self._pwm.set_params(speed_hz, 50) # 50% duty cycle
        print(f"Movement prepared: {steps} steps at {speed_hz} Hz.")
        
    def start(self):
        if self._is_moving: return
        if self._target_steps == 0:
            print("Error: No movement configured. Call setStep() first.")
            return

        print("Starting motor1...")
        self._is_moving = True
        
        # 启用驱动器 (ENA+ 低电平)
        self._enable_line.set_value(0)
        time.sleep(0.001) # 等待驱动器稳定
        
        # 启动PWM脉冲
        self._pwm.start()

    def stop(self):
        if not self._is_moving: return
        
        print("Stopping motor1...")
        self._is_moving = False
        
        # 停止PWM脉冲
        self._pwm.stop()
        
        # 禁用驱动器
        self._enable_line.set_value(1)
        
        print(f"Motor stopped. Total steps counted: {self._steps_counted}")
        self._target_steps = 0
        # _steps_counted 不需要重置，因为它在 setStep 中重置
        
    def is_running(self) -> bool:
        return self._is_moving
    
    # 满足用户要求的函数名别名
    isStart = is_running
    
    def cleanup(self):
        print("Cleaning up resources...")
        self._running = False
        self._monitor_thread.join(timeout=1.5)
        self.stop()
        self._pwm.unexport()
        self._dir_line.release()
        self._enable_line.release()
        self._counter_line.release()
        self._chip.close()
        print("Cleanup complete.")


    
# --- 使用示例 ---
if __name__ == "__main__":
    print("Stepper Motor Control with gpiod and sysfs PWM on RPi 5")
    print("NOTE: This script requires sudo to access /sys/class/pwm/")
    
    # --- 配置 ---
    # !! 确保这些引脚和你的接线、树莓派5的PWM配置一致 !!
    motor1_config = MotorConfig(
        step_pin=RED_GIMBAL_X_PWM,          # BCM 12 (PWM输出)
        dir_pin=RED_GIMBAL_X_DIR,           # BCM 16 (方向)
        enable_pin=RED_GIMBAL_X_ENA,        # BCM 20 (使能)
        counter_pin=RED_GIMBAL_X_COUNTER_PIN,        # BCM 5 (环回输入)
        pwm_chip='pwmchip2',  # RPi5: GPIO12 is on pwmchip2
        pwm_channel=0,
        motor_steps_per_rev=200,
        driver_microsteps=16
    )

    motor2_config = MotorConfig(
        step_pin=12,          # BCM 12 (PWM输出)
        dir_pin=16,           # BCM 16 (方向)
        enable_pin=20,        # BCM 20 (使能)
        counter_pin=5,        # BCM 5 (环回输入)
        pwm_chip='pwmchip2',  # RPi5: GPIO12 is on pwmchip2
        pwm_channel=0,
        motor_steps_per_rev=200,
        driver_microsteps=16
    )



    motor1 = Motor(motor1_config)

    
    try:
        print("\n--- Demo 1: Rotate 360 degrees forward ---")
        steps_for_one_rev = motor1._config.motor_steps_per_rev * motor1._config.driver_microsteps
        motor1.setDir(Motor.FORWARD)
        motor1.setStep(steps_for_one_rev, 1600)
        motor1.start()
        
        while motor1.isStart():
            print(f"  Running... Steps: {motor1._steps_counted}/{motor1._target_steps}")
            time.sleep(0.2)
        
        print("Demo 1 finished.")
        time.sleep(1)

        print("\n--- Demo 2: Rotate 90 degrees backward ---")
        angle = -90
        steps_for_angle = round(abs(angle) * motor1._config.steps_per_degree)
        motor1.setDir(Motor.BACKWARD)
        motor1.setStep(steps_for_angle, 800)
        motor1.start()

        # 等待运动完成
        while motor1.is_running():
            time.sleep(0.1)

        print("Demo 2 finished.")
        
    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
    finally:
        motor1.cleanup()
   
