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
"""What Scene View shows of one scene, the user's design: every track's notes laid over each other, as played or as written, and the chord heard on each beat.

Played is the song's own render, the one the exports and real-time playback use, so it shows what
every chain, groove, strum, shape and register does; a song with no seed draws its random parts
afresh, so it is one take. Written renders a copy of the set with everything taken out that works
after the patterns are read: every chain, shape, strum, Euclidean mask and groove, and the steps'
probability and the rows that read the registers, so that each note shows as its pattern writes it.
A clip whose pattern reads the registers is marked either way, since what the registers do to it
depends on the whole song before it, the user's ask: its notes are drawn apart, never mixed in.

The chord on a beat is found from every note sounding in it, across every track but the drums,
each counted by how long it sounds there: every note of a llamatron chord symbol must sound, up to
two others may sound besides as passing notes, and the chord that sounds longest wins, named and
numbered in the scene's scale, with the bass after a slash when it isn't the root.
"""

from typing import NamedTuple

from llamatron.composition.file_format import (
    CONDITION_ROWS, FIXED_CHORDS, REGISTER_NOTE_ROWS, REGISTER_VELOCITY_ROWS, Accidental, ChordSymbol, ClipSlotSetting, Quality, SceneSetting, Section,
    SongSetting, TrackSetting,
)
from llamatron.composition.euclid import euclid_settings
from llamatron.composition.setlist import Setlist
from llamatron.composition.shapes import shape_settings
from llamatron.composition.strum import strum_settings
from llamatron.exporters.timing import timed_events
from llamatron.music.note import FLAT_NAMES, SEMITONES_ABOVE_C, SHARP_NAMES
from llamatron.playback.song_renderer import SongRenderer
from llamatron.strings.marks import (
    MSG_ACCIDENTAL_MARKS, MSG_QUALITY_MARKS, MSG_SCENE_VIEW_FROM_SCENE, MSG_SCENE_VIEW_SLASH_CHORD, MSG_SCENE_VIEW_FROM_SONG, MSG_SCENE_VIEW_NO_GROOVE, MSG_SCENE_VIEW_TEMPO_RAMP,
)

HALF_STEPS_PER_OCTAVE = 12
# How many pitch classes may sound in a beat besides its chord, as a melody's passing notes.
MOST_OUTSIDE = 2
# A note of the chord sounds through more than this share of the beat, more than a sixteenth of a quarter, so that a passing note can't be one.
HELD_SHARE = 0.25
# The letters of the notes, from C, which a seven-note scale's degrees take one each.
LETTERS = 'CDEFGAB'
ROMAN_NUMERALS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']
# The pattern rows a written view takes out: the steps' probability and every row that reads a register.
PROBABILITY_ROW = 'probability'
READING_ROWS = [*REGISTER_NOTE_ROWS.values(), *REGISTER_VELOCITY_ROWS.values(), *CONDITION_ROWS.values()]
# A chord's root, its third and its fifth, as half steps, which say its quality.
MINOR_THIRD = 3
MAJOR_THIRD = 4
DIMINISHED_FIFTH = 6
AUGMENTED_FIFTH = 8
# How a chord symbol is shown: as llamatron writes it, but a major triad as its root alone and a dominant chord by its number alone, as lead sheets write them.
NO_SYMBOL = ''
DOMINANT_SEVENTH = '7'
DOMINANT_NINTH = '9'
DOMINANT_ELEVENTH = '11'
DOMINANT_THIRTEENTH = '13'
PLAIN_SYMBOLS = {
    ChordSymbol.MAJOR: NO_SYMBOL, ChordSymbol.DOMINANT7: DOMINANT_SEVENTH, ChordSymbol.DOMINANT9: DOMINANT_NINTH, ChordSymbol.DOMINANT11: DOMINANT_ELEVENTH,
    ChordSymbol.DOMINANT13: DOMINANT_THIRTEENTH,
}


class SceneNote(NamedTuple):
    """A note of the scene: its track's place in the song, when it starts and ends in whole notes from the scene's start, its pitch, whether it's a drum's, and whether its clip reads the registers."""

    track: int
    start: object
    end: object
    pitch: int
    drum: bool
    marked: bool


