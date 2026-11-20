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

"""Playing one pass through a pattern, step by step, into notes, chords and rests."""

from dataclasses import dataclass, field
from typing import NamedTuple

from llamatron.composition import defaults, file_format, limits
from llamatron.composition.checks import written_length
from llamatron.composition.conditions import draws_read, is_true
from llamatron.composition.file_format import Row, StepStatement
from llamatron.composition.named_scale import NamedScale
from llamatron.composition.song_file_error import SongFileError
from llamatron.generators.arp import along_scale
from llamatron.grid.clip import Clip
from llamatron.grid.control import Control
from llamatron.grid.keyswitch import SwitchedSlots
from llamatron.music import midi, note as note_values, sound as sound_values
from llamatron.music.sound import Sound
from llamatron.playback import drift
from llamatron.strings import errors
from llamatron.support import length as length_values
from llamatron.support.length import Length
from llamatron.support.rational import Rational

# How many octaves away a moved note can go to find one that fits the MIDI range. A move of
# whole octaves is taken out first, so this only has to cover the MIDI range itself.
MAX_OCTAVE_CHANGE = 10
# A step with no accidental moves its note by no half steps.
NO_ACCIDENTAL = ''
NO_HALF_STEPS = 0
# The list of steps a clip keeps its place in.
PATTERN_STEPS = 'steps'
# What registers add to a note or velocity when a step uses none of them.
NOTHING_ADDED = 0
# The start of a pass.
NO_TIME = 0
# The rows whose values a step plays from. A step's statements are gathered apart, whole, only where a pattern holds any.
PLAYED_ROWS = [row for row in file_format.PATTERN_ROWS if row not in file_format.STATEMENT_OF_ROW]
# Where what a step sounds keeps when it starts in the pass, before its pieces.
START = 0
# What a gate is multiplied by when its step is dotted or a triplet, as pairs, since every such step asks.
GATE_MODIFIER_PAIRS = {modifier: Length.exact(amount) for modifier, amount in file_format.GATE_MODIFIERS.items()}


@dataclass(kw_only=True, slots=True)
class Pass:
    """One pass through a pattern: its clip, and how long the ties at its start last.

    Ties at the very start of a pass continue the note that the pass before it ended with, which
    the pass can't reach, so whoever joins the passes lengthens that note by tied_from_before.
    """

    clip: Clip
    tied_from_before: Rational
    # How long the pass lasts, which is the pattern's length however the clip changes along the way.
    length: Rational
    # The keyswitch slots its steps' notes are played with, SwitchedSlots in time order, which no morph or generator touches.
    keyswitches: list = field(default_factory=list)
    # Whether a step's statement ended the clip during the pass, which then lasts only as far as it played, as a pass a step started over does.
    done: bool = False
class PlayedPattern(NamedTuple):
    """What playing needs to know of a pattern, gathered once for a clip: every step's values, and what no step of it does.

    A pattern that sends no CC values, changes no register or reads none is the usual one, and
    its steps skip that work, which is the same as doing it and finding nothing.
    """

    values: list
    sends_controls: bool
    sends_keyswitches: bool
    changes_registers: bool
    uses_registers: bool
    # Whether any step uses a draw or resets one, which is counted with the registers' changes.
    uses_draws: bool
    # Each step's statement about the registers that stops the clip, that starts the pattern over and that mutes the step, or None where no step holds one.
    stops: object
    restarts: object
    mutes: object
    # What each step does to the song's draws, a StepDraws a step, or None where no step uses, resets or redraws one.
    step_draws: object


class StepDraws(NamedTuple):
    """What one step does to the song's draws, all before its statements read the values, so that every use in the step sees one
    value of a draw: the draws it resets, and then the draws it takes, each once however many of its rows and statements use it."""

    resets: tuple
    drawn: tuple


# What a step sets the registers to and adds to them when its pattern changes none, or when a morph's target plays.
NO_ADDS = {}
# A step whose statements redraw nothing.
NO_REDRAWS = frozenset()
# A pass whose clip reads no draw that redraws as the pass starts.
NO_PASS_DRAWS = frozenset()
NO_SETS = {}


