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

"""The traits a style of music is made of, each a value that can be compared field by field (genres/measures/comparing.py), and that a
song measured from its render (genres/hearing/) is expressed in too, so that a song and a style, or two songs, or two styles,
compare the same way.

The melodic traits follow the research on expectation, David Huron's Sweet Anticipation above all: melodies move mostly by step,
a leap is usually followed by a step back the other way, a line drifts back towards the middle of its range and phrases arch and
fall towards their end; listeners learn those odds from the music they know, so each style holds its own. Nothing assumes a song
keeps one key, one time signature or one feel: Meter, Modulation and Groove say how a style changes them.
"""

from dataclasses import dataclass

from llamatron.genres.measures.comparing import Compare, Field, Unit


class Trait:
    """The traits a style can set, by name."""

    TEMPO = 'tempo'
    METER = 'meter'
    HARMONY = 'harmony'
    MODULATION = 'modulation'
    DRUMS = 'drums'
    GROOVE = 'groove'
    BASS = 'bass'
    MELODY = 'melody'
    VOCAL = 'vocal'
    EXPECTATION = 'expectation'
    PHRASING = 'phrasing'
    HOOK = 'hook'
    VOICE_LEADING = 'voice_leading'
    TEXTURE = 'texture'
    SOUNDS = 'sounds'
    ENERGY = 'energy'
    FORM = 'form'
    SOLOS = 'solos'


# The traits, in the order they are compared and shown.
TRAITS = (Trait.TEMPO, Trait.METER, Trait.HARMONY, Trait.MODULATION, Trait.DRUMS, Trait.GROOVE, Trait.BASS, Trait.MELODY,
          Trait.EXPECTATION, Trait.PHRASING, Trait.HOOK, Trait.VOICE_LEADING, Trait.VOCAL, Trait.TEXTURE, Trait.SOUNDS, Trait.ENERGY, Trait.FORM,
          Trait.SOLOS)


class Role:
    """The parts a style gives its sounds."""

    LEAD = 'lead'
    HARMONY = 'harmony'
    BASS = 'bass'
    PAD = 'pad'
    RHYTHM = 'rhythm'
    COUNTER = 'counter'
    DRUMS = 'drums'


class Section:
    """The sections of a song's form, which the generator writes; the analyzer doesn't guess them yet."""

    INTRO = 'intro'
    VERSE = 'verse'
    PRE_CHORUS = 'pre-chorus'
    CHORUS = 'chorus'
    BRIDGE = 'bridge'
    SOLO = 'solo'
    BREAKDOWN = 'breakdown'
    BUILD = 'build'
    DROP = 'drop'
    HEAD = 'head'
    STRAIN = 'strain'
    TRIO = 'trio'
    OUTRO = 'outro'


class Feel:
    """How a groove sits on the meter."""

    STRAIGHT = 'straight'
    SHUFFLE = 'shuffle'
    HALF_TIME = 'half-time'
    DOUBLE_TIME = 'double-time'
    LOOSE = 'loose'


class BassMotion:
    """How a style's bass moves."""

    ROOTS = 'roots'
    WALKING = 'walking'
    OCTAVES = 'octaves'
    SYNCOPATED = 'syncopated'
    BOOGIE = 'boogie'
    SUSTAINED = 'sustained'
    OOM_PAH = 'oom-pah'
    PEDAL = 'pedal'
    COUNTERPOINT = 'counterpoint'
    RIFF = 'riff'
    NONE = 'none'


class FillKind:
    """The kinds of drum fill."""

    TOM_DESCENT = 'tom descent'
    SNARE_RUN = 'snare run'
    TRIPLET = 'triplet fill'
    LINEAR = 'linear fill'
    CRASH_PUNCTUATION = 'crash punctuation'
    SPARSE = 'sparse pickup'


@dataclass(slots=True, kw_only=True, frozen=True)
class Tempo:
    """The beats a minute a style usually lies between; a song's is the one tempo it mostly plays at, low and high the same."""

    low: int
    high: int

    COMPARED = {'low': Field(way=Compare.RANGE, unit=Unit.BEATS_A_MINUTE, scale=40, weight=2)}

    def holds(self, tempo):
        return self.low <= tempo <= self.high

    def middle(self):
        return (self.low + self.high) // 2