class SceneNotes(NamedTuple):
    """A scene's notes, the song's track names by place, which tracks read the registers, how long the scene lasts in whole notes, and its beat and bar."""

    names: tuple
    notes: list
    marked_tracks: set
    length: object
    beat: object
    bar: object


class BeatChord(NamedTuple):
    """The chord heard on a beat: when the beat starts, the chord's name and its Roman numeral in the scene's scale."""

    start: object
    name: str
    numeral: str


def written_song(song):
    """Return a copy of a song, in a copy of its set, with everything that works after the patterns taken out, so that it renders the notes as written."""
    setlist = song.get_setlist()
    song_name = next(each for each in setlist.get_song_names() if setlist.get_song(each) is song)
    data = setlist.to_data()
    for pattern in data.get(Section.PATTERNS, {}).values():
        for row in [PROBABILITY_ROW, *READING_ROWS]:
            pattern.pop(row, None)
    shaped = [setting.get_name() for setting in shape_settings()]
    strummed = [setting.get_name() for setting in strum_settings()]
    masked = [setting.get_name() for setting in euclid_settings()]
    for song_data in data[Section.SONGS].values():
        song_data.pop(SongSetting.GROOVE, None)
        for track in (song_data.get(Section.TRACKS) or {}).values():
            for name in [TrackSetting.CHAINS, TrackSetting.GROOVE, *strummed, *masked]:
                track.pop(name, None)
        for scene in song_data.get(Section.SCENES) or []:
            for name in [SceneSetting.CHAINS, SceneSetting.GROOVE, *shaped]:
                scene.pop(name, None)
            for clip in (scene.get(SceneSetting.TRACKS) or {}).values():
                for name in [ClipSlotSetting.CHAINS, ClipSlotSetting.CHAIN, *shaped, *strummed]:
                    clip.pop(name, None)
    return Setlist.from_data(data=data).get_song(song_name)


def marked_tracks(*, song, index):
    """Return the names of the tracks whose clip in a scene plays a pattern that reads the registers."""
    scene = song.get_scenes()[index]
    marked = set()
    for name in song.get_track_names():
        clip_slot = scene.get_clip_slot(name)
        if clip_slot is not None and song.get_pattern(clip_slot.get_pattern_name()).uses_registers():
            marked.add(name)
    return marked


def scene_notes(*, song, index, written):
    """Return a scene's notes as played, the song's render, or as written, its patterns alone, with its rows laid end to end from the scene's start."""
    rendered = written_song(song) if written else song
    renderer = SongRenderer(rendered, seed=song.get_seed(), looping_scenes_go_round=True)
    grid = renderer.render()
    rows = grid.get_rows()
    starts = grid.row_starts()
    scene = rendered.get_scenes()[index]
    places = [place for place, written_scene in enumerate(renderer.get_scenes()) if written_scene.get_scene() is scene]
    names = tuple(song.get_track_names())
    marked = marked_tracks(song=song, index=index)
    origin = starts[places[0]] if places else 0
    notes = []
    end = origin
    for place in places:
        row = rows[place]
        end = max(end, starts[place] + grid.row_length(row))
        for column in grid.get_columns():
            clip = grid.get_clip(row=row, column=column)
            if clip is None or column.get_name() not in names:
                continue
            track = names.index(column.get_name())
            events, _ = timed_events(clip=clip, scale=grid.scale_at(row=row, column=column))
            for event in events:
                notes.append(SceneNote(track=track, start=starts[place] - origin + event.start, end=starts[place] - origin + event.end, pitch=event.midi_number,
                                       drum=column.is_drum(), marked=column.get_name() in marked))
    signature = song.get_time_signature()
    return SceneNotes(names=names, notes=notes, marked_tracks={names.index(name) for name in marked}, length=end - origin,
                      beat=signature.beat_length(), bar=signature.bar_length())


def chord_shapes():
    """Return each fixed chord symbol with its notes as half steps above the root, within one octave, the root among them."""
    return {symbol: frozenset({0, *[step % HALF_STEPS_PER_OCTAVE for step in kind.value]}) for symbol, kind in FIXED_CHORDS.items()}


