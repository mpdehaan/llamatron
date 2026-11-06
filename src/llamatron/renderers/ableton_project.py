# llamatron: a Python language and framework for producing MIDI clips.
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

import copy
import gzip
import itertools
import os
import re
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

from llamatron.renderers.clip_tree import _check_directory, _check_song
from llamatron.renderers.timing import BEATS_PER_WHOLE_NOTE, control_points, timed_events
from llamatron.clip_grid import _Validated

# Installed along with the code, so that a set can be written from anywhere.
DEFAULT_TEMPLATE = Path(__file__).resolve().parents[1] / 'templates' / 'live12.als'

MIN_LIVE_TEMPO = 20
MAX_LIVE_TEMPO = 999
EMPTY_CLIP_BEATS = 4
NOTE_OFF_VELOCITY = 64
NO_GROOVE = '-1'
ARRANGEMENT_TAKE_ID = 1
# Where Live puts a clip envelope's value from before the clip starts.
BEFORE_CLIP = '-63072000'
# A MIDI track's controllers start with pitch bend and channel pressure, and then CC 0 to 127.
FIRST_CC_TARGET = 2
# Live sets made by Live 12 have this major version, and a minor version that starts with 12.
LIVE_MAJOR_VERSION, LIVE_12_MINOR_VERSION = '5', '12.'
# Tracks and clips are numbered from 1 where Live shows them, and note ids start at 1.
FIRST_NUMBER = 1
# Where a clip in Session View starts, and where a clip's loop starts.
CLIP_START = 0
# A clip with nothing in it is EMPTY_CLIP_BEATS long, so Live shows something.
NO_LENGTH = 0
# How Live writes numbers in beats, and how the set's XML starts.
BEATS_FORMAT = '{beats:.17g}'
XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>\n'
XML_TEXT, XML_BYTES = 'unicode', 'utf-8'
# A set is gzipped XML, written without a time stamp so the same song always gives the same file.
NO_TIME_STAMP = 0
SET_FILE = '{name}.als'
# A track with no name is named the way Live names a new MIDI track.
UNNAMED_TRACK = '{number}-MIDI'
NO_NAME = ''
# Live writes true and false in lower case.
LIVE_TRUE, LIVE_FALSE = 'true', 'false'
# A controller target's tag ends in its number, like ControllerTargets.3.
TARGET_NUMBER_SEPARATOR = '.'


class Tag:
    """The names of the elements in a Live set that this renderer reads or writes."""

    LIVE_SET = 'LiveSet'
    NEXT_POINTEE_ID = 'NextPointeeId'
    MAIN_TRACK = 'MainTrack'
    SCENES = 'Scenes'
    TRACKS = 'Tracks'
    MIDI_TRACK = 'MidiTrack'
    RETURN_TRACK = 'ReturnTrack'
    MIDI_CLIP = 'MidiClip'
    FLOAT_EVENT = 'FloatEvent'
    CLIP_ENVELOPE = 'ClipEnvelope'
    ENVELOPE_TARGET = 'EnvelopeTarget'
    POINTEE_ID = 'PointeeId'
    AUTOMATION = 'Automation'
    EVENTS = 'Events'
    TRANSFORM_VIEW_STATE = 'AutomationTransformViewState'
    IS_TRANSFORM_PENDING = 'IsTransformPending'
    TIME_AND_VALUE_TRANSFORMS = 'TimeAndValueTransforms'
    LOOP_SLOT = 'LoopSlot'
    VALUE = 'Value'
    SCROLLER_TIME_PRESERVER = 'ScrollerTimePreserver'
    LEFT_TIME = 'LeftTime'
    RIGHT_TIME = 'RightTime'
    KEY_TRACK = 'KeyTrack'
    NOTES = 'Notes'
    MIDI_NOTE_EVENT = 'MidiNoteEvent'
    MIDI_KEY = 'MidiKey'


