# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""One song of a set: its tempo, scale, seed, registers, tracks and scenes.

A song arranges the set's patterns on its own tracks, scene by scene, and plays them in its own
scale and tempo. What it shares with the other songs in the set (the scales, patterns,
generators, chains and the settings for reading and showing patterns) it reads through its
setlist, so everything that plays or edits a song asks the song, and needn't know which object
holds what. Its tracks and registers are changed the same way as the set's sections: add_item,
remove_item, rename_item and so on, and renaming or removing a track tells the scenes.
"""

from llamatron.caching.revised import notes_change
from llamatron.composition import corrections, defaults, file_format, limits, sections
from llamatron.composition.checks import listed, number, pass_over_unknown, reading, time_signature, written_length
from llamatron.composition.draw import Draw
from llamatron.composition.file_format import GeneratorKind, SceneSetting, Section, sensible_visualizer, SongSetting, StepStatement
from llamatron.composition.genres import sensible_style, style_name
from llamatron.composition.groove import groove_for
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.llama_data import data_as_kept, data_built_anew, HoldsSettings, or_default, own_copy, written_settings
from llamatron.composition.named_items import moved_in_list, NamedItems
from llamatron.composition.register import Register
from llamatron.composition.scene import Scene
from llamatron.composition.setting import Checked, Choice, described, Length, settings_held
from llamatron.composition.track import Track
from llamatron.composition.traits import HoldsSections
from llamatron.user_strings import errors, names


# The kinds of generator whose settings name a track of the song.
KINDS_NAMING_A_TRACK = (GeneratorKind.HOCKET, GeneratorKind.FOLLOW_CHORDS, GeneratorKind.MUSICIAN)


def _check_scale_name(*, value, song):
    """Refuse a scale the set doesn't have. None is no scale."""
    if value is not None and not song.has_scale(value):
        raise InvalidValue(errors.ERR_SONG_NO_SUCH_SCALE.format(scale=value))


def _check_groove_name(*, value, song):
    """Refuse a groove that is neither a factory groove nor one of the set's."""
    if not isinstance(value, str) or not song.has_groove(value):
        raise InvalidValue(errors.ERR_SONG_NO_SUCH_GROOVE.format(name=value))


def _check_preview_instrument(*, value, song):
    """Refuse an instrument the set doesn't have. None is none."""
    if value is not None and not (isinstance(value, str) and song.has_instrument(value)):
        raise InvalidValue(errors.ERR_SONG_NO_SUCH_PREVIEW_INSTRUMENT.format(name=value))


def _check_wizard_choices(value):
    """Refuse what isn't a mapping: the song wizard's choices are kept as the wizard wrote them, and the wizard reads them with care."""
    if value is not None and not isinstance(value, dict):
        raise InvalidValue(errors.ERR_SONG_BAD_WIZARD.format(value=value))


# The song's own settings, each described once, in the order they're written to a file.
def _never_refused(value):
    """Refuse nothing: a visualizer, a genre, a subgenre or a variant that makes no sense is made sensible as it is read (sensible_visualizer, sensible_style)."""


SETTINGS = described(
    Checked(name=SongSetting.TEMPO, check=number),
    Checked(name=SongSetting.TIME_SIGNATURE, check=time_signature),
    Length(name=SongSetting.ENTRY_SIZE, most=limits.MAX_GATE, blank_allowed=True),
    Checked(name=SongSetting.SCALE, check=_check_scale_name, needs_song=True),
    Checked(name=SongSetting.GROOVE, check=_check_groove_name, needs_song=True),
    Checked(name=SongSetting.GENRE, check=_never_refused),
    Checked(name=SongSetting.SUBGENRE, check=_never_refused),
    Checked(name=SongSetting.VARIANT, check=_never_refused),
    Choice(name=SongSetting.LIVE_RESPONSIVENESS, choices=file_format.LIVE_RESPONSIVENESSES, default=corrections.LEFT_OUT, error=errors.ERR_BAD_LIVE_RESPONSIVENESS),
    Checked(name=SongSetting.VISUALIZER, check=_never_refused),
    Checked(name=SongSetting.PREVIEW_INSTRUMENT, check=_check_preview_instrument, needs_song=True),
    Checked(name=SongSetting.WIZARD, check=_check_wizard_choices),
)
# The settings whose message names the setting itself, so that a file's problem with one is placed at the song alone, like "song (verse): scale: ...".
NAMED_BY_THEIR_MESSAGE = (SongSetting.SCALE, SongSetting.GROOVE, SongSetting.PREVIEW_INSTRUMENT)
# Scenes are counted from 1 in messages, as they're shown.
FIRST_SCENE_NUMBER = 1
# What a song that says nothing of its genre gives.


