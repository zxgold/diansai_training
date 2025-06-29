# config.py

# --- 摄像头相关配置 ---
CAMERA_INDEX = 0             # 摄像头索引号，通常是0
FRAME_WIDTH = 1280           # 摄像头捕获宽度
FRAME_HEIGHT = 720           # 摄像头捕获高度

# --- 视觉处理相关配置 ---
# HSV 颜色范围 (需要你用工具实际标定)
RED_LOWER = (0, 120, 70)     # 红色的HSV下限
RED_UPPER = (10, 255, 255)
GREEN_LOWER = (35, 100, 100) # 绿色的HSV下限
GREEN_UPPER = (85, 255, 255)

# 屏幕标定后的尺寸 (像素)，1像素=1mm
SCREEN_STD_WIDTH = 500       # 500mm
SCREEN_STD_HEIGHT = 500      # 500mm

# --- 云台硬件相关配置 ---
# 红色云台步进电机GPIO引脚
RED_GIMBAL_X_STEP = 17
RED_GIMBAL_X_DIR = 27
RED_GIMBAL_Y_STEP = 22
RED_GIMBAL_Y_DIR = 23

# 绿色云台步进电机GPIO引脚
GREEN_GIMBAL_X_STEP = 5
GREEN_GIMBAL_X_DIR = 6
GREEN_GIMBAL_Y_STEP = 13
GREEN_GIMBAL_Y_DIR = 19

MOTOR_DELAY = 0.001          # 步进电机脉冲延迟，控制速度

# --- PID控制器相关配置 ---
PID_KP = 0.8                 # P - 比例增益
PID_KI = 0.05                # I - 积分增益
PID_KD = 0.1                 # D - 微分增益