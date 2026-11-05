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

import copy
import gzip
import itertools
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from src.renderers.clip_tree import _check_directory, _check_song
from src.renderers.timing import BEATS_PER_WHOLE_NOTE, VELOCITY, timed_notes
from src.song import _Validated

DEFAULT_TEMPLATE = Path(__file__).resolve().parents[2] / 'live12 Project' / 'live12.als'

MIN_LIVE_TEMPO = 20
MAX_LIVE_TEMPO = 999
EMPTY_CLIP_BEATS = 4
NOTE_OFF_VELOCITY = 64
NO_GROOVE = '-1'

# Live gives these elements ids that must be unique across the whole set.
_SHARED_ID_TAGS = re.compile(r'(Target|Targets\.\d+|Pointee)$')


def _check_template(template):
    if not isinstance(template, (str, os.PathLike)) or not os.fspath(template):
        raise ValueError(f'invalid template: {template!r}')


def _set_value(parent, path, value):
    parent.find(path).set('Value', str(value))


def _beats(whole_notes):
    """Return a fraction of a whole note as beats, in the way Live writes numbers."""
    return f'{float(whole_notes * BEATS_PER_WHOLE_NOTE):.17g}'


class AbletonProject:
    """Renders a Song as an Ableton Live 12 set, with its clips in Session View.

    The set is written to <directory>/<directory name>.als, and is built from a template
    saved by Live. Its first MIDI track, which must have a clip in it, is copied for each
    track in the song, along with any instruments on that track. The template's other MIDI
    and audio tracks are left out, and its return tracks are kept. Live's format isn't
    documented, so this only accepts templates from Live 12.
    """

    directory = _Validated(_check_directory)
    song = _Validated(_check_song)
    template = _Validated(_check_template)

    def __init__(self, directory, song, template=DEFAULT_TEMPLATE):
        self.directory = directory
        self.song = song
        self.template = template

    @property
    def path(self):
        """Where the set will be written."""
        name = os.path.basename(os.path.abspath(self.directory))
        return os.path.join(self.directory, f'{name}.als')

    def render(self):
        """Write the set, leaving any other files in the directory in place.

        If the set already exists, this prints a warning and stops without writing anything.
        """
        os.makedirs(self.directory, exist_ok=True)
        filename = os.path.basename(self.path)
        existing = sorted(os.listdir(self.directory))
        if filename in existing:
            print(f'warning: stopping without writing anything, because {self.path} already exists')
            return
        if existing:
            print(
                f'warning: {os.fspath(self.directory)} already contains '
                f'{len(existing)} other item(s), which will not be deleted: {", ".join(existing)}'
            )

        # Built before anything is written, so that an invalid clip doesn't leave a broken file.
        contents = gzip.compress(self._build(), mtime=0)
        with open(self.path, 'wb') as file:
            file.write(contents)

    def _build(self):
        """Return the XML of the finished set as bytes."""
        self._check_song_fits_live()
        with open(self.template, 'rb') as file:
            root = ET.fromstring(gzip.decompress(file.read()))
        if root.get('MajorVersion') != '5' or not root.get('MinorVersion', '').startswith('12.'):
            raise ValueError(f'{self.template} was not saved by Live 12: {root.attrib}')

        live_set = root.find('LiveSet')
        next_shared_id = itertools.count(int(live_set.find('NextPointeeId').get('Value')))
        self._set_tempo(live_set)
        self._build_scenes(live_set)
        self._build_tracks(live_set, next_shared_id)
        _set_value(live_set, 'NextPointeeId', next(next_shared_id))

        xml = ET.tostring(root, encoding='unicode')
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml}'.encode('utf-8')

    def _check_song_fits_live(self):
        if not self.song.scenes or not self.song.tracks:
            raise ValueError('a Live set needs at least one scene and one track')
        for tempo in [self.song.tempo] + [scene.tempo for scene in self.song.scenes]:
            if tempo is not None and not MIN_LIVE_TEMPO <= tempo <= MAX_LIVE_TEMPO:
                raise ValueError(
                    f'Live needs a tempo from {MIN_LIVE_TEMPO} to {MAX_LIVE_TEMPO}, got {tempo!r}'
                )

    def _set_tempo(self, live_set):
        """Set the song's tempo on the tempo control, and on the automation that drives it."""
        main_track = live_set.find('MainTrack')
        tempo = main_track.find('DeviceChain/Mixer/Tempo')
        _set_value(tempo, 'Manual', self.song.tempo)
        target = tempo.find('AutomationTarget').get('Id')
        for envelope in main_track.find('AutomationEnvelopes/Envelopes'):
            if envelope.find('EnvelopeTarget/PointeeId').get('Value') == target:
                for event in envelope.find('Automation/Events'):
                    event.set('Value', str(self.song.tempo))

    def _build_scenes(self, live_set):
        scenes = live_set.find('Scenes')
        prototype = scenes[0]
        scenes[:] = [self._build_scene(prototype, scene) for scene in self.song.scenes]

    def _build_scene(self, prototype, scene):
        element = copy.deepcopy(prototype)
        element.set('Id', str(scene.id))
        _set_value(element, 'Name', scene.name or '')
        tempo_is_set = scene.tempo is not None
        _set_value(element, 'Tempo', scene.tempo if tempo_is_set else self.song.tempo)
        _set_value(element, 'IsTempoEnabled', str(tempo_is_set).lower())
        return element

    def _build_tracks(self, live_set, next_shared_id):
        tracks = live_set.find('Tracks')
        midi_tracks = tracks.findall('MidiTrack')
        if not midi_tracks:
            raise ValueError(f'{self.template} needs a MIDI track to copy')
        clip_prototype = self._find_clip(midi_tracks[0])
        colors = [track.find('Color').get('Value') for track in midi_tracks]
        next_track_id = itertools.count(max(int(track.get('Id')) for track in tracks) + 1)

        built = [
            self._build_track(
                midi_tracks[0], clip_prototype, track, number,
                colors[number % len(colors)], next(next_track_id), next_shared_id,
            )
            for number, track in enumerate(self.song.tracks)
        ]
        tracks[:] = built + tracks.findall('ReturnTrack')

    def _find_clip(self, track):
        for clip in track.find('DeviceChain/MainSequencer/ClipSlotList').iter('MidiClip'):
            return clip
        raise ValueError(
            f'the first MIDI track in {self.template} needs a clip in it, because Live '
            'requires many details in a clip that are copied from there'
        )

    def _build_track(self, prototype, clip_prototype, track, number, color, track_id, next_shared_id):
        element = copy.deepcopy(prototype)
        element.set('Id', str(track_id))
        for item in element.iter():
            if 'Id' in item.attrib and _SHARED_ID_TAGS.search(item.tag):
                item.set('Id', str(next(next_shared_id)))

        _set_value(element, 'Name/EffectiveName', track.name or f'{number + 1}-MIDI')
        _set_value(element, 'Name/UserName', track.name or '')
        _set_value(element, 'Color', color)

        clips = [self.song.get_clip(scene, track) for scene in self.song.scenes]
        slots = element.find('DeviceChain/MainSequencer/ClipSlotList')
        empty_slot = self._empty_slot(slots[0])
        slots[:] = [
            self._build_slot(empty_slot, clip_prototype, clip, scene, track, place, color)
            for place, (scene, clip) in enumerate(zip(self.song.scenes, clips))
        ]
        frozen_slots = element.find('DeviceChain/FreezeSequencer/ClipSlotList')
        frozen_slots[:] = [
            self._numbered_copy(empty_slot, place) for place in range(len(self.song.scenes))
        ]
        return element

    def _empty_slot(self, slot):
        empty = copy.deepcopy(slot)
        value = empty.find('ClipSlot/Value')
        for child in list(value):
            value.remove(child)
        return empty

    def _numbered_copy(self, element, number):
        result = copy.deepcopy(element)
        result.set('Id', str(number))
        return result

    def _build_slot(self, empty_slot, clip_prototype, clip, scene, track, place, color):
        slot = self._numbered_copy(empty_slot, place)
        if clip is not None:
            slot.find('ClipSlot/Value').append(
                self._build_clip(clip_prototype, clip, scene, track, place, color)
            )
        return slot

    def _build_clip(self, prototype, clip, scene, track, place, color):
        notes, length = timed_notes(clip, self.song.scale_at(scene, track))
        beats = _beats(length) if length > 0 else str(EMPTY_CLIP_BEATS)

        element = copy.deepcopy(prototype)
        element.set('Id', str(place))
        element.set('Time', '0')
        _set_value(element, 'Name', clip.name or '')
        _set_value(element, 'Color', color)
        _set_value(element, 'CurrentStart', 0)
        _set_value(element, 'CurrentEnd', beats)
        for path, value in [
            ('LoopStart', 0), ('LoopEnd', beats), ('StartRelative', 0), ('LoopOn', 'true'),
            ('OutMarker', beats), ('HiddenLoopStart', 0), ('HiddenLoopEnd', beats),
        ]:
            _set_value(element, f'Loop/{path}', value)
        # The template's clip uses a groove, which would move the notes off their times, and its
        # key, which wouldn't match this clip's scale.
        _set_value(element, 'GrooveSettings/GrooveId', NO_GROOVE)
        _set_value(element, 'IsInKey', 'false')
        self._write_notes(element.find('Notes'), notes)
        return element

    def _write_notes(self, element, notes):
        key_tracks = element.find('KeyTracks')
        for child in list(key_tracks):
            key_tracks.remove(child)

        note_ids = itertools.count(1)
        pitches = sorted({midi_number for _, _, midi_number in notes})
        for key_id, pitch in enumerate(pitches):
            key_track = ET.SubElement(key_tracks, 'KeyTrack', Id=str(key_id))
            events = ET.SubElement(key_track, 'Notes')
            for start, end, midi_number in sorted(notes):
                if midi_number == pitch:
                    ET.SubElement(events, 'MidiNoteEvent', {
                        'Time': _beats(start),
                        'Duration': _beats(end - start),
                        'Velocity': str(VELOCITY),
                        'OffVelocity': str(NOTE_OFF_VELOCITY),
                        'NoteId': str(next(note_ids)),
                    })
            ET.SubElement(key_track, 'MidiKey', Value=str(pitch))
        _set_value(element, 'NoteIdGenerator/NextId', next(note_ids))
