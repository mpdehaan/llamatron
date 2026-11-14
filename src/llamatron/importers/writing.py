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
"""Writing a cut song as a set file holds it: its patterns, its scales and the song itself, named to sit among what the set has.

Names follow the user's rules of 2026-11-10:

- The song is named after the file, numbered when the set has a song of that name already, as a
  copied song is.
- A track is named after its voice.
- A pattern is named after the first track that plays it and numbered from 1, the first number
  the set doesn't have, like up a 1. When the user lets the import share patterns, a pattern
  the set already has, the same in every setting but its name, is used rather than made again.
- A key uses one of the set's scales only when that scale is still named after its root and kind,
  like C Major, and otherwise a scale named that way is added.
- A scene is named after the bars it plays, like bars 1-4.
"""

from dataclasses import dataclass

import mido

from llamatron.support.rational import Rational
from llamatron.composition.checks import fraction_text
from llamatron.composition.defaults import DEFAULT_VELOCITY
from llamatron.composition.file_format import (
    CC_ROWS, ClipSlotSetting, PatternSetting, Row, ScaleSetting, SceneSetting, Section, SongSetting, TrackSetting,
)
from llamatron.composition.named_scale import NamedScale
from llamatron.composition.naming import copy_name, default_scale_name, is_default_scale_name, unique_name
from llamatron.composition.pattern import Pattern
from llamatron.composition.song import Song
from llamatron.music.time_signature import TimeSignature
from llamatron.strings.importing import MSG_SCENE_BAR, MSG_SCENE_BARS, MSG_WHERE_IMPORTED
from llamatron.strings.names import MSG_NUMBERED_NAME
from llamatron.importers.steps import TIED

FIRST_PATTERN_NUMBER = 1
FIRST_BAR_NUMBER = 1
NO_REPEAT = 1
MICROSECONDS_PER_MINUTE = 60000000
# What a pattern, scale or song the import made is placed by in an error, which only a fault of the import's own can raise.
WHERE_IMPORTED = MSG_WHERE_IMPORTED


@dataclass(slots=True, kw_only=True)
class ImportedSong:
    """What an import adds to a set: the song's name and data, and the patterns and scales it makes, each by name, as a set file holds them."""

    name: str
    song: dict
    patterns: dict
    scales: dict
    # How many of the song's patterns the set already had, which the song uses rather than making them again.
    shared: int


def pattern_data(*, pattern, set_step_size):
    """Return a pattern's data from whether it is a drum's, its step size, its steps and its CC steps: the rows that hold anything, its own step size where the set's differs, and whether it is a drum's."""
    drum, step_size, steps, controls = pattern
    count = len(steps)
    rows = {row: [None] * count for row in (Row.DEGREE, Row.ACCIDENTAL, Row.OCTAVE, Row.CHORD, Row.GATE, Row.VELOCITY)}
    ties = [False] * count
    for place, step in enumerate(steps):
        if step == TIED:
            ties[place] = True
        elif step is not None:
            rows[Row.DEGREE][place] = step.degree
            rows[Row.ACCIDENTAL][place] = step.accidental
            rows[Row.OCTAVE][place] = step.octave
            rows[Row.CHORD][place] = step.chord
            rows[Row.GATE][place] = step.gate
            rows[Row.VELOCITY][place] = None if step.velocity == DEFAULT_VELOCITY else step.velocity
    data = {PatternSetting.STEPS: count}
    if step_size != set_step_size:
        data[PatternSetting.STEP_SIZE] = fraction_text(step_size)
    if drum:
        data[PatternSetting.DRUM] = True
    data.update({row: values for row, values in rows.items() if any(value is not None for value in values)})
    if any(ties):
        data[Row.TIE] = ties
    data.update(control_rows(controls))
    return data


def control_rows(controls):
    """Return the CC rows and the Slide row of a pattern's CC steps, each lane on the CC row of its place, holding only the rows that send anything."""
    count = len(controls)
    rows = {}
    for lane, row in enumerate(CC_ROWS):
        values = [None if step is None or lane >= len(step.values) else step.values[lane] for step in controls]
        if any(value is not None for value in values):
            rows[row] = values
    slides = [step is not None and step.slide for step in controls]
    if any(slides):
        rows[Row.SLIDE] = slides
    return rows if count else {}


