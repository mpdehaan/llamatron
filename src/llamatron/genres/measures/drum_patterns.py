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

"""The drum grooves styles are built on, a library of named patterns, the user's direction: a style uses several, never one
fixed beat. Each groove is a bar or two of every voice it uses, written as text a step at a time (x a hit, o a ghost or soft hit,
. none), on a grid of sixteenths, or of triplets for the swung and compound feels, so that a shuffle is never forced into
sixteenths. The grooves are the standard ones drummers learn for each style, described in strings/genres.py."""

from dataclasses import dataclass

from llamatron.strings.genres import GrooveName

STRONG = 'x'
SOFT = 'o'
STRONG_WEIGHT = 2
SOFT_WEIGHT = 1
NO_WEIGHT = 0
SIXTEENTHS = 4
TRIPLETS = 3
# Every groove is compared on a grid fine enough for both sixteenths and triplets: 12 steps a beat.
COMMON_STEPS_PER_BEAT = 12


class Voice:
    """The voices of a kit a groove is written for, which General MIDI's drum notes are sorted into."""

    KICK = 'kick'
    SNARE = 'snare'
    RIM = 'rim'
    CLAP = 'clap'
    HATS = 'hats'
    OPEN_HAT = 'open hat'
    RIDE = 'ride'
    CRASH = 'crash'
    TOMS = 'toms'
    PERCUSSION = 'percussion'


BACKBEAT_VOICES = (Voice.SNARE, Voice.RIM, Voice.CLAP)


def weights(text):
    """Return a voice's steps written as text, as each step's weight."""
    return tuple(STRONG_WEIGHT if mark == STRONG else SOFT_WEIGHT if mark == SOFT else NO_WEIGHT for mark in text.replace('|', ''))


