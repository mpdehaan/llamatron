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

"""What a chord is, said once for a pattern's step and a progression's chord (the user's design): a degree of a scale, a sharp
or flat, the scale type it borrows its notes from, a chord symbol, and the tensions added on top.

A chord's parts are worked out in one order. The scale type, when one is set, takes the place of the clip's scale on the same
root, so a chord of the parallel minor is borrowed into a major song. The degree and the sharp or flat give the root in that
scale. The symbol names the chord's notes outright, or leaves them to the scale. The tensions go on top. spelled_chord says
what that comes to, in a scale that is known, as a name, a longer name and the names of its notes, for the editors to show.
"""

from dataclasses import dataclass

from llamatron.composition.file_format import ACCIDENTALS, FIXED_CHORDS, SCALE_CHORDS, TENSIONS, Accidental, ChordSymbol, Tension
from llamatron.composition.named_scale import NamedScale
from llamatron.music.midi import HALF_STEPS_PER_OCTAVE
from llamatron.music.note import FLAT_NAMES, SEMITONES_ABOVE_C, SHARP_NAMES
from llamatron.strings.labels import MSG_CHORD_NAMES
from llamatron.strings.marks import MSG_CHORD_SUFFIXES, MSG_CHORD_TENSIONS_SHOWN, MSG_FLAT_SPELLED, MSG_SHARP_SPELLED, MSG_TENSION_SEPARATOR, MSG_UNNAMED_CHORD_SUFFIX

# The place of each of a chord's notes among the notes of a scale of seven, counted up from the chord's root at 0: the notes a
# quality replaces, and the notes between them, which a tension replaces.
ROOT_PLACE = 0
NINTH_PLACE = 1
THIRD_PLACE = 2
ELEVENTH_PLACE = 3
FIFTH_PLACE = 4
THIRTEENTH_PLACE = 5
SEVENTH_PLACE = 6
# Only a scale of seven notes has those places.
PLACED_SCALE_SIZE = 7
# The half steps above a root that are some kind of third (or the second or fourth of a suspended chord), of fifth, and of sixth or seventh.
THIRDS = range(2, 6)
FIFTHS = range(6, 9)
SEVENTHS = range(9, 12)
# The place each tension takes among a scale's notes.
TENSION_PLACES = {
    Tension.FLAT_NINTH: NINTH_PLACE, Tension.NINTH: NINTH_PLACE, Tension.SHARP_NINTH: NINTH_PLACE,
    Tension.ELEVENTH: ELEVENTH_PLACE, Tension.SHARP_ELEVENTH: ELEVENTH_PLACE,
    Tension.FLAT_THIRTEENTH: THIRTEENTH_PLACE, Tension.THIRTEENTH: THIRTEENTH_PLACE,
}
# The triad a scale builds when its notes can't be read, as a chord of a pentatonic's can't: a major one.
OTHER_TRIAD = (4, 7)
# The letters of the notes, which a chord's notes are spelled along: a third is two letters above its root, whatever its half steps.
LETTERS = 'CDEFGAB'
# How far a spelled note may lie from its letter's plain note: one sharp or one flat, and any further is named plainly.
MOST_SIGNS = 1
ROOT_WITHOUT_A_SCALE = 'C'
SHAPE_WITHOUT_A_SCALE = (0, 2, 4, 5, 7, 9, 11)
# The half steps of each named chord, by which a chord the scale builds is given its symbol.
SYMBOLS_BY_HALF_STEPS = {kind.value: symbol for symbol, kind in FIXED_CHORDS.items()}


@dataclass(slots=True, kw_only=True, frozen=True)
class SpelledChord:
    """A chord in a scale that is known: its root's name, its short name like A7(b9), its long name like A Dominant Seventh, and its notes' names from the root up."""

    root: str
    name: str
    long_name: str
    notes: tuple


def borrowed(*, scale, kind):
    """Return the scale a chord is drawn from: the scale given, or the scale of another type on its root when the chord borrows one."""
    return scale if kind is None or scale is None else NamedScale(root=scale.get_root(), kind=kind)


def letter_steps(half_steps):
    """Return how many letters above its root a chord's note is spelled, by its half steps above the root: a third two, a flat ninth one."""
    within = half_steps % HALF_STEPS_PER_OCTAVE
    if half_steps > HALF_STEPS_PER_OCTAVE:
        return {1: 1, 2: 1, 3: 1, 5: 3, 6: 3, 8: 5, 9: 5}.get(within, _plain_letter_steps(within))
    return _plain_letter_steps(within)


def _plain_letter_steps(within):
    return (0, 1, 1, 2, 2, 3, 4, 4, 4, 5, 6, 6)[within]