@dataclass(slots=True, kw_only=True, frozen=True)
class Meter:
    """A style's usual time signature, the others it changes to, and how often it changes, from 0 never to 1 every phrase."""

    usual: str
    others: tuple = ()
    changes: float = 0.0

    COMPARED = {'usual': Field(way=Compare.METER, unit=Unit.NAME, weight=2), 'others': Field(way=Compare.SET, unit=Unit.NAMES), 'changes': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.5, spread=0.1)}


@dataclass(slots=True, kw_only=True, frozen=True)
class Harmony:
    """The harmony a style favours: its progressions as Roman numerals of the key, its usual chord qualities, its modes, the
    chords it borrows from outside the key (such as bVII and iv), and how long a chord usually lasts, in beats."""

    progressions: tuple
    qualities: tuple
    modes: tuple
    beats_per_chord: float
    borrowed: tuple = ()
    chromatic: float = None
    rich: float = None
    planing: float = None
    whole_tone: float = None

    COMPARED = {
        'progressions': Field(way=Compare.SET, unit=Unit.NAMES, weight=0.5), 'qualities': Field(way=Compare.SET, unit=Unit.NAMES, weight=1.5), 'modes': Field(way=Compare.SET, unit=Unit.NAMES),
        'beats_per_chord': Field(way=Compare.NUMBER, unit=Unit.BEATS, scale=8, spread=2), 'borrowed': Field(way=Compare.SET, unit=Unit.NAMES, weight=0.5),
        'chromatic': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.2, spread=0.03, weight=1.5),
        'rich': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.25, spread=0.04, weight=1.5), 'planing': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.12, spread=0.02),
        'whole_tone': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.12, spread=0.02),
    }


@dataclass(slots=True, kw_only=True, frozen=True)
class Modulation:
    """How a style changes key: how often, from 0 never to 1 in every song; the moves it makes, each the half steps up from the
    old key; where they come (the sections); and how they're reached."""

    often: float
    moves: tuple = ()
    where: tuple = ()
    reached: tuple = ()
    travel: float = None

    COMPARED = {'travel': Field(way=Compare.NUMBER, unit=Unit.COUNT, scale=3, spread=0.4, weight=1.5), 'often': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.6, spread=0.2, weight=2), 'moves': Field(way=Compare.SET, unit=Unit.NAMES), 'where': Field(way=Compare.SET, unit=Unit.NAMES, weight=0.5),
                'reached': Field(way=Compare.SET, unit=Unit.NAMES, weight=0.5)}


@dataclass(slots=True, kw_only=True, frozen=True)
class Drums:
    """A style's drums: the grooves it plays (genres/measures/drum_patterns.py), several and never one fixed beat, the user's direction,
    the most typical first; how often it plays a fill, from 0 never to 1 every bar, and the kinds of fill; and the voice that
    keeps time (the hats, the ride, a crash wash or the toms). A measured song's grooves are the bars it plays most."""

    grooves: tuple
    fills: float = 0.2
    fill_kinds: tuple = ()
    timekeeper: str = None

    COMPARED = {'grooves': Field(way=Compare.GROOVES, unit=Unit.GROOVES, weight=3), 'fills': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.5, spread=0.15, weight=0.5),
                'fill_kinds': Field(way=Compare.SET, unit=Unit.NAMES, weight=0.5), 'timekeeper': Field(way=Compare.TEXT, unit=Unit.NAME, weight=0.5)}

    def main(self):
        return self.grooves[0] if self.grooves else None


@dataclass(slots=True, kw_only=True, frozen=True)
class Groove:
    """How a style sits against the beat, beyond the meter: its swing, the long eighth's share of a beat from 0.5 straight to
    about 0.67 a triplet swing; how far ahead of the beat (above 0) or behind it (below 0) its parts play, in hundredths of a
    beat; the share of its drum hits that are ghost notes; its feel; and how often the feel changes, from 0 to 1."""

    swing: float
    push: float = 0.0
    ghosts: float = 0.0
    feel: str = Feel.STRAIGHT
    feel_changes: float = 0.0

    COMPARED = {
        'swing': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.17, spread=0.04, weight=2), 'push': Field(way=Compare.NUMBER, unit=Unit.HUNDREDTHS_OF_A_BEAT, scale=6, spread=2), 'ghosts': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.4, spread=0.15),
        'feel': Field(way=Compare.TEXT, unit=Unit.NAME), 'feel_changes': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.5, weight=0.5),
    }


