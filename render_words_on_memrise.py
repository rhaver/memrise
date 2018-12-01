"""This module provides a script with a GUI that can access a course edit page
on Memrise (memrise.com) through a browser, render the words of the course's
levels (using either Pango or XeLaTeX), and add those rendered images to the
words in a (pre-existing) image column.
"""

import os
import time
# interaction with browser
from selenium import webdriver
# parsing HTML
from bs4 import BeautifulSoup
# running commands
import subprocess
# GUI elements
import tkinter as tk
from tkinter import ttk as ttk, font as tkf

def debug(s, indent=0):
    """Debugging log function."""
    if __debug__:
        print((' ' * indent) + s)

class PngTextRenderer:
    """Interface for a class that can render text to a PNG image file."""
    def __init__(self):
        """Constructor."""
        raise NotImplementedError('Abstract class PngTextRenderer')
    #
    def render_text(self, filename, text, font='Arial'):
        """Render the text with the given font to the given image filename."""
        raise NotImplementedError('Abstract class PngTextRenderer')

class XelatexImageMagickPngTextRenderer(PngTextRenderer):
    """Class to render text with (Xe)LaTeX and convert to PNG
    with ImageMagick.
    """
    #
    def __init__(self, hebrew_rtl=False):
        """Constructor."""
        # set up the template for the Pango string
        if hebrew_rtl:
            self._xelatex_format = r'''
                %!TEX TS-program = xelatex
                %!TEX encoding = UTF-8 Unicode
                \documentclass[border=10mm]{{standalone}}
                \nofiles
                \usepackage{{polyglossia}}
                \setmainlanguage{{hebrew}}
                \usepackage{{fontspec}}
                \defaultfontfeatures{{Mapping=tex-text,Scale=MatchLowercase}}
                \setmainfont{{{1}}}
                \begin{{document}}
                \fontsize{{30pt}}{{30pt}}
                \selectfont
                {0}
                \end{{document}}
                '''[1:].replace('                ', '')
        else:
            self._xelatex_format = r'''
                %!TEX TS-program = xelatex
                %!TEX encoding = UTF-8 Unicode
                \documentclass[border=10mm]{{standalone}}
                \nofiles
                \usepackage{{fixltx2e}}
                \usepackage{{fontspec}}
                \usepackage{{xunicode,xltxtra}}
                \defaultfontfeatures{{Mapping=tex-text,Scale=MatchLowercase}}
                \setmainfont{{{1}}}
                \begin{{document}}
                \fontsize{{30pt}}{{30pt}}
                \selectfont
                {0}
                \end{{document}}
                '''[1:].replace('                ', '')
        # create a translation table for unsafe characters in a XeLaTeX string
        self._trans = str.maketrans({
            '#': r'\#',
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\textasciicircum{}',
            '\\': r'\textbackslash{}',
            '"': r'\char"22'
            })
    #
    def make_string_xelatex_safe(self, unsafe_string):
        """Escape unsafe characters in a text to go into a XeLaTeX string."""
        return unsafe_string.translate(self._trans)
    #
    def render_text(self, filename, text, font='Arial'):
        """Render the text with the given font to the given image filename."""
        debug('<XeLaTeX.render_text>', indent=4)
        # set up the XeLaTeX document
        xelatex_string = self._xelatex_format.format(
            self.make_string_xelatex_safe(text),
            font
            )
        # render the text (to a PDF file) using XeLaTeX
        with subprocess.Popen(
                ['xelatex', '-output-directory={0}'.format(os.getcwd())],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=False
                ) as xelatex:
            xelatex.communicate(input=xelatex_string.encode('utf-8'))
        # convert the PDF to PNG using ImageMagick
        filename_tex = 'texput.pdf'
        filename_texlog = 'texput.log'
        subprocess.run([
            'magick', '-antialias', '-density', '1200',
            filename_tex,
            '-trim',
            filename
            ])
        # check the existence of the PNG
        if os.path.isfile(filename):
            debug('file "{}" produced'.format(filename), indent=4)
        # cleanup XeLaTeX files
        for file in [filename_tex, filename_texlog]:
            if os.path.isfile(file):
                os.remove(file)
                debug('temporary file "{}" removed'.format(file), indent=4)