def chord_of(*, weights, bass):
    """Return the chord heard in a beat, as its root's pitch class, its symbol and its bass's pitch class, or None.

    weights is the share of the beat each pitch class sounds through, however many notes sound it at
    once, so that a doubled root counts once. Every note of a chord must sound through more than
    HELD_SHARE of it, and up to MOST_OUTSIDE pitch classes may sound besides it, as a melody's passing
    notes; the chord whose notes
    sound longest wins, then the one with the fewest notes besides it, then the smallest, then the one
    whose root is the bass.
    """
    classes = set(weights)
    if len(classes) < 2:
        return None
    held = {pitch_class for pitch_class, weight in weights.items() if weight > HELD_SHARE}
    best = None
    for root in held:
        for symbol, shape in chord_shapes().items():
            members = {(root + step) % HALF_STEPS_PER_OCTAVE for step in shape}
            outside = classes - members
            if not members <= held or len(outside) > MOST_OUTSIDE:
                continue
            rank = (-sum(weights[pitch_class] for pitch_class in members), len(outside), len(shape), root != bass)
            if best is None or rank < best[0]:
                best = (rank, root, symbol, members)
    if best is None:
        return None
    _, root, symbol, members = best
    return root, symbol, bass if bass != root and bass in members else None


def quality_of_shape(shape):
    """Return a chord's quality from its notes above the root: minor or diminished on a minor third, augmented on a raised fifth, major otherwise."""
    if MINOR_THIRD in shape:
        return Quality.DIMINISHED if DIMINISHED_FIFTH in shape and AUGMENTED_FIFTH - 1 not in shape else Quality.MINOR
    return Quality.AUGMENTED if AUGMENTED_FIFTH in shape and AUGMENTED_FIFTH - 1 not in shape else Quality.MAJOR


def letter_spelled(scale):
    """Return a seven-note scale's notes spelled as a key signature spells them, each degree on the next letter, like Bb in F major, or None for another scale or one that would need a double sharp or flat."""
    shape = scale.get_half_steps()
    if len(shape) != len(LETTERS):
        return None
    root = scale.get_root()
    start = LETTERS.index(root[0])
    names = []
    for place, step in enumerate(shape):
        letter = LETTERS[(start + place) % len(LETTERS)]
        wanted = (SEMITONES_ABOVE_C[root] + step) % HALF_STEPS_PER_OCTAVE
        name = next((name for name in [*SHARP_NAMES, *FLAT_NAMES] if name[0] == letter and SEMITONES_ABOVE_C[name] % HALF_STEPS_PER_OCTAVE == wanted), None)
        if name is None:
            return None
        names.append(name)
    return names


def spelled(*, pitch_class, scale):
    """Return a pitch class's name as the scale spells it: its own note's name when the scale has it, and otherwise with flats when the scale spells any note with one, or sharps."""
    if scale is None:
        return SHARP_NAMES[pitch_class]
    names = letter_spelled(scale) or scale.get_note_names()
    for name in names:
        if SEMITONES_ABOVE_C[name] % HALF_STEPS_PER_OCTAVE == pitch_class:
            return name
    flats = any(name in FLAT_NAMES and name not in SHARP_NAMES for name in names)
    return (FLAT_NAMES if flats else SHARP_NAMES)[pitch_class]


def chord_texts(*, root, symbol, scale, bass=None):
    """Return a chord's name, its root spelled as the scale spells, its symbol, and its bass after a slash when the bass isn't its root, and its Roman numeral in the scale, a flat in front for a root between two of its notes."""
    name = spelled(pitch_class=root, scale=scale) + PLAIN_SYMBOLS.get(symbol, symbol)
    if bass is not None:
        name = MSG_SCENE_VIEW_SLASH_CHORD.format(chord=name, bass=spelled(pitch_class=bass, scale=scale))
    if scale is None:
        return name, NO_SYMBOL
    shape = scale.get_half_steps()
    above = (root - SEMITONES_ABOVE_C[scale.get_root()]) % HALF_STEPS_PER_OCTAVE
    accidental = NO_SYMBOL
    if above not in shape:
        above = (above + 1) % HALF_STEPS_PER_OCTAVE
        accidental = MSG_ACCIDENTAL_MARKS[Accidental.FLAT]
        if above not in shape:
            return name, NO_SYMBOL
    numeral = ROMAN_NUMERALS[shape.index(above) % len(ROMAN_NUMERALS)]
    quality = quality_of_shape(chord_shapes()[symbol])
    if quality in (Quality.MINOR, Quality.DIMINISHED):
        numeral = numeral.lower()
    return name, accidental + numeral + MSG_QUALITY_MARKS[quality]