@dataclass(slots=True, kw_only=True, frozen=True)
class Bass:
    """How a style's bass moves, and how many notes it usually plays in a bar; and the other ways its bass moves, each as much
    the style's as the first, with no claim of how often."""

    motion: str
    notes_per_bar: float
    other_motions: tuple = ()
    reach: float = None
    bar_span: float = None

    COMPARED = {'bar_span': Field(way=Compare.NUMBER, unit=Unit.HALF_STEPS, scale=12, spread=2, weight=1.5), 'reach': Field(way=Compare.NUMBER, unit=Unit.HALF_STEPS, scale=24, spread=4, weight=1.5), 'motion': Field(way=Compare.TEXT, unit=Unit.NAME, weight=2, also='other_motions'), 'notes_per_bar': Field(way=Compare.NUMBER, unit=Unit.PER_BAR, scale=8, spread=2)}


@dataclass(slots=True, kw_only=True, frozen=True)
class Melody:
    """How a style's melodies move: the share of moves by step (two half steps or fewer); the share of leaps that turn back
    (Huron's post-skip reversal); the usual range in half steps; the usual phrase in bars; the share of phrases that arch; where
    in a phrase its highest note usually falls, from 0 its start to 1 its end; and how much it repeats its own figures, from 0
    to 1, a hook-driven style high; and how many notes it plays a beat, its density, a spectrum from a slow air to a run of
    sixteenths, since speed is more than tempo."""

    steps: float
    reversals: float
    range: int
    phrase_bars: float
    arches: float
    peak: float = 0.5
    repetition: float = 0.5
    density: float = 2.0

    COMPARED = {
        'steps': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.4, spread=0.1, weight=1.5), 'reversals': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.5, spread=0.1), 'range': Field(way=Compare.NUMBER, unit=Unit.HALF_STEPS, scale=18, spread=4),
        'phrase_bars': Field(way=Compare.NUMBER, unit=Unit.BARS, scale=6, spread=1), 'arches': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.6, spread=0.15), 'peak': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.6, spread=0.15, weight=0.5),
        'repetition': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.6, spread=0.15), 'density': Field(way=Compare.NUMBER, unit=Unit.PER_BEAT, scale=3, spread=0.8),
    }


@dataclass(slots=True, kw_only=True, frozen=True)
class Expectation:
    """How a style plays the listener's prediction game, after Huron's Sweet Anticipation and the information-theoretic models
    that measure it (Pearce's IDyOM): the brain enjoys predicting what comes next, rewards itself when it's right, and is held by
    a mix of the expected and the violated; a style neither all predictable nor all surprising, but in its own balance.

    surprise is how unexpected the melody's notes are on average, from 0 wholly predictable to 1 wholly random, judged by the
    style's odds of motion and by what the song has already played; contrast is how much the surprise rises and falls, quiet
    stretches setting up a jolt; familiarity is the share of the song's material that returns, the veridical and dynamic
    expectations a song builds in itself; uncertainty is how unsure the listener is, before each note, of what comes next
    (IDyOM's entropy). Listeners like a surprise best where they were sure, and a predictable note best where they were unsure
    (Cheung and others, 2019; Gold and others, 2019), so the two are measured apart."""

    surprise: float
    contrast: float
    familiarity: float
    uncertainty: float = 0.5

    COMPARED = {'surprise': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.4, spread=0.1, weight=1.5), 'contrast': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.4, spread=0.1),
                'uncertainty': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.4, spread=0.1),
                'familiarity': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.5, spread=0.12, weight=1.5)}


@dataclass(slots=True, kw_only=True, frozen=True)
class Phrasing:
    """How a lead line is phrased, beyond its notes, which is much of why one soloist holds attention and another, as skilled,
    bores: space is the share of the line's time left as rests between phrases; burstiness how much its density varies, flurries
    against held notes; rhythmic variety how many different note lengths and offbeat placements it uses, from 0 to 1; dynamics
    how widely its velocity ranges, from 0 to 1; looseness how far its notes stray from the grid, in hundredths of a beat; and
    arc the share of phrases that build tension (rising, quickening) and release it. A line with little contrast in surprise,
    steady density, little space and no arcs reads as boring however hard it is to play."""

    space: float
    burstiness: float
    rhythmic_variety: float
    dynamics: float
    looseness: float
    arc: float

    COMPARED = {
        'space': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.4, spread=0.1), 'burstiness': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.8, spread=0.2),
        'rhythmic_variety': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.5, spread=0.12), 'dynamics': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.4, spread=0.1),
        'looseness': Field(way=Compare.NUMBER, unit=Unit.HUNDREDTHS_OF_A_BEAT, scale=6, spread=2, weight=0.5), 'arc': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.5, spread=0.15),
    }