def as_the_set_writes(data):
    """Return a pattern's data as the set would write the pattern, so that two patterns' data can be compared."""
    return Pattern.from_data(data=data, where=WHERE_IMPORTED).to_data()


def numbered_name(*, base, taken):
    """Return the base with the first number from 1 that makes a name nothing has, like up a 1."""
    number = FIRST_PATTERN_NUMBER
    while MSG_NUMBERED_NAME.format(base=base, number=number) in taken:
        number += 1
    return MSG_NUMBERED_NAME.format(base=base, number=number)


def tempo_of(microseconds):
    """Return a MIDI tempo as a song or scene holds it: a whole number of quarter notes a minute when one writes back the same, and the exact fraction otherwise."""
    exact = Rational(MICROSECONDS_PER_MINUTE, microseconds)
    whole = round(exact)
    if whole and mido.bpm2tempo(whole) == microseconds:
        return whole
    return fraction_text(exact)


def time_signature_text(beats_and_unit):
    """Return a MIDI time signature as a song holds it, like 6/8, or None for one llamatron can't hold."""
    beats, unit = beats_and_unit
    try:
        return TimeSignature(beats=beats, unit=unit).to_text()
    except ValueError:
        return None


def track_data(voice):
    """Return a voice's track settings: drum where it is a drum's, and the CC numbers of its lanes, the rest of the four lanes sending nothing."""
    data = {}
    if voice.drum:
        data[TrackSetting.DRUM] = True
    if voice.lanes:
        data[TrackSetting.CC] = [*voice.lanes, *[None] * (len(CC_ROWS) - len(voice.lanes))]
    return data