class PatternPlayer:
    """Plays a track's patterns in one scene, a pass at a time.

    It knows the song, for patterns, defaults and scales, the scene it plays in, the clip's scale,
    the track's transpose and the register the track's velocity is bound to, if any.
    """

    __slots__ = ('_song', '_scene', '_scale', '_scale_name', '_transpose', '_velocity_register', '_default_velocity', '_accent', '_scales_by_octave', '_scale_size', '_played_patterns', '_drifts')

    def __init__(self, *, song, scene, scale, track, scale_name=None, drifts=None):
        """scale_name is the scale the clip's degrees take their notes from: the clip's own, or the scene's when it's None.

        drifts is what the clip hears of the song's drifts, (DriftPlay, the names its chain names,
        where the scene starts from the song's top), or None for a clip that names none.
        """
        self._drifts = drifts
        self._song = song
        self._scene = scene
        self._scale = scale
        self._scale_name = scale_name or scene.get_scale_name()
        self._transpose = track.get_transpose()
        self._velocity_register = track.get_velocity_register()
        # What a step with no velocity typed plays at on this track, and what an accented step adds.
        self._default_velocity = song.default_velocity_of(track)
        self._accent = song.accent_of(track)
        # The scene's scale at each octave a note asked for, and its size, built once rather than for every note of every pass, since the scene's scale can't change while a clip plays.
        self._scales_by_octave = {}
        self._scale_size = None
        # Each pattern's step values, gathered the first pass it plays rather than for every pass, since no pattern changes while a clip plays.
        self._played_patterns = {}

    def _played(self, *, pattern_name, pattern):
        """Return a pattern's PlayedPattern, gathered the first time the pattern plays."""
        if pattern_name not in self._played_patterns:
            values = pattern.get_every_step_values(rows=PLAYED_ROWS)
            step_draws = self._step_draws(pattern=pattern, values=values)
            self._played_patterns[pattern_name] = PlayedPattern(
                values, pattern.sends_controls(), pattern.sends_keyswitches(),
                pattern.changes_registers(), pattern.uses_registers(), step_draws is not None,
                pattern.get_statements(StepStatement.STOP), pattern.get_statements(StepStatement.RESTART), pattern.get_statements(StepStatement.MUTE),
                step_draws,
            )
        return self._played_patterns[pattern_name]

    def _step_draws(self, *, pattern, values):
        """Return a StepDraws for each step of a pattern, from its steps' values, or None where no step uses, resets or redraws a draw."""
        redrawn = self._redrawn(pattern)
        if redrawn is None and not pattern.uses_draws():
            return None
        steps = []
        for step, step_values in enumerate(values):
            by_statements = redrawn[step] if redrawn is not None else NO_REDRAWS
            used = _draws_used(step_values)
            resets = _draws_reset(step_values)
            steps.append(StepDraws(resets, tuple(name for name in file_format.DRAW_NAMES if name in by_statements or name in used)))
        return steps

    def _redrawn(self, pattern):
        """Return the names each step's statements draw from, the draws that redraw in conditions, or None where no step's statement draws."""
        if not pattern.reads_draws():
            return None
        redrawing = {name for name in file_format.DRAW_NAMES if self._song.get_draw(name).redraws_in_conditions()}
        found = [set() for _ in range(pattern.get_steps())]
        for kind in file_format.STATEMENT_ROWS:
            for step, statement in enumerate(pattern.get_statements(kind) or []):
                if statement is not None:
                    found[step].update(name for name in draws_read(statement) if name in redrawing)
        return found if any(found) else None

    def _scene_scale_at(self, octave, *, effects=None, kind=None):
        """Return the clip's scale rooted at an octave, or the scale and root a drift overrides it with, built the first time each is asked for.

        kind is the scale type a step borrows its notes from, on the same root, or None for the scale's own.
        """
        scale_name = self._scale_name if effects is None or effects.scale is None else effects.scale
        root = None if effects is None else effects.root
        key = (octave, scale_name, root, kind)
        if key not in self._scales_by_octave:
            named = self._song.get_named_scale(scale_name)
            if root is not None or kind is not None:
                named = NamedScale(root=named.get_root() if root is None else root, kind=named.get_kind() if kind is None else kind)
            self._scales_by_octave[key] = named.scale_at(octave)
        return self._scales_by_octave[key]

    def play_pass(self, *, pattern_name, grab, direction, where, rolls, order, registers, start, changes_registers=True, pass_draws=NO_PASS_DRAWS):
        """Return one pass through a pattern as a Pass, with notes, chords and rests, starting at a time in the clip.

        Every step takes the same time, its step size, whatever order the steps play in, which is
        the pattern's direction unless direction overrides it. A step that plays sounds for its
        gate, which can run past later steps but not past the end of the pass. A tied step plays
        nothing and keeps the note that played just before it, in time, sounding to the end of
        the tied step, whatever its gate: ties win over the gate,
        so that the bar the editor draws is the length that plays. A tie after an empty step is silence, and
        ties at the start of the pass are left for the caller to join to the pass before. The
        pattern's grab steps play what grab, a GrabSource, gives for the time they start, if it's
        given, and a grab step with no degree of its own plays only that, or nothing. rolls is the random generator probability uses, and order the StepOrder.
        pass_draws names the draws the pass's first step takes besides its own, those the clip's statements redraw as the pass starts.

        registers is a RegisterRecorder or RegisterReader. Every step sets and adds to the
        registers, even one with no note, unless changes_registers is false, as for a morph's
        target, and then moves its note and velocity by the values of the registers it uses, after
        its own sets and adds. A note with no velocity of its own plays at the value of the register
        the track's velocity is bound to, if any. Last, its conditions and its probability decide
        whether its note sounds, which never undoes its sets and adds.
        """
        if not self._song.has_pattern(pattern_name):
            raise SongFileError(errors.ERR_PATTERN_PLAYER_NO_SUCH_PATTERN.format(where=where, name=pattern_name))
        pattern = self._song.get_pattern(pattern_name)
        step_size = self._song.get_pattern_step_size(pattern)
        length = self.pattern_length(pattern)
        # What each step plays is worked out in pairs of whole numbers, which make no object for a sum (support/length.py).
        # The times the registers, the grabs and the CC values are asked for stay Rationals, and are only made for a step that asks.
        step_length = Length.exact(step_size)
        pass_length = Length.exact(length)
        where = errors.ERR_WHERE_PATTERN.format(name=pattern_name)
        # What each step that plays sounds: when it starts in the pass, and its pieces, a note or chord for each ratchet.
        sounding = []
        controls = []
        # The keyswitch slots of the steps that play, and which of them the last step left for a tie to lengthen, if any.
        keyswitches = []
        switch_tied_to = None
        # Which entry of sounding the last step left sounding for a tie to lengthen, if any, and
        # how many tied steps came before anything else.
        tied_to = None
        leading_ties = 0
        played = self._played(pattern_name=pattern_name, pattern=pattern)
        changes = changes_registers and played.changes_registers
        draws = changes_registers and played.uses_draws
        uses_registers = played.uses_registers or draws
        reads_registers = uses_registers or self._velocity_register is not None
        counting = registers.is_counting()
        drum = pattern.is_drum()
        steps = order.next_steps(key=(PATTERN_STEPS, pattern_name), count=pattern.get_steps(), direction=direction or pattern.get_direction())
        # A morph's target neither changes the registers nor is cut short by them: only the clip's own pattern decides.
        stops = played.stops if changes_registers else None
        restarts = played.restarts if changes_registers else None
        mutes = None if counting else played.mutes
        # Where a step's statement cut the pass short, if one did, and whether it ended the clip or only started the pattern over.
        cut_at = None
        done = False
        step_draws = played.step_draws if changes_registers else None
        # Where a step falls in the clip, a Rational, is only worked out for a pattern whose steps ask: one that draws, reads or
        # changes the registers, grabs or hears a drift.
        asks_moment = step_draws is not None or stops is not None or restarts is not None or mutes is not None or changes or reads_registers or grab is not None or self._drifts is not None
        moment = None
        for slot, step in enumerate(steps):
            if asks_moment:
                moment = start + slot * step_size
            # Every draw the step takes is taken before its statements read the values, the step's one draw from it.
            drawing = step_draws[step] if step_draws is not None else None
            if not slot and pass_draws and changes_registers:
                drawing = _with_pass_draws(drawing=drawing, names=pass_draws)
            if drawing is not None and (drawing.drawn or drawing.resets):
                registers.before_statements(time=moment, draws=drawing.drawn, draw_resets=drawing.resets)
            # A step's statements are read first of all, before the step changes anything, in the order stop, restart, mute.
            if stops is not None and stops[step] is not None and _holds(statement=stops[step], values=registers.before_step(moment)):
                cut_at = slot
                done = True
                break
            # The first step played never starts the pattern over, which would take no time.
            if restarts is not None and slot and restarts[step] is not None and _holds(statement=restarts[step], values=registers.before_step(moment)):
                cut_at = slot
                break
            muted = mutes is not None and mutes[step] is not None and _holds(statement=mutes[step], values=registers.before_step(moment))
            time = Length.times(step_length, slot)
            values = played.values[step]
            # A step with no note can send CC values and add to the registers too.
            if played.sends_controls:
                controls += _controls_sent(values=values, time=slot * step_size)
            if changes or reads_registers:
                current = registers.at_step(time=moment, sets=_register_sets(values) if changes else NO_SETS, adds=_register_adds(values) if changes else NO_ADDS)
            if values[Row.TIE]:
                if tied_to is not None:
                    sounding[tied_to] = _tied_to(sounding=sounding[tied_to], end=Length.add(time, step_length))
                    if switch_tied_to is not None:
                        keyswitches[switch_tied_to] = keyswitches[switch_tied_to].ending((slot + 1) * step_size)
                elif slot == leading_ties:
                    leading_ties += 1
                continue
            grabbed = grab.note_at(moment) if grab and values[Row.GRAB] else None
            # A step with no note of its own can still grab one; with nothing to grab yet, it's silence, like an empty step.
            if values[Row.DEGREE] is None and grabbed is None:
                tied_to = None
                continue
            tied_to = len(sounding)
            note_moved = NOTHING_ADDED
            velocity_added = self._accent if values[Row.ACCENT] else NOTHING_ADDED
            velocity = values[Row.VELOCITY]
            if uses_registers:
                moved, added = _moved_by_values(values=values, current=current, drum=drum, draws=draws)
                note_moved += moved
                velocity_added += added
            if velocity is None and self._velocity_register is not None:
                velocity = current[self._velocity_register]
            effects = drift.NO_EFFECTS
            if self._drifts is not None:
                play, names, scene_start, origins = self._drifts
                effects = play.effects(names=names, time=scene_start + moment, origins=origins)
                velocity_added += effects.velocity
                if not drum:
                    note_moved += effects.degree
            gate = Length.shorter(_gate(values=values, step_length=step_length), Length.subtract(pass_length, time))
            switch_tied_to = None
            if played.sends_keyswitches and values[Row.KEYSWITCH]:
                # A keyswitch lasts as long as its note is written, whatever the note's probability or conditions decide.
                switch_tied_to = len(keyswitches)
                keyswitches.append(SwitchedSlots(slot * step_size, slot * step_size + Length.rational(gate), values[Row.KEYSWITCH]))
            sounding.append((time, self._step(
                values=values, grabbed=grabbed, length=gate, drum=drum, where=where, rolls=rolls, note_moved=note_moved, velocity=velocity,
                velocity_added=velocity_added, heard=not muted, counting=counting, effects=effects,
            )))
        clip = Clip(sounds=_in_sequence(sounding=sounding, length=pass_length, step_length=step_length), scale=self._scale, controls=controls)
        if cut_at is not None:
            return _cut_short(clip=clip, end=cut_at * step_size, tied_from_before=leading_ties * step_size, keyswitches=keyswitches, done=done)
        return Pass(clip=clip, tied_from_before=leading_ties * step_size, length=length, keyswitches=keyswitches)

    def pattern_length(self, pattern):
        """Return how long one pass through a pattern lasts, in whole notes."""
        return self._song.get_pattern_length(pattern)

    def _step(self, *, values, grabbed, length, drum, where, rolls, note_moved, velocity, velocity_added, heard, counting=False, effects=None):
        """Return what one step plays, lasting length, its gate, as more than one sound if it ratchets.

        grabbed is the MIDI number of the note its grab took, or None, which plays in place of its own,
        as the bottom note of the step's chord when the step has one.

        Registers move its note note_moved scale notes and add velocity_added to its velocity, which
        is velocity, the step's own or the bound register's, or the track's default velocity when that's None; an accent is part of what is added. A
        step whose conditions don't hold isn't heard, and every slice is a rest, so a ratchet
        sounds all its slices or none.
        effects, what the clip's drifts do to the step, add to its probability, held from 0 to
        100, and may change the scale and root its degrees play in.
        Each slice's notes are made once, already as long as a slice, at the step's velocity and
        with the glide of the last slice. They are sounds, the tuples of music/sound.py, and
        the length is a pair.
        """
        default = self._song.get_default_drum_octave() if drum else self._song.get_default_octave()
        octave = _value_or(value=values[Row.OCTAVE], default=default)
        velocity = _clamped_velocity(_value_or(value=velocity, default=self._default_velocity) + velocity_added)
        ratchet = values[Row.RATCHET] or defaults.DEFAULT_RATCHET
        offset = values[Row.RATCHET_OFFSET] or NO_HALF_STEPS
        slices = []
        transpose = NO_HALF_STEPS if drum else self._transpose
        slice_length = Length.shared(length, ratchet)
        last = ratchet - 1
        for place in range(ratchet):
            shift = transpose + note_moved + place * offset
            # Only the last slice glides into what follows the step.
            glide = bool(values[Row.GLIDE]) and place == last
            if grabbed is not None:
                sound = self._grabbed_sound(
                    number_grabbed=grabbed, chord=values[Row.CHORD], length=slice_length, velocity=velocity, glide=glide, shift=shift, drum=drum, where=where,
                )
            else:
                sound = self._sound(values=values, drum=drum, length=slice_length, velocity=velocity, glide=glide, octave=octave, shift=shift, where=where, effects=effects)
            if values[Row.TENSION]:
                sound = _with_tensions(chord=sound, tensions=values[Row.TENSION])
            slices.append(Sound.inverted(sound, values[Row.INVERSION]))
        if not heard:
            return [Sound.rest(piece[sound_values.LENGTH]) for piece in slices]
        probability = _value_or(value=values[Row.PROBABILITY], default=defaults.DEFAULT_PROBABILITY)
        if effects is not None and effects.probability:
            probability = max(min(probability + effects.probability, limits.MAX_PROBABILITY), limits.MIN_PROBABILITY)
        if probability >= limits.MAX_PROBABILITY or counting:
            return slices
        return [piece if _rolls_under(rolls=rolls, probability=probability) else Sound.rest(piece[sound_values.LENGTH]) for piece in slices]

    def _grabbed_sound(self, *, number_grabbed, chord, length, velocity, glide, shift, drum, where):
        """Return a grabbed note, moved along this clip's scale, or by half steps for drums, with the step's chord built on it.

        A note moved outside the MIDI range stays where it was grabbed. chord is the symbol on
        the step's Chord row, or None for a step that plays the one note.
        """
        note = Sound.note(length=length, midi=number_grabbed, velocity=velocity, glide=glide, name=note_values.SHARP_NAMES[number_grabbed % midi.HALF_STEPS_PER_OCTAVE])
        try:
            root = along_scale(note=note, steps=shift, scale=None if drum else self._scale)
        except ValueError:
            root = note
        # A drum pattern has no chords.
        if chord is None or drum:
            return root
        return self._chord_on(root=root, symbol=str(chord), where=where)

    def _chord_on(self, *, root, symbol, where):
        """Return the chord a symbol names with a grabbed note as its bottom note.

        A named chord like m7 adds notes exact half steps above the note. A scale chord like 7
        adds notes of this clip's scale above the note, which needs a scale. A note of the chord
        that would fall outside the MIDI range is left out.
        """
        if symbol in file_format.FIXED_CHORDS:
            scale = None
            moves = file_format.FIXED_CHORDS[symbol].value
        else:
            if self._scale is None:
                raise no_scale_error(where=where, scene=self._scene)
            scale = self._scale
            moves = [above for above in file_format.SCALE_CHORDS[symbol] if above]
        notes = [root]
        for move in moves:
            try:
                notes.append(along_scale(note=root, steps=move, scale=scale))
            except ValueError:
                pass
        return Sound.chord(notes) if len(notes) > 1 else root

    def _sound(self, *, values, drum, length, velocity, glide, octave, shift, where, effects=None):
        """Return a step's note or chord, moved by a number of scale degrees or, for drums, half steps.

        Each note has the length, velocity and glide given. A note moved outside the MIDI range
        goes to the nearest octave that fits.
        """
        def attempt(at_octave):
            if not drum:
                return self._degree_sound(values=values, length=length, velocity=velocity, glide=glide, octave=at_octave, shift=shift, where=where, effects=effects)
            name = values[Row.DEGREE] + (values[Row.ACCIDENTAL] or NO_ACCIDENTAL)
            note = Sound.named_note(name=name, octave=at_octave, length=length, velocity=velocity, glide=glide)
            return Sound.half_step(note, shift) if shift else note

        # Moving by a whole octave's worth of notes is the same as moving the octave, so a big
        # move, like four registers can make, starts from an octave in the MIDI range.
        octaves, shift = divmod(shift, self._notes_per_octave(drum))
        octave = max(note_values.MIN_OCTAVE, min(octave + octaves, note_values.MAX_OCTAVE))
        try:
            return attempt(octave)
        except ValueError as error:
            problem = error
        # Nearly every note fits where it is, so the other octaves are only listed for one that doesn't.
        for change in _other_octaves_to_try(shift or octaves):
            try:
                return attempt(octave + change)
            except ValueError:
                pass
        raise SongFileError(errors.ERR_CANT_PLAY.format(where=where, problem=problem)) from problem

    def _notes_per_octave(self, drum):
        """Return how many notes a move needs to go up an octave: the size of the scene's scale, or 12 half steps for drums."""
        if drum or self._scale_name is None:
            return midi.HALF_STEPS_PER_OCTAVE
        if self._scale_size is None:
            self._scale_size = len(self._scene_scale_at(note_values.MIN_OCTAVE).get_type().value)
        return self._scale_size

    def _degree_sound(self, *, values, length, velocity, glide, octave, shift, where, effects=None):
        if self._scale_name is None:
            raise no_scale_error(where=where, scene=self._scene)
        scale = self._scene_scale_at(octave, effects=effects, kind=values[Row.CHORD_SCALE])
        half_steps = file_format.ACCIDENTALS.get(values[Row.ACCIDENTAL], NO_HALF_STEPS)
        degree = values[Row.DEGREE]
        symbol = None if values[Row.CHORD] is None else str(values[Row.CHORD])
        if symbol is not None and symbol not in file_format.FIXED_CHORDS:
            # A chord of scale notes: the step's degree and the scale degrees above it that a symbol like 7 names.
            return Sound.chord([
                scale.sound_at(degree=degree + above, scale_notes=shift, half_steps=half_steps, length=length, velocity=velocity, glide=glide)
                for above in file_format.SCALE_CHORDS[symbol]
            ])
        root = scale.sound_at(degree=degree, scale_notes=shift, half_steps=half_steps, length=length, velocity=velocity, glide=glide)
        return root if symbol is None else Sound.chord_above(root, file_format.FIXED_CHORDS[symbol].value)


