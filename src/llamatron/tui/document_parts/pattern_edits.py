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

"""The Document's edits to patterns, and the answers the pattern editor asks about one: its notes as the piano roll sees them, its scales and its octaves."""


from llamatron.composition.file_format import Section
from llamatron.composition.pattern import Pattern

# How many steps a new pattern has.
NEW_PATTERN_STEPS = 16
# How many scale degrees to allow when the song has no scale to say.
DEGREE_LIMIT_WITHOUT_A_SCALE = 7


class PatternEdits:
    """The changes the pattern editor makes, each through the pattern's own setters, and what the editor asks about a pattern on every row and cell.

    It holds no data of its own: it works on what Document keeps, through `self._setlist`,
    `self.song()` and `self._change(method, ...)`, which makes one change through an object's own
    method and notes it.
    Answers are kept through `self.remembered(key=, on=, compute=)` until what they came from changes.
    """

    __slots__ = ()

    # Patterns.

    def _pattern(self, name):
        return self._setlist.get_pattern(name)

    def add_pattern(self, *, name, steps=None):
        """Add a pattern of empty steps: one bar of the current song's time signature unless a count is given, or 16 when a bar isn't whole steps."""
        if steps is None:
            steps = self.song().steps_in_a_bar() or NEW_PATTERN_STEPS
        self._change(self._setlist.add_item, section=Section.PATTERNS, name=name, item=Pattern(steps=steps, rows={}))

    def step_value(self, *, name, row, step):
        return self._pattern(name).get_value(row=row, step=step)

    def set_step_value(self, *, name, row, step, value):
        self._change(self._pattern(name).set_value, row=row, step=step, value=value)

    def clear_sound(self, *, name, step):
        """Empty a step, which keeps only its CC values, since they don't need a note."""
        self._change(self._pattern(name).clear_sound, step)

    # Notes as the piano roll handles them: by the steps they cover, through ties or a gate. The pattern knows how
    # (composition/pattern_notes.py); the document adds the pattern's step size and entry size, which the set may give it.

    def _step_size(self, name):
        """Return how long each step of a pattern is, which the pattern needs to read a gate as steps: its own step size, or else the set's."""
        return self.lengths().step_size(name)

    def _reshape(self, method, **named):
        """Make a change to a note through one of the pattern's methods that answers whether it could, noting a change only when it did, and return the answer."""
        made = method(**named)
        if made:
            self.changed(inside_a_pattern=True)
        return made

    def note_span(self, *, name, step):
        """Return how many steps the note on a step covers on the piano roll: its ties, or its gate rounded up to whole steps, and any ties right after that."""
        return self._pattern(name).note_span(step=step, step_size=self._step_size(name))

    def covering_notes(self, name):
        """Return the step of the note sounding through each step on the piano roll, by step, leaving out steps nothing covers, kept until the pattern or the set's step size changes."""
        return self.remembered(
            key=(PatternEdits.covering_notes.__name__, name), on=(self._pattern(name), self._setlist),
            compute=lambda: self._pattern(name).covering_notes(step_size=self._step_size(name)),
        )

    def _note_start(self, *, name, step):
        """Return the step the note covering a step starts on, or None when nothing covers it."""
        return self.covering_notes(name).get(step)

    def chord_tones(self, *, name, step, octave):
        """Return the notes a step's chord adds above its own note, each as a degree, an octave and an accidental, for the piano roll's ghosts, placed in the one scale the pattern plays under."""
        scale_name = self.pattern_scale(name)
        scale = None if scale_name is None else self._scale(scale_name)
        return self._pattern(name).chord_tones(step=step, octave=octave, scale=scale)

    def partial_cell(self, *, name, step):
        """Return what part of a note's last cell its gate fills, when the gate ends inside a step, or None when the cell is full, so that the roll's bar ends where the sound does."""
        return self._pattern(name).partial_cell(step=step, step_size=self._step_size(name))

    def place_note(self, *, name, step, degree, octave, accidental=None):
        """Draw a note of the pattern's entry size on a step, cutting the note it lands in."""
        self._change(
            self._pattern(name).draw_note, step=step, degree=degree, octave=octave, accidental=accidental,
            length=self.entry_size(name), step_size=self._step_size(name),
        )

    def split_note(self, *, name, step):
        """Split the note held through a step there, so that the rest of it is a note of its own, and return whether there was one to split."""
        return self._reshape(self._pattern(name).split_note, step=step)

    def lengthen_note(self, *, name, step):
        """Drag the end of the note covering a step one step later, and return whether there was a note with room after it."""
        start = self._note_start(name=name, step=step)
        if start is None:
            return False
        return self._reshape(self._pattern(name).lengthen_note, start=start, step_size=self._step_size(name))

    def shorten_note(self, *, name, step):
        """Drag the end of the note covering a step one step earlier, and return whether there was a note longer than one step."""
        start = self._note_start(name=name, step=step)
        if start is None:
            return False
        return self._reshape(self._pattern(name).shorten_note, start=start, step_size=self._step_size(name))

    def cycle_accidental(self, *, name, step):
        """Move the note covering a step on to the next of natural, sharp and flat, and return whether there was a note."""
        start = self._note_start(name=name, step=step)
        if start is None:
            return False
        self._change(self._pattern(name).cycle_accidental, start)
        return True

    def pattern_octave_range(self, name):
        """Return the lowest and highest octave of the one track that plays a pattern, or None when no track or more than one does."""
        return self.remembered(key=(PatternEdits.pattern_octave_range.__name__, name), on=(self.outside_patterns(),), compute=lambda: self._pattern_octave_range(name))

    def _pattern_octave_range(self, name):
        plays = {(song, track) for song, _, _, track in self._setlist.clip_slots_naming(section=Section.PATTERNS, name=name)}
        if len(plays) != 1:
            return None
        song_name, track_name = plays.pop()
        track = self._setlist.get_song(song_name).get_track(track_name)
        return track.get_lowest_octave(), track.get_highest_octave()

    def cc_numbers_for_pattern(self, *, name, lane):
        """Return the distinct CC numbers one of a pattern's CC lanes sends on the tracks that play it, in any song, None among them for a track where the lane sends nothing, and nothing when no track plays it."""
        return self.remembered(key=(PatternEdits.cc_numbers_for_pattern.__name__, name, lane), on=(self.outside_patterns(),), compute=lambda: self._cc_numbers_for_pattern(name=name, lane=lane))

    def _cc_numbers_for_pattern(self, *, name, lane):
        plays = dict.fromkeys((song, track) for song, _, _, track in self._setlist.clip_slots_naming(section=Section.PATTERNS, name=name))
        numbers = [self._setlist.get_song(song).get_track(track).get_cc_numbers()[lane] for song, track in plays]
        return list(dict.fromkeys(numbers))

    def allowed_inc_max(self, *, pattern, register):
        """Return the most a step of a pattern may add to a register or take from it: the narrowest of the songs that play the pattern, or the current song's when none does."""
        return self.remembered(
            key=(PatternEdits.allowed_inc_max.__name__, pattern, register), on=(self.outside_patterns(),),
            compute=lambda: self._setlist.allowed_inc_max_for_pattern(name=pattern, register=register) or self.song().get_register(register).get_allowed_inc_max(),
        )

    def steps_with_anything_past(self, *, name, steps):
        """Return how many steps from a position onward hold a note or a CC value."""
        return self._pattern(name).steps_with_anything_from(steps)

    def set_steps(self, *, name, steps):
        """Change how many steps a pattern has, cutting them or adding empty steps at the end."""
        self._change(self._pattern(name).set_steps, steps)

    def insert_step(self, *, name, step):
        self._change(self._pattern(name).insert_step, step)

    def remove_step(self, *, name, step):
        self._change(self._pattern(name).remove_step, step)

    def set_drum(self, *, name, drum):
        """Change a pattern's type, which clears the notes because they mean something else."""
        self._change(self._pattern(name).set_drum, drum)

    def set_direction(self, *, name, direction):
        self._change(self._pattern(name).set_direction, direction)

    def set_step_size(self, *, name, step_size):
        """Give a pattern its own step size, or None to use the set's."""
        self._change(self._pattern(name).set_step_size, step_size)

    def set_pattern_time_signature(self, *, name, time_signature):
        """Give a pattern its own time signature, written like 6/8, or None to use the song's."""
        self._change(self._pattern(name).set_time_signature, time_signature)

    def set_pattern_entry_size(self, *, name, entry_size):
        """Give a pattern its own entry size, written like 1/8, or None to use the song's."""
        self._change(self._pattern(name).set_entry_size, entry_size)

    def entry_size(self, name):
        """Return how long a note placed on a pattern's piano roll lasts, in whole notes."""
        return self.song().entry_size_for(self._pattern(name))

    def written_entry_size(self, name):
        """Return a pattern's own entry size as the file writes it, like 1/8, or None when it uses the song's."""
        entry_size = self._pattern(name).get_written_entry_size()
        return None if entry_size is None else str(entry_size)

    def reverse_after(self, *, name, step):
        """Reverse every step after this one."""
        self._change(self._pattern(name).reverse_after, step)

    def reverse_before(self, *, name, step):
        """Reverse every step before this one."""
        self._change(self._pattern(name).reverse_before, step)

    def reverse_steps(self, name):
        """Reverse the whole pattern, and return where a step ends up."""
        self._change(self._pattern(name).reverse)

    def pivot_around(self, *, name, step):
        """Swap what's before this step with what's after it, and return where the step ends up."""
        return self._change(self._pattern(name).pivot_around, step)

    def shuffle_steps(self, name):
        """Put the steps in a random order, drawn from the program's own random stream rather than any seed."""
        self._change(self._pattern(name).shuffle)

    def load_over(self, *, name, other):
        """Replace a pattern's contents with a copy of another's, keeping its name."""
        self._change(self._setlist.replace_item, section=Section.PATTERNS, name=name, item=self._pattern(other).copy())

    def has_grab_steps(self, name):
        """Return whether a pattern has any steps marked to grab."""
        return self._pattern(name).has_grab_steps()

    def has_notes(self, name):
        return self._pattern(name).has_notes()

    def degree_limit(self, name):
        """Return the highest degree to allow, from every scale that this pattern can play in.

        Scales come from the scene and then the song, in every song of the set, so a pattern used
        in several places can play in several scales, and the largest of those sets the limit.
        """
        return self.remembered(key=(PatternEdits.degree_limit.__name__, name), on=(self.outside_patterns(),), compute=lambda: self._degree_limit(name))

    def _degree_limit(self, name):
        names = [self.song().get_scale_name(), *self._setlist.scales_for_pattern(name)]
        sizes = [self.scale_size(scale) for scale in names if scale]
        return max(sizes) if sizes else DEGREE_LIMIT_WITHOUT_A_SCALE

    def scales_of_pattern(self, name):
        """Return the distinct scales a pattern plays under, in order: its uses' scenes' or songs', or the current song's when nothing uses it."""
        return self.remembered(key=(PatternEdits.scales_of_pattern.__name__, name), on=(self.outside_patterns(),), compute=lambda: self._scales_of_pattern(name))

    def _scales_of_pattern(self, name):
        if self._setlist.clip_slots_naming(section=Section.PATTERNS, name=name):
            names = self._setlist.scales_for_pattern(name)
        else:
            names = [self.song().get_scale_name()]
        return list(dict.fromkeys(scale for scale in names if scale))

    def pattern_scale(self, name):
        """Return the scale a pattern's notes can be named in, or None when its uses play it under more than one, or under none."""
        scales = self.scales_of_pattern(name)
        return scales[0] if len(scales) == 1 else None

    def scale_note_names(self, name):
        return self._scale(name).get_note_names()

    def note_name(self, *, name, step):
        """Return the name of a step's note, like F#3, in the scale the pattern plays under, or the current song's when that isn't known, or None."""
        song = self.song()
        scale_name = self.pattern_scale(name) or song.get_scale_name()
        scale = None if scale_name is None else song.get_named_scale(scale_name)
        return self._pattern(name).get_note_name(
            step=step, scale=scale, default_octave=song.get_default_octave(), default_drum_octave=song.get_default_drum_octave(),
            octave_label_offset=song.octave_label_offset(),
        )