class SongWriter:
    """What writes one cut song into a set's terms: the set it goes into, the voices, the cut, the bar lines, the step size and whether patterns may be shared."""

    __slots__ = ('_setlist', '_voices', '_cut', '_bars', '_step_size', '_share', '_track_names')

    def __init__(self, *, setlist, voices, cut, bars, step_size, share):
        self._setlist = setlist
        self._voices = voices
        self._cut = cut
        self._bars = bars
        self._step_size = step_size
        self._share = share
        self._track_names = self.track_names()

    def track_names(self):
        """Return each voice's track name, numbered where two voices would share one."""
        names = []
        for voice in self._voices:
            names.append(unique_name(base=voice.name, taken=set(names)))
        return names

    def written(self, *, name, time_signature):
        """Return the imported song, named name, with the patterns and scales it adds to the set."""
        patterns, shared, pattern_names = self.patterns()
        scales, scale_names = self.scales()
        first = self._cut.scenes[0]
        song = {SongSetting.TEMPO: tempo_of(first.tempo)}
        if time_signature is not None:
            song[SongSetting.TIME_SIGNATURE] = time_signature
        song[SongSetting.SCALE] = scale_names[first.key]
        song[Section.TRACKS] = {track: track_data(voice) for track, voice in zip(self._track_names, self._voices)}
        song[Section.SCENES] = [self.scene_data(scene=scene, song=song, pattern_names=pattern_names, scale_names=scale_names) for scene in self._cut.scenes]
        song_name = name if not self._setlist.has_song(name) else copy_name(name=name, taken=set(self._setlist.get_song_names()))
        return ImportedSong(name=song_name, song=song, patterns=patterns, scales=scales, shared=shared)

    def patterns(self):
        """Return the patterns the song adds by name, how many it shares with the set instead, and every pattern's name."""
        set_step_size = self._setlist.get_step_size()
        taken = set(self._setlist.get_item_names(Section.PATTERNS))
        existing = {}
        if self._share:
            for name in self._setlist.get_item_names(Section.PATTERNS):
                existing.setdefault(repr(self._setlist.get_item(section=Section.PATTERNS, name=name).to_data()), name)
        first_track = self.first_track_of_patterns()
        added = {}
        names = {}
        shared = 0
        for pattern in self._cut.patterns:
            data = pattern_data(pattern=pattern, set_step_size=set_step_size)
            same = existing.get(repr(as_the_set_writes(data)))
            if same is not None:
                names[pattern] = same
                shared += 1
                continue
            name = numbered_name(base=first_track[pattern], taken=taken)
            taken.add(name)
            added[name] = data
            names[pattern] = name
        return added, shared, names

    def first_track_of_patterns(self):
        """Return the name of the first track to play each pattern."""
        first = {}
        for scene in self._cut.scenes:
            for clip in scene.clips:
                first.setdefault(clip.pattern, self._track_names[clip.voice])
        return first

    def scales(self):
        """Return the scales the song adds by name, and the name of the scale each of its keys uses."""
        taken = set(self._setlist.get_item_names(Section.SCALES))
        added = {}
        names = {}
        for scene in self._cut.scenes:
            key = scene.key
            if key in names:
                continue
            names[key] = self.scale_already_named(key)
            if names[key] is None:
                name = unique_name(base=default_scale_name(root=key.root, kind=key.kind), taken=taken)
                taken.add(name)
                added[name] = {ScaleSetting.ROOT: key.root, ScaleSetting.TYPE: key.kind}
                names[key] = name
        return added, names

    def scale_already_named(self, key):
        """Return the name of the set's scale of this root and kind that is still named after them, or None."""
        for name in self._setlist.get_item_names(Section.SCALES):
            scale = self._setlist.get_item(section=Section.SCALES, name=name)
            data = scale.to_data()
            if (data[ScaleSetting.ROOT], data[ScaleSetting.TYPE]) == (key.root, key.kind) and is_default_scale_name(name=name, root=key.root, kind=key.kind):
                return name
        return None

    def scene_data(self, *, scene, song, pattern_names, scale_names):
        """Return one scene's data: its name, its repeat, its scale and tempo where they differ from the song's, and its clips."""
        data = {SceneSetting.NAME: self.scene_name(scene)}
        if scene.repeat > NO_REPEAT:
            data[SceneSetting.REPEAT] = scene.repeat
        if scale_names[scene.key] != song[SongSetting.SCALE]:
            data[SceneSetting.SCALE] = scale_names[scene.key]
        if tempo_of(scene.tempo) != song[SongSetting.TEMPO]:
            data[SceneSetting.TEMPO] = tempo_of(scene.tempo)
        clips = {}
        for clip in scene.clips:
            clip_data = {ClipSlotSetting.PATTERN: pattern_names[clip.pattern]}
            if clip.repeats > NO_REPEAT:
                clip_data[ClipSlotSetting.REPEAT] = clip.repeats
            clips[self._track_names[clip.voice]] = clip_data
        data[SceneSetting.TRACKS] = clips
        return data

    def scene_name(self, scene):
        """Return a scene's name from the bars it plays, all its repeats together, counted from 1."""
        start = scene.start * self._step_size
        last = (scene.start + (scene.end - scene.start) * scene.repeat - 1) * self._step_size
        first_bar = self.bar_number(start)
        last_bar = self.bar_number(last)
        if first_bar == last_bar:
            return MSG_SCENE_BAR.format(first=first_bar)
        return MSG_SCENE_BARS.format(first=first_bar, last=last_bar)

    def bar_number(self, time):
        """Return the number of the bar a time falls in, counted from 1."""
        return sum(1 for line in self._bars[:-1] if line <= time) - 1 + FIRST_BAR_NUMBER


def add_imported(*, setlist, imported):
    """Add an imported song to a set, with its scales and patterns first, since the song names them, and return the song."""
    for name, data in imported.scales.items():
        setlist.add_item(section=Section.SCALES, name=name, item=NamedScale.from_data(data=data, where=WHERE_IMPORTED, song=setlist))
    for name, data in imported.patterns.items():
        setlist.add_item(section=Section.PATTERNS, name=name, item=Pattern.from_data(data=data, where=WHERE_IMPORTED, song=setlist))
    song = Song.from_data(data=imported.song, where=WHERE_IMPORTED, setlist=setlist)
    song.fill_in_defaults()
    setlist.add_item(section=Section.SONGS, name=imported.name, item=song)
    return song