class ElementPath:
    """Paths to elements inside a Live set, from the element named first."""

    TEMPO = 'DeviceChain/Mixer/Tempo'
    MANUAL = 'Manual'
    AUTOMATION_TARGET = 'AutomationTarget'
    ENVELOPES = 'AutomationEnvelopes/Envelopes'
    ENVELOPE_POINTEE = 'EnvelopeTarget/PointeeId'
    AUTOMATION_EVENTS = 'Automation/Events'
    NAME = 'Name'
    SCENE_TEMPO = 'Tempo'
    TEMPO_ENABLED = 'IsTempoEnabled'
    COLOR = 'Color'
    CLIP_SLOTS = 'DeviceChain/MainSequencer/ClipSlotList'
    FROZEN_CLIP_SLOTS = 'DeviceChain/FreezeSequencer/ClipSlotList'
    ARRANGEMENT_EVENTS = 'DeviceChain/MainSequencer/ClipTimeable/ArrangerAutomation/Events'
    CONTROLLERS = 'DeviceChain/MainSequencer/MidiControllers'
    EFFECTIVE_NAME = 'Name/EffectiveName'
    USER_NAME = 'Name/UserName'
    # The Speaker is a track's on switch, so a muted track is one that's switched off.
    SPEAKER = 'DeviceChain/Mixer/Speaker/Manual'
    SLOT_VALUE = 'ClipSlot/Value'
    CURRENT_START = 'CurrentStart'
    CURRENT_END = 'CurrentEnd'
    TAKE_ID = 'TakeId'
    LOOP = 'Loop/{setting}'
    GROOVE = 'GrooveSettings/GrooveId'
    IN_KEY = 'IsInKey'
    NOTES = 'Notes'
    CLIP_ENVELOPES = 'Envelopes/Envelopes'
    KEY_TRACKS = 'KeyTracks'
    NEXT_NOTE_ID = 'NoteIdGenerator/NextId'


class Attribute:
    """The attributes of a Live set's elements that this renderer reads or writes."""

    VALUE = 'Value'
    ID = 'Id'
    TIME = 'Time'
    MAJOR_VERSION = 'MajorVersion'
    MINOR_VERSION = 'MinorVersion'
    DURATION = 'Duration'
    VELOCITY = 'Velocity'
    OFF_VELOCITY = 'OffVelocity'
    NOTE_ID = 'NoteId'


class LoopSetting:
    """A clip's loop settings, under its Loop element."""

    START = 'LoopStart'
    END = 'LoopEnd'
    START_RELATIVE = 'StartRelative'
    ON = 'LoopOn'
    OUT_MARKER = 'OutMarker'
    HIDDEN_START = 'HiddenLoopStart'
    HIDDEN_END = 'HiddenLoopEnd'


MSG_BAD_TEMPLATE = 'invalid template: {value!r}'
MSG_FILE_EXISTS = 'warning: stopping without writing anything, because {path} already exists'
MSG_OTHER_FILES = 'warning: {directory} already contains {count} other item(s), which will not be deleted: {files}'
MSG_NOT_LIVE_12 = '{template} was not saved by Live 12: {attributes}'
MSG_EMPTY_SONG = 'a Live set needs at least one scene and one track'
MSG_BAD_TEMPO = 'Live needs a tempo from {lowest} to {highest}, got {value!r}'
MSG_NO_MIDI_TRACK = '{template} needs a MIDI track to copy'
MSG_NO_CLIP = ('the first MIDI track in {template} needs a clip in it, because Live '
               'requires many details in a clip that are copied from there')
# File names, as the warnings list them.
FILE_LIST_SEPARATOR = ', '

# Live gives these elements ids that must be unique across the whole set.
_SHARED_ID_TAGS = re.compile(r'(Target|Targets\.\d+|Pointee)$')


def _check_template(template):
    if not isinstance(template, (str, os.PathLike)) or not os.fspath(template):
        raise ValueError(MSG_BAD_TEMPLATE.format(value=template))


def _set_value(parent, path, value):
    parent.find(path).set(Attribute.VALUE, str(value))


def _beats(whole_notes):
    """Return a fraction of a whole note as beats, in the way Live writes numbers."""
    return BEATS_FORMAT.format(beats=float(whole_notes * BEATS_PER_WHOLE_NOTE))


def _live_boolean(value):
    """Return true or false the way Live writes them."""
    return LIVE_TRUE if value else LIVE_FALSE


