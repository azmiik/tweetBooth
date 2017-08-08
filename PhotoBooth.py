# This module contains the over arching Photo Booth class, and the Main Menu class

import os
import subprocess
import RPi.GPIO as GPIO
import pygame
import time
import threading

from FileHandler import FileHandler
from ButtonHandler import ButtonHandler
from PrintOnScreen import TextPrinter, ImagePrinter, CursorPrinter, screen_colour_fill

import config


class PhotoBooth(object):
    'PhotoBooth is the base class that each photobooth feature inherits from'

    # Set up a variable to hold our pygame 'screen'
    screen = None
    filehandler = None
    buttonhandler = None
    size = None
    local_dirs_ready = True

    # For photobooth functions that upload photos into a dated folder,
    #    we should prefix the date URL with an ID number,
    #    and each hardware (that uploads to the same server) should change the following booth_id
    # TODO: Don't need to use it until we have more than one booth set up.
    booth_id = ""

    def __init__(self):
        self.set_up_gpio()
        self.init_pygame()
        self.buttonhandler = ButtonHandler()

        try:
            self.filehandler = FileHandler()
        except subprocess.CalledProcessError as e:
            self.local_dirs_ready = False

        # Stop the monitor blanking after inactivity
        os.system("setterm -blank 0 -powerdown 0")

    def __del__(self):
        print "Destructing PhotoBooth instance"

    def tidy_up(self):
        # NOTE: This was the __del__ method, but seems more reliable to call explicitly
        print "Tidying up PhotoBooth instance"
        ButtonHandler().light_button_leds('slr', False)  # Turn off all LEDs
        pygame.quit()  # End our pygame session
        GPIO.cleanup()  # Make sure we properly reset the GPIO ports we've used before exiting

        # Restore monitor blanking (TODO can we store previous values?)
        os.system("setterm -blank 30 -powerdown 30")

    def set_up_gpio(self):
        GPIO.setmode(GPIO.BCM)
        # GPIO.setup(camera_led_pin, GPIO.OUT, initial=False) # Set GPIO to output
        GPIO.setup(config.led_pin_select, GPIO.OUT)  # The 'Select' button LED
        GPIO.setup(config.led_pin_left, GPIO.OUT)  # The 'Left' button LED
        GPIO.setup(config.led_pin_right, GPIO.OUT)  # The 'Right' button LED

        # Detect falling edge on all buttons
        GPIO.setup(config.button_pin_select, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(config.button_pin_left, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(config.button_pin_right, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(config.button_pin_exit, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # Drumminhands found it necessary to switch off LEDs initially
        GPIO.output(config.led_pin_select, False)
        GPIO.output(config.led_pin_left, False)
        GPIO.output(config.led_pin_right, False)

    def init_pygame(self):
        pygame.init()
        self.size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
        print "Initialised PyGame: Screen Width " + str(self.size[0]) + " x Height " + str(self.size[1])

        pygame.display.set_caption('Photo Booth')
        pygame.mouse.set_visible(False)  # Hide the mouse cursor
        self.screen = pygame.display.set_mode(self.size, pygame.FULLSCREEN)

    def get_booth_id(self):
        return self.booth_id

    def get_pygame_screen(self):
        return self.screen

    def get_button_handler(self):
        return self.buttonhandler

    def get_file_handler(self):
        return self.filehandler

    def screen_saver(self):
        # If we have been waiting at the Main Menu for too long
        # then blank the screen, and pulse the Select button

        # Turn off the Left and Right button LEDs
        self.buttonhandler.light_button_leds('lr', False)

        # Make a copy of what is currently displayed on the screen
        screen_copy = pygame.Surface.copy(self.screen)

        # Turn off the screen
        screen_colour_fill(self.screen, config.black_colour)
        # os.system("sudo ./support/rpi-hdmi.sh off")

        # Start a separate thread to flash the Select LED
        flash_led_stop = threading.Event()
        flash_led = threading.Thread(target=self.buttonhandler.flash_button_leds,
                                     args=('s', 1, flash_led_stop))
        flash_led.start()

        # Wait until the Select button is pressed
        while not self.buttonhandler.button_is_down(config.button_pin_select):
            time.sleep(0.2)

        # Come out of screen saver
        # Turn on the button LEDs
        self.buttonhandler.light_button_leds('lsr', True)

        # Show the copy of the display that we made before going into screensaver
        self.screen.blit(screen_copy, (0, 0))
        pygame.display.flip()
        # os.system("sudo ./support/rpi-hdmi.sh on")

        # Stop the thread which has been flashing the Select LED
        flash_led_stop.set()
        flash_led.join()

        # In case the thread was still running and turned off the Select LED,
        #    make sure all the buttons are lit
        self.buttonhandler.light_button_leds('lsr', True)