def _with_tensions(*, chord, tensions):
    """Return a chord with its tensions added, each its half steps above the chord's first note, the root; a single note has none, and a
    tension the chord already holds or that would leave the MIDI range is left out."""
    if chord[sound_values.KIND] != sound_values.CHORD:
        return chord
    notes = list(chord[sound_values.NOTES])
    root = notes[0]
    held = {note[sound_values.MIDI] for note in notes}
    for tension in tensions:
        if root[sound_values.MIDI] + file_format.TENSIONS[tension] in held:
            continue
        try:
            notes.append(Sound.half_step(root, file_format.TENSIONS[tension]))
        except ValueError:
            pass
    return Sound.chord(notes)


def no_scale_error(*, where, scene):
    """Return the error for a pattern that uses scale degrees in a scene that has no scale, and nor does the song."""
    return SongFileError(errors.ERR_NO_SCALE.format(where=where, scene=scene.get_number()))


def check_pattern_has_a_scale(*, song, scene, pattern_name, clip_scale=None):
    """Raise the error playing a pattern in a scene would, if it has scale degrees and the scene has no scale.

    This is the check the estimate makes without playing, so it has to agree with _degree_sound:
    a drum pattern's notes are letters, not degrees, so it needs no scale.
    """
    pattern = song.get_pattern(pattern_name)
    if (clip_scale or scene.get_scale_name()) is None and not pattern.is_drum() and pattern.get_note_steps():
        raise no_scale_error(where=errors.ERR_WHERE_PATTERN.format(name=pattern_name), scene=scene)


