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

"""The start screen: the title on black with "Press ENTER to Start" under it, which the tracker opens on, after a classic video game's start page.

Shown over the main screen whenever the tracker is started from the command line to be used; a launch that plays on its own
never shows it. While it shows, real time is got ready underneath (Transport.prepare), as a game loads behind its title: the
scanner sweeps at least once, and on while anything loads, the prompt comes once all is ready, and only then does Enter take the
screen away and leave the main screen, with any dialog the opening raised, to be used.
"""

from llamatron.tui import keybindings
from llamatron.tui.components.title_card import Prompt, title_lines
from llamatron.tui.key_table import BindsKeys, pressed_key, quits_at_once
from llamatron.tui.screens.set.splash import Splash


class StartScreen(Splash, BindsKeys):
    """The title with its prompt, until Enter."""

    KEYS = keybindings.StartScreen
    PROMPT = True

    def __init__(self, *, ready=None, **named):
        """Takes what Splash takes; with no seconds it shows until Enter. ready answers whether what loads under the title is done,
        or is None when nothing loads."""
        named.setdefault('seconds', None)
        super().__init__(**named)
        self._ready = ready
        # When what loads was done, on the title's clock, None while it loads.
        self._loaded_at = 0.0 if ready is None else None

    def loaded_at(self):
        """Return when what loads under the title was done, the first time it is seen done, or None while it loads."""
        if self._loaded_at is None and self._ready():
            self._loaded_at = self.elapsed()
        return self._loaded_at

    def lines(self, *, width, height):
        return title_lines(width=width, height=height, elapsed=self.elapsed(), prompt=Prompt(loaded_at=self.loaded_at()), seconds=self._seconds)

    def keys(self):
        return [self.bind(self.KEYS.START, action=self.start)]

    def on_key(self, event):
        event.stop()
        event.prevent_default()
        name = pressed_key(event)
        if quits_at_once(name):
            self.app.exit()
            return
        for item in self.keys():
            if name in item.keys:
                item.press(name)
                return

    def start(self):
        """Take the start screen away, leaving what is under it, once what loads under it is done."""
        if self.loaded_at() is not None:
            self.app.pop_screen()
