import cv2

# 1. 创建一个VideoCapture对象
# 参数 0 表示使用系统中的第一个摄像头 (/dev/video0)
cap = cv2.VideoCapture(0)

# 2. 检查摄像头是否成功打开
if not cap.isOpened():
    print("错误：无法打开摄像头。")
    exit()

# 3. 循环读取摄像头的每一帧
while True:
    # cap.read() 返回两个值：
    # - ret: 一个布尔值，如果成功读取到帧，则为 True
    # - frame: 捕获到的图像帧 (一个 NumPy 数组)
    ret, frame = cap.read()

    # 如果没有成功读取到帧 (例如摄像头被拔出)，则退出循环
    if not ret:
        print("无法接收帧，可能已到达视频流末尾。正在退出...")
        break

    # 4. 在这里可以对 'frame' 进行你的视觉处理！
    # 例如：转换成灰度图
    # gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # 5. 显示原始图像帧
    cv2.imshow('My Vision Module - Press Q to Quit', frame)

    # 6. 等待按键，如果按下 'q'，则退出循环
    # cv2.waitKey(1) 表示等待1毫秒
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 7. 循环结束后，释放摄像头资源并关闭所有窗口
print("正在释放资源...")
cap.release()
cv2.destroyAllWindows()