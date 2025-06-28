import cv2
import numpy as np

print("脚本开始运行...")
print("尝试打开摄像头...")

# 1. 打开摄像头
# 参数 0 表示系统中的第一个摄像头
cap = cv2.VideoCapture(0)

# 检查摄像头是否成功打开
if not cap.isOpened():
    print("错误：无法打开摄像头。请检查摄像头是否连接正确，或是否被其他程序占用。")
    exit()

print("摄像头成功打开！按 'q' 键退出程序。")
print("请确保用鼠标点击一下弹出的窗口，使其获得焦点。")

# 2. 无限循环，处理摄像头的每一帧
while True:
    # 读取一帧图像
    ret, frame = cap.read()

    # 如果 ret 为 False，说明没有成功读取到帧（比如摄像头被拔出）
    if not ret:
        print("无法接收帧，可能已到达视频流末尾或摄像头断开。正在退出...")
        break

    # --- 图像处理核心区域 ---

    # A. 预处理：转为灰度图并进行高斯模糊
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)

    # B. 自适应阈值化：这是提取低对比度线条的关键！
    # 参数可以根据你的光照环境进行微调
    binary_image = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                         cv2.THRESH_BINARY_INV, 21, 5)

    # C. (可选) 形态学操作：清理噪点，连接断线
    kernel = np.ones((3,3), np.uint8)
    processed_image = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, kernel, iterations=2)

    # D. 霍夫直线检测：在处理后的二值图像上寻找直线
    lines = cv2.HoughLinesP(processed_image, 1, np.pi / 180, threshold=80,
                            minLineLength=50, maxLineGap=15)

    # E. 在原始彩色图像上绘制结果
    # 我们在一个副本上绘制，以保持原始 'frame' 不变
    result_frame = frame.copy()
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # 用鲜艳的红色粗线条画出检测到的直线
            cv2.line(result_frame, (x1, y1), (x2, y2), (0, 0, 255), 3)

    # --- 显示结果 ---
    
    # 显示最终带有检测结果的图像
    cv2.imshow("Line Detection Result", result_frame)
    
    # (调试用) 显示处理过程中的二值图像，方便你调整参数
    cv2.imshow("Processed Binary Image", processed_image)


    # 3. 监听键盘按键
    # cv2.waitKey(1) 会等待1毫秒，看是否有按键。
    # & 0xFF 是一个 recomendado 的位掩码，用于确保在所有系统上都能正确读取按键的ASCII码
    key = cv2.waitKey(1) & 0xFF

    # 如果按下的键是 'q'
    if key == ord('q'):
        print("检测到按键 'q'，正在退出循环...")
        break

# 4. 循环结束后，释放资源
print("正在释放摄像头并关闭所有窗口...")
cap.release()
cv2.destroyAllWindows()
print("程序已成功退出。")