def _tied_to(*, sounding, end):
    """Return what a step sounds, lasting exactly until end, for a tie on the step that ends there.

    Ties win over the gate. Usually the ties reach further than the gate, and the last piece is
    lengthened, so a tie holds the last slice of a ratchet. Where the gate reached past the tie,
    the pieces share the tied span equally instead, the way a ratchet splits its gate, so a
    ratchet keeps its count. A piece that probability turned into a rest stays as it is, because
    there's no note to hold.
    """
    start, pieces = sounding
    total = pieces[0][sound_values.LENGTH] if len(pieces) == 1 else Length.total([piece[sound_values.LENGTH] for piece in pieces])
    extra = Length.subtract(end, Length.add(start, total))
    last = pieces[-1]
    if extra == length_values.ZERO or last[sound_values.KIND] == sound_values.REST:
        return sounding
    if Length.is_positive(extra):
        return (start, [*pieces[:-1], Sound.lasting(last, Length.add(last[sound_values.LENGTH], extra))])
    span = Length.shared(Length.subtract(end, start), len(pieces))
    return (start, [Sound.lasting(piece, span) for piece in pieces])


def _gate(*, values, step_length):
    """Return how long a step's note sounds: its gate, or one step if it has none, made dotted or a triplet by its Dot row."""
    gate = step_length if values[Row.GATE] is None else Length.exact(written_length(value=values[Row.GATE], most=limits.MAX_GATE))
    modifier = values[Row.DOT]
    return gate if modifier is None else Length.multiplied(gate, GATE_MODIFIER_PAIRS[modifier])


