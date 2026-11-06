# llamatron: a Python language and framework for producing MIDI clips.
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
    python -m llamatron examples/retro_chill.yml
"""

import sys

from textual.app import App

from llamatron.composition.song_file_error import SongFileError
from llamatron.tui.base import ConfirmDialog
from llamatron.tui.document import Document
from llamatron.tui.pages import MainPage


class LlamatronApp(App):
    """Holds the song being edited, and asks before quitting with unsaved changes."""

    ENABLE_COMMAND_PALETTE = False
    BINDINGS = []
    CSS = """
    Screen { background: ansi_default; color: ansi_default; }
    ModalScreen { background: transparent; align: center middle; }
    #view { width: 100%; height: 100%; background: ansi_default; color: ansi_default; }
    #dialog { width: auto; height: auto; background: ansi_default; color: ansi_default; }
    #dialog-view { width: auto; height: auto; background: ansi_default; color: ansi_default; }
    """

    def __init__(self, document=None):
        super().__init__(ansi_color=True)
        self.document = document or Document()
        # Which rows the pattern editor shows under Degree, which stays as you move between patterns.
        self.row_set = 'normal'

    def on_mount(self):
        self.push_screen(MainPage(self))

    def request_quit(self):
        if self.document.dirty:
            def answered(result):
                if result:
                    self.exit()
            self.push_screen(ConfirmDialog('Quit', ['This song has unsaved changes, which will be lost. Quit anyway?']), answered)
        else:
            self.exit()

    async def action_quit(self):
        self.request_quit()


def main(argv=None):
    """Open a song if one is named, and return 1 if it can't be read."""
    arguments = sys.argv[1:] if argv is None else argv
    document = None
    if arguments:
        try:
            document = Document.load(arguments[0])
        except SongFileError as error:
            print(f'error: {error}', file=sys.stderr)
            return 1
    LlamatronApp(document).run()
    return 0


if __name__ == '__main__':
    sys.exit(main())
