#!/usr/bin/env python
# Each Photo function has its own class

import os
import time
import picamera  # http://picamera.readthedocs.org/en/release-1.4/install2.html
import subprocess
from PIL import Image
import threading
import random

from PrintOnScreen import OverlayOnCamera, TextPrinter, ImagePrinter, screen_colour_fill
from PhotoHandler import PhotoHandler

import config


class PhotoBoothFunction(object):
    'Base class for all the different Photo Booth functions'

    # Set up class variables that are common to all photobooth features
    menu_text = ""
    instructions = ""

    prep_delay_short = 2
    prep_delay_long = 3
    total_pics = 4  # Default number of pics to be taken

    capture_delay = 2  # Default delay between pics

    photo_width = 880
    screen = None

    filehandler = None
    textprinter = None
    imageprinter = None
    photohandler = None
    buttonhandler = None

    local_file_dir = None
    local_upload_file_dir = None
    remote_file_dir = None

    booth_id = ""

    image_extension = ".jpg"
    animated_image_extension = ".gif"
    photo_file_prefix = "photobooth"
    zip_filename = "photobooth_photos.zip"

    image_defs = []

    camera = None

    def __init__(self, photobooth):
        self.booth_id = photobooth.get_booth_id()
        self.screen = photobooth.get_pygame_screen()
        self.filehandler = photobooth.get_file_handler()
        self.buttonhandler = photobooth.get_button_handler()

        self.local_file_dir = self.filehandler.get_local_file_dir()
        self.local_upload_file_dir = self.filehandler.get_upload_file_dir()
        self.remote_file_dir = self.filehandler.get_remote_file_dir()

    def get_menu_text(self):
        return self.menu_text

    # Do some common setup, that all child classes need
    def take_photos(self):
        # Make a timestamped note in the console
        now = time.strftime("%Y-%m-%d-%H:%M:%S")
        print "Take photos - " + self.menu_text + ": " + now

        # Clear the local file directory, and the upload directory
        self.filehandler.delete_local_files()
        self.filehandler.delete_upload_files()

        # Get hold of the camera
        self.camera = picamera.PiCamera()
        self.camera.led = False
        self.camera.vflip = True
        self.camera.hflip = False

    # The Parent class's take_photos is barebones - to be called from Child instance
    def take_photos_and_close_camera(self, capture_delay):
        if (self.camera is None):
            return

        try:  # Take the photos
            self.camera.led = True
            time.sleep(0.25)  # Light the LED for just a bit

            local_file_dir = self.filehandler.get_local_file_dir()
            manipulate_thread_list = []

            # Take photos
            for i, filepath in enumerate(self.camera.capture_continuous(os.path.join(local_file_dir,
                                                                                     self.photo_file_prefix + '-' + '{counter:02d}' + self.image_extension))):
                print('Saving to ' + filepath)
                self.camera.led = False

                # Each photobooth function can override manipulate_photo() to process
                #     the photos before they are saved to disk
                # Kick off the processing in a separate thread, so as not to delay the photo taking
                manipulate_thread_list.append(threading.Thread(target=self.manipulate_photo,
                                                               args=(filepath,)))
                manipulate_thread_list[len(manipulate_thread_list) - 1].start()

                # If we have finished taking our photos, bail out
                if i == self.total_pics - 1:
                    break

                # Also provide a way for user to break out, by pressing Left button
                # TODO: Make this optional though function param?
                if self.buttonhandler.button_is_down(config.button_pin_left):
                    break

                time.sleep(capture_delay)  # pause in-between shots
                self.camera.led = True
                time.sleep(0.25)  # Light the LED for just a bit
        finally:
            self.camera.stop_preview()
            self.camera.close()
            self.camera = None

            # Wait for MainputlatePhoto() calls to end
            self.textprinter.print_text([["Please wait ...", 124, config.black_colour, "cm", 0]], 0, False)
            for curr_thread in manipulate_thread_list:
                curr_thread.join()

    # *** Display the instruction screen for the current photobooth function ***
    def display_instructions(self):
        instructions_msg = []
        for curr_line in self.instructions:
            instructions_msg.append([curr_line, 84, config.off_black_colour, "c", 0])

        # Print the heading on the screen
        self.textprinter.print_text([[self.menu_text,
                                      84,
                                      config.blue_colour,
                                      "ct",
                                      5]],
                                    0,
                                    True)

        self.textprinter.print_text(instructions_msg, 40, False)

        self.imageprinter.print_images([[config.start_overlay_image, 'cb', 0, 0]], False)
        self.imageprinter.print_images([[config.menu_side_overlay_image, 'lb', 0, 0]], False)

        # Wait for the user to press the Select button to exit to menu
        choice = ""
        while True:
            choice = self.buttonhandler.wait_for_buttons('ls', True)

            if (choice != 'screensaver'):
                break

        return choice

    def user_accept_photos(self):
        choice = None
        images_to_print = [
            [config.reject_overlay_image, 'lb', 0, 0],
            [config.accept_overlay_image, 'rb', 0, 0]
        ]

        self.imageprinter.print_images(images_to_print, False)

        while True:
            choice = self.buttonhandler.wait_for_buttons('lr', True)

            if (choice != 'screensaver'):
                break

        return choice

    def display_rejected_message(self):
        print "Photos rejected"
        self.textprinter.print_text([["Photos rejected", 124, config.black_colour, "cm", 0]], 0, True)
        time.sleep(2)

    # *** Show user where their photos have been uploaded to ***
    def display_download_url(self, remote_url_prefix, remote_upload_dir):
        download_url_msg = [
            ["To get your photos, visit:", 84, config.off_black_colour, "c", 0],
            [remote_url_prefix, 84, config.blue_colour, "c", 0],
            ["and enter your photobooth code:", 84, config.off_black_colour, "c", 0],
            [remote_upload_dir, 92, config.blue_colour, "c", 0]
        ]

        self.textprinter.print_text(download_url_msg, 40, True)

        self.imageprinter.print_images([[config.menu_overlay_image, 'cb', 0, 0]], False)

        # Wait for the user to press the Select button to exit to menu
        while True:
            choice = self.buttonhandler.wait_for_buttons('s', True)

            if (choice != 'screensaver'):
                break

    # *** If the upload threw an exception, apologise to the user ***
    def display_upload_failed_message(self):
        download_url_msg = [
            ["Upload Failed ... Sorry", 124, config.black_colour, "cm", 0]
        ]

        self.textprinter.print_text(download_url_msg, 40, True)

        self.imageprinter.print_images([[config.menu_overlay_image, 'cb', 0, 0]], False)

        # Wait for the user to press the Select button to exit to menu
        while True:
            choice = self.buttonhandler.wait_for_buttons('s', True)

            if (choice != 'screensaver'):
                break

    # A function to manipulate a just-taken photo, to override if necessary
    def manipulate_photo(self, filepath):
        pass

    def process_photos(self):
        self.textprinter.print_text([["Processing photos ...", 124, config.black_colour, "cb", 25]],
                                    0, True)
        self.photohandler.prepare_images(self.image_extension, self.image_defs, True)
        self.filehandler.zip_images(self.image_extension, self.zip_filename)

    def upload_photos_using_defs(self, file_defs):
        success = True

        try:
            self.filehandler.upload_files(file_defs)
        except subprocess.CalledProcessError as e:
            # If our upload threw an exception, then return 'None' in remote_upload_dir to let caller know
            # TODO: Check the actual error that came back, in case the upload was actually successful?
            success = False

        return success

    def set_total_pics(self, num_pics):
        self.total_pics = num_pics