def _holds(*, statement, values):
    """Return whether a step's statement holds for the registers' values as the step is reached, which is never while they are not known."""
    return values is not None and is_true(statement=statement, values=values)


def _cut_short(*, clip, end, tied_from_before, keyswitches, done):
    """Return the pass a step's statement cut short at a time in the pass: what it played before then, a note still sounding cut there. done says the clip ended, rather than the pattern starting over."""
    if end <= NO_TIME:
        return Pass(clip=Clip(sounds=[], scale=clip.get_scale()), tied_from_before=NO_TIME, length=NO_TIME, done=done)
    cut = clip.section(start=NO_TIME, end=end)
    controls = [control for control in clip.get_controls() if control.get_time() < end]
    kept = Clip(sounds=cut.get_sounds(), scale=clip.get_scale(), controls=controls)
    switches = [slots.ending(min(slots.end, end)) for slots in keyswitches if slots.start < end]
    return Pass(clip=kept, tied_from_before=min(tied_from_before, end), length=end, keyswitches=switches, done=done)


def _in_sequence(*, sounding, length, step_length):
    """Return the notes of a pass as a clip's sequence of sounds, from what each step that plays sounds.

    A note whose gate reaches exactly to the next note is an ordinary position, as it always
    was. A shorter one is followed by rests, one for each step until the next note. A longer one
    is held, so the next note starts while it still sounds. A longer one that probability
    dropped is silence until the next note, since there is no sound to hold.
    """
    positions = []
    now = length_values.ZERO
    count = len(sounding)
    for place, (start, played) in enumerate(sounding):
        following = sounding[place + 1][START] if place + 1 < count else length
        if Length.less(now, start):
            positions += _rests(start=now, end=start, step_length=step_length)
        gate = played[0][sound_values.LENGTH] if len(played) == 1 else Length.total([piece[sound_values.LENGTH] for piece in played])
        gap = Length.subtract(following, start)
        if Length.less(gap, gate):
            if len(played) == 1 and played[0][sound_values.KIND] == sound_values.REST:
                # Probability dropped the note, so there is nothing to hold over the next note: its steps are silent.
                positions += _rests(start=start, end=following, step_length=step_length)
            else:
                positions.append(_held(played=played, length=gap))
            now = following
        else:
            positions += played
            now = Length.add(start, gate)
    if Length.less(now, length):
        positions += _rests(start=now, end=length, step_length=step_length)
    return positions


