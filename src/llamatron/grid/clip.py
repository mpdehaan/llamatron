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

"""One cell of the grid a song renders into: a list of positions played in order."""

import re
from itertools import count

from llamatron.support.length import ZERO, Length
from llamatron.composition.groove import Groove
from llamatron.composition.checks import check_clip_length, check_loop, check_name, check_scale, check_time_signature_override
from llamatron.grid.control import Control
from llamatron.grid.positions import exact_length, fit_to_length, piece_of
from llamatron.music.chord import Chord
from llamatron.music.held import Held
from llamatron.music.note import Degree, Note, Rest
from llamatron.music.sound import CHORD, HELD, HELD_SOUND, KIND, LENGTH, NOTES, PARTS, PHRASE, REST, Sound
from llamatron.strings.errors import (
    ERR_CLIP_GRID_NOT_A_POSITION, ERR_INVALID_SECTION, ERR_INVALID_TIMES, ERR_NOT_A_GROOVE, ERR_NO_LENGTH, ERR_NOT_CONTROLS, ERR_NOT_NOTES,
)
from llamatron.strings.reprs import REPR_CLIP

# The shorthand a clip's list accepts: each dash is a quarter note of rest, and a note is its name and octave.
REST_DASH = '-'
QUARTER_NOTE = 0.25
NOTE_TEXT = re.compile(r'([A-G][#b]?)(\d+)')

# The classes a clip's list holds, for asking whether a value is already one of them.
POSITION_TYPES = (Note, Chord, Rest, Degree, Held)
POSITION_KINDS = frozenset(POSITION_TYPES)
# Every clip gets the next number when it's made, whichever grid it ends up in.
_next_clip_id = count(0)


def _to_position(value):
    """Turn shorthand for a clip into an object: 'E4' is a Note, 3 is a Degree and '--' is a Rest."""
    if isinstance(value, POSITION_TYPES):
        return value
    # bool is a subclass of int, but True is not a real degree.
    if type(value) is int:
        return Degree(number=value)
    if isinstance(value, str):
        if value and set(value) == {REST_DASH}:
            return Rest(len(value) * QUARTER_NOTE)
        match = NOTE_TEXT.fullmatch(value)
        if match:
            return Note(name=match[1], octave_number=int(match[2]))
    raise ValueError(ERR_CLIP_GRID_NOT_A_POSITION.format(value=value))


def _same_objects(*, first, second):
    """Return whether two sequences hold the very same objects, in order."""
    return len(first) == len(second) and all(a is b for a, b in zip(first, second))


def _control_time(control):
    return control.get_time()


