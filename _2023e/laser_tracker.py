import time
import gpiod
import cv2
import numpy as np

# --- 1. 全局硬件配置 ---

# 确认GPIO控制器芯片名称
# - 树莓派 5: 'gpiochip4'
# - 树莓派 4/3/2: 'gpiochip0'
CHIP_NAME = 'gpiochip4'

# 定义电机引脚 (BCM编号)
PINS_MOTOR1 = [4, 14, 22, 23]  # [IN1, IN2, IN3, IN4]
PINS_MOTOR2 = [6, 12, 5, 27]   # [IN1, IN2, IN3, IN4]

# 定义激光笔引脚
PIN_LASER = 26

# 将所有需要控制的引脚合并到一个列表中
ALL_PINS = PINS_MOTOR1 + PINS_MOTOR2 + [PIN_LASER]
# 找到激光引脚在ALL_PINS列表中的索引，方便后面单独控制
LASER_PIN_OFFSET = ALL_PINS.index(PIN_LASER)

# 全局变量
lines = None  # 用于持有gpiod线路对象

# --- 2. 统一的GPIO初始化和清理 ---

def setup_gpio():
    """
    初始化所有GPIO，请求并配置所有需要的引脚。
    """
    global lines
    try:
        chip = gpiod.Chip(CHIP_NAME)
        lines = chip.get_lines(ALL_PINS)
        lines.request(
            consumer="laser_motor_controller",
            type=gpiod.LINE_REQ_DIR_OUT,
            default_vals=[0] * len(ALL_PINS)  # 默认所有引脚都为低电平
        )
        print("GPIO setup successful.")
    except Exception as e:
        print(f"GPIO setup failed: {e}")
        print("Please ensure CHIP_NAME is correct for your Pi and run with 'sudo'.")
        exit(1)

def cleanup_gpio():
    """
    释放所有GPIO引脚。
    """
    global lines
    if lines:
        # 在释放前确保所有引脚为低电平
        lines.set_values([0] * len(ALL_PINS))
        lines.release()
        print("GPIO cleaned up.")

# --- 3. 硬件控制函数 (激光和电机) ---

def laser_on():
    if lines:
        lines.set_value(LASER_PIN_OFFSET, 1) # 设置激光引脚为高电平
        print("Laser ON")

def laser_off():
    if lines:
        lines.set_value(LASER_PIN_OFFSET, 0) # 设置激光引脚为低电平
        print("Laser OFF")

def motors_off():
    """
    通过将所有电机引脚设置为低电平来给电机断电。
    """
    if lines:
        # 创建一个包含所有引脚状态的列表，默认为当前状态
        current_values = lines.get_values()
        # 将电机1和电机2对应的引脚全部设为0
        for i in range(len(PINS_MOTOR1) + len(PINS_MOTOR2)):
            current_values[i] = 0
        lines.set_values(current_values)
        print("Motors de-energized.")

# --- 4. 视觉处理函数 ---

def find_laser_dot(frame):
    """
    在图像帧中寻找红色激光点，返回其中心坐标。
    """
    # 将图像从BGR色彩空间转换到HSV色彩空间
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # 定义红色的HSV范围。红色在HSV中可能跨越0/180，所以定义两个范围
    # 范围1 (偏暗的红色)
    lower_red1 = np.array([0, 120, 70])
    upper_red1 = np.array([10, 255, 255])
    mask1 = cv2.inRange(hsv_frame, lower_red1, upper_red1)

    # 范围2 (偏紫的红色)
    lower_red2 = np.array([170, 120, 70])
    upper_red2 = np.array([180, 255, 255])
    mask2 = cv2.inRange(hsv_frame, lower_red2, upper_red2)
    
    # 合并两个掩码
    mask = mask1 + mask2

    # 可选：使用形态学操作去除噪点
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # 寻找掩码中的轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # 如果找到了轮廓，找出最大的那个（激光点通常是最大最亮的）
    if contours:
        # 找到面积最大的轮廓
        max_contour = max(contours, key=cv2.contourArea)
        
        # 仅处理面积大于某个阈值的轮廓，以防噪点干扰
        if cv2.contourArea(max_contour) > 10:
            # 计算最大轮廓的中心
            M = cv2.moments(max_contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                return (cx, cy)
    
    return None # 如果没有找到激光点，返回None

# --- 5. 主程序 ---

if __name__ == "__main__":
    # 初始化GPIO
    setup_gpio()

    # 初始化摄像头
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("错误：无法打开摄像头。")
        cleanup_gpio()
        exit()
    print("Camera initialized.")

    try:
        # 1. 给电机断电，使其可以自由转动
        motors_off()
        
        # 2. 打开激光笔
        laser_on()
        
        print("\nMotors are off. Please manually position the laser.")
        print("The program is now tracking the red dot.")
        print("Press 'q' in the video window to quit.")

        # 3. 循环识别激光点
        while True:
            ret, frame = cap.read()
            if not ret:
                print("无法接收帧，退出...")
                break

            # 翻转图像，如果你的摄像头是倒置安装的
            # frame = cv2.flip(frame, -1)

            # 寻找激光点位置
            dot_position = find_laser_dot(frame)

            # 在画面上标记并打印坐标
            if dot_position:
                cx, cy = dot_position
                # 在原图上画一个圈来标记激光点
                cv2.circle(frame, (cx, cy), 15, (0, 255, 0), 2)
                cv2.putText(frame, f"({cx}, {cy})", (cx + 10, cy - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                print(f"Laser dot detected at: ({cx}, {cy})")
            else:
                print("Laser dot not found.")

            # 显示图像
            cv2.imshow('Laser Tracker - Press Q to Quit', frame)

            # 等待按键，如果按下 'q' 则退出
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    except KeyboardInterrupt:
        print("\nCtrl+C pressed. Exiting.")

    finally:
        # 确保所有资源都被正确释放
        print("\nCleaning up resources...")
        laser_off()
        cleanup_gpio()
        cap.release()
        cv2.destroyAllWindows()
        print("Cleanup complete. Program terminated.")