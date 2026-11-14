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

"""The start screen: the title on black with "Press ENTER to Start" under it, which the tracker opens on, the user's design after a classic video game's start page.

Shown over the main screen when the tracker is started from the command line to be used, unless
LLAMATRON_NO_SPLASH=1 (tui/launch.py); a launch that plays on its own never shows it. Enter takes it
away and leaves the main screen, with any dialog the opening raised, to be used.
"""

from llamatron.tui import keybindings
from llamatron.tui.key_table import BindsKeys, pressed_key, quits_at_once
from llamatron.tui.screens.splash import Splash


class StartScreen(Splash, BindsKeys):
    """The title with its prompt, until Enter."""

    KEYS = keybindings.StartScreen
    PROMPT = True

    def __init__(self, **named):
        """Takes what Splash takes; with no seconds it shows until Enter."""
        named.setdefault('seconds', None)
        super().__init__(**named)

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
        """Take the start screen away, leaving what is under it."""
        self.app.pop_screen()
