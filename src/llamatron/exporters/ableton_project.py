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

import copy
import gzip
import itertools
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from llamatron.support.files import READ_BYTES, WRITE_BYTES
from llamatron.support.rational import Rational
from llamatron.exporters.exporter import Exporter, ExportKind, WritesOneFile
from llamatron.exporters.timing import BEATS_PER_WHOLE_NOTE, control_points, timed_events
from llamatron.strings.names import MSG_ABLETON_EXPORT_LABEL
from llamatron.strings.errors import ERR_BAD_TEMPLATE, ERR_BAD_TEMPO, ERR_EMPTY_SONG, ERR_FILE_EXISTS, ERR_NO_CLIP, ERR_NO_MIDI_TRACK, ERR_NOT_LIVE_12

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
# Live stores the set's time signature as one number: the beats counted from 0, plus this for each
# doubling of the bottom number, so 4/4 is 3 + 2 * 99 = 201 and 6/8 is 5 + 3 * 99 = 302, as a set
# saved by Live 12 shows.
LIVE_SIGNATURE_UNIT_STEP = 99
# Live sets made by Live 12 have this major version, and a minor version that starts with 12.
LIVE_MAJOR_VERSION = '5'
LIVE_12_MINOR_VERSION = '12.'
# Tracks and clips are numbered from 1 where Live shows them, and note ids start at 1.
FIRST_NUMBER = 1
# Where a clip in Session View starts, and where a clip's loop starts.
CLIP_START = 0
# A clip with nothing in it is EMPTY_CLIP_BEATS long, so Live shows something.
NO_LENGTH = 0
# How Live writes numbers in beats, and how the set's XML starts.
BEATS_FORMAT = '{beats:.17g}'
XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>\n'
XML_TEXT = 'unicode'
XML_BYTES = 'utf-8'
# A set is gzipped XML, written without a time stamp so the same song always gives the same file.
NO_TIME_STAMP = 0
SET_FILE = '{name}.als'
# A track with no name is named the way Live names a new MIDI track.
UNNAMED_TRACK = '{number}-MIDI'
NO_NAME = ''
# Live writes true and false in lower case.
LIVE_TRUE = 'true'
LIVE_FALSE = 'false'
# A controller target's tag ends in its number, like ControllerTargets.3.
TARGET_NUMBER_SEPARATOR = '.'


class Tag:
    """The names of the elements in a Live set that this exporter reads or writes."""

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
    TIME_SIGNATURE = 'DeviceChain/Mixer/TimeSignature'
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
    CLIP_SIGNATURE_BEATS = 'TimeSignature/TimeSignatures/RemoteableTimeSignature/Numerator'
    CLIP_SIGNATURE_UNIT = 'TimeSignature/TimeSignatures/RemoteableTimeSignature/Denominator'
    CLIP_ENVELOPES = 'Envelopes/Envelopes'
    KEY_TRACKS = 'KeyTracks'
    NEXT_NOTE_ID = 'NoteIdGenerator/NextId'


class Attribute:
    """The attributes of a Live set's elements that this exporter reads or writes."""

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


# Live gives these elements ids that must be unique across the whole set.
_SHARED_ID_TAGS = re.compile(r'(Target|Targets\.\d+|Pointee)$')


def _check_template(template):
    if not isinstance(template, (str, os.PathLike)) or not os.fspath(template):
        raise ValueError(ERR_BAD_TEMPLATE.format(value=template))


def _set_value(*, parent, path, value):
    parent.find(path).set(Attribute.VALUE, str(value))


def _beats(whole_notes):
    """Return a fraction of a whole note as beats, in the way Live writes numbers."""
    return BEATS_FORMAT.format(beats=float(whole_notes * BEATS_PER_WHOLE_NOTE))


def _live_time_signature(signature):
    """Return a time signature as the one number Live's main track holds it as."""
    doublings = signature.get_unit().bit_length() - 1
    return (signature.get_beats() - 1) + LIVE_SIGNATURE_UNIT_STEP * doublings


def _live_boolean(value):
    """Return true or false the way Live writes them."""
    return LIVE_TRUE if value else LIVE_FALSE


def _empty_clip_length():
    """Return how long a clip with nothing in it lasts in Arrangement View, in whole notes."""
    return Rational(EMPTY_CLIP_BEATS, BEATS_PER_WHOLE_NOTE)


def _remove_children(element):
    """Remove everything inside an element, leaving the element itself."""
    for child in list(element):
        element.remove(child)


