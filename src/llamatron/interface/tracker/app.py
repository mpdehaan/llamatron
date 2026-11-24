# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The text UI's application, which opens on the main screen.

    python -m llamatron
    python -m llamatron examples/by_genre/electronic/minimal_techno.yml
"""

import sys
from textual.app import App
import time
import traceback

from llamatron.interface.pages.wizard import starts
from llamatron.interface.tracker import drawing, garbage, keys, launch as launch_values
from llamatron.interface.tracker.batch_stage import BatchStage
from llamatron.interface.tracker.components.scroll_text import scroll_seconds
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.document import Document
from llamatron.interface.tracker.launch import Launch, recording_problem
from llamatron.interface.tracker.made_preview import MadePreview
from llamatron.interface.tracker.pattern_preview import PatternPreview
from llamatron.interface.tracker.screens import editors
from llamatron.interface.tracker.screens.arrange.arrange_page import ArrangePage
from llamatron.interface.tracker.screens.set.demo_scroll import DemoScroll
from llamatron.interface.tracker.screens.set.main_page import MainPage
from llamatron.interface.tracker.screens.set.splash import Splash
from llamatron.interface.tracker.screens.set.start_screen import StartScreen
from llamatron.interface.tracker.screens.shared.everywhere import offer_corrected
from llamatron.interface.tracker.screens.shared.page import Page
from llamatron.interface.tracker.screens.wizard.wizard_page import WizardPage
from llamatron.interface.tracker.silent_instruments import warn_of_silent_instruments
from llamatron.interface.tracker.site_map import SiteMap
from llamatron.interface.tracker.status_line import StatusLine
from llamatron.interface.tracker.transport import Transport
from llamatron.interface.visualizers.modes import mode_called
from llamatron.model.file.song_file_error import SongFileError
from llamatron.user_strings import errors, labels


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
        """Hold a set, or a new one. start_screen opens on the start screen, as the command line does, when the launch is a plain one. A set that comes with corrections, which its file's values needed, is only opened once the Corrections dialog is answered Yes, over a new set. launch is what the tracker does on its own once open (interface/tracker/launch.py)."""
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
        self._status_line = StatusLine()
        # Which page the pattern editor shows, the piano roll or a set of rows, which stays as you move between patterns.
        # The pattern editor's open sections, kept for the session like the choice of the roll, so every pattern opens the way the last was left.
        self.open_sections = set(keys.OPEN_AT_START)
        # The settings pages' sections open now, by name, closed until opened and remembered for the session.
        self.open_field_sections = set()
        # The tab each kind of page with a tab box last showed, by the page's class, remembered for the session.
        self.chosen_tabs = {}
        # Which page shows each place a page opens by saying where it goes.
        self.site_map = SiteMap(editor_of=self.editor_of)
        # The headings open in the pattern editor's Munge dialog, kept for the session.
        self.open_munge_groups = set()
        self.on_roll = True
        # Whether Arrange shows its details view (R), kept for the session like the choice of the roll.
        self.shows_arrange_details = False
        # The directory each kind of file picker last showed, by the endings of its files, kept for the session, so that the
        # Open page and the import's picker each come back to where they were left.
        self.last_folders = {}
        # The Live sets the user has agreed to write over, so that exporting asks only the first time.
        self._confirmed_overwrites = set()
        # Real-time playback, which ticks on a timer of the app's while anything plays and redraws the page on top for its lights.
        self.transport = Transport(document_holder=self, set_timer=self.playback_timer, set_once=self.timer_once)
        # The pattern preview, made when first asked for, beside the transport it shares a clock and FluidSynth with.
        self._pattern_preview = None
        self._preview_beside = None
        # The set being edited while a draft is held over it, or None with no draft.
        self._behind_draft = None
        # The song wizard's preview, made when first asked for, beside the same transport.
        self._made_preview = None
        self._made_beside = None
        # The plain traceback of an error nothing caught, printed as the tracker closes (_handle_exception).
        self._crash_report = None

    def get_document(self):
        return self._document

    def pattern_preview(self):
        """Return the pattern preview, which plays one pattern beside whatever the transport plays, made beside the transport the first time it's asked for."""
        if self._pattern_preview is None or self._preview_beside is not self.transport:
            self._pattern_preview = PatternPreview(beside=self.transport)
            self._preview_beside = self.transport
        return self._pattern_preview

    def made_preview(self):
        """Return the song wizard's preview, which plays a part of a song made to be heard, made beside the transport the first time it's asked for."""
        if self._made_preview is None or self._made_beside is not self.transport:
            self._made_preview = MadePreview(beside=self.transport)
            self._made_beside = self.transport
        return self._made_preview

    def set_document(self, document):
        """Hold another set, after opening a file or starting a new one. A set comes with a history of its own, with nothing to undo, and nothing of the old one plays on."""
        self.transport.forget()
        self.pattern_preview().forget()
        self.made_preview().forget()
        self._document = document
        self._hold_long_lived()

    def open_draft(self, document):
        """Hold a draft set over the set being edited, until close_draft: every page opened meanwhile edits and plays the draft, as
        the pattern editor does on a tune the song wizard has made and not yet put in a song. Nothing of either set plays on."""
        self.transport.forget()
        self.pattern_preview().forget()
        self.made_preview().forget()
        self._behind_draft = self._document
        self._document = document

    def is_drafting(self):
        """Return whether a draft is held over the set being edited, when the set cannot be saved, opened over or exported."""
        return self._behind_draft is not None

    def close_draft(self):
        """Put the set being edited back and return the draft that was held over it."""
        draft = self._document
        self.transport.forget()
        self.pattern_preview().forget()
        self._document = self._behind_draft
        self._behind_draft = None
        return draft

    def playback_timer(self, *, seconds, tick):
        """Start the timer that ticks the transport and redraws the page on top while something plays, and return it to be stopped."""
        def ticked():
            tick()
            # The timer can tick once more as the tracker quits, with no screen left to draw.
            if self.screen_stack and isinstance(self.screen, Page):
                message = self.transport.take_live_message() or self.pattern_preview().take_live_message()
                if message is not None:
                    self.screen.refuse(message)
                problem = self.transport.take_problem()
                if problem is not None:
                    self.screen.tell(problem.title, *problem.lines)
                self.screen.draw()
        return self.set_interval(seconds, ticked)

    def timer_once(self, *, seconds, then):
        """Call a function once, after a time, for the transport, which follows an edit made while playing once it has settled."""
        self.set_timer(seconds, then)

    def edit_made(self, *, typed):
        """Tell what plays, the song and the pattern preview alike, that a key or a dialog's answer may have edited the set, so that
        an edit is heard as soon as it settles; typed says whether the key typed a digit, which another may follow."""
        self.transport.edit_made(typed=typed)
        if self._pattern_preview is not None:
            self._pattern_preview.edit_made(typed=typed)

    def exit(self, *arguments, **named):
        """Quit, silencing and ending the Realtime Sender Process first."""
        self.pattern_preview().close()
        self.made_preview().close()
        self.transport.close()
        super().exit(*arguments, **named)

    def get_status_line(self):
        return self._status_line

    def pages(self):
        """Return the pages open, from the main screen up to the one on top, leaving out any dialog over it."""
        return [screen for screen in self.screen_stack if isinstance(screen, Page)]

    def editor_of(self, section):
        """Return the class of the page that edits one named thing of a section, which a page asks for so that it imports no other page."""
        return editors.editor_of(section)

    def section_page_of(self, section):
        """Return the class of the page that shows the whole of a section of the song, which a page asks for so that it imports no other page."""
        return editors.section_page_of(section)

    def is_open(self, page):
        return page in self.screen_stack

    def go_back_to(self, page):
        """Close every screen above a page, so that it's the one shown."""
        while self.screen is not page:
            self.pop_screen()

    def show_wizard(self, page):
        """Open the song wizard over a page, as W does on the main screen."""
        if page.document().song().get_wizard_choices() is None:
            page.show_page(WizardPage(self))
        else:
            # On a song the wizard made, a dialog asks how to start first; ESC opens no wizard.
            # The last row is CANCEL, which opens no wizard, as ESC does.
            names = [*(labels.MSG_WIZARD_START_NAMES[start] for start in starts.STARTS), labels.MSG_WIZARD_START_CANCEL]

            def answered(place):
                if place < len(starts.STARTS):
                    page.show_page(WizardPage(self, start=starts.STARTS[place]))
            page.ask(dialog=ChoiceDialog(title=labels.MSG_WIZARD_START_TITLE, options=names), then=answered)

    def show_arrange_on_new_song(self):
        """Close every page down to the main screen and open Arrange, which shows the current song: where the song wizard leaves a person once it has made one."""
        first = self.pages()[0]
        self.go_back_to(first)
        first.show_page(ArrangePage(self))

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
        self._hold_long_lived()
        if self._offered is not None:
            offer_corrected(page=page, document=self._offered, corrections=self._corrections, then=lambda document: self._opened(page=page, document=document))
        elif self._document.get_path() is not None:
            if self._document.conversion_note() is not None:
                page.say(self._document.conversion_note())
            self._warn_of_silent_instruments(page)
        self._begin_launch(page)
        if self._start_screen:
            self.push_screen(StartScreen(ready=self.transport.prepare()))

    def _handle_exception(self, error):
        """Keep the traceback of an error nothing caught as plain text, printed as the tracker closes in place of Textual's boxed
        and coloured traceback with every frame's locals, which is hard to read once saved to a file or pasted."""
        self._crash_report = drawing.NOTHING.join(traceback.format_exception(error))
        super()._handle_exception(error)

    def _fatal_error(self):
        """Close the tracker after an error nothing caught, whose traceback _print_error_renderables prints."""
        self.bell()
        self._close_messages_no_wait()

    def _print_error_renderables(self):
        """Print a crash's traceback as plain text, straight to the terminal, so that no line is wrapped or coloured."""
        if self._crash_report is not None:
            sys.stderr.write(self._crash_report)
            self._crash_report = None
        super()._print_error_renderables()

    def _hold_long_lived(self):
        """Freeze what the tracker keeps, so that the collector's full passes leave it alone (interface/tracker/garbage.py); not
        under the tests, which make many trackers one after another in one process and need each collected once it is done."""
        if not self.is_headless:
            garbage.hold_long_lived()

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
        if self.launch.details:
            self.shows_arrange_details = True
        if self.launch.max_seconds is not None:
            self.set_timer(self.launch.max_seconds, self.exit)
        if self.launch.test_splash:
            # The start screen alone, to see it, and then the tracker quits (internal_tools/demo_splash_screen.py).
            self.push_screen(StartScreen(seconds=self.launch.splash_seconds))
            self.set_timer(self.launch.splash_seconds + self.launch.lead_in_seconds, lambda: self._after_title(self.exit))
        elif self.launch.for_recording:
            seconds = self.launch.title_seconds if self.launch.batch_video else self.launch.splash_seconds
            self.push_screen(Splash(seconds=seconds))
            self.set_timer(seconds, lambda: self._after_title(lambda: self._after_splash(page)))
        elif self.launch.autoplay:
            self._open_arrange(page)

    def _after_title(self, then):
        """Go on from the opening title: straight on, or with the launch's words crossing the screen first, in the title's place."""
        if self.launch.scroll_text is None:
            then()
            return
        seconds = self.launch.scroll_seconds
        if seconds is None:
            seconds = scroll_seconds(text=self.launch.scroll_text, width=self.size.width)
        self.pop_screen()
        self.push_screen(DemoScroll(text=self.launch.scroll_text, seconds=None))
        self.set_timer(seconds, then)

    def _after_splash(self, page):
        self.pop_screen()
        if self.launch.batch_video:
            self._open_stage(page)
        elif self.launch.interactive:
            self._open_arrange_for_a_performance(page)
        elif self.launch.autoplay:
            self._open_arrange(page)

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

    def is_staged(self):
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
                self.set_interval(launch_values.FINISHED_CHECK_SECONDS, self._quit_when_finished)

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

    def has_autoplay_started(self):
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
            print(errors.ERR_PRINTED.format(problem=error), file=sys.stderr)
            return 1
    if launch is not None and launch.for_recording:
        problem = recording_problem(document.song())
        if problem is not None:
            print(errors.ERR_PRINTED.format(problem=problem), file=sys.stderr)
            return 1
    LlamatronApp(document=document, corrections=corrections, launch=launch, start_screen=start_screen, cursor_on_open=not arguments).run()
    return 0


if __name__ == '__main__':
    sys.exit(main())
