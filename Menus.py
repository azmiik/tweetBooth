#!/usr/bin/env python
# This module contains the over arching Photo Booth class, and the Main Menu class


import time

import config


from print_on_screen import TextPrinter, ImagePrinter, CursorPrinter, screen_colour_fill


class Menus(object):
    'A class to handle the Main Menu'

    photobooth    = None
    buttonhandler = None

    # Set the text attributes for the main menu heading
    heading_font_colour = config.blue_colour

    # Set the text attributes for the menu item display
    menu_font_size      = 64
    menu_font_colour    = config.black_colour
    menu_item_alignment = "lm"
    menu_item_position  = 20

    menu_cursor_font_size   = 64
    menu_cursor_font_colour = config.blue_colour

    menu_item_line_spacing = 20
    menu_option_rects      = None

    # menu_objects holds instances of each Photo Booth function class that
    #    is added to the Main Menu
    menu_objects = []

    def __init__(self, photobooth):
        self.photobooth    = photobooth
        self.screen        = photobooth.get_pygame_screen()
        self.buttonhandler = photobooth.get_button_handler()
        self.textprinter   = TextPrinter(self.screen)
        self.imageprinter  = ImagePrinter(self.screen)

        screen_colour_fill(self.screen, config.white_colour)

    def __del__(self):
        print "Destructing Menus instance"
        self.photobooth = None

    def add_main_menu_item(self, item_class):
        self.menu_objects.append(item_class)

    def display_main_menu(self):
        self.text_defs  = []
        self.image_defs = []

        # Print the heading on the screen
        self.textprinter.print_text( [["Welcome to the Photo Booth",
                                       120,
                                       self.heading_font_colour,
                                       "ct",
                                       5]],
                                     0,
                                     True )

        # Print the main menu items
        for item_class in self.menu_objects:
            self.text_defs.append( [item_class.get_menu_text(),
                                    self.menu_font_size,
                                    self.menu_font_colour,
                                    self.menu_item_alignment,
                                    self.menu_item_position] )

        self.menu_option_rects = self.textprinter.print_text( self.text_defs,
                                                              self.menu_item_line_spacing,
                                                              False )

        # Print the image overlays onto the screen
        self.image_defs = [
            [config.go_up_overlay_image,   'lb', 0, 0],
            [config.go_down_overlay_image, 'rb', 0, 0],
            [config.select_overlay_image,  'cb', 0, 0]
        ]

        self.imageprinter.print_images(self.image_defs, False)

    def get_main_menu_selection(self):
        self.cursorprinter = CursorPrinter(self.screen, self.menu_cursor_font_size,
                                           self.menu_cursor_font_colour)

        self.menu_choice   = 0

        # Print the initial cursor at the first menu option
        self.cursorprinter.print_cursor(self.menu_option_rects, self.menu_choice)

        while True:
            self.button = self.buttonhandler.wait_for_buttons('lsr', False)
            if self.button == 'l':
                if self.menu_choice > 0:
                    self.menu_choice -= 1
                    self.cursorprinter.print_cursor( self.menu_option_rects, self.menu_choice)
            if self.button == 'r':
                if self.menu_choice < len(self.menu_option_rects) - 1:
                    self.menu_choice += 1
                    self.cursorprinter.print_cursor( self.menu_option_rects, self.menu_choice)
            if self.button == 's':
                self.buttonhandler.light_button_leds('lsr', False)
                break

            if self.button == 'exit':
                # The user pressed the exit button - how long did they keep it pressed for?
                self.start_time = time.time()
                time.sleep(0.2)

                self.menu_choice = -1 # -1 indicates a short exit button
                while self.buttonhandler.button_is_down(config.button_pin_exit):
                    time.sleep(0.2)
                    # If the exit button is held down for longer than 3 seconds
                    # then record a 'long exit button press'
                    if time.time() - self.start_time > 3:
                        self.menu_choice = -2 # -2 indicates a long exit button press
                        break

                break

            # If we have been sitting at the Main Menu for longer than screen_saver_seconds secs
            # then go into screen_saver mode.
            if self.button == 'screensaver':
                print "Monitor going into screen saver mode."
                self.photobooth.screen_saver() # HACK
                pass

        return self.menu_choice

    def get_menu_object_at_index(self, object_index):
        return self.menu_objects[object_index]
