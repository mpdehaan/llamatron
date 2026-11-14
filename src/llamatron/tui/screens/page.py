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

"""What every screen has in common: one drawing, and one table of keys.

A screen's keys are listed once, in keys(), and that list both handles them and draws them, so no
key can work without being shown. The keys every page has (save, open, export, undo, redo, quit,
help and about) come first in every table and are shown by the F1 dialog and the main screen,
while a page's footer shows only its own keys, so that it stays short.
"""

from rich.color import Color
from llamatron.tui.caption_strip import CAPTION_LINES
from llamatron.tui.themes import luminance
from rich.style import Style as RichStyle
from rich.text import Text
from textual.screen import Screen
from textual.widgets import Static

from llamatron.tui.dialogs.about_dialog import AboutDialog
from llamatron.tui.dialogs.help_dialog import HelpDialog
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.text import clock
from llamatron.tui.drawing import Box, fit, legend, LINE_BREAK, NOTHING, SELECTOR, SPACE, Style
from llamatron.strings.help import help_lines, HELP_NONE
from llamatron.tui.key_table import pressed_key, BindsKeys, quits_at_once
from llamatron.tui.screens.everywhere import everywhere_keys
from llamatron.strings.errors import ERR_EMPTY_NAME, ERR_NAME_IN_USE
from llamatron.strings.labels import MSG_NO_FILE_CRUMB, MSG_SET_CRUMB, MSG_SONG_CRUMB
from llamatron.strings.marks import MSG_CRUMB_SEPARATOR, MSG_NONE_SHOWN, MSG_SAVED_MARK, MSG_UNSAVED_CHANGES_MARK, MSG_UNSAVED_MARK
from llamatron.tui import keybindings


PROGRAM_NAME = 'llamatron'
VIEW_ID = 'view'
VIEW_SELECTOR = SELECTOR.format(id=VIEW_ID)
# How Rich cuts a line that's too wide.
OVERFLOW_ELLIPSIS = 'ellipsis'


# The header's lines, its two and the rule or stripe under them, and the height of a screen that also has room for a blank line under a theme's stripe.
HEADER_LINES = 3
ROOM_FOR_THE_GAP = 30
# A stripe's caption is black on a theme brighter than this, as relative luminance, and white on a darker one.
CAPTION_LIGHT_ABOVE = 0.35
CAPTION_DARK = (0, 0, 0)
CAPTION_LIGHT = (255, 255, 255)


# The space between the set's and song's names and the marks at the header's right.
HEADER_GAP = '  '


def caption_colour(theme):
    """Return the colour a stripe's caption is written in: black on a light theme and white on a dark one, so that it reads on either."""
    return CAPTION_DARK if luminance(theme) > CAPTION_LIGHT_ABOVE else CAPTION_LIGHT


