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

"""What several screens share: the scale and root pickers, the note lengths, the file suffixes and the key lists that list pages build from."""

from llamatron.composition import limits
from llamatron.composition.generator_settings import written_name
from llamatron.generators.arp import ChordOrder
from llamatron.music import time_signature
from llamatron.music.time_signature import is_time_signature
from llamatron.strings import errors, marks, messages, names
from llamatron.tui import drawing


SONG_SUFFIX = '.yml'
# Where a seed starts counting from when one is set on a field that had none.
NO_SEED = 0
SONG_SUFFIXES = (SONG_SUFFIX, '.yaml')
# The MIDI files the import's picker shows.
MIDI_SUFFIXES = ('.mid', '.midi')
ORDERS = [written_name(order) for order in ChordOrder]
DEFAULT_ORDER = ORDERS[0]


def octave_moved(*, octave, offset):
    """Return an octave moved by an offset, kept within the file's range."""
    return max(min(octave + offset, limits.MAX_OCTAVE), limits.MIN_OCTAVE)


def stepped(*, values, current, offset):
    """Return the next value in a list, starting from the middle if the current one isn't there."""
    text = str(current)
    place = values.index(text) if text in values else len(values) // 2
    return values[max(min(place + offset, len(values) - 1), 0)]


def numbers_text(numbers):
    """Return numbers with a space between them and a dash for each that isn't set, like 74 - - 1."""
    return drawing.SPACE.join(marks.MSG_NO_NUMBER_MARK if number is None else str(number) for number in numbers)


def list_keys(*, page, extra, always=()):
    """Return the keys every list of named things has: + adds, the extra ones only with something selected, and the always ones whatever is."""
    result = [page.bind(page.KEYS.BACK, action=page.go_back), *page.move_keys(), page.bind(page.KEYS.ADD, action=page.add)]
    if page.current() is not None:
        result += extra
    result += always
    return result


def move_key(page):
    """Return M, which picks up the selected row for Move mode."""
    return page.bind(page.KEYS.MOVE, action=page.start_moving)


def counts_text(counts):
    """Return an AutoRatchet's counts as typed, like 1 1 4, or nothing when it has none yet."""
    return drawing.SPACE.join(str(count) for count in counts or [])


def play_through(*, page, play, what, said):
    """Start real-time playback through the page's transport: tell why nothing can play if so, and otherwise play and say on the status line what started, or that what (the scene or clip, named) starts at the next bar."""
    problem = page.app.transport.problem()
    if problem is not None:
        page.tell(problem.title, *problem.lines)
        return
    tried = page.app.transport.try_play(play)
    if tried.refusal is not None:
        page.tell(errors.ERR_CANT_PLAY_TITLE, tried.refusal)
        return
    page.say(messages.MSG_STARTS_AT_NEXT_BAR.format(what=what) if tried.answer else said)


def scene_name(*, scene, index):
    """Return a scene's name, or what it's called by its place if the file gives it none."""
    name = scene.get_name()
    return names.MSG_NEW_SCENE_NAME.format(number=index + 1) if name is None else str(name)


def ask_time_signature(*, page, title, current, then, blank_allowed):
    """Ask for a time signature written like 6/8, and pass it on as text, or None for a blank where that's allowed."""
    def answered(text):
        text = text.strip()
        if not text and blank_allowed:
            then(None)
        elif is_time_signature(text):
            then(text)
        else:
            page.refuse(errors.ERR_TYPED_NOT_A_TIME_SIGNATURE.format(text=text, lowest=time_signature.MIN_BEATS, highest=time_signature.MAX_BEATS, units=time_signature.UNITS_LISTED))
    page.ask_text(title=title, value=current, then=answered)


def columns(rows):
    """Return one line for each (name, description) pair, with the descriptions lined up, for a picker's choices on the clip page and the pattern editor."""
    widest = max((len(name) for name, _ in rows), default=0)
    return [marks.MSG_COLUMN_LINE.format(name=name.ljust(widest), description=description).rstrip() for name, description in rows]