def covered(spans):
    """Return how long a set of spans of time cover together, each moment counted once however many spans hold it."""
    total = 0
    reach = None
    for begin, finish in sorted(spans):
        if reach is None or begin > reach:
            total += finish - begin
            reach = finish
        elif finish > reach:
            total += finish - reach
            reach = finish
    return total


def beat_chords(*, notes, scale):
    """Return the chord on each beat of the scene where one is heard, from every note sounding in the beat across every track but the drums, each counted by how long it sounds there."""
    chords = []
    beat = notes.beat
    start = 0 * beat
    while start < notes.length:
        end = start + beat
        spans = {}
        lowest = None
        for note in notes.notes:
            if note.drum or note.end <= start or note.start >= end:
                continue
            spans.setdefault(note.pitch % HALF_STEPS_PER_OCTAVE, []).append((max(note.start, start), min(note.end, end)))
            lowest = note.pitch if lowest is None else min(lowest, note.pitch)
        weights = {pitch_class: covered(pieces) / beat for pitch_class, pieces in spans.items()}
        found = chord_of(weights=weights, bass=None if lowest is None else lowest % HALF_STEPS_PER_OCTAVE)
        if found is not None:
            name, numeral = chord_texts(root=found[0], symbol=found[1], scale=scale, bass=found[2])
            chords.append(BeatChord(start=start, name=name, numeral=numeral))
        start = end
    return chords


class Effective(NamedTuple):
    """What a scene plays with in the end, and where each comes from, since overrides can confuse, the user's ask: its tempo, scale and groove, each with its source, and each track whose clip takes a scale of its own."""

    tempo: str
    tempo_source: str
    scale: object
    scale_source: str
    groove: str
    groove_source: str
    clip_scales: dict


SONG_SOURCE = MSG_SCENE_VIEW_FROM_SONG
SCENE_SOURCE = MSG_SCENE_VIEW_FROM_SCENE
NO_GROOVE = MSG_SCENE_VIEW_NO_GROOVE


def effective_values(*, song, index):
    """Return the tempo, scale and groove a scene plays with and where each comes from, and the tracks whose clips take scales of their own."""
    scene = song.get_scenes()[index]
    if scene.get_tempo_setting() is not None:
        tempo, tempo_source = str(scene.get_tempo_setting()), SCENE_SOURCE
    elif scene.get_tempo_start() is not None:
        tempo, tempo_source = MSG_SCENE_VIEW_TEMPO_RAMP.format(start=scene.get_tempo_start(), end=scene.get_tempo_end()), SCENE_SOURCE
    else:
        tempo, tempo_source = str(song.get_tempo()), SONG_SOURCE
    scale_name = scene.get_scale_name() or song.get_scale_name()
    scale_source = SCENE_SOURCE if scene.get_scale_name() else SONG_SOURCE
    choice = scene.get_groove_choice()
    if choice is None:
        groove, groove_source = song.get_groove_name(), SONG_SOURCE
    else:
        groove, groove_source = (NO_GROOVE if choice is False else choice), SCENE_SOURCE
    clip_scales = {}
    for name in song.get_track_names():
        clip_slot = scene.get_clip_slot(name)
        if clip_slot is not None and clip_slot.get_scale_name() and clip_slot.get_scale_name() != scale_name:
            clip_scales[name] = clip_slot.get_scale_name()
    return Effective(tempo=tempo, tempo_source=tempo_source, scale=scale_name, scale_source=scale_source, groove=groove, groove_source=groove_source,
                     clip_scales=clip_scales)