def new_song(*, scale=None):
    """Return the data of a new song: empty, at the default tempo, in a scale of the set's if one is named.

    This is also what a file that leaves settings out gets, so it holds no tracks or scenes: an empty
    file is an empty song.
    """
    data = {SongSetting.TEMPO: defaults.DEFAULT_TEMPO}
    if scale is not None:
        data[SongSetting.SCALE] = scale
    data[Section.TRACKS] = {}
    data[Section.SCENES] = []
    return data


def started_song(*, scale=None):
    """Return the data of a song to start composing in: a new song with its first track and scene, numbered 1."""
    data = new_song(scale=scale)
    data[Section.TRACKS] = {names.MSG_NEW_TRACK_NAME.format(number=defaults.FIRST_NUMBER): {}}
    data[Section.SCENES] = [{SceneSetting.NAME: names.MSG_NEW_SCENE_NAME.format(number=defaults.FIRST_NUMBER)}]
    return data


# A count of steps is whole when the division leaves this denominator.
WHOLE_STEPS = 1


class Song(HoldsSections, HoldsSettings):
    """One song: its settings, registers, tracks and scenes, reading what it shares from its setlist.

    Settings the file leaves out are kept as None and mean their defaults, and so do sections it
    leaves out, so that saving writes back only what was there.
    """

    __slots__ = ('_setlist', '_sections', '_scenes')

    SETTINGS = SETTINGS

    # A song names its own scale, groove and preview instrument. Its scenes and tracks name things too, and are its referring parts.
    REFERENCES = {Section.SCALES: (SongSetting.SCALE,), Section.GROOVES: (SongSetting.GROOVE,), Section.INSTRUMENTS: (SongSetting.PREVIEW_INSTRUMENT,)}

    def __init__(self, *, setlist):
        self.note_change()
        self._setlist = setlist
        self._settings = {name: None for name in SETTINGS}
        self._sections = {name: NamedItems(label=sections.SECTION_LABELS[name]) for name in sections.SONG_SECTIONS}
        self._scenes = None

    @classmethod
    def new(cls, *, setlist):
        """Return an empty song for a set, in the set's first scale if it has one."""
        return cls.from_data(data=new_song(scale=setlist.first_scale_name()), where=names.MSG_THE_FILE, setlist=setlist)

    @classmethod
    def started(cls, *, setlist):
        """Return a song to start composing in, with its first track and scene, in the set's first scale if it has one."""
        return cls.from_data(data=started_song(scale=setlist.first_scale_name()), where=names.MSG_THE_FILE, setlist=setlist)

    @classmethod
    def from_data(cls, *, data, where, setlist):
        """Read one song's data, checking every part of it, placing each error inside the song."""
        data = {} if data is None else data
        with reading(where):
            if not isinstance(data, dict):
                raise InvalidValue(errors.ERR_NOT_A_SONG.format(value=data))
            pass_over_unknown(data=data, allowed={*SETTINGS, *sections.SONG_SECTIONS, Section.SCENES})
        song = cls(setlist=setlist)
        song._read_settings(data=data, where=where)
        song._read_registers(data=data, where=where)
        song._read_draws(data=data, where=where)
        song._read_tracks(data=data, where=where)
        song._read_scenes(data=data, where=where)
        return song

    @notes_change
    def _read_settings(self, *, data, where):
        for setting in settings_held(settings=SETTINGS, data=data):
            name = setting.get_name()
            with reading(where if name in NAMED_BY_THEIR_MESSAGE else errors.ERR_WHERE_WITHIN.format(where=where, part=name)):
                setting.check_held(data, song=self)
        self._settings = {name: own_copy(data.get(name)) for name in SETTINGS}
        self._settings[SongSetting.VISUALIZER] = sensible_visualizer(self._settings[SongSetting.VISUALIZER])
        self._keep_style(genre=self._settings[SongSetting.GENRE], subgenre=self._settings[SongSetting.SUBGENRE], variant=self._settings[SongSetting.VARIANT])

    @notes_change
    def _keep_style(self, *, genre, subgenre, variant):
        """Keep a genre, subgenre and variant, each made sensible, so that none is ever one the program doesn't know."""
        genre, subgenre, variant = sensible_style(genre=genre, subgenre=subgenre, variant=variant)
        self._settings[SongSetting.GENRE] = genre
        self._settings[SongSetting.SUBGENRE] = subgenre
        self._settings[SongSetting.VARIANT] = variant

    def _read_registers(self, *, data, where):
        """Read the registers' settings. There are always four, so the file only names those it changes."""
        registers = data.get(Section.REGISTERS) or {}
        with reading(where):
            if not isinstance(registers, dict) or not set(registers) <= set(file_format.REGISTER_NAMES):
                raise InvalidValue(errors.ERR_REGISTERS_NOT_NAMED.format(names=listed(file_format.REGISTER_NAMES)))
        if Section.REGISTERS in data:
            self._set_section(section=Section.REGISTERS, items={
                name: Register.from_data(data=settings, where=self._where(where=where, label=names.MSG_REGISTER_WORD, name=name)) for name, settings in registers.items()
            })

    def _read_draws(self, *, data, where):
        """Read the draws' settings. There are always four, so the file only names those it changes."""
        draws = data.get(Section.DRAWS) or {}
        with reading(where):
            if not isinstance(draws, dict) or not set(draws) <= set(file_format.DRAW_NAMES):
                raise InvalidValue(errors.ERR_DRAWS_NOT_NAMED.format(names=listed(file_format.DRAW_NAMES)))
        if Section.DRAWS in data:
            self._set_section(section=Section.DRAWS, items={
                name: Draw.from_data(data=settings, where=self._where(where=where, label=names.MSG_DRAW_WORD, name=name)) for name, settings in draws.items()
            })

    def _read_tracks(self, *, data, where):
        tracks = data.get(Section.TRACKS) or {}
        with reading(where):
            if not isinstance(tracks, dict):
                raise InvalidValue(errors.ERR_TRACKS_NOT_NAMED)
        if Section.TRACKS in data:
            self._set_section(section=Section.TRACKS, items={
                name: Track.from_data(data=settings, where=self._where(where=where, label=names.MSG_TRACK_WORD, name=name), song=self) for name, settings in tracks.items()
            })

    @notes_change
    def _read_scenes(self, *, data, where):
        scenes = data.get(Section.SCENES) or []
        with reading(where):
            if not isinstance(scenes, list):
                raise InvalidValue(errors.ERR_SCENES_NOT_A_LIST)
        self._scenes = None if Section.SCENES not in data else [
            Scene.from_data(data=scene, where=errors.ERR_WHERE_WITHIN.format(where=where, part=errors.ERR_WHERE_SCENE_ENTRY.format(number=number)), song=self)
            for number, scene in enumerate(scenes, start=FIRST_SCENE_NUMBER)
        ]

    def _where(self, *, where, label, name):
        """Return how a message places one of the song's named items, like song (one), track (bass)."""
        return errors.ERR_WHERE_WITHIN.format(where=where, part=errors.ERR_WHERE_NAMED.format(label=label, name=name))

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
        return Song.from_data(data=self.to_data(), where=names.MSG_THE_FILE, setlist=self._setlist)

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
        return number(self._setting(name=SongSetting.TEMPO, default=defaults.DEFAULT_TEMPO))

    def get_time_signature(self):
        """Return the song's time signature, 4/4 unless the file sets one, which only changes what's drawn."""
        return time_signature(self._setting(name=SongSetting.TIME_SIGNATURE, default=defaults.DEFAULT_TIME_SIGNATURE))

    def steps_in_a_bar(self):
        """Return how many steps of the set's step size make one bar of this song's time signature, or None if a bar isn't whole steps.

        A new pattern is this long, so that a pattern in 3/4 starts as 12 sixteenths rather than
        16. 7/8 at a 1/4 step is three and a half steps, so None.
        """
        steps = self.get_time_signature().bar_length() / self._setlist.get_step_size()
        return steps.numerator if steps.denominator == WHOLE_STEPS else None

    def get_pattern_time_signature(self, pattern):
        """Return the time signature a pattern is drawn in: its own, or else the song's."""
        return pattern.get_time_signature() or self.get_time_signature()

    def get_entry_size(self):
        """Return how long a note placed on a piano roll lasts unless the pattern says otherwise, in whole notes, or None for one step."""
        entry_size = self.get_written_entry_size()
        return None if entry_size is None else written_length(value=entry_size, most=limits.MAX_GATE)

    def get_written_entry_size(self):
        """Return the song's entry size as the file writes it, like 1/8, or None for one step."""
        return self._settings[SongSetting.ENTRY_SIZE]

    def entry_size_for(self, pattern):
        """Return how long a note placed on a pattern's piano roll lasts: the pattern's own entry size, else the song's, else one of its steps."""
        return pattern.get_entry_size() or self.get_entry_size() or self.get_pattern_step_size(pattern)

    def get_scale_name(self):
        """Return the name of the song's scale, or None if it has none."""
        return self._settings[SongSetting.SCALE]

    def get_preview_instrument_name(self):
        """Return the name of the instrument Listen plays a pattern through, or None to play through the pattern's own track."""
        return self._settings[SongSetting.PREVIEW_INSTRUMENT]

    @notes_change
    def set_preview_instrument_name(self, name):
        """Choose the instrument of the set that Listen plays a pattern through, or None for the pattern's own track."""
        SETTINGS[SongSetting.PREVIEW_INSTRUMENT].check(name, song=self)
        self._settings[SongSetting.PREVIEW_INSTRUMENT] = name

    def get_live_responsiveness(self):
        """Return when an edit made while the song plays is heard: next_bar unless the song says."""
        return self._setting(name=SongSetting.LIVE_RESPONSIVENESS, default=defaults.DEFAULT_LIVE_RESPONSIVENESS)

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
        return self._setting(name=SongSetting.GROOVE, default=defaults.DEFAULT_GROOVE)

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

    def get_genre(self):
        """Return the genre the song says it is, or None when it says none."""
        return self._settings[SongSetting.GENRE]

    def get_subgenre(self):
        """Return the subgenre the song says it is, one of its genre's, or None when it says none."""
        return self._settings[SongSetting.SUBGENRE]

    def get_variant(self):
        """Return the variant of its subgenre the song says it is, or None when it says none."""
        return self._settings[SongSetting.VARIANT]

    def get_style_name(self):
        """Return one name for the song's genre and subgenre, a mashup's naming both, or None when the song says no genre."""
        return style_name(genre=self.get_genre(), subgenre=self.get_subgenre())

    @notes_change
    def set_genre(self, genre):
        """Say what genre the song is, None or a genre the program doesn't know for none. A subgenre and a variant of another genre go with it."""
        self._keep_style(genre=genre, subgenre=self.get_subgenre(), variant=self.get_variant())

    @notes_change
    def set_subgenre(self, subgenre):
        """Say what subgenre of its genre the song is, None or one the genre doesn't have for none. A variant of another subgenre goes with it."""
        self._keep_style(genre=self.get_genre(), subgenre=subgenre, variant=self.get_variant())

    @notes_change
    def set_variant(self, variant):
        """Say what variant of its subgenre the song is, None or one the subgenre doesn't have for none."""
        self._keep_style(genre=self.get_genre(), subgenre=self.get_subgenre(), variant=variant)

    def get_wizard_choices(self):
        """Return what the song wizard was told when it made the song, as data of the song's own, or None for a song the wizard didn't make."""
        return own_copy(self._settings[SongSetting.WIZARD])

    @notes_change
    def set_wizard_choices(self, choices):
        """Keep what the song wizard was told when it made the song, or None to keep nothing."""
        SETTINGS[SongSetting.WIZARD].check(choices)
        self._settings[SongSetting.WIZARD] = own_copy(choices)

    # Changing the tracks and registers, the same way the set changes its sections.

    def insert_item(self, *, section, name, item, place):
        """Add a named item at a place in a section, before the item that was there."""
        self._section(section).insert(name=name, item=item, place=place)

    def remove_item(self, *, section, name):
        """Take an item out of a section. Removing a track also removes its clip slots and stops grabs from it."""
        HoldsSections.remove_item(self, section=section, name=name)
        if section == Section.TRACKS:
            for scene in self.get_scenes():
                scene.remove_track(name)

    def rename_item(self, *, section, old, new):
        """Rename an item, keeping its place, and update everything in the song that names it."""
        self._section(section).rename(old=old, new=new)
        self.rename_references(section=section, old=old, new=new)
        # A Hocket and a Follow Chords belong to the set but name a track of the song, so a track's rename reaches the set's too.
        if section == Section.TRACKS and self._setlist is not None:
            for kind in KINDS_NAMING_A_TRACK:
                for name in self._setlist.get_generator_names(kind):
                    self._setlist.get_generator_settings(kind=kind, name=name).rename_references(section=section, old=old, new=new)

    def names_item(self, *, section, name):
        """Return whether the song's own setting names an item of a section: its scale, or its groove, which is the default groove, none, when it sets no other."""
        if section == Section.GROOVES:
            return self.get_groove_name() == name
        return super().names_item(section=section, name=name)

    def named_items(self):
        """Return what the song's own settings name, with its groove, which is the default groove when it sets no other."""
        return super().named_items() | {(Section.GROOVES, self.get_groove_name())}

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

    # The registers. There are always four, and the file names only those with settings changed.

    def get_register(self, name):
        """Return a register by its name, AX to DX, with its default settings if the file leaves it out."""
        return self._section(Section.REGISTERS).find(name) or Register()

    def set_register_setting(self, *, name, setting, value):
        """Change one setting of a register, AX to DX, by its file name, or None for its default."""
        if name not in file_format.REGISTER_NAMES:
            raise InvalidValue(errors.ERR_NO_SUCH_REGISTER.format(name=name, names=listed(file_format.REGISTER_NAMES)))
        register = self.get_register(name).copy()
        register.set_setting(name=setting, value=value)
        registers = {**dict(self._section(Section.REGISTERS).items()), name: register}
        changed = {name: registers[name] for name in file_format.REGISTER_NAMES if name in registers and not registers[name].is_default()}
        self._set_section(section=Section.REGISTERS, items=changed or None)

    # The draws. There are always four, and the file names only those with settings changed.

    def get_draw(self, name):
        """Return a draw by its name, AD to DD, with its default settings if the file leaves it out."""
        return self._section(Section.DRAWS).find(name) or Draw()

    def _written_draws(self):
        """Return the draws the file writes, the only ones that can hold a value: a draw left out is its default, which holds none."""
        return self._section(Section.DRAWS).values()

    def set_draw_setting(self, *, name, setting, value):
        """Change one setting of a draw, AD to DD, by its file name, or None for its default."""
        self._change_draw(name=name, change=lambda draw: draw.set_setting(name=setting, value=value))

    def set_draw_slot(self, *, name, place, value):
        """Give one slot of a draw a value, held within the draw's range, or make it blank with None."""
        self._change_draw(name=name, change=lambda draw: draw.set_slot(place=place, value=value))

    def set_draw_slot_count(self, *, name, count):
        """Make a draw hold count slots, new ones blank."""
        self._change_draw(name=name, change=lambda draw: draw.set_slot_count(count))

    def _change_draw(self, *, name, change):
        """Change a copy of a draw with change, and keep it, leaving the file to name only the draws with settings changed."""
        if name not in file_format.DRAW_NAMES:
            raise InvalidValue(errors.ERR_NO_SUCH_DRAW.format(name=name, names=listed(file_format.DRAW_NAMES)))
        draw = self.get_draw(name).copy()
        change(draw)
        draws = {**dict(self._section(Section.DRAWS).items()), name: draw}
        changed = {name: draws[name] for name in file_format.DRAW_NAMES if name in draws and not draws[name].is_default()}
        self._set_section(section=Section.DRAWS, items=changed or None)

    def uses_draws(self):
        """Return whether any draw holds a value, so that a render need only follow the draws when one does."""
        return any(draw.filled_places() for draw in self._written_draws())

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
            raise InvalidValue(errors.ERR_NO_SUCH_SCENE.format(index=index, count=len(scenes)))
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
            raise InvalidValue(errors.ERR_NO_SUCH_SCENE.format(index=index, count=len(self._scenes or [])))

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
        return [(number, scene) for number, scene in self.numbered_scenes() if self.scene_never_ends(scene)]

    def scene_never_ends(self, scene):
        """Return whether every clip of a scene loops and no step of a pattern they play can stop its clip, so that nothing ends the scene."""
        if not scene.every_clip_loops():
            return False
        patterns = [name for track in scene.get_track_names() for name in scene.get_clip_slot(track).get_pattern_names()]
        return not any(self.has_pattern(name) and self.get_pattern(name).has_statements(StepStatement.STOP) for name in patterns)

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

    def default_velocity_of(self, track):
        """Return the velocity a step with none typed plays at on a track: the track's own, else its instrument's, else the loudest."""
        own = track.get_default_velocity()
        if own is not None:
            return own
        instrument = self.instrument_of(track)
        of_instrument = None if instrument is None else instrument.get_default_velocity()
        return defaults.DEFAULT_VELOCITY if of_instrument is None else of_instrument

    def accent_of(self, track):
        """Return what an accented step adds to its velocity on a track: the track's accent on top of its instrument's."""
        instrument = self.instrument_of(track)
        return track.get_accent() + (defaults.DEFAULT_INSTRUMENT_ACCENT if instrument is None else instrument.get_accent())

    def instrument_of(self, track):
        """Return a track's instrument, or None when it names none or the set has none of that name."""
        name = track.get_instrument_name()
        return self.get_instrument(name) if name is not None and self.has_instrument(name) else None

    def get_chain(self, name):
        return self._setlist.get_chain(name)

    def forget_generator(self, name):
        """Take a generator out of every list of generators of the song: its tracks', its scenes' and its clips'."""
        listing = [self._section(Section.TRACKS).get(track) for track in self.get_track_names()]
        for scene in self.get_scenes():
            listing += [scene, *[scene.get_clip_slot(track) for track in scene.get_track_names()]]
        for holder in listing:
            if name in holder.get_chain_names():
                holder.set_chain_names(names=[each for each in holder.get_chain_names() if each != name], song=self)

    def chain_run(self, name):
        """Return the chain a name in a list of generators runs (Setlist.chain_run)."""
        return self._setlist.chain_run(name)

    def has_generator_named(self, name):
        return self._setlist.has_generator_named(name)

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

    def scenes_change_registers(self):
        """Return whether any of its scenes, or any clip of one, sets a register or adds to one, or whether a draw that holds a
        value redraws in conditions, which a statement of a scene, a clip, a track, a chain or a generator can draw from."""
        return any(scene.changes_registers() for scene in self.get_scenes()) or any(
            draw.redraws_in_conditions() and draw.filled_places() for draw in self._written_draws()
        )

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


