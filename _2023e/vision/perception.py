import time
import gpiod
import cv2
import numpy as np

# --- 配置区 ---
# --- 硬件配置 ---
# 使用 `gpioinfo` 命令查找正确的芯片名称
# 树莓派通常是 "gpiochip0"
# Jetson 设备可能是 "gpiochip0" 或 "gpiochip4"
CHIP_NAME = "gpiochip4"      # <--- 请根据你的设备修改！
LASER_PIN = 26               # 使用的GPIO BCM编号
CAM=ERA_INDEX = 0             # 摄像头索引，通常是0

# --- 图像处理配置 ---
# 这是检测微小、不清晰激光点的关键！
# 强烈建议使用调参脚本找到最佳值，然后更新到这里。
# 这是一个示例范围，可能需要你微调。
LOWER_RED = np.array([160, 70, 70]) # HSV下限 [色相, 饱和度, 亮度]
UPPER_RED = np.array([179, 255, 255]) # HSV上限

# 轮廓面积筛选，用于过滤噪声和大型干扰物
MIN_LASER_AREA = 1    # 激光点轮廓的最小面积（像素）
MAX_LASER_AREA = 50  # 激光点轮廓的最大面积（像素）

# --- 函数定义 ---

def detect_laser_position_improved(frame):
    """
    从给定的帧中检测激光点位置。
    这个版本经过优化，更适合检测微小或不清晰的激光点。
    
    1. 使用精确的HSV范围进行颜色过滤。
    2. 使用形态学开运算去除小的背景噪声。
    3. 筛选出在合理面积范围内的轮廓，而不是简单地取最大轮廓。
    """
    # 1. 转换到HSV色彩空间
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # 2. 创建颜色掩码
    # 注意：如果你的红色范围跨越0，需要像原始代码那样创建两个掩码并合并
    # 如果你的红色范围不跨越0（例如都在160-179之间），一个掩码就够了
    mask = cv2.inRange(hsv, LOWER_RED, UPPER_RED)

    # 3. 形态学开运算：去除小的白色噪点，让激光点轮廓更清晰
    # kernel = np.ones((3, 3), np.uint8)
    # mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # 4. 寻找所有轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    cx, cy = None, None
    
    # 5. 遍历所有找到的轮廓，进行筛选
    if contours:
        best_contour = None
        max_area_found = 0

        for contour in contours:
            area = cv2.contourArea(contour)
            # 筛选条件：面积必须在预设的最小和最大值之间
            if MIN_LASER_AREA < area < MAX_LASER_AREA:
                # 在所有符合条件的轮廓中，我们依然选择最大的那个
                if area > max_area_found:
                    max_area_found = area
                    best_contour = contour
        
        # 如果找到了最佳轮廓，则计算其中心点
        if best_contour is not None:
            M = cv2.moments(best_contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                # 在原始帧上标记，以便在窗口中显示
                cv2.circle(frame, (cx, cy), 10, (0, 255, 0), 2)
                cv2.putText(frame, f"({cx},{cy})", (cx + 15, cy + 5), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    return cx, cy

# --- 主程序 ---

if __name__ == "__main__":
    # 初始化所有硬件资源为 None
    cap = None
    chip = None
    laser_line = None

    try:
        # --- 1. 初始化硬件 ---
        print("正在初始化摄像头...")
        cap = cv2.VideoCapture(CAMERA_INDEX)
        if not cap.isOpened():
            raise IOError(f"无法打开摄像头索引 {CAMERA_INDEX}")
        # 设置摄像头分辨率（添加这部分）
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # 宽度
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)  # 高度
        print("正在初始化GPIO...")
        chip = gpiod.Chip(CHIP_NAME)
        laser_line = chip.get_line(LASER_PIN)
        laser_line.request(consumer="laser_control", type=gpiod.LINE_REQ_DIR_OUT)
        
        # --- 2. 开启激光 ---
        print("开启激光...")
        laser_line.set_value(1)
        time.sleep(1) # 等待1秒，让激光和摄像头曝光稳定

        # --- 3. 进入主循环 ---
        print("开始检测... 按下 'ESC' 键或 Ctrl+C 退出。")
        while True:
            ret, frame = cap.read()
            if not ret:
                print("无法读取摄像头画面，退出...")
                break
            
            # 使用改进的函数检测激光位置
            x, y = detect_laser_position_improved(frame)
            
            if x is not None:
                # 打印到控制台，可以限制打印频率以避免刷屏
                print(f"检测到激光点位置: ({x}, {y})") 
                pass # 坐标已经显示在图像上了
            
            # 显示结果画面
            cv2.imshow("Laser Detection", frame)
            
            # 按 ESC 键也可以退出循环
            if cv2.waitKey(1) & 0xFF == 27:
                print("检测到 'ESC' 按键，正在退出...")
                break
            
    except KeyboardInterrupt:
        print("\n检测到用户中断 (Ctrl+C)...")
        
    except Exception as e:
        print(f"发生错误: {e}")

    finally:
        # --- 4. 清理所有资源 ---
        # 这个块里的代码无论程序是正常结束、出错还是被中断，都一定会执行
        print("正在清理资源...")
        if laser_line:
            print("关闭激光...")
            laser_line.set_value(0) # 确保关闭激光
            laser_line.release()
        if chip:
            chip.close()
        if cap:
            print("释放摄像头...")
            cap.release()
        
        cv2.destroyAllWindows()
        print("程序已终止。")

