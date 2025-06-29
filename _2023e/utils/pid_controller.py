# utils/pid_controller.py
import time

class PID:
    def __init__(self, Kp, Ki, Kd, setpoint=0):
        self.Kp, self.Ki, self.Kd = Kp, Ki, Kd
        self.setpoint = setpoint
        self.last_error, self.integral = 0, 0
        self.last_time = time.time()

    def compute(self, current_value):
        """计算PID输出"""
        now = time.time()
        dt = now - self.last_time
        
        error = self.setpoint - current_value
        self.integral += error * dt
        derivative = (error - self.last_error) / dt
        
        output = self.Kp * error + self.Ki * self.integral + self.Kd * derivative
        
        self.last_error = error
        self.last_time = now
        
        return output