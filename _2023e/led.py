import time

import RPi.GPIO as GPIO

# 红色激光笔控制引脚
LASER_PIN = 26
GND_PIN = 39  # 仅用于接地，无需在代码中设置

def setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LASER_PIN, GPIO.OUT)
    GPIO.output(LASER_PIN, GPIO.LOW)  # 默认关闭激光

def laser_on():
    GPIO.output(LASER_PIN, GPIO.HIGH)  # 打开激光

def laser_off():
    GPIO.output(LASER_PIN, GPIO.LOW)   # 关闭激光

def cleanup():
    GPIO.output(LASER_PIN, GPIO.LOW)
    GPIO.cleanup()

# 示例用法
if __name__ == "__main__":
    setup()
    try:
        laser_on()
        time.sleep(2)  # 激光亮2秒
        laser_off()
    finally:
        cleanup()