@dataclass(slots=True, kw_only=True, frozen=True)
class DrumPattern:
    """A named groove: its name (a GrooveName), the beats in its bar, its steps to a beat, and each voice's steps."""

    name: str
    beats: int
    steps_per_beat: int
    voices: dict

    def bars(self):
        return max(1, max((len(steps) for steps in self.voices.values()), default=0) // (self.beats * self.steps_per_beat))

    def on_common_grid(self):
        """Return each voice's weights spread on twelve steps a beat, so that grooves on sixteenths and on triplets compare."""
        spread = COMMON_STEPS_PER_BEAT // self.steps_per_beat
        result = {}
        for voice, steps in self.voices.items():
            grid = [NO_WEIGHT] * (len(steps) * spread)
            for place, weight in enumerate(steps):
                grid[place * spread] = weight
            result[voice] = tuple(grid)
        return result

    def kick_on_every_beat(self):
        steps = self.voices.get(Voice.KICK, ())
        return len(steps) >= self.beats * self.steps_per_beat and all(steps[beat * self.steps_per_beat] for beat in range(self.beats))

    def kick_hits_in_a_bar(self):
        return sum(1 for weight in self.voices.get(Voice.KICK, ()) if weight) / self.bars()

    def has_backbeat(self):
        """Return whether a backbeat voice hits beats 2 and 4 of a bar of four."""
        if self.beats != 4:
            return False
        for voice in BACKBEAT_VOICES:
            steps = self.voices.get(voice, ())
            if len(steps) >= 4 * self.steps_per_beat and steps[self.steps_per_beat] == STRONG_WEIGHT and steps[3 * self.steps_per_beat] == STRONG_WEIGHT:
                return True
        return False


def groove(name, *, beats=4, steps_per_beat=SIXTEENTHS, **voices):
    """Return a groove from each voice's steps written as text; a voice named with an underscore takes its space."""
    return DrumPattern(name=name, beats=beats, steps_per_beat=steps_per_beat,
                       voices={voice.replace('_', ' '): weights(text) for voice, text in voices.items()})


G = GrooveName
E8 = 'x.x.x.x.x.x.x.x.'
E16 = 'xoxoxoxoxoxoxoxo'
Q4 = 'x...x...x...x...'
BB = '....x.......x...'
OFF = '..x...x...x...x.'
SHUFFLE_HATS = 'x.xx.xx.xx.x'

GROOVES = (
    # Rock and its family.
    groove(G.ROCK_BEAT, kick='x.......x.......', snare=BB, hats=E8),
    groove(G.ROCK_AND_OF_THREE, kick='x.......x.x.....', snare=BB, hats=E8),
    groove(G.ROCK_SYNCOPATED, kick='x.....x...x.....', snare=BB, hats=E8),
    groove(G.ROCK_SIXTEENTHS, kick='x.......x.x.....', snare=BB, hats=E16),
    groove(G.ROCK_QUARTER_HATS, kick='x.......x.x.....', snare=BB, hats=Q4),
    groove(G.ROCK_RIDE, kick='x.......x.x.....', snare=BB, ride=E8),
    groove(G.ROCK_FOUR_FLOOR, kick=Q4, snare=BB, hats=E8),
    groove(G.ROCK_HALF_TIME, kick='x.....x...x.....', snare='........x.......', hats=E8),
    groove(G.ROCK_DRIVING_EIGHTHS, kick=E8, snare=BB, hats=E8),
    groove(G.ROCK_TOM_GROOVE, kick='x.......x.......', snare=BB, toms='x..x..x...x.x...'),
    groove(G.MOTORIK, kick='x.....x.x.....x.', snare=BB, hats=E8),
    groove(G.PUNK_DRIVE, kick='x.x...x.x.x...x.', snare=BB, hats=E8),
    groove(G.SKANK_BEAT, kick=Q4, snare=OFF, crash=Q4),
    groove(G.D_BEAT, kick='x.....x.x.....x.', snare='....x.......x...', crash=E8),
    groove(G.ROCK_SHUFFLE, steps_per_beat=TRIPLETS, kick='x.....x.....', snare='...x.....x..', hats=SHUFFLE_HATS),
    groove(G.HALF_TIME_SHUFFLE, steps_per_beat=TRIPLETS, kick='x....x......', snare='.o..o.x.o.oo', hats=SHUFFLE_HATS),
    groove(G.TRIPLET_KICK_GROOVE, steps_per_beat=TRIPLETS, kick='x.xx..x.xx..', snare='...x.....x..', hats='x..x..x..x..'),
    groove(G.TWELVE_EIGHT, steps_per_beat=TRIPLETS, kick='x.....x.....', snare='...x.....x..', hats='xxxxxxxxxxxx'),
    groove(G.BO_DIDDLEY, kick='x.......x.......', toms='x..x..x...x.x...', percussion='x..x..x...x.x...'),
    # Metal.
    groove(G.GALLOP, kick='x.xxx.xxx.xxx.xx', snare=BB, hats=E8),
    groove(G.DOUBLE_KICK, kick='xxxxxxxxxxxxxxxx', snare=BB, crash=Q4),
    groove(G.THRASH_BEAT, kick=E8, snare=OFF, hats=E8),
    groove(G.BLAST_BEAT, kick='xxxxxxxxxxxxxxxx', snare=E8, ride=E8),
    groove(G.DOOM_DIRGE, kick='x...............', snare='........x.......', crash='x.......x.......'),
    groove(G.GROOVE_METAL_CHUG, kick='x..x..x.x..x....', snare=BB, hats=Q4),
    # Country, folk and old-time.
    groove(G.TRAIN_BEAT, kick='x.......x.......', snare='oooxoooxoooxooox'),
    groove(G.TWO_BEAT, kick='x.......x.......', snare=BB, hats=E8),
    groove(G.COUNTRY_TWO_STEP, kick='x.......x.......', rim=BB, hats=E8),
    groove(G.BLUEGRASS_CHOP, snare=BB, percussion=BB),
    groove(G.WALTZ, beats=3, kick='x...........', snare='....x...x...', hats='x...x...x...'),
    groove(G.SIX_EIGHT, beats=2, steps_per_beat=TRIPLETS, kick='x.....', snare='...x..', hats='xxxxxx'),
    groove(G.MARCH, kick='x.......x.......', snare='x.xxx.x.x.xxx.x.'),
    # Blues, jazz and swing.
    groove(G.SHUFFLE, steps_per_beat=TRIPLETS, kick='x.....x.....', snare='...x.....x..', hats=SHUFFLE_HATS),
    groove(G.SLOW_BLUES, steps_per_beat=TRIPLETS, kick='x.....x.....', snare='...x.....x..', hats='xxxxxxxxxxxx'),
    groove(G.SWING_RIDE, steps_per_beat=TRIPLETS, kick='o..o..o..o..', hats='...x.....x..', ride='x..x.xx..x.x'),
    groove(G.BRUSH_BALLAD, steps_per_beat=TRIPLETS, kick='o.....o.....', snare='o..o..o..o..', hats='...x.....x..'),
    groove(G.BEBOP_RIDE, steps_per_beat=TRIPLETS, kick='.....o....o.', snare='..o.....o..o', hats='...x.....x..', ride='x..x.xx..x.x'),
    groove(G.DIXIELAND_TWO, kick='x.......x.......', snare='....x.......x...', percussion=Q4),
    groove(G.SECOND_LINE, kick='x..x....x..x.x..', snare='o.oxo.o.o.oxo.o.'),
    groove(G.JAZZ_WALTZ, beats=3, steps_per_beat=TRIPLETS, kick='o........', hats='...x..x..', ride='x..x.xx..'),
    groove(G.BIG_BAND_SHOUT, steps_per_beat=TRIPLETS, kick='x..x..x..x..', snare='...x.....x..', ride='x..x.xx..x.x', crash='x...........'),
    groove(G.SPY_GROOVE, steps_per_beat=TRIPLETS, kick='x.....x.....', snare='...x.....x..', ride='x..x.xx..x.x'),
    # Soul, funk and R&B.
    groove(G.MOTOWN, kick='x.......x.x.....', snare=Q4, percussion=Q4, hats=E8),
    groove(G.NORTHERN_STOMP, kick=Q4, snare=Q4, percussion=E8),
    groove(G.FUNK_GHOSTS, kick='x..x..x...x..x..', snare='....x..o.o..x..o', hats=E16),
    groove(G.LINEAR_FUNK, kick='x..x..x...x.....', snare='....x.o.....x.o.', hats='.xx....x.xx....x'),
    groove(G.NEW_ORLEANS_FUNK, kick='x..x....x.x..x..', snare='o..ox.o.o..ox.o.', hats=E16),
    groove(G.DISCO, kick=Q4, snare=BB, hats=Q4, open_hat=OFF),
    groove(G.GOSPEL_SHUFFLE, steps_per_beat=TRIPLETS, kick='x.....x.x...', snare='...x..o..x.o', hats=SHUFFLE_HATS),
    groove(G.NEW_JACK_SWING, steps_per_beat=TRIPLETS, kick='x....xx....x', snare='...x.....x..', hats='x.xx.xx.xx.x'),
    groove(G.AFROBEAT, kick='x..x..x...x.....', snare='....o..x.o..x..o', hats=E16, open_hat='..x.......x.....'),
    # Latin and Caribbean.
    groove(G.BOSSA_NOVA, kick='x..xx..xx..xx..x|x..xx..xx..xx..x', rim='x..x..x...x..x..|..x..x..x..x....', hats=E8 + E8),
    groove(G.SAMBA, kick='x..xx..xx..xx..x', hats=E16, rim='x.x..x.x.x..x.x.'),
    groove(G.SON_CLAVE, kick='x..x....x..x....', percussion='x..x..x...x.x...', hats=E8),
    groove(G.RUMBA_CLAVE, kick='x..x....x..x....', percussion='x..x...x..x.x...', toms='......x.......x.'),
    groove(G.SONGO, kick='...x.......x....', rim='..x.x..x..x.x..x', hats=E8, toms='.......x......x.'),
    groove(G.MOZAMBIQUE, kick='x...x...x...x...', percussion='x.x.x.x.xx.xx.x.', toms='...x..x....x..x.'),
    groove(G.TUMBAO_ROCK, kick='x..x...x..x.....', snare='......x.....x...', hats=E8, percussion='x..x..x...x.x...'),
    groove(G.ONE_DROP, steps_per_beat=TRIPLETS, kick='......x.....', rim='......x.....', hats='x..x..x..x..'),
    groove(G.ROCKERS, kick=Q4, rim='........x.......', hats=E8),
    groove(G.STEPPERS, kick=Q4, snare='........x.......', hats=OFF),
    # Electronic.
    groove(G.HOUSE, kick=Q4, clap=BB, hats=Q4, open_hat=OFF),
    groove(G.TECHNO, kick=Q4, clap=BB, hats=E16),
    groove(G.MINIMAL_TECHNO, kick=Q4, rim='......x.......x.', hats=OFF),
    groove(G.TRANCE, kick=Q4, clap=BB, hats=E16, open_hat=OFF),
    groove(G.BIG_ROOM, kick=Q4, clap=BB, open_hat=OFF),
    groove(G.EURODANCE, kick=Q4, snare=BB, hats=E16, open_hat=OFF),
    groove(G.ELECTRO, kick='x.....x...x.....', clap=BB, hats=E16),
    groove(G.BREAKBEAT, kick='x.x.......xx....', snare='....x..o.o..x..o', hats=E8),
    groove(G.BIG_BEAT, kick='x.........x.x...', snare='....x.......x...', hats=E8, open_hat='......x.........'),
    groove(G.DRUM_AND_BASS, kick='x.........x.....', snare=BB, hats=E16),
    groove(G.JUNGLE, kick='x.x.......xx....|x.........x.....', snare='....x..o.o..x..o|....x..x.o..x...', hats=E8 + E8),
    groove(G.UK_GARAGE, steps_per_beat=TRIPLETS, kick='x.....x..x..', snare='...x.....x..', hats='.xx.xx.xx.xx'),
    groove(G.IDM_BROKEN, kick='x..x.....x.x..x.', snare='....x..o...x.o..', hats='xoxx.xoxxo.xxoxo'),
    groove(G.GLITCH_STUTTER, kick='x.x.....xxx.....', snare='....xxxx....x...', hats='x.x.xxxxx.x.xxxx'),
    groove(G.SYNTH_POP, kick='x.......x.x.....', snare=BB, hats=E16),
    groove(G.GATED_POP, kick='x.......x.x.....', snare=BB, hats=E8, toms='..............xx'),
    groove(G.DANCE_POP, kick=Q4, snare=BB, hats=E16, open_hat=OFF),
    groove(G.SYNTHWAVE, kick='x.......x.......', snare=BB, hats=E8),
    groove(G.DARK_PULSE, kick=Q4, hats=E16),
    groove(G.CHIPTUNE, kick='x.......x.x.....', snare=BB, hats=E8),
    # Hip hop.
    groove(G.BOOM_BAP, steps_per_beat=TRIPLETS, kick='x....x.x....', snare='...x.....x..', hats='x.xx.xx.xx.x'),
    groove(G.TRAP, kick='x......x..x.....', snare='........x.......', hats='xxxxxxxxxxxxxxxx'),
    groove(G.LO_FI, steps_per_beat=TRIPLETS, kick='x....x..x...', snare='...x.....x.o', hats='x.xx.xx.xx.x'),
    # Orchestral and none.
    groove(G.TIMPANI_ROLL, toms='xxxxxxxxxxxxxxxx'),
    groove(G.MARCHING_SNARE, snare='x.xxx.xxx.xxx.x.', kick='x.......x.......'),
    groove(G.NO_DRUMS),
)

