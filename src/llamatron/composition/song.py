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
"""One song of a set: its tempo, scale, seed, registers, tracks and scenes.

A song arranges the set's patterns on its own tracks, scene by scene, and plays them in its own
scale and tempo. What it shares with the other songs in the set (the scales, patterns,
generators, chains and the settings for reading and showing patterns) it reads through its
setlist, so everything that plays or edits a song asks the song, and needn't know which object
holds what. Its tracks and registers are changed the same way as the set's sections: add_item,
remove_item, rename_item and so on, and renaming or removing a track tells the scenes.
"""

from llamatron.composition.checks import check_keys, is_whole_number, listed, number, reading, time_signature, written_length
from llamatron.composition.limits import MAX_GATE
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.groove import groove_for
from llamatron.composition.defaults import DEFAULT_GROOVE, DEFAULT_LIVE_RESPONSIVENESS, DEFAULT_SEED, DEFAULT_TEMPO, DEFAULT_TIME_SIGNATURE, FIRST_NUMBER
from llamatron.composition.corrections import LEFT_OUT
from llamatron.composition.setting import Checked, Choice, Length, described, settings_held, Text
from llamatron.composition.file_format import LIVE_RESPONSIVENESSES, REGISTER_NAMES, sensible_visualizer, GeneratorKind, SceneSetting, Section, SongSetting
from llamatron.composition.llama_data import LlamaData, data_as_kept, data_built_anew, or_default, written_settings
from llamatron.composition.named_items import NamedItems, moved_in_list
from llamatron.composition.register import Register
from llamatron.composition.scene import Scene
from llamatron.composition.sections import SECTION_LABELS, SONG_SECTIONS
from llamatron.composition.track import Track
from llamatron.strings.errors import (
    ERR_BAD_LIVE_RESPONSIVENESS, ERR_NOT_TEXT, ERR_NO_SUCH_REGISTER, ERR_NO_SUCH_SCENE, ERR_NOT_A_SONG, ERR_REGISTERS_NOT_NAMED, ERR_SONG_NO_SUCH_GROOVE,
    ERR_SCENES_NOT_A_LIST, ERR_SONG_BAD_SEED, ERR_SONG_NO_SUCH_SCALE, ERR_TRACKS_NOT_NAMED, ERR_WHERE_NAMED, ERR_WHERE_SCENE_ENTRY,
    ERR_WHERE_WITHIN,
)
from llamatron.strings.names import MSG_NEW_SCENE_NAME, MSG_NEW_TRACK_NAME, MSG_REGISTER_WORD, MSG_THE_FILE, MSG_TRACK_WORD
from llamatron.support.revised import notes_change



def _check_scale_name(*, value, song):
    """Refuse a scale the set doesn't have. None is no scale."""
    if value is not None and not song.has_scale(value):
        raise InvalidValue(ERR_SONG_NO_SUCH_SCALE.format(scale=value))


def _check_groove_name(*, value, song):
    """Refuse a groove that is neither a factory groove nor one of the set's."""
    if not isinstance(value, str) or not song.has_groove(value):
        raise InvalidValue(ERR_SONG_NO_SUCH_GROOVE.format(name=value))


def seed_number(value):
    """Return a seed, checking that it's an integer or None, which means a new take each export."""
    if value is not None and not is_whole_number(value):
        raise InvalidValue(ERR_SONG_BAD_SEED.format(value=value))
    return value


# The song's own settings, each described once, in the order they're written to a file.
def _never_refused(value):
    """Refuse nothing: a visualizer setting that makes no sense is made sensible as it's read (sensible_visualizer), the user's rule."""


SETTINGS = described(
    Checked(name=SongSetting.TEMPO, check=number),
    Checked(name=SongSetting.TIME_SIGNATURE, check=time_signature),
    Length(name=SongSetting.ENTRY_SIZE, most=MAX_GATE, blank_allowed=True),
    Checked(name=SongSetting.SCALE, check=_check_scale_name, needs_song=True),
    Checked(name=SongSetting.SEED, check=seed_number),
    Checked(name=SongSetting.GROOVE, check=_check_groove_name, needs_song=True),
    Text(name=SongSetting.GENRE, error=ERR_NOT_TEXT),
    Choice(name=SongSetting.LIVE_RESPONSIVENESS, choices=LIVE_RESPONSIVENESSES, default=LEFT_OUT, error=ERR_BAD_LIVE_RESPONSIVENESS),
    Checked(name=SongSetting.VISUALIZER, check=_never_refused),
)
# The settings whose message names the setting itself, so that a file's problem with one is placed at the song alone, like "song (verse): scale: ...".
NAMED_BY_THEIR_MESSAGE = (SongSetting.SCALE, SongSetting.GROOVE)
# Scenes are counted from 1 in messages, as they're shown.
FIRST_SCENE_NUMBER = 1
# What a song that says nothing of its genre gives.
NO_GENRE = ''