class ImageMagickPangoPngTextRenderer(PngTextRenderer):
    """Class to render text to an image using ImageMagick with Pango."""
    #
    def __init__(self):
        """Constructor."""
        # set up the template for the Pango string
        self._pango_format = (
            'pango:<markup>'
            '<span font_family="{1}" size="192000"> \n {0} \n </span>'
            '</markup>'
            )
        # create a translation table for unsafe characters in a Pango string
        self._trans = str.maketrans({
            '&': r'&amp\;',
            '<': r'&lt\;',
            '>': r'&gt\;',
            '"': r'&quot\;',
            '\'': r'&apos\;',
            '\\': r'&#x5c\;',
            '%': r'&#x25\;'
            })
    #
    def make_string_pango_safe(self, unsafe_string):
        """Escape unsafe characters in a text to go into a Pango string."""
        return unsafe_string.translate(self._trans)
    #
    def render_text(self, filename, text, font='Arial'):
        """Render the text with the given font to the given image filename."""
        debug('<Pango.render_text>', indent=4)
        # set up the Pango string
        pango_string = self._pango_format.format(
            self.make_string_pango_safe(text),
            font
            )
        # render the Pango string to PNG using ImageMagick
        subprocess.run([
            'magick', '-background', 'white', '-density', '600',
            pango_string,
            '-transparent', 'white', '-antialias', '-resize', '25%', '-trim',
            filename
            ])

class MemriseImageAdder:
    """Class to sign in to Memrise using Chrome and render and upload
    images for the words in a given column of an open level in a course
    edit page."""
    #
    def __init__(self):
        """Constructor."""
        self._driver = None
    #
    def __enter__(self):
        """Enter runtime context."""
        return self
    #
    def __exit__(self, exc_type, exc_value, traceback):
        """Exit runtime context."""
        return True
    #
    def __del__(self):
        """"Destructor."""
        # close any currently active webdriver session
        self._quit_driver()
    #
    def _quit_driver(self):
        """Close current webdriver session, if any."""
        if self._driver:
            self._driver.quit()
            self._driver = None
    #
    def _get_renderer(self, engine='pango'):
        """Instantiate a text to PNG renderer."""
        if engine.lower() == 'xelatex':
            return XelatexImageMagickPngTextRenderer(hebrew_rtl=True)
        else:
            return ImageMagickPangoPngTextRenderer()
    #
    def render_and_upload(self, column, engine, font, skip_existing_images,
                          hebrew_rtl=False):
        """Render and upload images for the words in the unfolded levels of
        the currently opened Memrise course edit page.
        """
        debug(
            '<MIA.render_and_upload>(column={}, engine="{}", font="{}", '
            'skip_existing_images={}, hebrew_rtl={})'.format(
                column, engine, font, skip_existing_images, hebrew_rtl
                )
            )
        # make the column zero-indexed
        column -= 1
        # instantiate renderer
        renderer = self._get_renderer(engine)
        debug('renderer: {}'.format(renderer))
        # parse the currently opened page's HTML source
        html = self._driver.page_source
        soup = BeautifulSoup(html, 'lxml')
        # find all the unfolded class levels and process them
        i = 0
        for level in soup.select('div[class="level"]'):
            i += 1
            debug('open lesson number {}'.format(i), indent=1)
            # go through each table row (entry)
            j = 0
            for entry in level.find_all('tr', {'class': 'thing'}):
                j += 1
                # get the entry's ID
                tr_id = entry.get('data-thing-id')
                debug('entry number {} with id {}'.format(j, tr_id), indent=2)
                # extract the word (first text column)
                cells = entry.find_all('td', {'class': 'cell'})
                debug('column count is {}'.format(len(cells)), indent=2)
                if column < len(cells):
                    word_cell = cells[column]
                    word = word_cell.find('div', {'class': 'text'}).string
                    # check if it has an image
                    image = entry.select_one('td.cell.image button')
                    has_image = 'disabled' not in image.get('class')
                    debug('word = "{}"'.format(word.encode('utf-8')), indent=3)
                    debug('has_image = "{}"'.format(has_image), indent=3)
                    # generate and upload image if it doesn't have one
                    if not (skip_existing_images and has_image):
                        # find the input field in Chrome
                        input_field = (
                            self._driver.find_element_by_css_selector(
                                ('tr[data-thing-id=\'{}\'] '
                                'td[class~=\'image\'] input').format(tr_id)
                                )
                            )
                        debug('input field = {}'.format(
                            input_field.get_attribute('outerHTML')),
                            indent=3
                            )
                        # render the image
                        image_name = 'render{}.png'.format(tr_id)
                        try:
                            renderer.render_text(image_name, word, font)
                        except:
                            debug('"Failed to generate image.', indent=3)
                        # if rendered successfully, upload and delete image
                        if os.path.isfile(image_name):
                            debug('sending image to input', indent=3)
                            input_field.send_keys(
                                os.path.join(os.getcwd(), image_name)
                                )
                            time.sleep(1)
                            debug('removing file "{}"'.format(image_name), indent=3)
                            os.remove(image_name)
            debug('lesson {} done, processed {} entries'.format(i, j), indent=1)
        debug('Done, processed {} lessons'.format(i))
    #
    def start_chrome(self):
        """Start a Chrome session."""
        debug('<MIA.start_chrome>')
        # close any inadvertently active webdriver session
        self._quit_driver()
        # start a new session
        self._driver = webdriver.Chrome()
        self._driver.get('https://www.memrise.com/login/')
    #
    def start_firefox(self):
        """Start a Firefox session."""
        debug('<MIA.start_firefox>')
        # close any inadvertently active webdriver session
        self._quit_driver()
        # start a new session
        self._driver = webdriver.Firefox()
        self._driver.get('https://www.memrise.com/login/')