def _empty_clip_length():
    """Return how long a clip with nothing in it lasts in Arrangement View, in whole notes."""
    return Fraction(EMPTY_CLIP_BEATS, BEATS_PER_WHOLE_NOTE)


def _remove_children(element):
    """Remove everything inside an element, leaving the element itself."""
    for child in list(element):
        element.remove(child)


class AbletonProject:
    """Renders a ClipGrid as an Ableton Live 12 set, in both Session View and Arrangement View.

    In Session View, each scene and track slot holds its clip. In Arrangement View, the
    scenes play one after another from the start, each lasting as long as its longest clip.

    The set is written to <directory>/<directory name>.als, and is built from a template
    saved by Live. Its first MIDI track, which must have a clip in it, is copied for each
    track in the song, along with any instruments on that track. The template's other MIDI
    and audio tracks are left out, and its return tracks are kept. Live's format isn't
    documented, so this only accepts templates from Live 12.

    The name sets the file's name, instead of the directory's.
    """

    __slots__ = ('_directory', '_song', '_template', 'name')

    directory = _Validated(_check_directory)
    song = _Validated(_check_song)
    template = _Validated(_check_template)

    def __init__(self, directory, song, template=DEFAULT_TEMPLATE, name=None):
        self.directory = directory
        self.song = song
        self.template = template
        self.name = name

    @property
    def path(self):
        """Where the set will be written."""
        name = self.name or os.path.basename(os.path.abspath(self.directory))
        return os.path.join(self.directory, SET_FILE.format(name=name))

    def render(self):
        """Write the set, leaving any other files in the directory in place.

        If the set already exists, this prints a warning and stops without writing anything.
        """
        os.makedirs(self.directory, exist_ok=True)
        filename = os.path.basename(self.path)
        existing = sorted(os.listdir(self.directory))
        if filename in existing:
            print(MSG_FILE_EXISTS.format(path=self.path))
            return
        if existing:
            print(MSG_OTHER_FILES.format(directory=os.fspath(self.directory), count=len(existing), files=FILE_LIST_SEPARATOR.join(existing)))

        # Built before anything is written, so that an invalid clip doesn't leave a broken file.
        contents = gzip.compress(self._build(), mtime=NO_TIME_STAMP)
        with open(self.path, 'wb') as file:
            file.write(contents)

    def _build(self):
        """Return the XML of the finished set as bytes."""
        self._check_song_fits_live()
        with open(self.template, 'rb') as file:
            root = ET.fromstring(gzip.decompress(file.read()))
        if not _saved_by_live_12(root):
            raise ValueError(MSG_NOT_LIVE_12.format(template=self.template, attributes=root.attrib))

        live_set = root.find(Tag.LIVE_SET)
        next_shared_id = itertools.count(int(live_set.find(Tag.NEXT_POINTEE_ID).get(Attribute.VALUE)))
        starts = self._scene_starts()
        self._set_tempo(live_set, starts)
        self._build_scenes(live_set)
        self._build_tracks(live_set, next_shared_id, starts)
        _set_value(live_set, Tag.NEXT_POINTEE_ID, next(next_shared_id))

        xml = ET.tostring(root, encoding=XML_TEXT)
        return (XML_DECLARATION + xml).encode(XML_BYTES)

    def _check_song_fits_live(self):
        if not self.song.scenes or not self.song.tracks:
            raise ValueError(MSG_EMPTY_SONG)
        for tempo in [self.song.tempo] + [scene.tempo for scene in self.song.scenes]:
            if tempo is not None and not MIN_LIVE_TEMPO <= tempo <= MAX_LIVE_TEMPO:
                raise ValueError(MSG_BAD_TEMPO.format(lowest=MIN_LIVE_TEMPO, highest=MAX_LIVE_TEMPO, value=tempo))

    def _scene_starts(self):
        """Return when each scene starts in Arrangement View, in fractions of a whole note."""
        starts = []
        now = Fraction(CLIP_START)
        for scene in self.song.scenes:
            starts.append(now)
            now += self._scene_length(scene) or _empty_clip_length()
        return starts

    def _scene_length(self, scene):
        """Return how long a scene's longest clip lasts, or nothing if it has no clips."""
        clips = [self.song.get_clip(scene, track) for track in self.song.tracks]
        lengths = [clip.total_length() for clip in clips if clip is not None]
        return max(lengths, default=NO_LENGTH)

    def _set_tempo(self, live_set, starts):
        """Set the tempo control and its automation, with changes for any scene tempos."""
        main_track = live_set.find(Tag.MAIN_TRACK)
        tempo = main_track.find(ElementPath.TEMPO)
        _set_value(tempo, ElementPath.MANUAL, self.song.tempo)
        target = tempo.find(ElementPath.AUTOMATION_TARGET).get(Attribute.ID)
        for envelope in main_track.find(ElementPath.ENVELOPES):
            if envelope.find(ElementPath.ENVELOPE_POINTEE).get(Attribute.VALUE) == target:
                events = envelope.find(ElementPath.AUTOMATION_EVENTS)
                for event in events:
                    event.set(Attribute.VALUE, str(self.song.tempo))
                if any(scene.tempo is not None for scene in self.song.scenes):
                    self._add_tempo_changes(events, starts)

    def _add_tempo_changes(self, events, starts):
        next_id = len(events)
        for offset, (scene, start) in enumerate(zip(self.song.scenes, starts)):
            ET.SubElement(events, Tag.FLOAT_EVENT, {
                Attribute.ID: str(next_id + offset),
                Attribute.TIME: _beats(start),
                Attribute.VALUE: str(self.song.tempo if scene.tempo is None else scene.tempo),
            })

    def _build_scenes(self, live_set):
        scenes = live_set.find(Tag.SCENES)
        prototype = scenes[0]
        scenes[:] = [self._build_scene(prototype, scene) for scene in self.song.scenes]

    def _build_scene(self, prototype, scene):
        element = copy.deepcopy(prototype)
        element.set(Attribute.ID, str(scene.id))
        _set_value(element, ElementPath.NAME, scene.name or NO_NAME)
        tempo_is_set = scene.tempo is not None
        _set_value(element, ElementPath.SCENE_TEMPO, scene.tempo if tempo_is_set else self.song.tempo)
        _set_value(element, ElementPath.TEMPO_ENABLED, _live_boolean(tempo_is_set))
        return element

    def _build_tracks(self, live_set, next_shared_id, starts):
        tracks = live_set.find(Tag.TRACKS)
        midi_tracks = tracks.findall(Tag.MIDI_TRACK)
        if not midi_tracks:
            raise ValueError(MSG_NO_MIDI_TRACK.format(template=self.template))
        clip_prototype = self._find_clip(midi_tracks[0])
        colors = [track.find(ElementPath.COLOR).get(Attribute.VALUE) for track in midi_tracks]
        next_track_id = itertools.count(_highest_id(tracks) + 1)

        built = []
        for number, track in enumerate(self.song.tracks):
            color = colors[number % len(colors)]
            built.append(self._build_track(midi_tracks[0], clip_prototype, track, number, color, next(next_track_id), next_shared_id, starts))
        tracks[:] = built + tracks.findall(Tag.RETURN_TRACK)

    def _find_clip(self, track):
        for clip in track.find(ElementPath.CLIP_SLOTS).iter(Tag.MIDI_CLIP):
            return clip
        raise ValueError(MSG_NO_CLIP.format(template=self.template))

    def _build_track(self, prototype, clip_prototype, track, number, color, track_id, next_shared_id, starts):
        element = copy.deepcopy(prototype)
        element.set(Attribute.ID, str(track_id))
        _renumber_shared_ids(element, next_shared_id)

        _set_value(element, ElementPath.EFFECTIVE_NAME, track.name or UNNAMED_TRACK.format(number=number + FIRST_NUMBER))
        _set_value(element, ElementPath.USER_NAME, track.name or NO_NAME)
        _set_value(element, ElementPath.COLOR, color)
        _set_value(element, ElementPath.SPEAKER, _live_boolean(not track.mute))

        controllers = _controller_ids(element)
        clips = [self.song.get_clip(scene, track) for scene in self.song.scenes]
        slots = element.find(ElementPath.CLIP_SLOTS)
        empty_slot = self._empty_slot(slots[0])
        slots[:] = [
            self._build_slot(empty_slot, clip_prototype, clip, scene, track, place, color, controllers)
            for place, (scene, clip) in enumerate(zip(self.song.scenes, clips))
        ]
        frozen_slots = element.find(ElementPath.FROZEN_CLIP_SLOTS)
        frozen_slots[:] = [self._numbered_copy(empty_slot, place) for place in range(len(self.song.scenes))]
        arrangement = element.find(ElementPath.ARRANGEMENT_EVENTS)
        arrangement[:] = self._arrangement_clips(clip_prototype, clips, track, color, controllers, starts)
        return element

    def _arrangement_clips(self, clip_prototype, clips, track, color, controllers, starts):
        """Return the clips of a track in Arrangement View, each at the time its scene starts."""
        return [
            self._build_clip(clip_prototype, clip, scene, track, place, color, controllers, start=start)
            for place, (scene, clip, start) in enumerate(zip(self.song.scenes, clips, starts))
            if clip is not None
        ]

    def _empty_slot(self, slot):
        empty = copy.deepcopy(slot)
        _remove_children(empty.find(ElementPath.SLOT_VALUE))
        return empty

    def _numbered_copy(self, element, number):
        result = copy.deepcopy(element)
        result.set(Attribute.ID, str(number))
        return result

    def _build_slot(self, empty_slot, clip_prototype, clip, scene, track, place, color, controllers):
        slot = self._numbered_copy(empty_slot, place)
        if clip is not None:
            slot.find(ElementPath.SLOT_VALUE).append(
                self._build_clip(clip_prototype, clip, scene, track, place, color, controllers)
            )
        return slot

    def _build_clip(self, prototype, clip, scene, track, place, color, controllers, start=None):
        notes, length = timed_events(clip, self.song.scale_at(scene, track))
        beats = _beats(length) if length > NO_LENGTH else str(EMPTY_CLIP_BEATS)

        element = copy.deepcopy(prototype)
        element.set(Attribute.ID, str(place))
        _set_value(element, ElementPath.NAME, clip.name or NO_NAME)
        _set_value(element, ElementPath.COLOR, color)
        if start is None:
            element.set(Attribute.TIME, str(CLIP_START))
            _set_value(element, ElementPath.CURRENT_START, CLIP_START)
            _set_value(element, ElementPath.CURRENT_END, beats)
        else:
            end = start + (length if length > NO_LENGTH else _empty_clip_length())
            element.set(Attribute.TIME, _beats(start))
            _set_value(element, ElementPath.CURRENT_START, _beats(start))
            _set_value(element, ElementPath.CURRENT_END, _beats(end))
            _set_value(element, ElementPath.TAKE_ID, ARRANGEMENT_TAKE_ID)
        for setting, value in _loop_settings(beats, clip.loop):
            _set_value(element, ElementPath.LOOP.format(setting=setting), value)
        # The template's clip uses a groove, which would move the notes off their times, and its
        # key, which wouldn't match this clip's scale.
        _set_value(element, ElementPath.GROOVE, NO_GROOVE)
        _set_value(element, ElementPath.IN_KEY, LIVE_FALSE)
        self._write_notes(element.find(ElementPath.NOTES), notes)
        self._write_envelopes(element.find(ElementPath.CLIP_ENVELOPES), clip, length, controllers)
        return element

    def _write_envelopes(self, envelopes, clip, length, controllers):
        """Write one clip envelope for each CC number the clip sends."""
        _remove_children(envelopes)
        for envelope_id, (number, lane) in enumerate(sorted(control_points(clip, length).items())):
            envelope = ET.SubElement(envelopes, Tag.CLIP_ENVELOPE, Id=str(envelope_id))
            target = ET.SubElement(envelope, Tag.ENVELOPE_TARGET)
            ET.SubElement(target, Tag.POINTEE_ID, Value=controllers[number])
            automation = ET.SubElement(envelope, Tag.AUTOMATION)
            events = ET.SubElement(automation, Tag.EVENTS)
            for event_id, (time, value) in enumerate(_envelope_points(lane)):
                ET.SubElement(events, Tag.FLOAT_EVENT, Id=str(event_id), Time=time, Value=str(value))
            view = ET.SubElement(automation, Tag.TRANSFORM_VIEW_STATE)
            ET.SubElement(view, Tag.IS_TRANSFORM_PENDING, Value=LIVE_FALSE)
            ET.SubElement(view, Tag.TIME_AND_VALUE_TRANSFORMS)
            ET.SubElement(ET.SubElement(envelope, Tag.LOOP_SLOT), Tag.VALUE)
            scroller = ET.SubElement(envelope, Tag.SCROLLER_TIME_PRESERVER)
            ET.SubElement(scroller, Tag.LEFT_TIME, Value=str(CLIP_START))
            ET.SubElement(scroller, Tag.RIGHT_TIME, Value=str(CLIP_START))

    def _write_notes(self, element, notes):
        key_tracks = element.find(ElementPath.KEY_TRACKS)
        _remove_children(key_tracks)

        note_ids = itertools.count(FIRST_NUMBER)
        for key_id, pitch in enumerate(_pitches(notes)):
            key_track = ET.SubElement(key_tracks, Tag.KEY_TRACK, Id=str(key_id))
            events = ET.SubElement(key_track, Tag.NOTES)
            for start, end, midi_number, velocity in sorted(notes):
                if midi_number == pitch:
                    ET.SubElement(events, Tag.MIDI_NOTE_EVENT, {
                        Attribute.TIME: _beats(start),
                        Attribute.DURATION: _beats(end - start),
                        Attribute.VELOCITY: str(velocity),
                        Attribute.OFF_VELOCITY: str(NOTE_OFF_VELOCITY),
                        Attribute.NOTE_ID: str(next(note_ids)),
                    })
            ET.SubElement(key_track, Tag.MIDI_KEY, Value=str(pitch))
        _set_value(element, ElementPath.NEXT_NOTE_ID, next(note_ids))


