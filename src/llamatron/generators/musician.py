# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The musicians of a band: each plays a track's part as a player of that instrument would in the song.

A pattern says which notes; a musician says how the band plays them. A rhythm guitarist who
hears the singer start a line backs off, a lead guitarist waits for the singer to breathe, an
organist holds a chord where a pianist strikes it, and the whole band plays a verse softer than
its chorus. A musician reads what is round it, the kind of section its scene is, the chords and
the tune of other tracks, and plays its clip's notes accordingly: every note is one the clip
wrote, moved to the chord, left out, held, shortened, struck again or made louder or softer.
Nothing is drawn by chance but a loose player's loudness, which comes from the song's seed.
"""

import random

from llamatron.generators.base import ClipGenerator
from llamatron.generators.follow_chords import FollowChords
from llamatron.generators.parts import parts_of
from llamatron.math.rational import Rational
from llamatron.music import midi, sound as sound_values
from llamatron.music.sound import Sound

EIGHTH = Rational(1, 8)
SIXTEENTH = Rational(1, 16)
QUARTER = Rational(1, 4)

# The musicians, by the instrument each plays.
RHYTHM_GUITARIST = 'rhythm guitarist'
BASSIST = 'bassist'
DRUMMER = 'drummer'
BACKING_PIANO = 'backing piano'
BACKING_ORGAN = 'backing organ'
BACKING_SYNTH = 'backing synth'
LEAD_GUITARIST = 'lead guitarist'
LEAD_ORGAN = 'lead organ'
LEAD_PIANO = 'lead piano'
LEAD_SYNTH = 'lead synth'
ANSWERING_PLAYER = 'answering player'
BACKUP_SINGERS = 'backup singers'
HORN_SECTION = 'horn section'
STRING_SECTION = 'string section'
PERCUSSIONIST = 'percussionist'

# How much of a part a musician plays: fewer of its notes, all of them, or its long notes struck again.
SPARSE = 'sparse'
LIGHT = 'light'
AS_WRITTEN = 'as written'
BUSY = 'busy'
VERY_BUSY = 'very busy'
ACTIVITIES = (SPARSE, LIGHT, AS_WRITTEN, BUSY, VERY_BUSY)
# How loud a musician plays against the part as written, in steps, and what one step is in velocity.
QUIETEST = -3
LOUDEST = 3
USUAL_LOUDNESS = 0
LOUDNESS_STEP = 7
# How far a loose musician's loudness wanders from note to note, in steps, and what one step is in velocity.
TIGHT = 0
LOOSEST = 3
LOOSENESS_STEP = 4
# What a musician does while the tune sounds on another track.
NO_GIVING_WAY = 'none'
GIVES_WAY_SOME = 'some'
GIVES_WAY_OFTEN = 'often'
IN_THE_GAPS = 'plays in the gaps'
GIVES_WAY = (NO_GIVING_WAY, GIVES_WAY_SOME, GIVES_WAY_OFTEN, IN_THE_GAPS)
# How much softer a note under the tune is, by how far the musician gives way.
SOFTER_UNDER_TUNE = {GIVES_WAY_SOME: 12, GIVES_WAY_OFTEN: 22}
# Which notes of a bar a musician leans on.
NO_ACCENTS = 'none'
DOWNBEAT = 'downbeat'
BACKBEAT = 'backbeat'
OFFBEATS = 'offbeats'
ACCENTS = (NO_ACCENTS, DOWNBEAT, BACKBEAT, OFFBEATS)
ACCENT_DEPTH = 12
# How a musician's notes are held: as the part writes them, each until the next, or short.
HELD_NOTES = 'held'
SHORT_NOTES = 'short'
NOTE_LENGTHS = (AS_WRITTEN, HELD_NOTES, SHORT_NOTES)
# The longest a short note sounds.
SHORT_NOTE = EIGHTH
# Where on the instrument a musician plays: as written, or an octave lower or higher, always inside what the instrument can play.
LOW = 'low'
HIGH = 'high'
RANGES = (LOW, AS_WRITTEN, HIGH)
OCTAVE = midi.HALF_STEPS_PER_OCTAVE
RANGE_SHIFTS = {LOW: -OCTAVE, AS_WRITTEN: 0, HIGH: OCTAVE}
# What a musician does with its part in a kind of section.
WHOLE = 'whole'
SOFTER = 'softer'
THINNED = 'thinned'
HEAD_ONLY = 'head only'
MUTED = 'muted'
HITS = 'hits'
FORMS = (WHOLE, SOFTER, THINNED, HEAD_ONLY, MUTED, HITS)
SOFTER_DEPTH = 18
MUTED_DEPTH = 10
# The head of a part is the first bar of every so many.
BARS_TO_A_HEAD = 2
# The settings a kind of section has of its own.
PLAYS = 'plays'
PLAYED = 'played'


class Surroundings:
    """What a musician hears round its clip: the kind of section the scene is, the chords of the track it reads them from and when the tune sounds on another track."""

    __slots__ = ('section', 'chords', 'tune')

    def __init__(self, *, section=None, chords=None, tune=None):
        self.section = section
        # What says the chord at a time (playback/chord_source.py), or None for none to follow.
        self.chords = chords
        # What says whether the tune sounds at a time (playback/tune_source.py), or None for no tune to hear.
        self.tune = tune


class Musician(ClipGenerator):
    """Plays a clip as a musician of the band would: by the kind of section, round the tune, and with the player's own touch.

    A subclass is one instrument's player, and says what the instrument can play and how its
    player behaves when a setting is left out.
    """

    __slots__ = ('_bar', '_beat', '_surroundings', '_activity', '_loudness', '_looseness', '_gives_way', '_accents', '_notes', '_range', '_by_section', '_seed')

    # The lowest and the highest note the instrument plays, as MIDI numbers, or None for an instrument whose notes are not pitches to move.
    LOWEST = None
    HIGHEST = None
    # What the musician does with a setting left out.
    USUAL_GIVES_WAY = NO_GIVING_WAY
    USUAL_NOTES = AS_WRITTEN

    def __init__(self, *, bar, beat, surroundings=None, activity=AS_WRITTEN, loudness=USUAL_LOUDNESS, looseness=TIGHT, gives_way=None, accents=NO_ACCENTS, notes=None,
                 range=AS_WRITTEN, by_section=None, seed=None, continuation=None):
        # How long a bar and a beat last, in whole notes.
        self._bar = bar
        self._beat = beat
        self._surroundings = surroundings or Surroundings()
        self._activity = activity
        self._loudness = loudness
        self._looseness = looseness
        self._gives_way = self.USUAL_GIVES_WAY if gives_way is None else gives_way
        self._accents = accents
        self._notes = self.USUAL_NOTES if notes is None else notes
        self._range = range
        self._by_section = by_section or {}
        self._seed = seed

    def moves_pitches(self):
        """Return whether the instrument's notes are pitches, which follow the chords and have a range; a drum's are not."""
        return self.LOWEST is not None

    def _generate(self, clip):
        own = self._by_section.get(self._surroundings.section, {})
        if not own.get(PLAYS, True):
            return self._resting(clip), clip.get_length()
        if self.moves_pitches() and self._surroundings.chords is not None:
            clip = FollowChords(chords=self._surroundings.chords).generate(clip)
        parts = parts_of(_settled(sounds=clip.resolved_sounds(), scale=clip.get_scale()))
        self._play_form(parts=parts, form=own.get(PLAYED, WHOLE))
        self._play_activity(parts)
        self._give_way(parts)
        self._hold_notes(parts)
        self._lean_on(parts)
        self._play_in_range(parts)
        self._play_loud(parts)
        sounds = []
        for part in parts:
            sounds += part.sounds()
        return sounds, clip.get_length()

    def _resting(self, clip):
        """Return a clip's sounds with every note silent, so that the clip lasts as long as written."""
        sounds = []
        for part in parts_of(clip.resolved_sounds()):
            if part.is_note():
                part.silence()
            sounds += part.sounds()
        return sounds

    def _in_bar(self, part):
        """Return how far into its bar a part starts, in whole notes."""
        return part.start - (part.start // self._bar) * self._bar

    def _on_grid(self, *, part, grid):
        """Return whether a part starts on a multiple of a length counted from the start of its bar."""
        return (self._in_bar(part) / grid).is_whole()

    def _play_form(self, *, parts, form):
        """Play the part as a kind of section asks: softer, thinned to the notes on the beats, its head alone, muted, or as hits on each bar's first beat."""
        for part in _notes_of(parts):
            if form == SOFTER:
                part.louder_by(-SOFTER_DEPTH)
            elif form == THINNED and not self._on_grid(part=part, grid=self._beat):
                part.silence()
            elif form == HEAD_ONLY and int(part.start // self._bar) % BARS_TO_A_HEAD:
                part.silence()
            elif form == MUTED:
                part.heard = min(part.heard, SIXTEENTH)
                part.louder_by(-MUTED_DEPTH)
            elif form == HITS:
                if self._on_grid(part=part, grid=self._bar):
                    part.heard = min(part.heard, QUARTER)
                else:
                    part.silence()

    def _play_activity(self, parts):
        """Play fewer of the part's notes or strike its long notes again: a sparse player keeps the notes on the bar's halves and a light one the notes on the beats, each with every note a beat long or longer; a busy player strikes a note of a quarter or longer twice and a very busy one a note of an eighth or longer twice."""
        for part in _notes_of(parts):
            if self._activity in (SPARSE, LIGHT):
                grid = self._bar / 2 if self._activity == SPARSE and (self._bar / 2 / self._beat).is_whole() else self._beat
                if part.heard < self._beat and not self._on_grid(part=part, grid=grid):
                    part.silence()
            elif self._activity in (BUSY, VERY_BUSY):
                if part.heard >= (QUARTER if self._activity == BUSY else EIGHTH):
                    part.strikes = 2

    def _give_way(self, parts):
        """Make room for the tune while it sounds on another track: softer, softer and only on the beats, or silent until the tune rests."""
        tune = self._surroundings.tune
        if tune is None or self._gives_way == NO_GIVING_WAY:
            return
        for part in _notes_of(parts):
            if not tune.sounds_at(part.start):
                continue
            if self._gives_way == IN_THE_GAPS:
                part.silence()
                continue
            part.louder_by(-SOFTER_UNDER_TUNE[self._gives_way])
            if self._gives_way == GIVES_WAY_OFTEN and part.heard < self._beat and not self._on_grid(part=part, grid=self._beat):
                part.silence()

    def _hold_notes(self, parts):
        """Hold each note until the next one starts, or cut each short, where the musician plays its notes so."""
        notes = _notes_of(parts)
        if self._notes == HELD_NOTES:
            for part, after in zip(notes, notes[1:]):
                if part.strikes == 1:
                    part.heard = max(part.heard, after.start - part.start)
        elif self._notes == SHORT_NOTES:
            for part in notes:
                part.heard = min(part.heard, SHORT_NOTE * part.strikes)

    def _lean_on(self, parts):
        """Play the notes the musician leans on louder: each bar's first, the notes on the second beat of every two, or the notes between the beats."""
        if self._accents == NO_ACCENTS:
            return
        for part in _notes_of(parts):
            in_bar = self._in_bar(part)
            on_beat = (in_bar / self._beat).is_whole()
            leaned = {DOWNBEAT: in_bar == 0, BACKBEAT: on_beat and int(in_bar / self._beat) % 2 == 1, OFFBEATS: not on_beat}[self._accents]
            if leaned:
                part.louder_by(ACCENT_DEPTH)

    def _play_in_range(self, parts):
        """Move the part an octave lower or higher where the musician plays there, each note then brought by octaves inside what the instrument can play."""
        if not self.moves_pitches() or self._range == AS_WRITTEN:
            return
        for part in _notes_of(parts):
            part.moved_by(RANGE_SHIFTS[self._range])
            while part.lowest() is not None and part.lowest() < self.LOWEST:
                part.moved_by(OCTAVE)
            while part.lowest() is not None and part.pitch() > self.HIGHEST and part.lowest() - OCTAVE >= self.LOWEST:
                part.moved_by(-OCTAVE)

    def _play_loud(self, parts):
        """Play every note louder or softer by the musician's loudness, and a loose musician's notes each a little louder or softer by chance, drawn from the seed."""
        dice = random.Random(self._seed)
        reach = self._looseness * LOOSENESS_STEP
        for part in _notes_of(parts):
            wander = dice.randint(-reach, reach) if reach else 0
            if self._loudness or wander:
                part.louder_by(self._loudness * LOUDNESS_STEP + wander)


class RhythmGuitarist(Musician):
    """Strums or picks the chords; backs off a little under the tune."""

    __slots__ = ()
    LOWEST = 40
    HIGHEST = 76
    USUAL_GIVES_WAY = GIVES_WAY_SOME


class Bassist(Musician):
    """Holds the bottom of the band, and gives way to nobody."""

    __slots__ = ()
    LOWEST = 28
    HIGHEST = 55


class Drummer(Musician):
    """Plays a piece of the kit: its notes are drums, so no chord moves them."""

    __slots__ = ()


class BackingPiano(Musician):
    """Strikes the chords under the band, softer while the tune sounds."""

    __slots__ = ()
    LOWEST = 36
    HIGHEST = 96
    USUAL_GIVES_WAY = GIVES_WAY_SOME


class BackingOrgan(Musician):
    """Holds each chord until the next, as an organ does with no pedal to let go, softer while the tune sounds."""

    __slots__ = ()
    LOWEST = 36
    HIGHEST = 84
    USUAL_GIVES_WAY = GIVES_WAY_SOME
    USUAL_NOTES = HELD_NOTES


class BackingSynth(Musician):
    """Holds a pad under the band, softer while the tune sounds."""

    __slots__ = ()
    LOWEST = 36
    HIGHEST = 96
    USUAL_GIVES_WAY = GIVES_WAY_SOME
    USUAL_NOTES = HELD_NOTES


class LeadGuitarist(Musician):
    """Plays its licks where the tune rests."""

    __slots__ = ()
    LOWEST = 52
    HIGHEST = 88
    USUAL_GIVES_WAY = IN_THE_GAPS


class LeadOrgan(Musician):
    """Plays its lines where the tune rests, each note held into the next."""

    __slots__ = ()
    LOWEST = 48
    HIGHEST = 91
    USUAL_GIVES_WAY = IN_THE_GAPS
    USUAL_NOTES = HELD_NOTES


class LeadPiano(Musician):
    """Plays its lines where the tune rests."""

    __slots__ = ()
    LOWEST = 48
    HIGHEST = 100
    USUAL_GIVES_WAY = IN_THE_GAPS


class LeadSynth(Musician):
    """Plays its lines where the tune rests."""

    __slots__ = ()
    LOWEST = 48
    HIGHEST = 100
    USUAL_GIVES_WAY = IN_THE_GAPS


class AnsweringPlayer(Musician):
    """Answers the tune: silent while it sounds, heard when it rests."""

    __slots__ = ()
    LOWEST = 48
    HIGHEST = 88
    USUAL_GIVES_WAY = IN_THE_GAPS


class BackupSingers(Musician):
    """Hold their notes under the tune, softer than the singer."""

    __slots__ = ()
    LOWEST = 48
    HIGHEST = 79
    USUAL_GIVES_WAY = GIVES_WAY_SOME
    USUAL_NOTES = HELD_NOTES


class HornSection(Musician):
    """Plays short stabs, softer while the tune sounds."""

    __slots__ = ()
    LOWEST = 46
    HIGHEST = 82
    USUAL_GIVES_WAY = GIVES_WAY_SOME
    USUAL_NOTES = SHORT_NOTES


class StringSection(Musician):
    """Holds each chord into the next, softer while the tune sounds."""

    __slots__ = ()
    LOWEST = 36
    HIGHEST = 96
    USUAL_GIVES_WAY = GIVES_WAY_SOME
    USUAL_NOTES = HELD_NOTES


class Percussionist(Musician):
    """Plays hand percussion: its notes are drums, so no chord moves them."""

    __slots__ = ()


# The musician of each instrument, in the order they are offered.
MUSICIANS = {
    RHYTHM_GUITARIST: RhythmGuitarist, BASSIST: Bassist, DRUMMER: Drummer, BACKING_PIANO: BackingPiano, BACKING_ORGAN: BackingOrgan, BACKING_SYNTH: BackingSynth,
    LEAD_GUITARIST: LeadGuitarist, LEAD_ORGAN: LeadOrgan, LEAD_PIANO: LeadPiano, LEAD_SYNTH: LeadSynth, ANSWERING_PLAYER: AnsweringPlayer,
    BACKUP_SINGERS: BackupSingers, HORN_SECTION: HornSection, STRING_SECTION: StringSection, PERCUSSIONIST: Percussionist,
}
INSTRUMENTS = tuple(MUSICIANS)


def _notes_of(parts):
    """Return the parts that are notes or chords, in order: what a musician plays, as against the rests between."""
    return [part for part in parts if part.is_note()]


def _settled(*, sounds, scale):
    """Return a clip's sounds with each degree settled as its note in the clip's scale, where the clip has one."""
    if scale is None:
        return list(sounds)
    return [Sound.settled(sound, scale) if sound[sound_values.KIND] == sound_values.DEGREE else sound for sound in sounds]
