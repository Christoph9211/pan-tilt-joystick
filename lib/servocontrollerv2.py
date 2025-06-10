from machine import Pin, PWM

class ServoController:
    def __init__(self, pins=[18, 19, 20, 21], freq=50):
        """
        Initialize the ServoController with given pins.
        
        Args:
            pins (list): List of GPIO pins to use for servos.
            freq (int): PWM frequency (default 50Hz for standard servos).
        """
        self._servos = [PWM(Pin(pin)) for pin in pins]
        self.freq = freq
        for servo in self._servos:
            servo.freq(freq)
    
    def servo(self, num, angle, degrees=180):
        """
        Set the angle of a servo motor.
        
        Args:
            num (int): Servo number (1-indexed).
            angle (float): Desired angle.
            degrees (int): Maximum degrees of rotation (default 180).
            
        Raises:
            ValueError: If servo number or angle is out of bounds.
        """
        if not 1 <= num <= len(self._servos):
            raise ValueError(f"Servo number must be between 1 and {len(self._servos)}")
        if not 0 <= angle <= degrees:
            raise ValueError(f"Angle must be between 0 and {degrees}")
        
        # Map angle to duty cycle (2.5% to 12.5%)
        duty = int(((angle / degrees) * 8000) + 3000)
        self._servos[num - 1].duty_u16(duty)
        print(f"Servo {num}: angle={angle}, duty={duty}")  # Debug log
    
    def release(self, num=None):
        """
        Release servo(s) to stop holding position.
        
        Args:
            num (int, optional): Servo number to release. If None, releases all servos.
        """
        if num is not None:
            if not 1 <= num <= len(self._servos):
                raise ValueError(f"Servo number must be between 1 and {len(self._servos)}")
            self._servos[num - 1].duty_u16(0)
            print(f"Servo {num} released")  # Debug log
        else:
            for i, servo in enumerate(self._servos, start=1):
                servo.duty_u16(0)
                print(f"Servo {i} released")  # Debug log
    
    def cleanup(self):
        """
        Deinitialize all PWM objects.
        """
        for servo in self._servos:
            servo.deinit()
        print("All servos deinitialized")  # Debug log