def spelled_note(*, root, half_steps):
    """Return the name of the note some half steps above a root's name, on the letter a chord spells it with: Ab's third is C, A's flat ninth is Bb."""
    letter = LETTERS[(LETTERS.index(root[0]) + letter_steps(half_steps)) % len(LETTERS)]
    pitch = (SEMITONES_ABOVE_C[root] + half_steps) % HALF_STEPS_PER_OCTAVE
    signs = (pitch - SEMITONES_ABOVE_C[letter] + HALF_STEPS_PER_OCTAVE // 2) % HALF_STEPS_PER_OCTAVE - HALF_STEPS_PER_OCTAVE // 2
    if abs(signs) > MOST_SIGNS:
        return (FLAT_NAMES if MSG_FLAT_SPELLED in root else SHARP_NAMES)[pitch]
    return letter + (MSG_SHARP_SPELLED * signs if signs > 0 else MSG_FLAT_SPELLED * -signs)


def root_name(*, scale, degree, accidental):
    """Return the name of a chord's root in a scale: the scale's note on its degree, on that degree's letter in a scale of seven, a half step up or down with a sharp or flat."""
    root = ROOT_WITHOUT_A_SCALE if scale is None else scale.get_root()
    shape = SHAPE_WITHOUT_A_SCALE if scale is None else scale.get_half_steps()
    place = (degree - 1) % len(shape)
    half_steps = shape[place] + ACCIDENTALS.get(accidental, 0)
    pitch = (SEMITONES_ABOVE_C[root] + half_steps) % HALF_STEPS_PER_OCTAVE
    if len(shape) != PLACED_SCALE_SIZE:
        return (FLAT_NAMES if accidental == Accidental.FLAT or MSG_FLAT_SPELLED in root else SHARP_NAMES)[pitch]
    letter = LETTERS[(LETTERS.index(root[0]) + place) % len(LETTERS)]
    signs = (pitch - SEMITONES_ABOVE_C[letter] + HALF_STEPS_PER_OCTAVE // 2) % HALF_STEPS_PER_OCTAVE - HALF_STEPS_PER_OCTAVE // 2
    if abs(signs) > MOST_SIGNS:
        return (FLAT_NAMES if accidental == Accidental.FLAT else SHARP_NAMES)[pitch]
    return letter + (MSG_SHARP_SPELLED * signs if signs > 0 else MSG_FLAT_SPELLED * -signs)


def scale_chord_half_steps(*, scale, degree, places):
    """Return the half steps above a degree of the scale notes some places above it, as a chord of the scale stacks them."""
    shape = SHAPE_WITHOUT_A_SCALE if scale is None else scale.get_half_steps()
    start = (degree - 1) % len(shape)
    result = []
    for above in places:
        octaves, place = divmod(start + above, len(shape))
        result.append(octaves * HALF_STEPS_PER_OCTAVE + shape[place] - shape[start])
    return tuple(result)


def chord_half_steps(*, scale, degree, symbol, tensions=None, own_degree=None):
    """Return a chord's notes as half steps above its root, the root's 0 left out, its tensions last.

    A named symbol's are its own. A scale chord's, and those of no symbol at all, which is the scale's triad, are the scale's
    on the chord's degree, or on own_degree where the chord keeps the sound of another degree, as a progression's chord with
    a sharp or flat keeps the sound of degree 1.
    """
    if symbol is not None and str(symbol) in FIXED_CHORDS:
        own = FIXED_CHORDS[str(symbol)].value
    else:
        places = SCALE_CHORDS[ChordSymbol.SCALE_TRIAD if symbol is None else str(symbol)]
        own = scale_chord_half_steps(scale=scale, degree=degree if own_degree is None else own_degree, places=[place for place in places if place])
    return own + tuple(TENSIONS[tension] for tension in tensions or () if TENSIONS[tension] not in own)


def symbol_of(half_steps):
    """Return the symbol of the named chord some half steps above a root make, or None when no named chord has them."""
    return SYMBOLS_BY_HALF_STEPS.get(tuple(half_steps))


def spelled_chord(*, scale, degree, accidental=None, kind=None, symbol=None, tensions=None, own_degree=None):
    """Return what a chord comes to in a scale: its names and its notes' names.

    scale is the NamedScale the chord plays under, or None for the major scale on C, as a song with no scale is shown.
    """
    drawn_from = borrowed(scale=scale, kind=kind)
    root = root_name(scale=drawn_from, degree=degree, accidental=accidental)
    own = chord_half_steps(scale=drawn_from, degree=degree, symbol=symbol, own_degree=own_degree)
    named = str(symbol) if symbol is not None and str(symbol) in FIXED_CHORDS else symbol_of(own)
    added = [tension for tension in TENSIONS if tension in (tensions or ()) and TENSIONS[tension] not in own]
    shown_tensions = MSG_CHORD_TENSIONS_SHOWN.format(tensions=MSG_TENSION_SEPARATOR.join(added)) if added else ''
    suffix = MSG_UNNAMED_CHORD_SUFFIX if named is None else MSG_CHORD_SUFFIXES[named]
    long_name = root if named is None else root + ' ' + MSG_CHORD_NAMES[named].split(',')[0].title()
    notes = (root, *[spelled_note(root=root, half_steps=half_steps) for half_steps in (*own, *[TENSIONS[tension] for tension in added])])
    return SpelledChord(root=root, name=root + suffix + shown_tensions, long_name=(long_name + ' ' + shown_tensions).strip(), notes=notes)


def replaced_places(*, symbol, tensions):
    """Return, for a progression's chord, the half steps above its root that the notes of a figure take at each place of the
    scale above the root: a named symbol sets its third, fifth and seventh, and each tension the note between.

    A place the chord doesn't name is left out, and the figure's note there stays the scale's.
    """
    places = {}
    if symbol is not None:
        for half_steps in FIXED_CHORDS[str(symbol)].value:
            within = half_steps % HALF_STEPS_PER_OCTAVE
            if half_steps > HALF_STEPS_PER_OCTAVE:
                places[{2: NINTH_PLACE, 5: ELEVENTH_PLACE, 9: THIRTEENTH_PLACE}[within]] = within
            elif within in THIRDS:
                places[THIRD_PLACE] = within
            elif within in FIFTHS:
                places[FIFTH_PLACE] = within
            elif within in SEVENTHS:
                places[SEVENTH_PLACE] = within
    for tension in tensions or ():
        places[TENSION_PLACES[tension]] = TENSIONS[tension] % HALF_STEPS_PER_OCTAVE
    return places
