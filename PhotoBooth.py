# This module contains the over arching Photo Booth class, and the Main Menu class

import os
import subprocess
import RPi.GPIO as GPIO
import pygame
import time
import threading

import FileHandler
import ButtonHandler
from print_on_screen import TextPrinter, ImagePrinter, CursorPrinter, screen_colour_fill

import config

class PhotoBooth(object):
    'PhotoBooth is the base class that each photobooth feature inherits from'

    # Set up a variable to hold our pygame 'screen'
    screen           = None
    filehandler      = None
    buttonhandler    = None
    size             = None
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
        ButtonHandler().light_button_leds('slr', False) # Turn off all LEDs
        pygame.quit()  # End our pygame session
        GPIO.cleanup() # Make sure we properly reset the GPIO ports we've used before exiting

        # Restore monitor blanking (TODO can we store previous values?)
        os.system("setterm -blank 30 -powerdown 30")

    def set_up_gpio(self):
        GPIO.setmode(GPIO.BCM)
        #GPIO.setup(camera_led_pin, GPIO.OUT, initial=False) # Set GPIO to output
        GPIO.setup(config.led_pin_select,GPIO.OUT) # The 'Select' button LED
        GPIO.setup(config.led_pin_left,GPIO.OUT) # The 'Left' button LED
        GPIO.setup(config.led_pin_right,GPIO.OUT) # The 'Right' button LED

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
        pygame.mouse.set_visible(False) # Hide the mouse cursor
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
        #os.system("sudo ./support/rpi-hdmi.sh off")

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
        self.screen.blit(screen_copy, (0,0))
        pygame.display.flip()
        #os.system("sudo ./support/rpi-hdmi.sh on")

        # Stop the thread which has been flashing the Select LED
        flash_led_stop.set()
        flash_led.join()

        # In case the thread was still running and turned off the Select LED,
        #    make sure all the buttons are lit
        self.buttonhandler.light_button_leds('lsr', True)


##########################################
### Photo Booth function OfficialPhoto ###
class OfficialPhoto(PhotoBoothFunction):
    'Class to take official portrait photographs'

    def __init__(self, photobooth):
        self.menu_text = "Take official profile photo (for Learn etc.)"

        self.booth_id = photobooth.get_booth_id()
        self.screen = photobooth.get_pygame_screen()
        self.filehandler = photobooth.get_file_handler()
        self.buttonhandler = photobooth.get_button_handler()

        self.local_file_dir = self.filehandler.get_local_file_dir()
        self.local_upload_file_dir = self.filehandler.get_upload_file_dir()
        self.remote_file_dir = self.filehandler.get_remote_file_dir()

        self.textprinter = TextPrinter(self.screen)
        self.imageprinter = ImagePrinter(self.screen)
        self.photohandler = PhotoHandler(self.screen, self.filehandler)

        # Set image definitions - width, height, dpi
        self.image_defs = [
            ['learn', 150, 150, 300],
            ['pure', 160, 185, 300],
            ['eevec', 100, 150, 300],
            ['office365', 300, 300, 300]
        ]

    def start(self, total_pics=PhotoBoothFunction.total_pics):
        # Take and display photos
        self.total_pics = total_pics

        # Display the instructions for this photobooth function
        total_pics_msg = str(self.total_pics) + " photo"
        if self.total_pics > 1:
            total_pics_msg += "s"
        self.instructions = [
            "A template will appear on screen",
            "Following that, " + total_pics_msg + " will be taken",
            "(red light will appear before each photo)",
            "Press the Start button to begin"
        ]
        choice = self.display_instructions()
        # If the user selected Exit, bail out
        if choice == "l":
            return

        self.take_photos()

        self.photohandler.show_photos_tiled(self.image_extension)
        time.sleep(2)
        choice = self.user_accept_photos()

        # See if user wants to accept photos
        if (choice == 'r'):
            self.process_photos()
            remote_upload_dir = self.upload_photos()

            if remote_upload_dir is None:
                self.display_upload_failed_message()
            else:
                remote_url_prefix = self.filehandler.get_remote_url_prefix()
                self.display_download_url(remote_url_prefix, remote_upload_dir)
        else:
            self.display_rejected_message()

    def take_photos(self):
        ################################# Step 1 - Initial Preparation ##########################
        super(OfficialPhoto, self).take_photos()

        ################################# Step 2 - Setup camera #################################
        # Make the image square, using the photo_width
        pixel_width = self.photo_width
        pixel_height = self.photo_width

        self.camera.resolution = (pixel_width, pixel_height)

        ################################# Step 3 - Start camera preview ########################
        screen_colour_fill(self.screen, config.black_colour)

        self.camera.start_preview()

        ################################# Step 4 - Prepare user ################################
        self.overlay_on_camera = OverlayOnCamera(self.camera)

        # Apply overlay images & messages to prepare the user
        self.overlay_on_camera.camera_overlay(config.face_target_overlay_image)
        time.sleep(self.prep_delay_short)
        self.overlay_on_camera.camera_overlay(config.face_target_fit_face_overlay_image)
        time.sleep(self.prep_delay_long)
        self.overlay_on_camera.camera_overlay(config.face_target_overlay_image)
        time.sleep(self.prep_delay_short)
        self.overlay_on_camera.camera_overlay(config.face_target_smile_overlay_image)
        time.sleep(self.prep_delay_long)
        self.overlay_on_camera.camera_overlay(config.face_target_overlay_image)
        time.sleep(self.prep_delay_short)

        ################################# Step 5 - Take Photos ################################
        self.take_photos_and_close_camera(self.capture_delay)

    def upload_photos(self):
        self.textprinter.print_text([["Uploading photos ...", 124, config.black_colour, "cm", 0]],
                                    0, True)

        remote_upload_dir = StringOperations().get_random_string(10)

        file_defs = [
            # Upload the ZIP archive of photos
            [os.path.join(self.local_upload_file_dir, '*.zip'), '',
             os.path.join(self.remote_file_dir, remote_upload_dir), 1, True],
            # Upload just the first of the photo files
            [os.path.join(self.local_file_dir, '*' + self.image_extension), 'photobooth_photo',
             os.path.join(self.remote_file_dir, remote_upload_dir), 1, True],
            # Upload the HTML file for this particular set of photos
            [os.path.join('html', 'individual', 'index-single.html'), 'index',
             os.path.join(self.remote_file_dir, remote_upload_dir), 1, True],
            # Make sure the base .htaccess and index files are in place
            [os.path.join('html', 'index.php'), '',
             self.remote_file_dir, 1, True],
            [os.path.join('html', 'redirect.html'), '',
             self.remote_file_dir, 1, True],
            [os.path.join('html', '.htaccess'), '',
             self.remote_file_dir, 1, True],
            # Make sure that all common files are in place
            [os.path.join('html', 'common', '*.css'), '',
             os.path.join(self.remote_file_dir, 'common'), 0, True],
        ]

        success = self.upload_photos_using_defs(file_defs)

        if success:
            return remote_upload_dir
        else:
            return None