def _held(*, played, length):
    """Return what a step sounds held in its place, so that the next position starts after length while it sounds on."""
    if len(played) > 1:
        return Sound.phrase(played, length)
    return Sound.held(played[0], length)


def _rests(*, start, end, step_length):
    """Return the rests from a start to an end, one for each step, with the first ending at the next step."""
    rests = []
    now = start
    # Only the first rest can start between two steps, so the steps after it are counted on from its end.
    step_end = Length.times(step_length, Length.whole_times(start, step_length) + 1)
    while Length.less(now, end):
        piece_end = step_end if Length.less(step_end, end) else end
        rests.append((sound_values.REST, Length.subtract(piece_end, now)))
        now = piece_end
        step_end = Length.add(step_end, step_length)
    return rests


def _register_adds(values):
    """Return what a step adds to each register it adds to, by register name."""
    return {name: values[row] for name, row in file_format.REGISTER_ADD_ROWS.items() if values[row]}


def _moved_by_values(*, values, current, drum, draws):
    """Return how far a step's +Note and +Vel rows move its note and its velocity by the registers' values, and by the draws'
    where the pattern uses draws. A drum pattern has no scale to move a note along, so only its velocity moves."""
    note_moved = NOTHING_ADDED if drum else _used_values(values=values, current=current, rows=file_format.REGISTER_NOTE_ROWS)
    velocity_added = _used_values(values=values, current=current, rows=file_format.REGISTER_VELOCITY_ROWS)
    if draws:
        note_moved += NOTHING_ADDED if drum else _used_values(values=values, current=current, rows=file_format.DRAW_NOTE_ROWS)
        velocity_added += _used_values(values=values, current=current, rows=file_format.DRAW_VELOCITY_ROWS)
    return note_moved, velocity_added


