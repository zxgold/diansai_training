import gpiod
import numpy as np
import time
from dataclasses import dataclass

@dataclass
class MotorConfig:
    chip_name: str = 'gpiochip4'
    in1: int
    in2: int
    in3: int
    in4: int
    delay: float = 0.0001

class Motor:
    def __init__(self, config: MotorConfig):
        self.config = config
        self.lines = None
        self.pins = [
            config.in1, config.in2, config.in3, config.in4
        ]
        self.setup()

    def setup(self):
        try:
            chip = gpiod.Chip(self.config.chip_name)
            self.lines = chip.get_lines(self.pins)
            self.lines.request(
                consumer="e_23_motor_driver",
                type=gpiod.LINE_REQ_DIR_OUT,
                default_vals=[0] * len(self.pins)
            )
            
        except Exception as e:
            print(f"GPIO setup failed: {e}")
            print("Please ensure you are running with 'sudo' and the CHIP_NAME is correct.")
            return False
        return True
    
    def destroy(self):
        """
        释放所有GPIO引脚，在程序结束时调用。
        """
        if self.lines:
            # 将所有引脚设为低电平
            self.lines.set_values([0] * len(self.all_pins))
            # 释放引脚
            self.lines.release()
            print("\nGPIO cleaned up.")
            self.lines = None
    
    def __del__(self):
        """
        析构函数，确保在对象销毁时调用 destroy 方法。
        """
        self.destroy()

    def setStep(self, w1, w2, w3, w4):
        """
        设置电机1的四个引脚状态。
        """
        current_values = self.lines.get_values()  # 获取当前所有引脚的状态
        # 更新电机1对应的引脚状态
        current_values[0] = w1
        current_values[1] = w2
        current_values[2] = w3
        current_values[3] = w4
        self.lines.set_values(current_values)

    def stop(self):
        self.setStep(0, 0, 0, 0)

    def rightward(self, steps):
        delay = self.config.delay
        for _ in range(steps):
            self.setStep(1, 0, 1, 0)
            time.sleep(delay)
            self.setStep(0, 1, 1, 0)
            time.sleep(delay)
            self.setStep(0, 1, 0, 1)
            time.sleep(delay)
            self.setStep(1, 0, 0, 1)
            time.sleep(delay)
        self.stop()

    def leftward(self, steps):
        delay = self.config.delay
        for _ in range(steps):
            self.setStep(1, 0, 0, 1)
            time.sleep(delay)
            self.setStep(0, 1, 0, 1)
            time.sleep(delay)
            self.setStep(0, 1, 1, 0)
            time.sleep(delay)
            self.setStep(1, 0, 1, 0)
            time.sleep(delay)
        self.stop()

    def downward(self, steps):
        self.leftward(steps)

    def upward(self, steps):
        self.rightward(steps)

    def loop(self, angle):
        print("rightward--->leftward:")
        steps = int(angle / 360 * 6400)
        self.rightward(steps)
        self.leftward(steps)
        print("stop...")
        time.sleep(1)


if __name__ == '__main__':
    # 定义电机配置，每个引脚单独指定
    motor1_config = MotorConfig(
        in1=4,
        in2=14,
        in3=22,
        in4=23
    )
    motor2_config = MotorConfig(
        in1=6,
        in2=12,
        in3=5,
        in4=27
    )

    # 创建电机驱动实例
    motor1 = Motor(motor1_config)
    motor2 = Motor(motor2_config)

    try:
        while True:
            a = input("please input angle:")
            if not a:
                continue  # Handle empty input

            t0 = time.time()
            motor1.loop(float(a))
            motor2.loop(float(a))

            print(f"Operation took: {time.time() - t0:.2f} seconds")

    except KeyboardInterrupt:
        print("\nCtrl+C pressed. Exiting.")
    except ValueError:
        print("Invalid input. Please enter a number.")
    finally:
        # 无论程序如何退出（正常结束或异常），都确保GPIO被清理
        motor1.destroy()
        motor2.destroy()