class GUI:
    _msg_readmefirst = '''
        In order to use this script that interacts with a browser, you need
        to have either ChromeDriver (for Chrome) or geckodriver (for Firefox)
        and have its executable included in your operating system's PATH
        variable).
        ChromeDriver can be found at http://chromedriver.chromium.org .
        geckodriver can be found at https://github.com/mozilla/geckodriver .

        Furthermore you need ImageMagick to be installed (and its executables
        need to be included in your operating system's PATH variable).
        ImageMagick can be found at https://www.imagemagick.org .

        Additionally, if you wish to render text using the XeLaTeX engine,
        a TeX distribution needs to be installed on your system and the
        xelatex command needs to be included in your operating system's PATH
        variable).
        TeX distributions can be found at
        https://www.latex-project.org/get/#tex-distributions .
        For conversion from XeLaTeX's PDF output to a PNG image, ImageMagick
        also needs Ghostscript to be installed. Ghostscript can be found at
        https://www.ghostscript.com .

        Make sure the above requirements are met before proceeding to launch
        a browser window.
        '''.replace('        ', '')[1:-1]
    _msg_navigate = '''
        Please log in to Memrise in the browser window that was launched.
        Then, navigate to the course you wish to add images to.
        Go to the course's edit page and unfold the levels that you wish to be
        processed.

        You may then press the continue button.

        (In the next step, you will be able to specify which column's text you
        want to render, which rendering engine to use (Pango or XeLaTeX),
        which font you want to use, and if you wish to skip items that already
        have an image.
        Clicking the Start button will then prompt the script to process all
        unfolded levels.)
        '''.replace('        ', '')[1:-1]
    #
    def _show_warning_dialog(self, master, title, text, ok_object_function):
        """Make a modal dialog window that displays a warning
        on prerequisites.
        """
        p = 20
        cancel_action = self.close_main_window
        # create a new window
        self._dialog = tk.Toplevel(master)
        dlg = self._dialog
        dlg.title(title)
        # add warning text
        tk.Message(dlg, text=text, borderwidth=p).pack()
        # add buttons
        frame_buttons = tk.Frame(dlg)
        frame_buttons.pack()
        ok_object_function(frame_buttons).pack(side=tk.LEFT, padx=p, pady=p//2)
        tk.Button(
            frame_buttons, text='Cancel', command=cancel_action
            ).pack(side=tk.RIGHT, padx=p, pady=p//2)
        # only one window in the task bar
        dlg.transient(self._tk)
        # make sure a close is treated as a cancel
        dlg.protocol('WM_DELETE_WINDOW', cancel_action)
        # modal behaviour (keep focus)
        dlg.grab_set()
        master.wait_window(dlg)
    #
    def _build_main_window(self, master):
        """Build the main application window."""
        p = 10
        # set window title
        master.title('Memrise image renderer')
        # use a frame for the comboboxes
        frame_options = tk.Frame(master)
        frame_options.pack()
        # add spinbox to select the text source column
        tk.Label(
            frame_options, text='Text column'
            ).grid(row=1, column=1, padx=p, pady=p)
        self._spinbox_column = tk.Spinbox(frame_options, from_=1, to=99)
        self._spinbox_column.grid(row=1, column=2, padx=p, pady=p)
        # add combobox to choose Pango/XeLaTeX engine
        tk.Label(
            frame_options, text='Rendering engine'
            ).grid(row=2, column=1, padx=p, pady=p)
        engines = ['Pango', 'XeLaTeX']
        self._combobox_engine = ttk.Combobox(
            frame_options, values=engines, state='readonly'
            )
        self._combobox_engine.grid(row=2, column=2, padx=p, pady=p)
        self._combobox_engine.set('Pango')
        # add combobox to choose an available font
        tk.Label(
            frame_options, text='Select font'
            ).grid(row=3, column=1, padx=p, pady=p)
        fonts = sorted((x for x in tkf.families() if not x.startswith('@')))
        self._combobox_font = ttk.Combobox(
            frame_options, values=fonts, state='readonly'
            )
        self._combobox_font.grid(row=3, column=2, padx=p, pady=p)
        self._combobox_font.set('Arial' if 'Arial' in fonts else fonts[0])
        # add checkboxes for additional options
        # - skip items that already have an image
        self._checkbox_skip_images_status = tk.IntVar()
        self._checkbox_skip_images = tk.Checkbutton(
            frame_options, text='Skip items that already have an image',
            variable=self._checkbox_skip_images_status, 
            )
        self._checkbox_skip_images.grid(
            row=4, column=1, columnspan=2, padx=p, pady=p
            )
        self._checkbox_skip_images.select()
        # - Hebrew right-to-left
        self._checkbox_hebrew_rtl_status = tk.IntVar()
        self._checkbox_hebrew_rtl = tk.Checkbutton(
            frame_options, text='Hebrew right-to-left',
            variable=self._checkbox_hebrew_rtl_status
            )
        self._checkbox_hebrew_rtl.grid(
            row=5, column=1, columnspan=2, padx=p, pady=p // 2
            )
        # add execution button
        tk.Button(
            master, text='Start', command=self._button_start_click
            ).pack(padx=p, pady=p)
    #
    def __init__(self, memrise_image_adder):
        """Build a Tk window with a combobox to select column/engine/font
        and a button to execute.
        """
        self._memrise_image_adder = memrise_image_adder
        self._tk = tk.Tk()
        self._build_main_window(self._tk)
        self._show_warning_dialog(
            self._tk, 'Step 1: read me first!',
            self._msg_readmefirst, self._make_browser_buttons_frame
            )
        if self._tk:
            self._show_warning_dialog(
                self._tk, 'Step 2: navigate to course',
                self._msg_navigate, lambda x: tk.Button(
                    x, text='Continue', command=self._btn_ok2_click
                    )
                )
        if self._tk:
            self._tk.mainloop()
    #
    def close_main_window(self):
        """Close the GUI's main window, ending the main loop."""
        self._tk.destroy()
    #
    def _make_browser_buttons_frame(self, master):
        """Make a frame with buttons for launching browsers."""
        frame_browsers = tk.Frame(master)
        tk.Button(
            frame_browsers, text='Chrome', command=self._btn_chrome_click
            ).pack()
        tk.Button(
            frame_browsers, text='Firefox', command=self._btn_firefox_click
            ).pack(pady=10)
        return frame_browsers
    #
    def _btn_chrome_click(self):
        """Handle a click on the OK button in the (1st) warning dialog."""
        self._memrise_image_adder.start_chrome()
        self._dialog.destroy()
    #
    def _btn_firefox_click(self):
        """Handle a click on the OK button in the (1st) warning dialog."""
        self._memrise_image_adder.start_firefox()
        self._dialog.destroy()
    #
    def _btn_ok2_click(self):
        """Handle a click on the OK button in the (2nd) warning dialog."""
        self._dialog.destroy()
    #
    def _button_start_click(self):
        """Handle a click on the Start button."""
        # gather the chosen settings
        column = int(self._spinbox_column.get())
        engine = self._combobox_engine.get()
        font = self._combobox_font.get()
        skip_existing_images = self._checkbox_skip_images_status.get() != 0
        hebrew_rtl = self._checkbox_hebrew_rtl_status.get() != 0
        # get to rendering and uploading
        self._memrise_image_adder.render_and_upload(
            column, engine, font, skip_existing_images,
            hebrew_rtl=hebrew_rtl
            )

def main():
    """Main method."""
    with MemriseImageAdder() as mia:
        GUI(mia)

if __name__ == '__main__':
	main()