class AbletonProject(WritesOneFile, Exporter):
    """Exports a ClipGrid as an Ableton Live 12 set, in both Session View and Arrangement View.

    In Session View, each scene and track slot holds its clip. In Arrangement View, the
    scenes play one after another from the start, each lasting as long as its longest clip.

    The set is written to <directory>/<name>.als, where the name is the directory's unless one is
    given, which the tracker and the command line do, and is built from a template
    saved by Live. Its first MIDI track, which must have a clip in it, is copied for each
    track in the song, along with any instruments on that track. The template's other MIDI
    and audio tracks are left out, and its return tracks are kept. Live's format isn't
    documented, so this only accepts templates from Live 12.

    """

    __slots__ = ('_template',)

    KIND = ExportKind.ABLETON
    LABEL = MSG_ABLETON_EXPORT_LABEL
    FILE = SET_FILE

    def __init__(self, *, directory, grid, template=DEFAULT_TEMPLATE, name=None):
        super().__init__(directory=directory, grid=grid, name=name)
        _check_template(template)
        self._template = template

    @classmethod
    def for_song(cls, *, directory, grid, name, template=None):
        """Return the exporter of a played song as a Live set, built from a template, or the one that comes with the program."""
        return cls(directory=directory, grid=grid, name=name, template=template or DEFAULT_TEMPLATE)

    def get_template(self):
        return self._template

    def export(self):
        """Write the set, leaving any other files in the directory in place.

        If the set already exists, this prints a warning and stops without writing anything.
        """
        os.makedirs(self._directory, exist_ok=True)
        if os.path.exists(self.path()):
            print(ERR_FILE_EXISTS.format(path=self.path()))
            return

        # Built before anything is written, so that an invalid clip doesn't leave a broken file.
        contents = gzip.compress(self._build(), mtime=NO_TIME_STAMP)
        with open(self.path(), WRITE_BYTES) as file:
            file.write(contents)

    def _build(self):
        """Return the XML of the finished set as bytes."""
        self._check_song_fits_live()
        with open(self._template, READ_BYTES) as file:
            root = ET.fromstring(gzip.decompress(file.read()))
        if not _saved_by_live_12(root):
            raise ValueError(ERR_NOT_LIVE_12.format(template=self._template, attributes=root.attrib))

        live_set = root.find(Tag.LIVE_SET)
        next_shared_id = itertools.count(int(live_set.find(Tag.NEXT_POINTEE_ID).get(Attribute.VALUE)))
        starts = self._scene_starts()
        self._set_tempo(live_set=live_set, starts=starts)
        self._set_time_signature(live_set)
        self._build_scenes(live_set)
        self._build_tracks(live_set=live_set, next_shared_id=next_shared_id, starts=starts)
        _set_value(parent=live_set, path=Tag.NEXT_POINTEE_ID, value=next(next_shared_id))

        xml = ET.tostring(root, encoding=XML_TEXT)
        return (XML_DECLARATION + xml).encode(XML_BYTES)

    def _check_song_fits_live(self):
        if not self._grid.get_rows() or not self._grid.get_columns():
            raise ValueError(ERR_EMPTY_SONG)
        for tempo in [self._grid.get_tempo()] + [scene.get_tempo() for scene in self._grid.get_rows()]:
            if tempo is not None and not MIN_LIVE_TEMPO <= tempo <= MAX_LIVE_TEMPO:
                raise ValueError(ERR_BAD_TEMPO.format(lowest=MIN_LIVE_TEMPO, highest=MAX_LIVE_TEMPO, value=tempo))

    def _scene_starts(self):
        """Return when each scene starts in Arrangement View, in fractions of a whole note."""
        starts = []
        now = Rational(CLIP_START)
        for scene in self._grid.get_rows():
            starts.append(now)
            now += self._grid.row_length(scene) or _empty_clip_length()
        return starts

    def _set_tempo(self, *, live_set, starts):
        """Set the tempo control and its automation, with changes for any scene tempos."""
        main_track = live_set.find(Tag.MAIN_TRACK)
        tempo = main_track.find(ElementPath.TEMPO)
        _set_value(parent=tempo, path=ElementPath.MANUAL, value=self._grid.get_tempo())
        target = tempo.find(ElementPath.AUTOMATION_TARGET).get(Attribute.ID)
        for envelope in main_track.find(ElementPath.ENVELOPES):
            if envelope.find(ElementPath.ENVELOPE_POINTEE).get(Attribute.VALUE) == target:
                events = envelope.find(ElementPath.AUTOMATION_EVENTS)
                for event in events:
                    event.set(Attribute.VALUE, str(self._grid.get_tempo()))
                if any(scene.get_tempo() is not None for scene in self._grid.get_rows()):
                    self._add_tempo_changes(events=events, starts=starts)

    def _set_time_signature(self, live_set):
        """Set the time signature control and its automation, so that Live draws the song's bars."""
        main_track = live_set.find(Tag.MAIN_TRACK)
        signature = main_track.find(ElementPath.TIME_SIGNATURE)
        code = _live_time_signature(self._grid.get_time_signature())
        _set_value(parent=signature, path=ElementPath.MANUAL, value=code)
        target = signature.find(ElementPath.AUTOMATION_TARGET).get(Attribute.ID)
        for envelope in main_track.find(ElementPath.ENVELOPES):
            if envelope.find(ElementPath.ENVELOPE_POINTEE).get(Attribute.VALUE) == target:
                for event in envelope.find(ElementPath.AUTOMATION_EVENTS):
                    event.set(Attribute.VALUE, str(code))

    def _add_tempo_changes(self, *, events, starts):
        next_id = len(events)
        for offset, (scene, start) in enumerate(zip(self._grid.get_rows(), starts)):
            ET.SubElement(events, Tag.FLOAT_EVENT, {
                Attribute.ID: str(next_id + offset),
                Attribute.TIME: _beats(start),
                Attribute.VALUE: str(self._grid.get_tempo() if scene.get_tempo() is None else scene.get_tempo()),
            })

    def _build_scenes(self, live_set):
        scenes = live_set.find(Tag.SCENES)
        prototype = scenes[0]
        scenes[:] = [self._build_scene(prototype=prototype, scene=scene) for scene in self._grid.get_rows()]

    def _build_scene(self, *, prototype, scene):
        element = copy.deepcopy(prototype)
        element.set(Attribute.ID, str(scene.get_id()))
        _set_value(parent=element, path=ElementPath.NAME, value=scene.get_name() or NO_NAME)
        tempo_is_set = scene.get_tempo() is not None
        _set_value(parent=element, path=ElementPath.SCENE_TEMPO, value=scene.get_tempo() if tempo_is_set else self._grid.get_tempo())
        _set_value(parent=element, path=ElementPath.TEMPO_ENABLED, value=_live_boolean(tempo_is_set))
        return element

    def _build_tracks(self, *, live_set, next_shared_id, starts):
        tracks = live_set.find(Tag.TRACKS)
        midi_tracks = tracks.findall(Tag.MIDI_TRACK)
        if not midi_tracks:
            raise ValueError(ERR_NO_MIDI_TRACK.format(template=self._template))
        clip_prototype = self._find_clip(midi_tracks[0])
        colors = [track.find(ElementPath.COLOR).get(Attribute.VALUE) for track in midi_tracks]
        next_track_id = itertools.count(_highest_id(tracks) + 1)

        built = []
        for number, track in enumerate(self._grid.get_columns()):
            color = colors[number % len(colors)]
            built.append(self._build_track(prototype=midi_tracks[0], clip_prototype=clip_prototype, track=track, number=number, color=color, track_id=next(next_track_id), next_shared_id=next_shared_id, starts=starts))
        tracks[:] = built + tracks.findall(Tag.RETURN_TRACK)

    def _find_clip(self, track):
        for clip in track.find(ElementPath.CLIP_SLOTS).iter(Tag.MIDI_CLIP):
            return clip
        raise ValueError(ERR_NO_CLIP.format(template=self._template))

    def _build_track(self, *, prototype, clip_prototype, track, number, color, track_id, next_shared_id, starts):
        element = copy.deepcopy(prototype)
        element.set(Attribute.ID, str(track_id))
        _renumber_shared_ids(element=element, next_shared_id=next_shared_id)

        _set_value(parent=element, path=ElementPath.EFFECTIVE_NAME, value=track.get_name() or UNNAMED_TRACK.format(number=number + FIRST_NUMBER))
        _set_value(parent=element, path=ElementPath.USER_NAME, value=track.get_name() or NO_NAME)
        _set_value(parent=element, path=ElementPath.COLOR, value=color)
        _set_value(parent=element, path=ElementPath.SPEAKER, value=_live_boolean(not track.get_mute()))

        controllers = _controller_ids(element)
        clips = [self._grid.get_clip(row=scene, column=track) for scene in self._grid.get_rows()]
        slots = element.find(ElementPath.CLIP_SLOTS)
        empty_slot = self._empty_slot(slots[0])
        slots[:] = [
            self._build_slot(empty_slot=empty_slot, clip_prototype=clip_prototype, clip=clip, scene=scene, track=track, place=place, color=color, controllers=controllers)
            for place, (scene, clip) in enumerate(zip(self._grid.get_rows(), clips))
        ]
        frozen_slots = element.find(ElementPath.FROZEN_CLIP_SLOTS)
        frozen_slots[:] = [self._numbered_copy(element=empty_slot, number=place) for place in range(len(self._grid.get_rows()))]
        arrangement = element.find(ElementPath.ARRANGEMENT_EVENTS)
        arrangement[:] = self._arrangement_clips(clip_prototype=clip_prototype, clips=clips, track=track, color=color, controllers=controllers, starts=starts)
        return element

    def _arrangement_clips(self, *, clip_prototype, clips, track, color, controllers, starts):
        """Return the clips of a track in Arrangement View, each at the time its scene starts."""
        return [
            self._build_clip(prototype=clip_prototype, clip=clip, scene=scene, track=track, place=place, color=color, controllers=controllers, start=start)
            for place, (scene, clip, start) in enumerate(zip(self._grid.get_rows(), clips, starts))
            if clip is not None
        ]

    def _empty_slot(self, slot):
        empty = copy.deepcopy(slot)
        _remove_children(empty.find(ElementPath.SLOT_VALUE))
        return empty

    def _numbered_copy(self, *, element, number):
        result = copy.deepcopy(element)
        result.set(Attribute.ID, str(number))
        return result

    def _build_slot(self, *, empty_slot, clip_prototype, clip, scene, track, place, color, controllers):
        slot = self._numbered_copy(element=empty_slot, number=place)
        if clip is not None:
            slot.find(ElementPath.SLOT_VALUE).append(
                self._build_clip(prototype=clip_prototype, clip=clip, scene=scene, track=track, place=place, color=color, controllers=controllers)
            )
        return slot

    def _build_clip(self, *, prototype, clip, scene, track, place, color, controllers, start=None):
        notes, length = timed_events(clip=clip, scale=self._grid.scale_at(row=scene, column=track))
        beats = _beats(length) if length > NO_LENGTH else str(EMPTY_CLIP_BEATS)

        element = copy.deepcopy(prototype)
        element.set(Attribute.ID, str(place))
        _set_value(parent=element, path=ElementPath.NAME, value=clip.get_name() or NO_NAME)
        _set_value(parent=element, path=ElementPath.COLOR, value=color)
        if start is None:
            element.set(Attribute.TIME, str(CLIP_START))
            _set_value(parent=element, path=ElementPath.CURRENT_START, value=CLIP_START)
            _set_value(parent=element, path=ElementPath.CURRENT_END, value=beats)
        else:
            end = start + (length if length > NO_LENGTH else _empty_clip_length())
            element.set(Attribute.TIME, _beats(start))
            _set_value(parent=element, path=ElementPath.CURRENT_START, value=_beats(start))
            _set_value(parent=element, path=ElementPath.CURRENT_END, value=_beats(end))
            _set_value(parent=element, path=ElementPath.TAKE_ID, value=ARRANGEMENT_TAKE_ID)
        for setting, value in _loop_settings(beats=beats, loops=clip.get_loop()):
            _set_value(parent=element, path=ElementPath.LOOP.format(setting=setting), value=value)
        # The template's clip uses a groove, which would move the notes off their times, and its
        # key, which wouldn't match this clip's scale.
        _set_value(parent=element, path=ElementPath.GROOVE, value=NO_GROOVE)
        _set_value(parent=element, path=ElementPath.IN_KEY, value=LIVE_FALSE)
        # The clip's grid follows its pattern's time signature, if it has one, and otherwise the song's.
        signature = clip.get_time_signature() or self._grid.get_time_signature()
        _set_value(parent=element, path=ElementPath.CLIP_SIGNATURE_BEATS, value=signature.get_beats())
        _set_value(parent=element, path=ElementPath.CLIP_SIGNATURE_UNIT, value=signature.get_unit())
        self._write_notes(element=element.find(ElementPath.NOTES), notes=notes)
        self._write_envelopes(envelopes=element.find(ElementPath.CLIP_ENVELOPES), clip=clip, length=length, controllers=controllers)
        return element

    def _write_envelopes(self, *, envelopes, clip, length, controllers):
        """Write one clip envelope for each CC number the clip sends."""
        _remove_children(envelopes)
        for envelope_id, (number, lane) in enumerate(sorted(control_points(clip=clip, length=length).items())):
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

    def _write_notes(self, *, element, notes):
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
        _set_value(parent=element, path=ElementPath.NEXT_NOTE_ID, value=next(note_ids))


def _saved_by_live_12(root):
    """Return whether a set's root element says Live 12 saved it."""
    return (root.get(Attribute.MAJOR_VERSION) == LIVE_MAJOR_VERSION
            and root.get(Attribute.MINOR_VERSION, NO_NAME).startswith(LIVE_12_MINOR_VERSION))


def _highest_id(elements):
    """Return the highest id among some elements, so that new ones can be numbered after it."""
    return max(int(element.get(Attribute.ID)) for element in elements)


def _renumber_shared_ids(*, element, next_shared_id):
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


def _loop_settings(*, beats, loops):
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
