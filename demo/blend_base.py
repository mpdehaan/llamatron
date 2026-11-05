# noose6: a Python language and framework for producing MIDI clips.
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

"""The shared recipe for a song that slowly turns one tune into another.

A demo gives BlendPiece two tunes of the same length, with their chords, and a list of Parts:

    First tune      The opening measures, with its real chords.
    Parts           Sections blend further and further into the second tune, each in a chosen
                    BlendMode, with a little
                    AutoRatchet, MixUp2 and Backfill. Whichever tune is ahead sets the scale,
                    rhythm and chords, and Smoother repairs the melody to fit. Chords can
                    arpeggiate, and a bass line in counterpoint moves through its styles.
    Second tune     All of it, with its real chords arpeggiated and the bass in a canon.

Each part has its own register, so that they never overlap, and kick and snare tracks play
through the whole song, for drum sounds to be assigned to them.
"""

from collections import namedtuple
from fractions import Fraction

from src.analyzers.chord_change_finder import ChordChangeFinder
from src.analyzers.phrase_finder import PhraseFinder
from src.analyzers.scale_detector import ScaleDetector
from src.generators.arp import Arp, ChordOrder
from src.legacy.generators.backfill import Backfill
from src.generators.blend import Blend, BlendMode
from src.legacy.generators.counterpoint import Counterpoint, CounterpointStyle
from src.legacy.generators.force_scale import ForceScale
from src.legacy.generators.harmonize import Harmonize
from src.legacy.generators.mix_up2 import MixUp2
from src.legacy.generators.register import Register
from src.legacy.generators.smoother import Smoother
from src.generators.auto_ratchet import AutoRatchet
from src.generators.take_rhythm import TakeRhythm
from src.note import Note, Rest
from src.score import Score
from src.song import Clip

DEFAULT_SEED = 7

# Every part has its own space. The melody stays above these, and A1 is a piano's lowest key.
BASS_LOW, BASS_HIGH = Note('A', 1), Note('A', 2)
CHORDS_LOW, CHORDS_HIGH = Note('A#', 2), Note('B', 3)

# Drum notes are very short, and only their timing matters. A measure has four beats.
DRUM_LENGTH = Fraction(1, 16)
BEAT = Fraction(1, 4)
KICK_NOTE = Note('C', 3, DRUM_LENGTH)
SNARE_NOTE = Note('D', 3, DRUM_LENGTH)
KICK_BEATS = [1]
SNARE_BEATS = [2, 3, 4]

# Each part blends measures first to last (counting from 1) by amount, as a percentage, in
# the given mode. It arpeggiates its chords with notes arp_step long, or not at all if that's
# None, and adds a bass line in counterpoint of the given style.
Part = namedtuple('Part', ['first', 'last', 'amount', 'blend_mode', 'arp_step', 'bass_style'])


def decorate(melody, leader, scale, seed=DEFAULT_SEED):
    """Add small touches, each with a fixed result so that they don't flicker between steps.

    MixUp2 swaps notes of different lengths, so the rhythm is put back straight after it.
    """
    melody = TakeRhythm(leader).generate(MixUp2([0.05], seed=seed).generate(melody))
    melody = AutoRatchet([1, 1, 1, 1, 1, 1, 1, 2]).generate(melody)
    return Backfill([0.25], scale=scale, seed=seed).generate(melody)


def slice_points(melody, chords):
    """Cut at every measure, and also where a phrase ends or the chords change.

    Cutting at every measure gives enough slices for small steps to change the music.
    """
    measures = range(1, int(melody.total_length()) + 1)
    return sorted({*measures, *PhraseFinder().analyze(melody), *ChordChangeFinder().analyze(chords)})


def drums(note, beats, measures):
    """Return a clip that plays a short note on the given beats of every measure."""
    positions = []
    for beat in range(4):
        positions += [note, Rest(BEAT - DRUM_LENGTH)] if beat + 1 in beats else [Rest(BEAT)]
    return Clip(notes=positions).repeated(measures)


class BlendPiece:
    """Builds a Song that turns one tune into another, as described at the top of this file."""

    def __init__(self, first_name, first, first_chords, second_name, second, second_chords,
                 progression, opening_last_measure, arp_step, flowing_step,
                 seed=DEFAULT_SEED, use_smoother=True):
        for melody, chords in [(first, first_chords), (second, second_chords), (first, second)]:
            if melody.total_length() != chords.total_length():
                raise ValueError(
                    f'the tunes and charts must all last the same time, but found '
                    f'{melody.total_length()} and {chords.total_length()}, so try Stretch first'
                )
        self.first_name, self.first, self.first_chords = first_name, first, first_chords
        self.second_name, self.second, self.second_chords = second_name, second, second_chords
        self.progression = progression
        self.opening_last_measure = opening_last_measure
        self.arp_step = arp_step
        self.flowing_step = flowing_step
        self.seed = seed
        self.use_smoother = use_smoother
        self.first_scale = ScaleDetector().analyze(first)
        self.second_scale = ScaleDetector().analyze(second)

    def build_song(self):
        score = Score(tempo=120)
        opening = self.first.measures(1, self.opening_last_measure)
        chart = self.first_chords.measures(1, self.opening_last_measure)
        chords = Harmonize([chart], scale=self.first_scale).generate(opening)
        self._play(score, self.first_name, opening, self._accompaniment(chords, None))

        for part in self.progression:
            self._play_part(score, part)

        chords = Harmonize([self.second_chords], scale=self.second_scale).generate(self.second)
        bass = self._bass_line(self.second, chords, CounterpointStyle.CANON, self.second_scale)
        self._play(score, self.second_name, self.second, self._accompaniment(chords, self.arp_step), bass)
        return score.song

    def _play_part(self, score, part):
        first = self.first.measures(part.first, part.last)
        first_chords = self.first_chords.measures(part.first, part.last)
        second = self.second.measures(part.first, part.last)
        second_chords = self.second_chords.measures(part.first, part.last)
        points = slice_points(first, first_chords)

        if part.amount <= 50:
            leader, chart, scale = first, first_chords, self.first_scale
        else:
            leader, chart, scale = second, second_chords, self.second_scale

        melody = Blend(second, part.amount, mode=part.blend_mode, points=points, seed=self.seed).generate(first)
        melody = TakeRhythm(leader).generate(melody)
        melody = ForceScale(scale).generate(decorate(melody, leader, scale, self.seed))
        chords = Harmonize([ForceScale(scale).generate(chart)], scale=scale).generate(melody)
        if self.use_smoother:
            melody = Smoother(chords).generate(melody)
        bass = self._bass_line(melody, chords, part.bass_style, scale)
        self._play(score, f'Morph at {part.amount}', melody, self._accompaniment(chords, part.arp_step), bass)

    def _bass_line(self, melody, chords, style, scale):
        return Counterpoint(
            chords, style=style, low=BASS_LOW, high=BASS_HIGH, step=self.flowing_step,
            scale=scale, seed=self.seed,
        ).generate(melody)

    def _accompaniment(self, chords, step):
        """Move the chords into their own space, and arpeggiate them if there's a step."""
        played = Register(CHORDS_LOW, CHORDS_HIGH).generate(chords)
        return played if step is None else Arp(step, ChordOrder.UP_DOWN).generate(played)

    def _play(self, score, name, melody, chords, bass=None):
        """Add a scene, with the drums playing for as long as the melody does."""
        measures = int(melody.total_length())
        score.play(
            name, melody, chords, bass,
            kick=drums(KICK_NOTE, KICK_BEATS, measures),
            snare=drums(SNARE_NOTE, SNARE_BEATS, measures),
        )