@dataclass(slots=True, kw_only=True, frozen=True)
class Hook:
    """A style's hooks, which matter with or without a singer, since even music without words should be remembered and hummed:
    strength is the share of the song a short figure of a bar or two covers, on whatever part plays it, a riff or a melody;
    hummable is how well that figure fits a hum, from 0 to 1 (within an octave, mostly by step, a handful of notes, a rhythm of
    its own); and placement is the share of its returns that land on the song's high points."""

    strength: float
    hummable: float
    placement: float

    COMPARED = {'strength': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.5, spread=0.12, weight=1.5), 'hummable': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.5, spread=0.15),
                'placement': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.5, spread=0.15, weight=0.5)}


@dataclass(slots=True, kw_only=True, frozen=True)
class VoiceLeading:
    """How a style's voices move against one another, measured between every pair of lines where both move: the share of
    contrary motion, one rising as the other falls; the share of oblique motion, one holding as the other moves; parallel
    perfect intervals (fifths and octaves moving in step) per hundred motions, which the chorale forbids and rock's power chords
    are made of; and how independent the voices' rhythms are, from 0 always together to 1 never. Counterpoint's rules are one
    region of this trait, never every style's: each style holds its own values, the user's direction."""

    contrary: float
    oblique: float
    parallels: float
    independence: float

    COMPARED = {'contrary': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.4, spread=0.08), 'oblique': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.4, spread=0.08),
                'parallels': Field(way=Compare.NUMBER, unit=Unit.PER_HUNDRED, scale=30, spread=4, weight=1.5), 'independence': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.5, spread=0.1)}


@dataclass(slots=True, kw_only=True, frozen=True)
class Vocal:
    """The line a person would sing, apart from the backing, as a spectrum and never a yes or no: how singable a style's lead
    is, from 0 an instrument's line no voice could follow to 1 a song's tune; its range in half steps; the share of its notes
    that each carry one syllable, short and often repeated as words are recited; how many bars it sings before a breath; and
    the General MIDI programs that can carry it, the most voice-like first."""

    singable: float
    range: int
    syllabic: float
    breath_bars: float
    carriers: tuple = ()

    COMPARED = {
        'singable': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.5, spread=0.15, weight=3), 'range': Field(way=Compare.NUMBER, unit=Unit.HALF_STEPS, scale=18, spread=4),
        'syllabic': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.6, spread=0.15), 'breath_bars': Field(way=Compare.NUMBER, unit=Unit.BARS, scale=4, spread=1),
        'carriers': Field(way=Compare.SET, unit=Unit.SOUNDS, weight=0.5),
    }


@dataclass(slots=True, kw_only=True, frozen=True)
class Texture:
    """How many parts a style usually plays at once; how much two of them take turns, from 0 never to 1 throughout, as a voice
    and an answering instrument do in call and response; and how many notes every part together plays a beat, a spectrum from
    sparse to dense that tempo alone doesn't tell."""

    parts: float
    call_and_response: float
    density: float = 6.0
    span: float = None
    chordal: float = None

    COMPARED = {'chordal': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.4, spread=0.06), 'span': Field(way=Compare.NUMBER, unit=Unit.HALF_STEPS, scale=24, spread=4, weight=1.5), 'parts': Field(way=Compare.NUMBER, unit=Unit.COUNT, scale=6, spread=1.5), 'call_and_response': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.6, spread=0.15),
                'density': Field(way=Compare.NUMBER, unit=Unit.PER_BEAT, scale=8, spread=2.5)}


@dataclass(slots=True, kw_only=True, frozen=True)
class Sounds:
    """Which General MIDI programs, numbered from 1, a style gives each role, the most typical first."""

    roles: dict

    COMPARED = {'roles': Field(way=Compare.ROLES, unit=Unit.SOUNDS)}

    def for_role(self, role):
        return self.roles.get(role, ())