def _saved_by_live_12(root):
    """Return whether a set's root element says Live 12 saved it."""
    return (root.get(Attribute.MAJOR_VERSION) == LIVE_MAJOR_VERSION
            and root.get(Attribute.MINOR_VERSION, NO_NAME).startswith(LIVE_12_MINOR_VERSION))


def _highest_id(elements):
    """Return the highest id among some elements, so that new ones can be numbered after it."""
    return max(int(element.get(Attribute.ID)) for element in elements)


def _renumber_shared_ids(element, next_shared_id):
    """Give every element inside a copied track that needs a set-wide id a new one, so none repeat."""
    for item in element.iter():
        if Attribute.ID in item.attrib and _SHARED_ID_TAGS.search(item.tag):
            item.set(Attribute.ID, str(next(next_shared_id)))


def _controller_ids(track):
    """Return the id of each CC number's controller target on a track, which a clip's CC envelope points at."""
    return {
        int(item.tag.split(TARGET_NUMBER_SEPARATOR)[1]) - FIRST_CC_TARGET: item.get(Attribute.ID)
        for item in track.find(ElementPath.CONTROLLERS)
    }


def _loop_settings(beats, loops):
    """Return a clip's loop settings, as (setting, value), for a clip that lasts some beats."""
    return [
        (LoopSetting.START, CLIP_START), (LoopSetting.END, beats), (LoopSetting.START_RELATIVE, CLIP_START),
        (LoopSetting.ON, _live_boolean(loops)), (LoopSetting.OUT_MARKER, beats),
        (LoopSetting.HIDDEN_START, CLIP_START), (LoopSetting.HIDDEN_END, beats),
    ]


def _envelope_points(lane):
    """Return the (time, value) points of one CC lane's envelope.

    Live draws a straight line between points, which is what a slide is. A value that doesn't
    slide holds until the next one, so it gets a second point there at the old value. The first
    value also holds from before the clip starts.
    """
    points = [(BEFORE_CLIP, lane[0][1])]
    for place, (time, value, _) in enumerate(lane):
        if place and not lane[place - 1][2]:
            points.append((_beats(time), lane[place - 1][1]))
        points.append((_beats(time), value))
    return points


def _pitches(notes):
    """Return each MIDI note number the notes use, lowest first, once each."""
    return sorted({midi_number for _, _, midi_number, _ in notes})
