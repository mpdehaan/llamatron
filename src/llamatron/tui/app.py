# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""The text UI's application, which opens on the main screen.

    python -m llamatron
    python -m llamatron examples/by_genre/electronic/minimal_techno.yml
"""

import sys
import time

from textual.app import App

from llamatron.composition.song_file_error import SongFileError
from llamatron.tui.batch_stage import BatchStage
from llamatron.tui.document import Document
from llamatron.tui.launch import FINISHED_CHECK_SECONDS, Launch, recording_problem
from llamatron.visualizers.modes import mode_called
from llamatron.tui.screens.arrange_page import ArrangePage
from llamatron.tui.screens.everywhere import offer_corrected
from llamatron.tui.screens.main_page import MainPage
from llamatron.tui.screens.page import Page
from llamatron.tui.screens.splash import Splash
from llamatron.tui.screens.start_screen import StartScreen
from llamatron.tui.keys import OPEN_AT_START
from llamatron.tui.status_line import StatusLine
from llamatron.tui.transport import Transport
from llamatron.tui.silent_instruments import warn_of_silent_instruments
from llamatron.strings.errors import ERR_PRINTED


# inherit_bindings=False drops Textual's own Ctrl+Q, since Quit is Q on the main screen alone.
class LlamatronApp(App, inherit_bindings=False):
    """Holds the set being edited, the status line every page shares, and offers to save before quitting.

    The pages reach Textual's stack of screens only through this class and Page's show_page and
    go_back, so that the toolkit could be replaced without touching the pages.
    """

    ENABLE_COMMAND_PALETTE = False
    BINDINGS = []
    CSS = """
    Screen { background: ansi_default; color: ansi_default; }
    ModalScreen { background: transparent; align: center middle; }
    #view { width: 100%; height: 100%; background: ansi_default; color: ansi_default; }
    #dialog { width: auto; height: auto; background: ansi_default; color: ansi_default; }
    #dialog-view { width: auto; height: auto; background: ansi_default; color: ansi_default; }
    """

    def __init__(self, *, document=None, corrections=(), launch=None, start_screen=False, cursor_on_open=False):
        """Hold a set, or a new one. start_screen opens on the start screen, as the command line does, when the launch is a plain one. A set that comes with corrections, which its file's values needed, is only opened once the Corrections dialog is answered Yes, over a new set. launch is what the tracker does on its own once open (tui/launch.py)."""
        super().__init__(ansi_color=True)
        self._document = Document() if document is None or corrections else document
        self._offered = document if corrections else None
        self._corrections = corrections
        self.launch = Launch() if launch is None else launch
        self._start_screen = start_screen and self.launch.is_plain()
        # Whether the main screen's cursor starts on Open, as when the command line names no set.
        self._cursor_on_open = cursor_on_open
        self._autoplay_started = False
        # The Arrange page a batch video's stage is on, once it shows.
        self._staged = None
        # Whether an interactive take is ending, so that it ends once.
        self._take_ending = False
        # What drives a launch from outside, the video tutorial's runner, for the tool's report and the tests.
        self.driven = None
        self._status_line = StatusLine()
        # What the video tutorial says, shown at the foot of every page while it runs, and None otherwise (tui/caption_strip.py).
        self._caption_strip = None
        # Which page the pattern editor shows, the piano roll or a set of rows, which stays as you move between patterns.
        # The pattern editor's open sections, kept for the session like the choice of the roll, so every pattern opens the way the last was left.
        self.open_sections = set(OPEN_AT_START)
        # The settings pages' sections open now, by name, closed until opened and remembered for the session.
        self.open_field_sections = set()
        self.on_roll = True
        # Whether Arrange shows its details view (R), the user's design, kept for the session like the choice of the roll.
        self.shows_arrange_details = False
        # The Live sets the user has agreed to write over, so that exporting asks only the first time.
        self._confirmed_overwrites = set()
        # Real-time playback, which ticks on a timer of the app's while anything plays and redraws the page on top for its lights.
        self.transport = Transport(document_holder=self, set_timer=self.playback_timer)

    def get_document(self):
        return self._document

    def set_document(self, document):
        """Hold another set, after opening a file or starting a new one. A set comes with a history of its own, with nothing to undo, and nothing of the old one plays on."""
        self.transport.forget()
        self._document = document

    def playback_timer(self, *, seconds, tick):
        """Start the timer that ticks the transport and redraws the page on top while something plays, and return it to be stopped."""
        def ticked():
            tick()
            # The timer can tick once more as the tracker quits, with no screen left to draw.
            if self.screen_stack and isinstance(self.screen, Page):
                message = self.transport.take_live_message()
                if message is not None:
                    self.screen.refuse(message)
                self.screen.draw()
        return self.set_interval(seconds, ticked)

    def exit(self, *arguments, **named):
        """Quit, silencing and ending the Realtime Sender Process first."""
        self.transport.close()
        super().exit(*arguments, **named)

    def status_line(self):
        return self._status_line

    def caption_strip(self):
        return self._caption_strip

    def show_caption_strip(self, strip):
        """Show the caption strip at the foot of every page from now on, the video tutorial's, and draw the pages again."""
        self._caption_strip = strip
        self.redraw_pages()

    def redraw_pages(self):
        """Draw every open page again, those under a dialog too, which shows them through."""
        for page in self.pages():
            page.draw()

    def pages(self):
        """Return the pages open, from the main screen up to the one on top, leaving out any dialog over it."""
        return [screen for screen in self.screen_stack if isinstance(screen, Page)]

    def is_open(self, page):
        return page in self.screen_stack

    def go_back_to(self, page):
        """Close every screen above a page, so that it's the one shown."""
        while self.screen is not page:
            self.pop_screen()

    def has_confirmed_overwrite(self, path):
        return path in self._confirmed_overwrites

    def confirm_overwrite(self, path):
        """Remember that writing over a Live set was agreed to, so that it isn't asked again this session."""
        self._confirmed_overwrites.add(path)

    def on_mount(self):
        page = MainPage(self)
        if self._cursor_on_open:
            page.select_open()
        self.push_screen(page)
        if self._offered is not None:
            offer_corrected(page=page, document=self._offered, corrections=self._corrections, then=lambda document: self._opened(page=page, document=document))
        elif self._document.get_path() is not None:
            self._warn_of_silent_instruments(page)
        self._begin_launch(page)
        if self._start_screen:
            self.push_screen(StartScreen())

    def _opened(self, *, page, document):
        """Hold the set the Corrections dialog was answered Yes for, and warn of its instruments that will not sound."""
        self.set_document(document)
        self._warn_of_silent_instruments(page)

    def _warn_of_silent_instruments(self, page):
        """Tell which of the set's instruments will not sound here, unless the tracker plays on its own, where a dialog would stop it."""
        if self.launch.is_plain():
            warn_of_silent_instruments(page=page, document=self._document)

    # Playing on its own, by the command line's flags.

    def _begin_launch(self, page):
        """Do what the launch says: the splash first when launched for recording, then Arrange and play, and the clock that ends the take."""
        if self.launch.max_seconds is not None:
            self.set_timer(self.launch.max_seconds, self.exit)
        if self.launch.test_splash:
            # The start screen alone, to see it, and then the tracker quits (internal_tools/demo_splash_screen.py).
            self.push_screen(StartScreen(seconds=self.launch.splash_seconds))
            self.set_timer(self.launch.splash_seconds + self.launch.lead_in_seconds, self.exit)
        elif self.launch.for_recording:
            seconds = self.launch.title_seconds if self.launch.batch_video else self.launch.splash_seconds
            self.push_screen(Splash(seconds=seconds))
            self.set_timer(seconds, lambda: self._after_splash(page))
        elif self.launch.driven_by is not None:
            self._begin_driving()
        elif self.launch.autoplay:
            self._open_arrange(page)

    def _after_splash(self, page):
        self.pop_screen()
        if self.launch.batch_video:
            self._open_stage(page)
        elif self.launch.interactive:
            self._open_arrange_for_a_performance(page)
        elif self.launch.driven_by is not None:
            self._begin_driving()
        elif self.launch.autoplay:
            self._open_arrange(page)

    def _begin_driving(self):
        """Hand the tracker to what drives it from outside, and once that is done, watch for the end of what it played when the launch quits then."""
        self.driven = self.launch.driven_by(self)
        self.driven.start(then=self._driving_done)

    def _driving_done(self):
        self._autoplay_started = self.transport.is_playing()
        if self.launch.quit_when_finished:
            if not self._autoplay_started:
                self.set_timer(self.launch.lead_out_seconds, self.exit)
            else:
                self.set_interval(FINISHED_CHECK_SECONDS, self._quit_when_finished)

    def _open_arrange(self, page):
        arrange = ArrangePage(self)
        page.show_page(arrange)
        if self.launch.visualizer is not None:
            arrange.show_visualizer(mode_called(self.launch.visualizer))
        self.set_timer(self.launch.lead_in_seconds, lambda: self._autoplay(arrange))

    def _open_arrange_for_a_performance(self, page):
        """Open Arrange with the cursor on the corner, where Space starts the song, and play nothing: the person recording starts it."""
        arrange = ArrangePage(self)
        page.show_page(arrange)
        arrange.go_to_corner()
        if self.launch.visualizer is not None:
            arrange.show_visualizer(mode_called(self.launch.visualizer))
        arrange.draw()

    def _open_stage(self, page):
        """Open Arrange for a batch video, its cursor on the corner and the stage over it, and start the song once READY has shown."""
        arrange = ArrangePage(self)
        page.show_page(arrange)
        arrange.go_to_corner()
        arrange.show_visualizer(mode_called(self.launch.visualizer))
        arrange.stage = BatchStage(began=time.monotonic(), bar_length=self._document.song().get_time_signature().bar_length(), alternate=self.launch.alternate)
        self._staged = arrange
        arrange.draw()
        self.set_timer(self.launch.ready_seconds, lambda: self._start_staged_song(arrange))

    def _start_staged_song(self, arrange):
        """Start the batch video's song, the box growing into the frame, or, for the opening alone, cut to black and quit."""
        if self.launch.opening_only:
            arrange.stage.cut_to_black()
            arrange.draw()
            self.set_timer(self.launch.lead_out_seconds, self.exit)
            return
        arrange.stage.start_song(at=time.monotonic())
        self._autoplay(arrange)

    def staged(self):
        """Return the Arrange page a batch video's stage is on, or None, for the tests."""
        return self._staged

    def end_take(self):
        """End an interactive take: let what played ring out, then show the splash again and quit, once however often it's asked."""
        if not self.launch.interactive or self._take_ending:
            return
        self._take_ending = True
        self.set_timer(self.launch.lead_out_seconds, self._finish)

    def _autoplay(self, arrange):
        """Play the song from the top, as Space on Arrange's corner does, and from then on watch for its end when the launch quits then."""
        arrange.play_song()
        arrange.draw()
        self._autoplay_started = self.transport.is_playing()
        if self.launch.quit_when_finished:
            if not self._autoplay_started:
                # Nothing could play, and the page is telling why in a dialog: a launch that would quit when finished has nothing to wait for.
                self.set_timer(self.launch.lead_out_seconds, self.exit)
            else:
                self.set_interval(FINISHED_CHECK_SECONDS, self._quit_when_finished)

    def _quit_when_finished(self):
        if self._autoplay_started and not self.transport.is_playing():
            self._autoplay_started = False
            if self._staged is not None:
                self._staged.stage.end(at=time.monotonic(), seconds=self.launch.lead_out_seconds)
            self.set_timer(self.launch.lead_out_seconds, self._finish)

    def _finish(self):
        """Quit once the song has ended and rung out, showing the splash again first when launched for recording, so that the video ends on it."""
        if not self.launch.for_recording:
            self.exit()
            return
        if self.launch.batch_video:
            # A batch video has faded to black already, and ends on black, with no splash.
            self.set_timer(self.launch.hold_seconds, self.exit)
            return
        self.push_screen(Splash(seconds=self.launch.splash_seconds))
        self.set_timer(self.launch.splash_seconds + self.launch.hold_seconds, self.exit)

    def autoplay_started(self):
        """Return whether the launch's play has begun, for the tests."""
        return self._autoplay_started


def main(*, argv=None, launch=None, start_screen=False):
    """Open a set file if one is named, on the start screen when start_screen says, and return 1 if it can't be read, or if it can't be played the way the launch asks."""
    arguments = sys.argv[1:] if argv is None else argv
    document = None
    corrections = ()
    if arguments:
        try:
            document, corrections = Document.load_or_correct(arguments[0])
        except SongFileError as error:
            print(ERR_PRINTED.format(problem=error), file=sys.stderr)
            return 1
    if launch is not None and launch.for_recording:
        problem = recording_problem(document.song())
        if problem is not None:
            print(ERR_PRINTED.format(problem=problem), file=sys.stderr)
            return 1
    LlamatronApp(document=document, corrections=corrections, launch=launch, start_screen=start_screen, cursor_on_open=not arguments).run()
    return 0


if __name__ == '__main__':
    sys.exit(main())