class Clip:
    """One cell of the song's grid: a list of notes, chords, rests and degrees played in order.

    The list can use shorthand: 'E4' is a Note, 3 is a Degree, and each dash is a
    quarter note of rest, so '--' is a half rest. Notes and degrees without their own
    length use note_length, and degrees use whichever scale applies when rendered.

    A length of None ends the clip after the last position. Otherwise the clip is
    exactly that long, adding silence or cutting off notes to fit. Like note
    lengths, it's a fraction of a whole note, so 1 is a whole note or four quarters.
    A scale of None uses the scene's or song's. Clips have no tempo of their own. Loop
    is whether Live plays the clip again when it reaches its end. Controls are the MIDI CC
    values it sends, which generators keep, and sections and repeats cut and repeat with the
    notes.

    A clip holds its positions one of two ways. Given notes, it keeps the Notes, Chords, Rests,
    Degrees and Held it was given, which is how a test or a tool builds one. Given sounds, it
    keeps the tuples a render makes (music/sound.py), which is what playing, the generators
    and the exporters work on. get_notes() and get_sounds() give either clip either way.
    """

    __slots__ = ('_id', '_name', '_notes', '_sounds', '_scale', '_length', '_note_length', '_loop', '_controls', '_time_signature', '_groove', '_strum', '_nudge', '_handed')

    def __init__(self, *, name=None, notes=None, sounds=None, scale=None, length=None, note_length=None, loop=True, controls=None, time_signature=None):
        check_loop(loop)
        self._id = next(_next_clip_id)
        self.set_name(name)
        if sounds is None:
            self.set_notes([] if notes is None else notes)
        else:
            self._notes = None
            self._sounds = sounds
        self.set_scale(scale)
        self.set_length(length)
        self.set_note_length(note_length)
        self._loop = loop
        self._controls = self._sorted_controls([] if controls is None else controls)
        self.set_time_signature(time_signature)
        self._groove = None
        self._strum = None
        self._nudge = None
        self._handed = ()

    def get_id(self):
        return self._id

    def get_name(self):
        return self._name

    def set_name(self, name):
        check_name(name)
        self._name = name

    def get_notes(self):
        """The clip's own list of positions as Notes, Chords, Rests, Degrees and Held, which can be appended to.

        A clip made of sounds makes the objects the first time it's asked and keeps them from
        then on in place of the sounds, so that the list is the clip's own either way.
        """
        if self._notes is None:
            self._notes = [Sound.position(sound) for sound in self._sounds]
            self._sounds = None
        return self._notes

    def set_notes(self, notes):
        if not isinstance(notes, (list, tuple)):
            raise ValueError(ERR_NOT_NOTES.format(value=notes))
        # This makes a new list, so that clips built from the same list don't share it. A note,
        # chord or rest is kept as it is, and only shorthand is read.
        self._notes = [position if type(position) in POSITION_KINDS else _to_position(position) for position in notes]
        self._sounds = None

    def get_sounds(self):
        """The clip's positions as sounds, the tuples of music/sound.py, which is what a render makes and reads.

        A clip that keeps objects says them as sounds each time it's asked, since its list can
        be appended to, and anything in the list that is no position raises ValueError.
        """
        if self._sounds is None:
            return [Sound.of(position) for position in self._notes]
        return self._sounds

    def has_positions(self):
        """Return whether the clip lists anything at all."""
        return bool(self._notes if self._sounds is None else self._sounds)

    def get_scale(self):
        return self._scale

    def get_groove(self):
        """Return the Groove the clip plays with, or None for straight timing. The exporters' timing applies it."""
        return self._groove

    def set_groove(self, groove):
        """Give the clip a Groove, or None, which the renderer does once the clip is finished, so generators never see one."""
        if groove is not None and not isinstance(groove, Groove):
            raise ValueError(ERR_NOT_A_GROOVE.format(value=groove))
        self._groove = groove

    def get_strum(self):
        """Return how the clip strums its chords, a StrumPlan, or None when it strums nothing. The exporters' timing plays it."""
        return self._strum

    def get_nudge(self):
        """Return how the clip's notes are nudged early or late, a NudgePlan, or None. The exporters' timing plays it, on top of the groove."""
        return self._nudge

    def set_nudge(self, nudge):
        """Give the clip a NudgePlan, or None, which the renderer does once the clip is finished, as it gives its groove."""
        self._nudge = nudge

    def get_handed(self):
        """Return the notes a Hocket hands the clip, HandedNotes in time order, which the exporters' timing adds to the clip's own; none unless the renderer gave some."""
        return self._handed

    def set_handed(self, notes):
        """Give the clip the notes its Hocket hands it, which the renderer does once the clip is finished, as it gives its groove."""
        self._handed = tuple(notes)

    def set_strum(self, strum):
        """Give the clip a StrumPlan, or None, which the renderer does once the clip is finished, as it gives its groove."""
        self._strum = strum

    def set_scale(self, scale):
        check_scale(scale)
        self._scale = scale

    def get_length(self):
        return self._length

    def set_length(self, length):
        check_clip_length(length)
        self._length = length

    def get_note_length(self):
        return self._note_length

    def set_note_length(self, note_length):
        check_clip_length(note_length)
        self._note_length = note_length

    def get_loop(self):
        return self._loop

    def get_time_signature(self):
        """Return the TimeSignature its pattern was written in, or None for the song's, for the bars a DAW draws for the clip."""
        return self._time_signature

    def set_time_signature(self, signature):
        check_time_signature_override(signature)
        self._time_signature = signature

    def get_controls(self):
        """The clip's CC values, in time order."""
        return self._controls

    def add_controls(self, controls):
        """Add CC values to the clip, among those it has, in time order."""
        self._controls = self._sorted_controls([*self._controls, *controls])

    def _sorted_controls(self, controls):
        if not isinstance(controls, (list, tuple)) or not all(isinstance(item, Control) for item in controls):
            raise ValueError(ERR_NOT_CONTROLS.format(value=controls))
        return sorted(controls, key=_control_time)

    def resolved_notes(self):
        """Return the notes with every missing length filled in from note_length.

        Raises ValueError if a length is missing and there's no note_length. Degrees
        stay as degrees, because they don't become notes until they're rendered.
        """
        return [Sound.position(sound) for sound in self.resolved_sounds()]

    def resolved_sounds(self):
        """Return the clip's sounds with every missing length filled in from note_length, which a rendered clip's already are."""
        return [self._filled(sound) for sound in self.get_sounds()]

    def _filled(self, sound):
        """Return a sound with its missing lengths filled in, or the sound itself if none were missing."""
        kind = sound[KIND]
        if kind == PHRASE:
            parts = [self._filled(part) for part in sound[PARTS]]
            return sound if _same_objects(first=parts, second=sound[PARTS]) else (PHRASE, sound[LENGTH], tuple(parts))
        if kind == HELD:
            filled = self._filled(sound[HELD_SOUND])
            return sound if filled is sound[HELD_SOUND] else (HELD, sound[LENGTH], filled)
        if sound[LENGTH] is not None:
            # A rest, or a note, degree or chord with every length of its own, which is nearly every position of a rendered clip.
            return sound
        if kind == CHORD:
            return Sound.chord([self._filled(note) for note in sound[NOTES]])
        return Sound.with_length(sound, self._note_length_for(sound))

    def _note_length_for(self, sound):
        """Return the length for a note or degree that has none, which is the clip's note_length, as a pair."""
        if self._note_length is None:
            raise ValueError(ERR_NO_LENGTH.format(position=Sound.position(sound)))
        return Length.exact(self._note_length)

    def _resolved_length(self, sound):
        """Return how long a sound lasts once its missing lengths are filled in, as a pair, without building anything."""
        kind = sound[KIND]
        if kind == HELD or kind == PHRASE:
            # What it holds is checked for missing lengths too, as resolving it would.
            for part in sound[PARTS] if kind == PHRASE else [sound[HELD_SOUND]]:
                self._resolved_length(part)
            return sound[LENGTH]
        if sound[LENGTH] is not None:
            return sound[LENGTH]
        if kind == CHORD:
            return Length.longest([self._resolved_length(note) for note in sound[NOTES]])
        return self._note_length_for(sound)

    def played_notes(self):
        """Return resolved notes that fill the clip's set length, if it has one."""
        return [Sound.position(sound) for sound in self.played_sounds()]

    def played_sounds(self):
        """Return resolved sounds that fill the clip's set length, if it has one."""
        sounds = self.resolved_sounds()
        return sounds if self._length is None else fit_to_length(positions=sounds, length=Length.exact(self._length))

    def total_length(self):
        """Return how long the clip lasts, as an exact fraction of a whole note."""
        if self._length is not None:
            return exact_length(self._length)
        return Length.rational(Length.total([self._resolved_length(sound) for sound in self.get_sounds()]))

    def section(self, *, start, end):
        """Return a new Clip of the part from start to end, in fractions of a whole note.

        A note that crosses either edge is cut, so its second half plays as a new note.
        Anything past the end of the clip becomes silence, so the result always lasts
        exactly end minus start.
        """
        start = exact_length(start)
        end = exact_length(end)
        if start < 0 or end <= start:
            raise ValueError(ERR_INVALID_SECTION.format(start=start, end=end))
        # Every note is asked where it lies between the two ends, so the ends are pairs from here on.
        first = Length.of(start)
        last = Length.of(end)
        sounds = []
        sound_start = ZERO
        for sound in self.played_sounds():
            if not Length.less(sound_start, last):
                # Everything from here on starts after the section ends.
                break
            sound_end = Length.add(sound_start, sound[LENGTH])
            if Length.at_most(first, sound_start) and Length.at_most(sound_end, last):
                # A position that lies wholly inside the section is kept as it is.
                sounds.append(sound)
            else:
                piece_start = Length.longer(first, sound_start)
                piece_end = Length.shorter(last, sound_end)
                if Length.less(piece_start, piece_end):
                    sounds.append(piece_of(position=sound, offset=Length.subtract(piece_start, sound_start), length=Length.subtract(piece_end, piece_start)))
            sound_start = sound_end
        if Length.less(sound_start, last):
            sounds.append((REST, Length.subtract(last, Length.longer(sound_start, first))))
        controls = [item.moved_by(-start) for item in self._controls if start <= item.get_time() < end]
        return Clip(name=self._name, sounds=sounds, scale=self._scale, note_length=self._note_length, controls=controls)

    def repeated(self, times):
        """Return a new Clip that plays this one times in a row, so it lasts times as long."""
        if type(times) is not int or times < 1:
            raise ValueError(ERR_INVALID_TIMES.format(times=times))
        length = self.total_length()
        controls = [item.moved_by(length * place) for place in range(times) for item in self._controls]
        return Clip(
            name=self._name, sounds=self.played_sounds() * times, scale=self._scale,
            note_length=self._note_length, controls=controls,
        )

    def __repr__(self):
        # Printing a clip leaves it holding what it held, so the objects are made for the text alone.
        notes = self._notes if self._sounds is None else [Sound.position(sound) for sound in self._sounds]
        return REPR_CLIP.format(name=self._name, notes=notes, scale=self._scale, length=self._length, note_length=self._note_length, id=self._id)