##########################################
### Photo function TweetPhoto ###
class TwitterPhoto(PhotoBoothFunction):
    'Class to take picture and post to twitter'

    def __init__(self, photobooth):
        self.menu_text = "Tweet Photo"

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
            ['twitter', 880, 440, 72],
        ]

    def start(self, total_pics=PhotoBoothFunction.total_pics):
        # Take and display photos
        self.total_pics = total_pics

        # Display the instructions for this photobooth function
        total_pics_msg = str(self.total_pics) + " photo"
        if self.total_pics > 1:
            total_pics_msg += "s"
        self.instructions = [
            "Get Ready, " + total_pics_msg + " will be taken",
            "buttons below will count down before each picture",
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
        super(TwitterPhoto, self).take_photos()

        ################################# Step 2 - Setup camera #################################
        # Make the image square, using the photo_width
        pixel_width = self.photo_width
        pixel_height = self.photo_width / 2

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

        success = True

        if success:
            return remote_upload_dir
        else:
            return None


class StringOperations(object):
    def __init__(self):
        pass

    def get_random_string(self, str_len):
        # Miss out easy-to-confuse characters 'lI1O0'
        chars = 'abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789_-'
        # chars = string.ascii_letters + string.digits + '_-'
        result = ''.join(random.choice(chars) for i in range(str_len))
        return result