@dataclass(slots=True, kw_only=True, frozen=True)
class Energy:
    """How a style's energy rises and falls across a song: levels from 0 to 10 in order through it, and how far the quietest
    and loudest stand apart, from 0 to 1; and the other shapes its songs take, each as much the style's as the first."""

    arc: tuple
    contrast: float = 0.5
    other_arcs: tuple = ()

    COMPARED = {'arc': Field(way=Compare.CURVE, unit=Unit.LEVELS, weight=2, also='other_arcs'), 'contrast': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.6, spread=0.15)}


@dataclass(slots=True, kw_only=True, frozen=True)
class Form:
    """How a song in the style is laid out, for the generator: its sections in order, each with its usual length in bars. The
    analyzer doesn't guess sections yet, so a measured song leaves form unknown and it isn't compared."""

    sections: tuple

    COMPARED = {}

    def names(self):
        return [name for name, _ in self.sections]

    def bars(self):
        return sum(bars for _, bars in self.sections)


@dataclass(slots=True, kw_only=True, frozen=True)
class Solos:
    """How a style uses solos, the user's direction that the library know when solos are normal, when they come, how they sit
    in the song, who plays them and how many, so that one can be asked for or left out: presence is the share of songs with at
    least one, from 0 (a style without solos) to 1; count how many a song with solos usually has; bars how long one usually is;
    players who solos, most usual first; spots where in the song they come; bases what they're played over, which says how they
    relate to the song, from its own changes to a vamp or changes of their own that have nothing to do with it; improvised how
    far they're made up on the spot rather than composed, from 0 to 1; and trading how often soloists take short turns in
    answer to one another. The analyzer doesn't find solos yet, so a measured song leaves it unknown."""

    presence: float
    count: float
    bars: float
    players: tuple
    spots: tuple
    bases: tuple
    improvised: float
    trading: float = 0.0

    COMPARED = {'presence': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.6, spread=0.15, weight=1.5), 'count': Field(way=Compare.NUMBER, unit=Unit.COUNT, scale=3, spread=0.75),
                'bars': Field(way=Compare.NUMBER, unit=Unit.BARS, scale=32, spread=8), 'players': Field(way=Compare.SET, unit=Unit.NAMES), 'spots': Field(way=Compare.SET, unit=Unit.NAMES, weight=0.5),
                'bases': Field(way=Compare.SET, unit=Unit.NAMES), 'improvised': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.6, spread=0.15), 'trading': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.6, spread=0.15, weight=0.5)}


@dataclass(slots=True, kw_only=True, frozen=True)
class Spacing:
    """How a song's parts are spaced: the half steps from the bass's middle to the lead's; the share of pairs of parts whose
    usual ranges overlap; the share of beats with close intervals sounding below the low register; the share of the lead's
    notes with accompaniment sounding above them; and the share of beats with a hole, two sounding notes next to each other
    more than two octaves apart, the parts too far apart for the middle to be filled. Measured of a song and set by no style
    yet, so it is no trait: its fields are measures all the same (measures/registry.py)."""

    bass_to_lead: float
    crowding: float
    mud: float
    masking: float
    hollow: float

    COMPARED = {'bass_to_lead': Field(way=Compare.NUMBER, unit=Unit.HALF_STEPS, scale=24, spread=6), 'crowding': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.5, spread=0.15),
                'mud': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.3, spread=0.05), 'masking': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.5, spread=0.1),
                'hollow': Field(way=Compare.NUMBER, unit=Unit.SHARE, scale=0.5, spread=0.1)}


# The class that holds each trait's fields and says how each compares.
TRAIT_KINDS = {
    Trait.TEMPO: Tempo, Trait.METER: Meter, Trait.HARMONY: Harmony, Trait.MODULATION: Modulation, Trait.DRUMS: Drums, Trait.GROOVE: Groove,
    Trait.BASS: Bass, Trait.MELODY: Melody, Trait.EXPECTATION: Expectation, Trait.PHRASING: Phrasing, Trait.HOOK: Hook,
    Trait.VOICE_LEADING: VoiceLeading, Trait.VOCAL: Vocal, Trait.TEXTURE: Texture, Trait.SOUNDS: Sounds, Trait.ENERGY: Energy, Trait.FORM: Form,
    Trait.SOLOS: Solos,
}


