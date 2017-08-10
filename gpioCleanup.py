import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

GPIO.setup(16, GPIO.IN)
GPIO.setup(20, GPIO.IN)
GPIO.setup(23, GPIO.IN)
GPIO.setup(18, GPIO.IN)
GPIO.setup(17, GPIO.IN)
GPIO.setup(27, GPIO.IN)
GPIO.setup(5, GPIO.IN)

led_pin_select = 16
led_pin_left = 23
led_pin_right = 17

GPIO.setup(led_pin_select, GPIO.OUT)  # The 'Select' button LED
GPIO.setup(led_pin_left, GPIO.OUT)  # The 'Left' button LED
GPIO.setup(led_pin_right, GPIO.OUT)  # The 'Right' button LED

for i in range(10):
    GPIO.output(led_pin_select, GPIO.HIGH)
    GPIO.output(led_pin_left, GPIO.HIGH)
    GPIO.output(led_pin_right, GPIO.HIGH)

    time.sleep(1)

    GPIO.output(led_pin_select, GPIO.LOW)
    GPIO.output(led_pin_left, GPIO.LOW)
    GPIO.output(led_pin_right, GPIO.LOW)

    time.sleep(1)

GPIO.cleanup()
