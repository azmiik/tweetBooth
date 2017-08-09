import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)

GPIO.setup(16, GPIO.IN)
GPIO.setup(20, GPIO.IN)
GPIO.setup(23, GPIO.IN)
GPIO.setup(18, GPIO.IN)
GPIO.setup(17, GPIO.IN)
GPIO.setup(27, GPIO.IN)
GPIO.setup(5, GPIO.IN)

GPIO.cleanup()