class Page(BindsKeys, Screen):
    """A full screen, drawn as one piece of text."""

    # The page's theme colour (tui/themes.py), or None for the plain rule, as the main screen and Arrange keep.
    THEME = None

    KEYS = keybindings.Page

    crumbs = ()
    # A screen that draws its keys itself turns this off.
    shows_legend = True
    # What F1's second panel shows, as short lines that have to fit an 80 by 24 console.
    HELP = HELP_NONE

    def __init__(self, document_holder):
        super().__init__()
        self.holder = document_holder
        # The screen's height at the last draw, for a page whose layout shouldn't change with the height of its legend.
        self.screen_height = 0

    def document(self):
        return self.holder.get_document()

    def say(self, text):
        """Show a message on the status line, which every page shares, until the next key press."""
        self.holder.status_line().say(text)

    def resting_status(self):
        """Return what the status line says while nothing else is said, which is nothing unless a page has something to say of where its cursor rests, as the pattern editor says a chord's name."""
        return NOTHING

    def refuse(self, text):
        """Show why a key did nothing or what went wrong on the status line, in amber, the user's design, so that a refusal isn't missed."""
        self.holder.status_line().say(text, refusal=True)

    # What an undo or redo asks of a page, since it may take away what the page shows or move what it shows.

    def still_exists(self):
        """Return whether what this page shows is still in the set, which an undo or redo can take away."""
        return True

    def remember_place(self):
        """Return what the cursor is on, in a form that survives the set being rebuilt, or None."""
        return None

    def restore_place(self, place):
        """Put the cursor back on what remember_place returned, if it's still there."""

    def crumb_trail(self):
        """Return the crumbs after the file's, which a page whose thing can be renamed works out each time."""
        return self.crumbs

    def follow_renames(self, renames):
        """Keep showing the same thing after an undo or redo renamed it.

        renames is what the step renamed, by section, as old name to new name. A page that shows
        nothing an undo can rename does nothing, and a page of one named thing follows it
        (ShowsNamedItem, in shows_named_item.py).
        """

    def compose(self):
        yield Static(id=VIEW_ID)

    def on_mount(self):
        self.draw()

    def on_screen_resume(self):
        self.draw()

    def on_resize(self):
        self.draw()

    def keys(self):
        """Return this screen's keys, which can change with what's under the cursor."""
        return []

    def key_table(self):
        """Return every key that works here: the keys every page has, then this screen's own."""
        return [*everywhere_keys(self), *self.page_key_table()]

    def page_key_table(self):
        """Return this screen's own keys as the table shows them, which a list page adds to."""
        return self.in_order(self.keys())

    def shown_keys(self):
        """Return the keys the footer shows: the page's own that aren't hidden, since the F1 dialog lists the rest."""
        return [item for item in self.page_key_table() if item.shown]

    def show_help(self):
        where = MSG_CRUMB_SEPARATOR.join(self.crumb_trail())
        # F1 isn't listed in its own dialog, by the user's choice (2026-11-09): it closes the dialog, and leaving it out puts Undo and Redo in one column.
        everywhere = [key for key in everywhere_keys(self) if key.binding is not self.KEYS.HELP]
        self.app.push_screen(HelpDialog(where=where, everywhere=everywhere, own=self.page_key_table(), about=help_lines(self.HELP)))

    def show_about(self):
        self.app.push_screen(AboutDialog(name=PROGRAM_NAME))

    def body(self, *, width, height):
        """Return the lines between the header and the keys."""
        return []

    def duration(self):
        """Return the seconds to show in the header, None if unknown, or False to show nothing."""
        return False

    def time_text(self):
        """Return the text at the right of the crumbs: the duration as a clock, or nothing."""
        seconds = self.duration()
        return clock(seconds) if seconds is not False else NOTHING

    def on_key(self, event):
        event.stop()
        event.prevent_default()
        name = pressed_key(event)
        if name is None:
            return
        if quits_at_once(name):
            # Ctrl+C quits whatever the page is doing, even while its keys are its own, as the Notes page's are while editing.
            self.app.exit()
            return
        table = self.key_table()
        for item in table:
            if name in item.keys:
                self.holder.status_line().clear()
                item.press(name)
                self.document().record_edit()
                # An undo can have closed this page, and a closed page has nothing to draw on.
                if self.app.is_open(self):
                    self.draw()
                return

    def takes_text(self):
        """Return whether typed characters go into text here rather than acting as the page's keys, which a list's search and the Description page's text do; the tests' typing asks first, so that a name typed at the wrong moment can't press keys."""
        return False

    def go_back(self):
        """Close the page. Leaving a page stops a preview it played, the user's rule, while a song played from Arrange plays on, so that it can be edited as it plays."""
        self.stop_playing()
        self.app.pop_screen()

    def show_page(self, page):
        self.stop_playing()
        self.app.push_screen(page)

    def stop_playing(self):
        """Stop a listening page's preview, if one plays, as its page is left or another opened over it; a song played from Arrange plays on, the user's rule."""
        if self.app.transport.is_previewing():
            self.app.transport.stop_all()
        self.app.pattern_preview().stop()

    def ask(self, *, dialog, then):
        """Show a dialog, and pass its answer to a function unless it was cancelled."""
        def answered(result):
            if result is not None:
                then(result)
            # An answer that changed the set is one undo step, like the key press that asked.
            self.document().record_edit()
            if self.app.is_open(self):
                self.draw()
        self.app.push_screen(dialog, answered)

    def ask_name(self, *, title, value, taken, then):
        """Ask for a name that isn't empty or already in use."""
        def named(text):
            text = text.strip()
            if not text:
                self.refuse(ERR_EMPTY_NAME)
            elif text != value and text in taken:
                self.refuse(ERR_NAME_IN_USE.format(name=text))
            elif text != value:
                then(text)
        self.ask(dialog=PromptDialog(title=title, value=value), then=named)

    def tell(self, title, *lines):
        self.app.push_screen(MessageDialog(title=title, messages=list(lines)))

    def set_crumb(self):
        """Return the words naming the open set's file, or (unsaved)."""
        return MSG_SET_CRUMB.format(file=self.document().get_file_name() or MSG_NO_FILE_CRUMB)

    def song_crumb(self):
        """Return the words naming the current song, or (none)."""
        return MSG_SONG_CRUMB.format(song=self.document().current_song_name() or MSG_NONE_SHOWN)

    def save_mark(self):
        """Return the mark at the header's right: unsaved for a set that has no file yet, unsaved changes for a set changed since its file was written or read, and saved otherwise."""
        if self.app.launch.for_recording:
            # A set launched for recording holds the recorder's instruments, which are never saved, so the mark would say unsaved changes in every video.
            return NOTHING
        document = self.document()
        if not document.get_path():
            return MSG_UNSAVED_MARK
        return MSG_UNSAVED_CHANGES_MARK if document.is_dirty() else MSG_SAVED_MARK

    def header(self, width):
        """Return the header's lines: where you are and what is open, then the rule or the theme's stripe.

        The user's design, keeping what matters most in the corners: the first line has the crumbs,
        which change with every page, in the left corner, llamatron centred, and the set's file and
        the save mark at the right; the second has the current song and the song's length at the
        right. The set and the song are one block, left-justified and as wide as it needs, just left
        of the save mark and the length, so that llamatron stays exactly centred; it gives way when
        the crumbs or the block need its room. On a page with a theme, the stripe carries the page's
        caption, what the page is doing.
        """
        marks = [self.save_mark(), self.time_text()]
        names = [self.set_crumb(), self.song_crumb()]
        marks_width = max(len(mark) for mark in marks)
        names_width = max(len(name) for name in names)
        names_start = max(width - 1 - marks_width - len(HEADER_GAP) - names_width, 1)
        crumbs = MSG_CRUMB_SEPARATOR.join(self.crumb_trail())
        first = self.header_line(width=width, left=crumbs, names=names[0], names_start=names_start, mark=marks[0], centre=PROGRAM_NAME)
        second = self.header_line(width=width, left=NOTHING, names=names[1], names_start=names_start, mark=marks[1])
        theme = self.theme()
        if theme is None:
            return [first, second, Text(Box.HEAVY_RULE * width)]
        # The page's theme colour, the user's design: a solid stripe in place of the rule carrying the page's caption, and a blank line
        # under it before the page where the screen has room, so that an 80 by 24 console keeps every line it had.
        caption = fit(text=self.caption(), width=max(width - 2, 1)).rstrip()
        text = Text((SPACE + caption).ljust(width)[:width], style=RichStyle(bold=True, color=Color.from_rgb(*caption_colour(theme)), bgcolor=Color.from_rgb(*theme)))
        stripe = [first, second, text]
        return stripe + [Text(NOTHING)] if self.has_room_for_the_gap() else stripe

    def caption(self):
        """Return what the theme's stripe says the page is doing: its own crumb, in capitals, unless the page says more."""
        return self.crumb_trail()[-1].upper()

    def header_line(self, *, width, left, names, names_start, mark, centre=None):
        """Return one bold header line: the left text in the left corner, the names from names_start, the mark in the right corner, and the centre text, when given, exactly in the middle, giving way when the left text or the names need its room; the left text is cut to leave room for the rest."""
        characters = [SPACE] * width
        mark_start = max(width - len(mark) - 1, 0)
        left_end = names_start - len(HEADER_GAP)
        centre_start = max((width - len(centre or NOTHING)) // 2, 0)
        if centre and len(left) + 2 <= centre_start and centre_start + len(centre) + len(HEADER_GAP) <= names_start:
            characters[centre_start:centre_start + len(centre)] = list(centre)
            left_end = min(left_end, centre_start - 1)
        shown = fit(text=left, width=max(left_end - 1, 1)).rstrip() if left else NOTHING
        characters[1:1 + len(shown)] = list(shown)
        shown_names = names[:max(mark_start - len(HEADER_GAP) - names_start, 0)]
        characters[names_start:names_start + len(shown_names)] = list(shown_names)
        characters[mark_start:mark_start + len(mark)] = list(mark)
        return Text(NOTHING.join(characters[:width]), style=Style.BOLD, no_wrap=True)

    def has_room_for_the_gap(self):
        """Return whether the screen is tall enough for the blank line under a theme's stripe."""
        return self.theme() is not None and self.size.height >= ROOM_FOR_THE_GAP

    def header_lines(self):
        """Return how many lines the header takes: its two lines, the rule or the theme's stripe, and the blank line under the stripe where there's room."""
        return HEADER_LINES + (1 if self.has_room_for_the_gap() else 0)

    def theme(self):
        """Return the page's theme colour (tui/themes.py), which a stripe under the header shows, or None for a page that keeps the plain rule."""
        return self.THEME

    def staged_screen(self, *, screen, width, height):
        """Return the whole screen to show from the page's lines: as they are, unless a page draws something over all of it, as Arrange does for a batch video's stage."""
        return screen

    def draw(self):
        if not self.is_attached or not self.query(VIEW_SELECTOR):
            return
        width, height = self.size
        if width <= 0 or height <= 0:
            return
        strip = self.holder.caption_strip()
        # The video tutorial's captions take the foot of the screen, and the page moves up to make room.
        if strip is not None:
            height = max(height - CAPTION_LINES, 1)
        self.screen_height = height
        lines = self.page_lines(width=width, height=height)
        screen = self.staged_screen(screen=lines, width=width, height=height)
        if strip is not None:
            screen = screen + strip.lines(width)
        self.query_one(VIEW_SELECTOR, Static).update(Text(LINE_BREAK).join(screen))

    def page_lines(self, *, width, height):
        """Return the page's lines at a size: the header, the body, the status line, the rule and the legend, which draw shows and a batch video's stage draws again smaller inside its frame."""
        top = self.header(width)
        bottom = legend(keys=self.shown_keys(), width=width) if self.shows_legend else []
        rule = [Text(Box.RULE * width, style=Style.DIM)] if bottom else []
        # The status line is dim, as the user asked, so that it reads as a note rather than part of the page.
        line = self.holder.status_line()
        status = Text(SPACE + fit(text=line.text() or self.resting_status(), width=width - 1), style=Style.REFUSAL if line.is_refusal() else Style.DIM)
        room = max(height - len(top) - len(rule) - len(bottom) - 1, 1)
        lines = self.body(width=width, height=room)[:room]
        lines += [Text(NOTHING) for _ in range(room - len(lines))]
        # A line that wrapped would push the keys off the bottom of the screen.
        for line in lines:
            line.truncate(width, overflow=OVERFLOW_ELLIPSIS)
        return [*top, *lines, status, *rule, *bottom]
