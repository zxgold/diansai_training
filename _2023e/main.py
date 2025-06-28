import gpiod
import time
import numpy as np
import math

# --- 1. 全局硬件配置 ---
# 红色激光笔[GPIO26,GPIO39(GND)]
# PIN_LASER = 26 # BCM 编号
# 定义GPIO控制器芯片的名称
# 对于树莓派5，通常是 'gpiochip4'
# 对于树莓派4及更早版本，通常是 'gpiochip0'
CHIP_NAME = 'gpiochip4'

# 定义所有需要用到的引脚（BCM编号）
PINS_MOTOR1 = [4, 14, 22, 23]  # [IN1, IN2, IN3, IN4]pul，pul
PINS_MOTOR2 = [6, 12, 5, 27]   # [IN12, IN22, IN32, IN42]
# ALL_PINS = PINS_MOTOR1 + PINS_MOTOR2 + [PIN_LASER] 
ALL_PINS = PINS_MOTOR1 + PINS_MOTOR2

# 全局变量来持有请求到的GPIO线路对象
lines = None
delay = 0.0001

# --- 2. 初始化和清理函数 ---

def setup():
    """
    初始化GPIO，请求并配置所有需要的引脚。
    这个函数应该在程序开始时只调用一次。
    """
    global lines
    try:
        # 获取GPIO控制器芯片
        chip = gpiod.Chip(CHIP_NAME)
        
        # 从芯片请求所有需要的线路
        lines = chip.get_lines(ALL_PINS)
        
        # 将所有线路配置为输出模式，并设置默认值为低电平(0)
        lines.request(
            consumer="e_23_motor_driver",
            type=gpiod.LINE_REQ_DIR_OUT,
            default_vals=[0] * len(ALL_PINS)
        )
        print("GPIO setup successful.")
    except Exception as e:
        print(f"GPIO setup failed: {e}")
        print("Please ensure you are running with 'sudo' and the CHIP_NAME is correct.")
        exit(1) # 如果初始化失败，直接退出程序

def destroy():
    """
    释放所有GPIO引脚，在程序结束时调用。
    """
    global lines
    if lines:
        # 将所有引脚设为低电平
        lines.set_values([0] * len(ALL_PINS))
        # 释放引脚
        lines.release()
        print("\nGPIO cleaned up.")

# --- 3. 底层电机控制函数 ---

def setStep(w1, w2, w3, w4):
    """
    设置电机1的四个引脚状态。
    """
    # gpiod更高效的方式是批量设置，我们在这里构造一个包含所有引脚状态的列表
    current_values = lines.get_values() # 获取当前所有引脚的状态
    # 更新电机1对应的引脚状态
    current_values[0] = w1
    current_values[1] = w2
    current_values[2] = w3
    current_values[3] = w4
    lines.set_values(current_values)

def setStep2(w1, w2, w3, w4):
    """
    设置电机2的四个引脚状态。
    """
    current_values = lines.get_values() # 获取当前所有引脚的状态
    # 更新电机2对应的引脚状态
    current_values[4] = w1
    current_values[5] = w2
    current_values[6] = w3
    current_values[7] = w4
    lines.set_values(current_values)

def stop():
    setStep(0, 0, 0, 0)
    
def stop2():
    setStep2(0, 0, 0, 0)

# --- 4. 高层运动逻辑 (这部分函数几乎不需要修改) ---
# 你的 rightward, leftward, upward, downward 等函数都依赖于 setStep 和 setStep2，
# 所以它们可以保持不变。

def rightward(steps):
    global delay
    for _ in range(steps):
        setStep(1, 0, 1, 0); time.sleep(delay)
        setStep(0, 1, 1, 0); time.sleep(delay)
        setStep(0, 1, 0, 1); time.sleep(delay)
        setStep(1, 0, 0, 1); time.sleep(delay)
    stop()
    
def rightward2(steps):
    global delay
    for _ in range(steps):
        setStep2(1, 0, 1, 0); time.sleep(delay)
        setStep2(0, 1, 1, 0); time.sleep(delay)
        setStep2(0, 1, 0, 1); time.sleep(delay)
        setStep2(1, 0, 0, 1); time.sleep(delay)
    stop2()
        
def leftward(steps):
    global delay
    for _ in range(steps):
        setStep(1, 0, 0, 1); time.sleep(delay)
        setStep(0, 1, 0, 1); time.sleep(delay)
        setStep(0, 1, 1, 0); time.sleep(delay)
        setStep(1, 0, 1, 0); time.sleep(delay)
    stop()

def leftward2(steps):
    global delay
    for _ in range(steps):
        setStep2(1, 0, 0, 1); time.sleep(delay)
        setStep2(0, 1, 0, 1); time.sleep(delay)
        setStep2(0, 1, 1, 0); time.sleep(delay)
        setStep2(1, 0, 1, 0); time.sleep(delay)
    stop2()

# ... downward, upward, downward2, upward2 函数也保持不变 ...
def downward(steps):
    leftward(steps) # Stepper motor logic is often symmetrical

def upward(steps):
    rightward(steps)

def downward2(steps):
    leftward2(steps)

def upward2(steps):
    rightward2(steps)

# --- 5. 测试循环和主程序入口 (稍微修改) ---

def loop(angle):
    print("rightward--->leftward:")
    steps = int(angle / 360 * 6400)
    rightward(steps)
    leftward(steps)
    print("stop...")
    time.sleep(1)

def loop2(angle):
    print("upward--->downward:")
    steps = int(angle / 360 * 6400)
    upward2(steps)
    downward2(steps) # stop2() is already in downward2
    print("stop...")
    time.sleep(1)
    
if __name__ == '__main__':
    # 只需要在程序开始时调用一次 setup
    setup()
    try:
        while True:
            a = input("please input angle:")
            if not a: continue # Handle empty input
            
            t0 = time.time()
            loop(float(a))
            #loop2(float(a))
            
            print(f"Operation took: {time.time() - t0:.2f} seconds")
            
    except KeyboardInterrupt:
        print("\nCtrl+C pressed. Exiting.")
    except ValueError:
        print("Invalid input. Please enter a number.")
    finally:
        # 无论程序如何退出（正常结束或异常），都确保GPIO被清理
        destroy()