def _with_pass_draws(*, drawing, names):
    """Return a pass's first step's StepDraws with the draws its clip's statements redraw as the pass starts taken too, each once."""
    resets = drawing.resets if drawing is not None else ()
    drawn = drawing.drawn if drawing is not None else ()
    return StepDraws(resets, tuple(name for name in file_format.DRAW_NAMES if name in drawn or name in names))


def _draws_used(values):
    """Return the draws a step's rows use, each once however many of its rows use it, in the order the draws come."""
    return tuple(name for name in file_format.DRAW_NAMES if values[file_format.DRAW_NOTE_ROWS[name]] or values[file_format.DRAW_VELOCITY_ROWS[name]])


def _draws_reset(values):
    """Return the draws a step resets before it draws, in the order the draws come."""
    return tuple(name for name, row in file_format.DRAW_RESET_ROWS.items() if values[row])


def _register_sets(values):
    """Return what a step sets each register to, by register name, for each register it sets."""
    return {name: values[row] for name, row in file_format.REGISTER_SET_ROWS.items() if values[row] is not None}


def _used_values(*, values, current, rows):
    """Return the total of the registers a step uses on some rows, like its +Note rows: each register's current value added (1) or subtracted (-1)."""
    return sum((current[name] * values[row] for name, row in rows.items() if values[row]), NOTHING_ADDED)


def _controls_sent(*, values, time):
    """Return the CC values a step sends at a time, one for each CC lane it has a value on."""
    return [
        Control(time=time, number=lane, value=values[row], slide=bool(values[Row.SLIDE]))
        for lane, row in enumerate(file_format.CC_ROWS) if values[row] is not None
    ]


def _value_or(*, value, default):
    """Return a step's value, or a default if the step leaves it blank."""
    return default if value is None else value


def _clamped_velocity(velocity):
    """Return a velocity moved into the range MIDI allows, if registers pushed it out."""
    return max(min(velocity, midi.MAX_VELOCITY), midi.MIN_VELOCITY)


def _rolls_under(*, rolls, probability):
    """Return whether a step with a probability, from 0 to 100, plays this time."""
    return rolls.random() * limits.MAX_PROBABILITY < probability


def _other_octaves_to_try(shift):
    """Return the octave changes to try for a note that doesn't fit where it is, nearest first, so a moved note can find an octave that fits.

    A note that isn't moved is only tried where it is, so it has no others.
    """
    if not shift:
        return []
    return [change for size in range(1, MAX_OCTAVE_CHANGE + 1) for change in (-size, size)]