def new_song(*, scale=None):
    """Return the data of a new song: empty, at the default tempo, in a scale of the set's if one is named.

    This is also what a file that leaves settings out gets, so it holds no tracks or scenes: an empty
    file is an empty song.
    """
    data = {SongSetting.TEMPO: DEFAULT_TEMPO}
    if scale is not None:
        data[SongSetting.SCALE] = scale
    data[Section.TRACKS] = {}
    data[Section.SCENES] = []
    return data


def started_song(*, scale=None):
    """Return the data of a song to start composing in: a new song with its first track and scene, numbered 1."""
    data = new_song(scale=scale)
    data[Section.TRACKS] = {MSG_NEW_TRACK_NAME.format(number=FIRST_NUMBER): {}}
    data[Section.SCENES] = [{SceneSetting.NAME: MSG_NEW_SCENE_NAME.format(number=FIRST_NUMBER)}]
    return data


# A count of steps is whole when the division leaves this denominator.
WHOLE_STEPS = 1


class Song(LlamaData):
    """One song: its settings, registers, tracks and scenes, reading what it shares from its setlist.

    Settings the file leaves out are kept as None and mean their defaults, and so do sections it
    leaves out, so that saving writes back only what was there.
    """

    __slots__ = ('_setlist', '_settings', '_sections', '_scenes')

    # A song names its own scale and groove. Its scenes and tracks name things too, and are its referring parts.
    REFERENCES = {Section.SCALES: (SongSetting.SCALE,), Section.GROOVES: (SongSetting.GROOVE,)}

    def __init__(self, *, setlist):
        self.note_change()
        self._setlist = setlist
        self._settings = {name: None for name in SETTINGS}
        self._sections = {name: NamedItems(label=SECTION_LABELS[name]) for name in SONG_SECTIONS}
        self._scenes = None

    @classmethod
    def new(cls, *, setlist):
        """Return an empty song for a set, in the set's first scale if it has one."""
        return cls.from_data(data=new_song(scale=setlist.first_scale_name()), where=MSG_THE_FILE, setlist=setlist)

    @classmethod
    def started(cls, *, setlist):
        """Return a song to start composing in, with its first track and scene, in the set's first scale if it has one."""
        return cls.from_data(data=started_song(scale=setlist.first_scale_name()), where=MSG_THE_FILE, setlist=setlist)

    @classmethod
    def from_data(cls, *, data, where, setlist):
        """Read one song's data, checking every part of it, placing each error inside the song."""
        data = {} if data is None else data
        with reading(where):
            if not isinstance(data, dict):
                raise InvalidValue(ERR_NOT_A_SONG.format(value=data))
            check_keys(data=data, allowed={*SETTINGS, *SONG_SECTIONS, Section.SCENES})
        song = cls(setlist=setlist)
        song._read_settings(data=data, where=where)
        song._read_registers(data=data, where=where)
        song._read_tracks(data=data, where=where)
        song._read_scenes(data=data, where=where)
        return song

    @notes_change
    def _read_settings(self, *, data, where):
        for setting in settings_held(settings=SETTINGS, data=data):
            name = setting.get_name()
            with reading(where if name in NAMED_BY_THEIR_MESSAGE else ERR_WHERE_WITHIN.format(where=where, part=name)):
                setting.check_held(data, song=self)
        self._settings = {name: data.get(name) for name in SETTINGS}
        self._settings[SongSetting.VISUALIZER] = sensible_visualizer(self._settings[SongSetting.VISUALIZER])

    def _read_registers(self, *, data, where):
        """Read the registers' settings. There are always four, so the file only names those it changes."""
        registers = data.get(Section.REGISTERS) or {}
        with reading(where):
            if not isinstance(registers, dict) or not set(registers) <= set(REGISTER_NAMES):
                raise InvalidValue(ERR_REGISTERS_NOT_NAMED.format(names=listed(REGISTER_NAMES)))
        if Section.REGISTERS in data:
            self._set_section(section=Section.REGISTERS, items={
                name: Register.from_data(data=settings, where=self._where(where=where, label=MSG_REGISTER_WORD, name=name)) for name, settings in registers.items()
            })

    def _read_tracks(self, *, data, where):
        tracks = data.get(Section.TRACKS) or {}
        with reading(where):
            if not isinstance(tracks, dict):
                raise InvalidValue(ERR_TRACKS_NOT_NAMED)
        if Section.TRACKS in data:
            self._set_section(section=Section.TRACKS, items={
                name: Track.from_data(data=settings, where=self._where(where=where, label=MSG_TRACK_WORD, name=name), song=self) for name, settings in tracks.items()
            })

    @notes_change
    def _read_scenes(self, *, data, where):
        scenes = data.get(Section.SCENES) or []
        with reading(where):
            if not isinstance(scenes, list):
                raise InvalidValue(ERR_SCENES_NOT_A_LIST)
        self._scenes = None if Section.SCENES not in data else [
            Scene.from_data(data=scene, where=ERR_WHERE_WITHIN.format(where=where, part=ERR_WHERE_SCENE_ENTRY.format(number=number)), song=self)
            for number, scene in enumerate(scenes, start=FIRST_SCENE_NUMBER)
        ]

    def _where(self, *, where, label, name):
        """Return how a message places one of the song's named items, like song (one), track (bass)."""
        return ERR_WHERE_WITHIN.format(where=where, part=ERR_WHERE_NAMED.format(label=label, name=name))

    @notes_change
    def _set_section(self, *, section, items):
        """Give a section its items as read from the file, or None for a section the file leaves out."""
        self._sections[section] = NamedItems(label=SECTION_LABELS[section], items=items)

    def _section(self, section):
        return self._sections[section]

    def to_data(self):
        return self._data_from(data_built_anew)

    def kept_data(self):
        """Return the song's data with each track's, register's and scene's as that part keeps it, put together each time, since a part changes without its song changing."""
        return self._data_from(data_as_kept)

    def _data_from(self, part_data):
        data = written_settings(self._settings)
        for section, items in self._sections.items():
            if items.is_written():
                data[section] = items.data_from(part_data)
        if self._scenes is not None:
            data[Section.SCENES] = [part_data(scene) for scene in self._scenes]
        return data

    def copy(self):
        """Return a copy of the song, in the same set."""
        return Song.from_data(data=self.to_data(), where=MSG_THE_FILE, setlist=self._setlist)

    @notes_change
    def fill_in_defaults(self):
        """Give every setting and section a new song has a value where a file left it out, so that saving writes them.

        The scale stays as it is, because a file without one has no scale, rather than the one a
        new song starts in.
        """
        for name, value in new_song().items():
            if name in self._settings and self._settings[name] is None:
                self._settings[name] = value
        for items in self._sections.values():
            items.fill_in()
        if self._scenes is None:
            self._scenes = []

    def get_setlist(self):
        """Return the set this song belongs to."""
        return self._setlist

    # The song's own settings, with their defaults.

    def get_tempo(self):
        """Return the song's tempo in quarter notes a minute, as an exact number."""
        return number(self._setting(name=SongSetting.TEMPO, default=DEFAULT_TEMPO))

    def get_time_signature(self):
        """Return the song's time signature, 4/4 unless the file sets one, which only changes what's drawn."""
        return time_signature(self._setting(name=SongSetting.TIME_SIGNATURE, default=DEFAULT_TIME_SIGNATURE))

    def steps_in_a_bar(self):
        """Return how many steps of the set's step size make one bar of this song's time signature, or None if a bar isn't whole steps.

        A new pattern is this long, so that a pattern in 3/4 starts as 12 sixteenths rather than
        16, as the user asked on 2026-11-07. 7/8 at a 1/4 step is three and a half steps, so None.
        """
        steps = self.get_time_signature().bar_length() / self._setlist.get_step_size()
        return steps.numerator if steps.denominator == WHOLE_STEPS else None

    def get_pattern_time_signature(self, pattern):
        """Return the time signature a pattern is drawn in: its own, or else the song's."""
        return pattern.get_time_signature() or self.get_time_signature()

    def get_entry_size(self):
        """Return how long a note placed on a piano roll lasts unless the pattern says otherwise, in whole notes, or None for one step."""
        entry_size = self.get_written_entry_size()
        return None if entry_size is None else written_length(value=entry_size, most=MAX_GATE)

    def get_written_entry_size(self):
        """Return the song's entry size as the file writes it, like 1/8, or None for one step."""
        return self._settings[SongSetting.ENTRY_SIZE]

    def entry_size_for(self, pattern):
        """Return how long a note placed on a pattern's piano roll lasts: the pattern's own entry size, else the song's, else one of its steps."""
        return pattern.get_entry_size() or self.get_entry_size() or self.get_pattern_step_size(pattern)

    def get_seed(self):
        """Return the seed every random choice is made from, or None, which makes every export a new take."""
        return self._setting(name=SongSetting.SEED, default=DEFAULT_SEED)

    def get_scale_name(self):
        """Return the name of the song's scale, or None if it has none."""
        return self._settings[SongSetting.SCALE]

    def get_live_responsiveness(self):
        """Return when an edit made while the song plays is heard: next_bar unless the song says."""
        return self._setting(name=SongSetting.LIVE_RESPONSIVENESS, default=DEFAULT_LIVE_RESPONSIVENESS)

    @notes_change
    def set_live_responsiveness(self, value):
        SETTINGS[SongSetting.LIVE_RESPONSIVENESS].check(value)
        self._settings[SongSetting.LIVE_RESPONSIVENESS] = value

    def get_visualizer(self):
        """Return the visualizer mode Arrange's visualizer key shows first for this song, by its name, or None to take the set's."""
        return self._settings[SongSetting.VISUALIZER]

    @notes_change
    def set_visualizer(self, name):
        """Name the visualizer mode shown first for this song, or None to take the set's; a name that isn't a mode's is None."""
        self._settings[SongSetting.VISUALIZER] = sensible_visualizer(name)

    def get_groove_name(self):
        """Return the name of the groove every clip takes unless its scene or track chooses otherwise: none by default."""
        return self._setting(name=SongSetting.GROOVE, default=DEFAULT_GROOVE)

    @notes_change
    def set_groove_name(self, name):
        """Give the song a groove by name, which can be a factory groove's or one of the set's."""
        SETTINGS[SongSetting.GROOVE].check(name, song=self)
        self._settings[SongSetting.GROOVE] = name

    def groove_at(self, *, scene, track):
        """Return the groove a track's clip in a scene plays with, or None for none: the track's choice, then the scene's, then the song's."""
        choices = [self.get_track(track).get_groove_choice(), scene.get_groove_choice(), self.get_groove_name()]
        return groove_for(choices=choices, song=self)

    def _setting(self, *, name, default):
        """Return one of the song's settings, or its default if the file leaves it out."""
        return or_default(value=self._settings[name], default=default)

    @notes_change
    def set_tempo(self, tempo):
        SETTINGS[SongSetting.TEMPO].check(tempo)
        self._settings[SongSetting.TEMPO] = tempo

    @notes_change
    def set_time_signature(self, text):
        """Set the time signature, written like 6/8."""
        SETTINGS[SongSetting.TIME_SIGNATURE].check(text)
        self._settings[SongSetting.TIME_SIGNATURE] = text

    @notes_change
    def set_entry_size(self, entry_size):
        """Set the entry size, written like 1/8, or None for one step."""
        SETTINGS[SongSetting.ENTRY_SIZE].check(entry_size)
        self._settings[SongSetting.ENTRY_SIZE] = entry_size

    @notes_change
    def set_scale_name(self, name):
        """Give the song a scale by name, or None for no scale."""
        SETTINGS[SongSetting.SCALE].check(name, song=self)
        self._settings[SongSetting.SCALE] = name

    @notes_change
    def set_seed(self, seed):
        """Set the seed, or None for a new take each export."""
        SETTINGS[SongSetting.SEED].check(seed)
        self._settings[SongSetting.SEED] = seed

    def get_genre(self):
        """Return what kind of music the song is, or blank text when it doesn't say."""
        return self._settings[SongSetting.GENRE] or NO_GENRE

    @notes_change
    def set_genre(self, text):
        """Say what kind of music the song is, blank text leaving it out of the file."""
        text = text.strip()
        SETTINGS[SongSetting.GENRE].check(text)
        self._settings[SongSetting.GENRE] = text or None

    # Changing the tracks and registers, the same way the set changes its sections.

    def has_item(self, *, section, name):
        return self._section(section).has(name)

    def get_item(self, *, section, name):
        return self._section(section).get(name)

    def get_item_names(self, section):
        """Return the names in a section, in the song's order."""
        return self._section(section).names()

    def add_item(self, *, section, name, item, after=None):
        """Add a named item to a section, at the end, or right after another item."""
        self._section(section).add(name=name, item=item, after=after)

    def insert_item(self, *, section, name, item, place):
        """Add a named item at a place in a section, before the item that was there."""
        self._section(section).insert(name=name, item=item, place=place)

    def replace_item(self, *, section, name, item):
        """Put a new item under an existing name, keeping its place."""
        self._section(section).replace(name=name, item=item)

    def remove_item(self, *, section, name):
        """Take an item out of a section. Removing a track also removes its clip slots and stops grabs from it."""
        self._section(section).remove(name)
        if section == Section.TRACKS:
            for scene in self.get_scenes():
                scene.remove_track(name)

    def rename_item(self, *, section, old, new):
        """Rename an item, keeping its place, and update everything in the song that names it."""
        self._section(section).rename(old=old, new=new)
        self.rename_references(section=section, old=old, new=new)
        # A Hocket belongs to the set but names a track of the song as its source, so a track's rename reaches the set's hockets too (the user's rule of 2026-11-11).
        if section == Section.TRACKS and self._setlist is not None:
            for name in self._setlist.get_generator_names(GeneratorKind.HOCKET):
                self._setlist.get_generator_settings(kind=GeneratorKind.HOCKET, name=name).rename_references(section=section, old=old, new=new)

    def names_item(self, *, section, name):
        """Return whether the song's own setting names an item of a section: its scale, or its groove, which is the default groove, none, when it sets no other."""
        if section == Section.GROOVES:
            return self.get_groove_name() == name
        return super().names_item(section=section, name=name)

    def referring_parts(self):
        """Return its scenes, which name scales and grooves and hold the clips, and its tracks, which name grooves."""
        return [*self.get_scenes(), *self._section(Section.TRACKS).values()]

    def copy_track(self, *, name, new):
        """Add a copy of a track right after it, with copies of its clip slots in every scene."""
        self._section(Section.TRACKS).add(name=new, item=self.get_track(name).copy(), after=name)
        for scene in self.get_scenes():
            clip_slot = scene.get_clip_slot(name)
            if clip_slot is not None:
                scene.set_clip_slot(track=new, clip_slot=clip_slot.copy(), song=self)

    def move_item(self, *, section, place, offset):
        """Move an item up or down its section, and return whether it moved, which it can't past either end."""
        return self._section(section).move(place=place, offset=offset)

    def sort_items(self, section):
        """Put a section's items in alphabetical order, ignoring case."""
        self._section(section).sort()

    # The registers. There are always four, and the file names only those with settings changed.

    def get_register(self, name):
        """Return a register by its name, AX to DX, with its default settings if the file leaves it out."""
        return self._section(Section.REGISTERS).find(name) or Register()

    def set_register_setting(self, *, name, setting, value):
        """Change one setting of a register, AX to DX, by its file name, or None for its default."""
        if name not in REGISTER_NAMES:
            raise InvalidValue(ERR_NO_SUCH_REGISTER.format(name=name, names=listed(REGISTER_NAMES)))
        register = self.get_register(name).copy()
        register.set_setting(name=setting, value=value)
        registers = {**dict(self._section(Section.REGISTERS).items()), name: register}
        changed = {name: registers[name] for name in REGISTER_NAMES if name in registers and not registers[name].is_default()}
        self._set_section(section=Section.REGISTERS, items=changed or None)

    # The scenes, in the order they play.

    def get_scenes(self):
        """Return the scenes in the order they play."""
        return list(self._scenes or [])

    def get_scene(self, index):
        self._check_scene(index)
        return self._scenes[index]

    @notes_change
    def add_scene(self, *, index, scene):
        """Put a scene at a place in the order, or at the end if index is the number of scenes."""
        scenes = self.get_scenes()
        if not 0 <= index <= len(scenes):
            raise InvalidValue(ERR_NO_SUCH_SCENE.format(index=index, count=len(scenes)))
        scenes.insert(index, scene)
        self._scenes = scenes

    def copy_scene(self, *, index, name):
        """Put a copy of a scene right after it, under a new name, and return the copy."""
        scene = self.get_scene(index).copy()
        scene.set_name(name)
        self.add_scene(index=index + 1, scene=scene)
        return scene

    @notes_change
    def remove_scene(self, index):
        self._check_scene(index)
        del self._scenes[index]

    @notes_change
    def move_scene(self, *, index, offset):
        """Move a scene up or down the order, and return whether it moved, which it can't past either end."""
        moved = moved_in_list(items=self.get_scenes(), place=index, offset=offset)
        if moved is None:
            return False
        self._scenes = moved
        return True

    def _check_scene(self, index):
        if not 0 <= index < len(self._scenes or []):
            raise InvalidValue(ERR_NO_SUCH_SCENE.format(index=index, count=len(self._scenes or [])))

    # What uses what, so that the tracker can refuse to delete something still in use and list its uses.

    def numbered_scenes(self):
        """Return (number, scene) for each scene, numbered from 1 as people count them."""
        return list(enumerate(self.get_scenes(), start=FIRST_SCENE_NUMBER))

    # What names an item of a section, which is what uses the item. The song's own choice is names_item().

    def clip_slots_naming(self, *, section, name):
        """Return (number, scene, track) for each clip that names an item of a section: the clips that play or morph to a pattern, run a chain or grab from a track."""
        return [(number, scene, track) for number, scene in self.numbered_scenes() for track in scene.clip_slots_naming(section=section, name=name)]

    def scenes_naming(self, *, section, name):
        """Return (number, scene) for each scene that chose an item of a section, a scale or a groove, not counting the song's own choice."""
        return [(number, scene) for number, scene in self.numbered_scenes() if scene.names_item(section=section, name=name)]

    def tracks_naming(self, *, section, name):
        """Return the name of each track that chose an item of a section, which is a groove."""
        return [track for track in self.get_track_names() if self.get_track(track).names_item(section=section, name=name)]

    def scenes_that_never_end(self):
        """Return (number, scene) for each scene in which every clip loops."""
        return [(number, scene) for number, scene in self.numbered_scenes() if scene.every_clip_loops()]

    def track_clip_count(self, name):
        """Return how many scenes a track plays in."""
        return sum(1 for scene in self.get_scenes() if scene.has_clip_slot(name))

    # The song's own named objects.

    def has_track(self, name):
        return self._section(Section.TRACKS).has(name)

    def get_track(self, name):
        return self._section(Section.TRACKS).get(name)

    def get_track_names(self):
        """Return the names of the tracks, in the song's order."""
        return self._section(Section.TRACKS).names()

    # What the song shares with the rest of its set, read through the setlist, so that playing and
    # editing a song only ever ask the song.

    def has_scale(self, name):
        return self._setlist.has_scale(name)

    def has_groove(self, name):
        return self._setlist.has_groove(name)

    def get_groove(self, name):
        return self._setlist.get_groove(name)

    def get_groove_names(self):
        """Return every groove the song can choose: the factory grooves, then the set's own."""
        return self._setlist.get_groove_names()

    def get_scale_names(self):
        return self._setlist.get_scale_names()

    def get_named_scale(self, name):
        return self._setlist.get_named_scale(name)

    def has_pattern(self, name):
        return self._setlist.has_pattern(name)

    def get_pattern(self, name):
        return self._setlist.get_pattern(name)

    def get_pattern_names(self):
        return self._setlist.get_pattern_names()

    def has_generator(self, *, kind, name):
        return self._setlist.has_generator(kind=kind, name=name)

    def get_generator_settings(self, *, kind, name):
        return self._setlist.get_generator_settings(kind=kind, name=name)

    def get_generator_names(self, kind):
        return self._setlist.get_generator_names(kind)

    def has_chain(self, name):
        return self._setlist.has_chain(name)

    def has_instrument(self, name):
        return self._setlist.has_instrument(name)

    def get_instrument(self, name):
        return self._setlist.get_instrument(name)

    def get_chain(self, name):
        return self._setlist.get_chain(name)

    def get_chain_names(self):
        return self._setlist.get_chain_names()

    def get_step_size(self):
        return self._setlist.get_step_size()

    def get_written_step_size(self):
        return self._setlist.get_written_step_size()

    def get_pattern_step_size(self, pattern):
        return self._setlist.get_pattern_step_size(pattern)

    def get_pattern_length(self, pattern):
        return self._setlist.get_pattern_length(pattern)

    def changes_registers(self):
        return self._setlist.changes_registers()

    def get_default_octave(self):
        return self._setlist.get_default_octave()

    def get_default_drum_octave(self):
        return self._setlist.get_default_drum_octave()

    def get_octave_labels(self):
        return self._setlist.get_octave_labels()

    def octave_label_offset(self):
        return self._setlist.octave_label_offset()

    def shown_octave(self, octave):
        return self._setlist.shown_octave(octave)

    def stored_octave(self, shown):
        return self._setlist.stored_octave(shown)


