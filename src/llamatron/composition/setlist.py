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
"""The setlist: everything a set file holds, as objects that save and load themselves.

A set is what llamatron edits and saves: the scales, patterns, generators and chains that every
song in it shares, and its songs, each with its own tempo, scale, seed, tracks, registers and
scenes, like the songs played in one concert. It isn't a Live set: each song exports to a Live
set, or to MIDI files, of its own.

The set's named sections are all changed the same way, by section: add_item, remove_item,
rename_item and so on, and renaming something tells every song and chain that refers to it by
name. Every change checks its value the way reading a file does and raises InvalidValue if it's
wrong, leaving the set as it was.
"""

import copy
import os

from llamatron.composition import checks, corrections as corrections_values, defaults, file_format, generator_settings, groove, limits as set_limits, sections
from llamatron.composition.chain import Chain
from llamatron.composition.checks import reading, written_length
from llamatron.composition.corrections import Correction
from llamatron.composition.file_format import ClipSlotSetting, PatternSetting, Row, ScaleSetting, SceneSetting, Section, sensible_generator_order, sensible_hidden_visualizers, sensible_visualizer, SetlistSetting
from llamatron.composition.groove import check_groove_name, factory_groove, Groove, is_factory_groove
from llamatron.composition.instrument import Instrument
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.llama_data import data_as_kept, data_built_anew, HoldsSettings, or_default, own_copy, written_settings
from llamatron.composition.migrations import Conversion
from llamatron.composition.named_items import NamedItems
from llamatron.composition.named_scale import NamedScale, scale_type_name
from llamatron.composition.naming import copy_name, is_taken, name_in_copied_group, name_order, split_part_names, unique_name
from llamatron.composition.pattern import held_add, Pattern
from llamatron.composition.setlist_reader import as_a_set_is_written, closed_groups_held, open_types_held, read_corrected, set_file_data
from llamatron.composition.setlist_writer import dump_setlist
from llamatron.composition.setting import Checked, Choice, described, Flag, Length, settings_held, Text, WholeNumber
from llamatron.composition.song import Song, started_song
from llamatron.composition.song_file_error import SongFileError
from llamatron.composition.traits import HoldsSections
from llamatron.music import note
from llamatron.music.scale import ScaleType
from llamatron.strings import errors, names as names_text
from llamatron.support import files, version as version_values
from llamatron.support.revised import notes_change
from llamatron.support.version import is_version



def _check_version(value):
    """Refuse a version that isn't three whole numbers separated by dots. Nothing depends on the version yet, but it has to be one."""
    if not is_version(value):
        raise InvalidValue(errors.ERR_SONG_BAD_VERSION.format(value=value))


def _never_refused(value):
    """Refuse nothing: a visualizer setting that makes no sense is made sensible as it's read (sensible_visualizer)."""


# The set's own settings, each described once, in the order they're written to a file. The title, author, description and notes are only for people reading or sharing the file.
SETTINGS = described(
    Checked(name=SetlistSetting.VERSION, check=_check_version),
    Text(name=SetlistSetting.TITLE, error=errors.ERR_NOT_TEXT),
    Text(name=SetlistSetting.AUTHOR, error=errors.ERR_NOT_TEXT),
    Text(name=SetlistSetting.DESCRIPTION, error=errors.ERR_NOT_TEXT),
    Text(name=SetlistSetting.NOTES, error=errors.ERR_NOT_TEXT),
    Length(name=SetlistSetting.STEP_SIZE, most=set_limits.MAX_STEP_SIZE),
    WholeNumber(name=SetlistSetting.DEFAULT_OCTAVE, lowest=set_limits.MIN_OCTAVE, highest=set_limits.MAX_OCTAVE, error=errors.ERR_CHECKS_BAD_OCTAVE),
    WholeNumber(name=SetlistSetting.DEFAULT_DRUM_OCTAVE, lowest=set_limits.MIN_OCTAVE, highest=set_limits.MAX_OCTAVE, error=errors.ERR_CHECKS_BAD_OCTAVE),
    Choice(name=SetlistSetting.OCTAVE_LABELS, choices=file_format.OCTAVE_LABEL_CHOICES, default=corrections_values.LEFT_OUT, error=errors.ERR_SONG_BAD_OCTAVE_LABELS),
    Choice(name=SetlistSetting.DEFAULT_FOLLOW_ACTION, choices=file_format.FOLLOW_ACTION_CHOICES, default=corrections_values.LEFT_OUT, error=errors.ERR_BAD_DEFAULT_FOLLOW_ACTION),
    Flag(name=SetlistSetting.REAL_TIME, error=errors.ERR_REAL_TIME_NOT_TRUE_OR_FALSE),
    Checked(name=SetlistSetting.VISUALIZER, check=_never_refused),
    Checked(name=SetlistSetting.HIDDEN_VISUALIZERS, check=_never_refused),
    Checked(name=SetlistSetting.GENERATOR_ORDER, check=_never_refused),
    Flag(name=SetlistSetting.PROTECTED, error=errors.ERR_PROTECTED_NOT_TRUE_OR_FALSE),
)
# The settings whose message names the setting itself, so that a file's problem with one has no place in front of it.
NAMED_BY_THEIR_MESSAGE = (SetlistSetting.VERSION, SetlistSetting.TITLE, SetlistSetting.AUTHOR, SetlistSetting.DESCRIPTION, SetlistSetting.NOTES)
# What a text setting is when the file leaves it out.
NO_TEXT = ''
# The class that reads each item of a section of the set.
ITEM_KINDS = {
    Section.SCALES: NamedScale,
    Section.PATTERNS: Pattern,
    **{section: generator_settings.GENERATOR_SETTINGS[kind] for kind, section in file_format.NAMED_GENERATORS.items()},
    Section.CHAINS: Chain,
    Section.GROOVES: Groove,
    Section.INSTRUMENTS: Instrument,
    Section.SONGS: Song,
}
# The sections taken in from another set, in the order a set is read, so that each can name what the ones before it hold.
SECTIONS_TAKEN_IN = [Section.SCALES, Section.PATTERNS, *file_format.NAMED_GENERATORS.values(), Section.CHAINS, Section.GROOVES, Section.INSTRUMENTS, Section.SONGS]
# The sections whose items are read knowing the set, where the others take the set in place of a song, to look names up in.
READ_WITH_THE_SET = (Section.CHAINS, Section.SONGS)
# The scale a new set starts with, which can be deleted.
DEFAULT_SCALE = 'scale-1'


# The starter pattern of a new set: one bar of sixteenths in 4/4, with the root on every beat, so
# that a new set shows what a pattern looks like and plays from the first moment.
# Everything in it can be deleted, like the C major scale.
STARTER_PATTERN_STEPS = 16
STARTER_STEPS_PER_BEAT = 4
STARTER_DEGREE = 1


def starter_pattern():
    """Return the data of the starter pattern: the root on each beat of one bar, with a blank gate, so each note lasts its step."""
    degrees = [STARTER_DEGREE if step % STARTER_STEPS_PER_BEAT == 0 else None for step in range(STARTER_PATTERN_STEPS)]
    return {PatternSetting.STEPS: STARTER_PATTERN_STEPS, Row.DEGREE: degrees}


def new_setlist():
    """Return the data of a new set: a C major scale and a starter pattern, both deletable, and one song called untitled whose first track plays the pattern in its first scene, the pattern in the group named after that track."""
    first_pattern = names_text.MSG_NEW_PATTERN_NAME.format(number=defaults.FIRST_NUMBER)
    first_track = names_text.MSG_NEW_TRACK_NAME.format(number=defaults.FIRST_NUMBER)
    song = started_song(scale=DEFAULT_SCALE)
    song[Section.SCENES][0][SceneSetting.TRACKS] = {first_track: {ClipSlotSetting.PATTERN: first_pattern}}
    return {
        Section.SCALES: {DEFAULT_SCALE: {ScaleSetting.ROOT: note.ROOT_NAMES[0], ScaleSetting.TYPE: scale_type_name(ScaleType.MAJOR)}},
        SetlistSetting.STEP_SIZE: defaults.DEFAULT_STEP_SIZE,
        SetlistSetting.DEFAULT_OCTAVE: defaults.DEFAULT_OCTAVE, SetlistSetting.DEFAULT_DRUM_OCTAVE: defaults.DEFAULT_DRUM_OCTAVE,
        SetlistSetting.OCTAVE_LABELS: defaults.DEFAULT_OCTAVE_LABELS,
        Section.PATTERNS: {first_pattern: {**starter_pattern(), PatternSetting.GROUP: first_track}}, Section.ARPS: {}, Section.AUTO_RATCHETS: {}, Section.DRIFTS: {}, Section.PROGRESSIONS: {}, Section.VOICE_LEADINGS: {}, Section.STRUMS: {}, Section.GUITARIFIES: {}, Section.EUCLIDS: {}, Section.DENSITIES: {}, Section.SWELLS: {}, Section.ARTICULATES: {}, Section.GLIDES: {}, Section.SHORTENS: {}, Section.RUSHES: {}, Section.DRAGS: {}, Section.HOCKETS: {}, Section.FOLLOW_CHORDS: {}, Section.PHRASINGS: {}, Section.MUSICIANS: {}, Section.CHAINS: {},
        Section.SONGS: {names_text.MSG_DEFAULT_SONG_NAME: song},
    }


# The kind of generator each generator section holds.
GENERATOR_KINDS_OF_SECTIONS = {section: kind for kind, section in file_format.NAMED_GENERATORS.items()}


class Setlist(HoldsSections, HoldsSettings):
    """The set the user composes: its settings, named scales, patterns, generators and chains, and its songs.

    Settings the file leaves out are kept as None and mean their defaults, and so do sections it
    leaves out, so that saving writes back only what was there. Objects refer to each other by
    name, and the set looks the names up; each song does the same for what it shares.
    """

    __slots__ = ('_sections', '_closed_groups', '_open_types', '_conversion')

    SETTINGS = SETTINGS

    def __init__(self):
        self.note_change()
        # The pattern groups shown closed: no part of the set's data, so no undo or restore touches it (file_format.CLOSED_PATTERN_GROUPS).
        self._closed_groups = []
        # The types of generator shown open on the Generators page, kept the same way (file_format.OPEN_GENERATOR_TYPES).
        self._open_types = []
        # What reading the set's file moved from an older layout, which the tracker says once the file is open.
        self._conversion = Conversion()
        self._settings = {name: None for name in SETTINGS}
        self._sections = {name: NamedItems(label=sections.SECTION_LABELS[name]) for name in sections.SETLIST_SECTIONS}

    @classmethod
    def read_file(cls, path):
        """Return the set in a file, or raise SongFileError if it can't be read or something's wrong with it.

        The file is read with load_safely, which only ever makes plain data, so reading a file
        can never run code. A file saved before sets existed holds one song, which is named after
        the file.
        """
        data, conversion = set_file_data(path)
        setlist = cls.from_data(data=data)
        setlist._conversion = conversion
        return setlist

    @classmethod
    def read_file_corrected(cls, path):
        """Return the set in a file with every value that can't be used changed to the allowed value nearest it, and the corrections made.

        This is for a file that read_file refused with a problem that has a correction
        (SongFileError.get_correction). A problem with no correction still raises
        SongFileError. The file itself isn't changed.
        """
        data, conversion = set_file_data(path)
        setlist, corrections = cls.from_data_corrected(data=data)
        setlist._conversion = conversion
        return setlist, corrections

    def get_conversion(self):
        return self._conversion

    def write_file(self, path):
        """Write the set to a file, making any directories it needs. Every saved file records the version that wrote it."""
        self.set_version(version_values.VERSION)
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, files.WRITE_TEXT, encoding=files.FILE_ENCODING) as file:
            file.write(dump_setlist(self._file_data()))

    def _file_data(self):
        """Return what a file holds: the set's data, and the pattern groups shown closed and the types of generator shown open, where any are."""
        data = self.to_data()
        closed = self.get_closed_pattern_groups()
        if closed:
            data[file_format.CLOSED_PATTERN_GROUPS] = closed
        opened = self.get_open_generator_types()
        if opened:
            data[file_format.OPEN_GENERATOR_TYPES] = opened
        return data

    @classmethod
    def new(cls):
        """Return a new set: one empty song, a C Major scale that can be deleted, and every setting a saved file writes."""
        return cls.from_data(data=new_setlist())

    @notes_change
    def fill_in_defaults(self):
        """Give every setting and section a new set has a value where a file left it out, so that saving writes them."""
        for name, value in new_setlist().items():
            if name in self._settings and self._settings[name] is None:
                self._settings[name] = value
        for items in self._sections.values():
            items.fill_in()
        for song in self.get_songs():
            song.fill_in_defaults()

    @classmethod
    def from_data(cls, *, data, where=names_text.MSG_THE_FILE, song=None):
        """Read a whole set's data, as the objects write it, checking every part of it, in the order the file is read."""
        setlist = cls()
        written = as_a_set_is_written(data=data, where=where, allowed=SETTINGS)
        setlist._read(written)
        setlist._closed_groups = closed_groups_held(written)
        setlist._open_types = open_types_held(written)
        return setlist

    @classmethod
    def from_data_corrected(cls, *, data, where=names_text.MSG_THE_FILE):
        """Return the set a file's data describes with every value that can't be used changed to the allowed value nearest it, and the corrections made, in the order they were found.

        The data is read as from_data reads it, which stops at the first wrong value. A value
        with an allowed value near it comes with a correction (composition/corrections.py),
        which is applied to a copy of the data before reading again, until the set reads. A
        problem with no correction raises SongFileError, as it does for from_data. The data
        given isn't changed.
        """
        data = as_a_set_is_written(data=copy.deepcopy(data), where=where, allowed=SETTINGS)

        def read(written):
            setlist = cls()
            setlist._read(written)
            return setlist
        return read_corrected(read=read, data=data)

    def restore(self, data):
        """Become what data says: data this set kept earlier (kept_data), which an undo or a redo goes back to.

        The set reads the data as from_data does, section by section, and reading keeps every
        item the set already has under its name with that very data, so only what differs is
        built again. A whole song counts as one item. The data is taken as it is, unchecked for
        an older file's layout, since the set wrote it.
        """
        self._read(data)

    def _read(self, data):
        """Read every setting and section from a set file's data, in the order the file is read: each section can name what the ones before it hold."""
        self._read_settings(data)
        self._read_scales(data)
        self._read_items(data=data, section=Section.PATTERNS)
        for section in file_format.NAMED_GENERATORS.values():
            self._read_generators(data=data, section=section)
        self._read_items(data=data, section=Section.CHAINS)
        self._read_grooves(data)
        self._read_instruments(data)
        self._read_songs(data)
        self._check_adds_within_limits(data)

    def _check_adds_within_limits(self, data):
        """Refuse a pattern whose += rows add more than the narrowest Allowed Inc Max of the songs that play it, with the correction that brings them within it."""
        for name in self.get_pattern_names():
            pattern = self.get_pattern(name)
            for register, row in file_format.REGISTER_ADD_ROWS.items():
                if not pattern.adds_anything(row):
                    continue
                most = self.allowed_inc_max_for_pattern(name=name, register=register)
                if most is None or not pattern.adds_past(row=row, most=most):
                    continue
                holder = data[Section.PATTERNS][name]
                found = holder[row]
                used = [held_add(value=value, most=most) for value in found]
                with reading(self._where(section=Section.PATTERNS, name=name)):
                    raise InvalidValue(errors.ERR_ADD_PAST_ALLOWED.format(row=row, register=register, most=most),
                                       correction=Correction(holder=holder, key=row, name=row, found=found, used=used))

    @notes_change
    def _read_settings(self, data):
        for setting in settings_held(settings=SETTINGS, data=data):
            name = setting.get_name()
            with reading(checks.TOP_OF_FILE if name in NAMED_BY_THEIR_MESSAGE else name):
                setting.check_held(data)
        self._settings = {name: own_copy(data.get(name)) for name in SETTINGS}
        self._settings[SetlistSetting.VISUALIZER] = sensible_visualizer(self._settings[SetlistSetting.VISUALIZER])
        self._settings[SetlistSetting.HIDDEN_VISUALIZERS] = sensible_hidden_visualizers(self._settings[SetlistSetting.HIDDEN_VISUALIZERS])
        self._settings[SetlistSetting.GENERATOR_ORDER] = sensible_generator_order(self._settings[SetlistSetting.GENERATOR_ORDER])

    def _read_scales(self, data):
        if not isinstance(data.get(Section.SCALES) or {}, dict):
            raise SongFileError(errors.ERR_SCALES_NOT_NAMED)
        self._read_items(data=data, section=Section.SCALES)

    def _read_grooves(self, data):
        grooves = data.get(Section.GROOVES) or {}
        if not isinstance(grooves, dict):
            raise SongFileError(errors.ERR_GROOVES_NOT_NAMED)
        for name in grooves:
            with reading(self._where(section=Section.GROOVES, name=name)):
                check_groove_name(name)
        self._read_items(data=data, section=Section.GROOVES)

    def _read_instruments(self, data):
        if not isinstance(data.get(Section.INSTRUMENTS) or {}, dict):
            raise SongFileError(errors.ERR_INSTRUMENTS_NOT_NAMED)
        self._read_items(data=data, section=Section.INSTRUMENTS)

    def _read_generators(self, *, data, section):
        if not isinstance(data.get(section) or {}, dict):
            raise SongFileError(errors.ERR_GENERATORS_NOT_NAMED.format(section=section))
        self._read_items(data=data, section=section)

    def _read_songs(self, data):
        if not isinstance(data.get(Section.SONGS) or {}, dict):
            raise SongFileError(errors.ERR_SONGS_NOT_NAMED)
        self._read_items(data=data, section=Section.SONGS)

    def _read_items(self, *, data, section):
        """Give a section the items the data holds, naming each one in any error, or no items for a section the data leaves out.

        An item the set already has under its name, keeping this very data, stays as it is, and
        every other item is read from its data. A new set has no items, so it reads them all,
        and a set going back to an earlier state (restore) reads only what differs.
        """
        if section not in data:
            self._set_section(section=section, items=None)
            return
        self._set_section(section=section, items={name: self._item(section=section, name=name, data=item) for name, item in (data[section] or {}).items()})

    def _item(self, *, section, name, data):
        """Return the item of a section that its data describes: the one the set has already, if it keeps this very data, or one read from the data."""
        same = self._sections[section].same_item(name=name, data=data)
        if same is not None:
            return same
        where = self._where(section=section, name=name)
        if section in READ_WITH_THE_SET:
            return ITEM_KINDS[section].from_data(data=data, where=where, setlist=self)
        return ITEM_KINDS[section].from_data(data=data, where=where, song=self)

    def _where(self, *, section, name):
        """Return how a message places one item of a section, like pattern (tune)."""
        return errors.ERR_WHERE_NAMED.format(label=sections.SECTION_LABELS[section], name=name)

    def to_data(self):
        return self._data_from(data_built_anew)

    def kept_data(self):
        """Return the set's data with each item's as the item keeps it, put together each time, since an item changes without the set changing.

        The pieces are shared with every earlier asker, the undo history among them, and are
        never changed.
        """
        return self._data_from(data_as_kept)

    def _data_from(self, part_data):
        data = written_settings(self._settings)
        for section, items in self._sections.items():
            if items.is_written():
                data[section] = items.data_from(part_data)
        return data

    # The set's settings, with their defaults.

    def get_step_size(self):
        """Return how long each step of a pattern is, in whole notes, unless the pattern sets its own."""
        return written_length(value=self._setting(name=SetlistSetting.STEP_SIZE, default=defaults.DEFAULT_STEP_SIZE), most=set_limits.MAX_STEP_SIZE)

    def get_written_step_size(self):
        """Return the step size as the file writes it, like 1/16, which a new arp starts from."""
        return self._setting(name=SetlistSetting.STEP_SIZE, default=defaults.DEFAULT_STEP_SIZE)

    def get_pattern_step_size(self, pattern):
        """Return how long each step of a pattern is: its own step size, or else the set's."""
        step_size = pattern.get_step_size()
        return self.get_step_size() if step_size is None else step_size

    def get_pattern_length(self, pattern):
        """Return how long one pass through a pattern lasts, in whole notes: its steps times its step size.

        Every pass lasts exactly this, whatever the steps hold and whatever order they play in,
        which is what lets clip and scene lengths be worked out without playing anything.
        """
        return pattern.get_steps() * self.get_pattern_step_size(pattern)

    def changes_registers(self):
        """Return whether any pattern sets a register or adds to one, any arpeggiator adds to one, or any scene or clip sets or adds to one, so that playing changes the registers' values."""
        return any(pattern.changes_registers() for pattern in self._section(Section.PATTERNS).values()) or any(
            generator.adds_to_registers() for section in (Section.ARPS, Section.DRIFTS) for generator in self._section(section).values()
        ) or any(song.scenes_change_registers() for song in self._section(Section.SONGS).values())

    def get_default_octave(self):
        return self._setting(name=SetlistSetting.DEFAULT_OCTAVE, default=defaults.DEFAULT_OCTAVE)

    def get_default_drum_octave(self):
        return self._setting(name=SetlistSetting.DEFAULT_DRUM_OCTAVE, default=defaults.DEFAULT_DRUM_OCTAVE)

    def get_octave_labels(self):
        """Return how the tracker numbers octaves on screen: Live's labels, or llamatron's own from C0."""
        return self._setting(name=SetlistSetting.OCTAVE_LABELS, default=defaults.DEFAULT_OCTAVE_LABELS)

    def octave_label_offset(self):
        """Return how far below the file's octave numbers the shown ones are: 2 with Live's labels."""
        return file_format.OCTAVE_LABEL_OFFSETS[self.get_octave_labels()]

    def shown_octave(self, octave):
        """Return an octave from the file as the tracker shows it, in the set's octave labels."""
        return octave - self.octave_label_offset()

    def stored_octave(self, shown):
        """Return an octave typed in the set's octave labels as the file numbers it."""
        return shown + self.octave_label_offset()

    def get_default_follow_action(self):
        """Return what a clip sends down in real-time playback when its scene is done, unless the clip says otherwise: one of FOLLOW_ACTION_CHOICES."""
        return self._setting(name=SetlistSetting.DEFAULT_FOLLOW_ACTION, default=defaults.DEFAULT_FOLLOW_ACTION)

    def follow_action_of(self, clip_slot):
        """Return what a clip slot sends down in real-time playback when its scene is done: its own setting, or the set's default."""
        written = clip_slot.get_written_follow_action()
        return self.get_default_follow_action() if written is None else written

    def is_protected(self):
        """Return whether the set's file is protected, so that the tracker saves a copy rather than writing over it."""
        return self._setting(name=SetlistSetting.PROTECTED, default=defaults.DEFAULT_PROTECTED)

    def get_genres(self):
        """Return the genres the set's songs say they are, each once in the songs' order."""
        return list(dict.fromkeys(genre for genre in (self.get_song(name).get_style_name() for name in self.get_song_names()) if genre))

    def get_title(self):
        return self._setting(name=SetlistSetting.TITLE, default=NO_TEXT)

    def get_author(self):
        return self._setting(name=SetlistSetting.AUTHOR, default=NO_TEXT)

    def get_description(self):
        """Return the one line that says what the set is, like the tune it plays, or blank."""
        return self._setting(name=SetlistSetting.DESCRIPTION, default=NO_TEXT)

    def get_notes(self):
        """Return the set's notes, text of any length for people reading or sharing the file, or blank."""
        return self._setting(name=SetlistSetting.NOTES, default=NO_TEXT)

    def has_notes(self):
        return bool(self._settings[SetlistSetting.NOTES])

    def _setting(self, *, name, default):
        """Return one of the set's settings, or its default if the file leaves it out."""
        return or_default(value=self._settings[name], default=default)

    # Changing the set's own settings.

    @notes_change
    def set_version(self, version):
        """Record the version of llamatron that's writing the file."""
        SETTINGS[SetlistSetting.VERSION].check(version)
        self._settings[SetlistSetting.VERSION] = version

    @notes_change
    def set_step_size(self, step_size):
        """Set how long each step of a pattern is unless the pattern sets its own, written like 1/16."""
        SETTINGS[SetlistSetting.STEP_SIZE].check(step_size)
        self._settings[SetlistSetting.STEP_SIZE] = step_size

    @notes_change
    def set_default_octave(self, octave):
        SETTINGS[SetlistSetting.DEFAULT_OCTAVE].check(octave)
        self._settings[SetlistSetting.DEFAULT_OCTAVE] = octave

    @notes_change
    def set_default_drum_octave(self, octave):
        SETTINGS[SetlistSetting.DEFAULT_DRUM_OCTAVE].check(octave)
        self._settings[SetlistSetting.DEFAULT_DRUM_OCTAVE] = octave

    @notes_change
    def set_octave_labels(self, labels):
        SETTINGS[SetlistSetting.OCTAVE_LABELS].check(labels)
        self._settings[SetlistSetting.OCTAVE_LABELS] = labels

    @notes_change
    def set_default_follow_action(self, advance):
        SETTINGS[SetlistSetting.DEFAULT_FOLLOW_ACTION].check(advance)
        self._settings[SetlistSetting.DEFAULT_FOLLOW_ACTION] = advance

    @notes_change
    def set_real_time(self, value):
        SETTINGS[SetlistSetting.REAL_TIME].check(value)
        self._settings[SetlistSetting.REAL_TIME] = value

    @notes_change
    def set_protected(self, value):
        SETTINGS[SetlistSetting.PROTECTED].check(value)
        self._settings[SetlistSetting.PROTECTED] = value

    def set_title(self, text):
        self._set_text(name=SetlistSetting.TITLE, text=text.strip())

    def set_author(self, text):
        self._set_text(name=SetlistSetting.AUTHOR, text=text.strip())

    def set_description(self, text):
        """Set the one line that says what the set is. Blank text removes it."""
        self._set_text(name=SetlistSetting.DESCRIPTION, text=text.strip())

    def set_notes(self, text):
        """Set the notes, kept as given, so that their lines stay as written. Blank text removes them."""
        self._set_text(name=SetlistSetting.NOTES, text=text)

    @notes_change
    def _set_text(self, *, name, text):
        """Store text that's only for people, or leave it out of the file when it's blank."""
        SETTINGS[name].check(text)
        self._settings[name] = text if text.strip() else None

    # Changing the named sections, all the same way. An item is a Pattern, NamedScale, Chain,
    # generator settings object or Song, and the set keeps the names in it right.

    def add_item(self, *, section, name, item, after=None):
        """Add a named item to a section, at the end, or right after another item. A groove can't take a factory groove's name."""
        if section == Section.GROOVES:
            check_groove_name(name)
        self._check_generator_name(section=section, name=name, old=None)
        HoldsSections.add_item(self, section=section, name=name, item=item, after=after)

    def rename_item(self, *, section, old, new):
        """Rename an item, keeping its place, and update everything that names it. A groove can't take a factory groove's name."""
        if section == Section.GROOVES:
            check_groove_name(new)
        self._check_generator_name(section=section, name=new, old=old)
        self._section(section).rename(old=old, new=new)
        self.rename_references(section=section, old=old, new=new)
        if section in GENERATOR_KINDS_OF_SECTIONS:
            self._rename_in_generator_order(kind=GENERATOR_KINDS_OF_SECTIONS[section], old=old, new=new)

    def every_generator_name(self):
        """Return the name of every generator of every kind and of every chain, which share one list in a set file and so may share no name."""
        return [name for section in sections.GENERATOR_SECTIONS for name in self._section(section).names()]

    def _check_generator_name(self, *, section, name, old):
        """Refuse a name for a generator or a chain that a generator or chain of another kind has, old being the name it is renamed from."""
        if section not in sections.GENERATOR_SECTIONS:
            return
        others = [held for held in sections.GENERATOR_SECTIONS if held != section]
        taken = next((held for held in others if is_taken(name=name, taken=[each for each in self._section(held).names() if each != old])), None)
        if taken is not None:
            raise InvalidValue(errors.ERR_NAME_TAKEN.format(label=sections.SECTION_LABELS[taken], name=name))

    # The order of the Generators page: every generator on one list, kept in an order of its own.

    def ordered_generators(self):
        """Return every generator as (kind, name) in the Generators page's order: the order kept, leaving out any generator
        gone, then any it doesn't name, kind by kind in each kind's own order."""
        existing = [(kind, name) for kind, section in file_format.LISTED_GENERATORS.items() for name in self._section(section).names()]
        kept = []
        for entry in self._settings[SetlistSetting.GENERATOR_ORDER] or []:
            pair = next(iter(entry.items()))
            if pair in existing and pair not in kept:
                kept.append(pair)
        return kept + [pair for pair in existing if pair not in kept]

    @notes_change
    def set_generator_order(self, pairs):
        """Keep the Generators page's order, every generator as (kind, name)."""
        self._settings[SetlistSetting.GENERATOR_ORDER] = sensible_generator_order([{kind: name} for kind, name in pairs])

    def move_generator(self, *, place, offset):
        """Move a generator up or down the Generators page's list, and return whether it moved, which it can't past either end."""
        pairs = self.ordered_generators()
        moved = place + offset
        if not 0 <= moved < len(pairs):
            return False
        pairs.insert(moved, pairs.pop(place))
        self.set_generator_order(pairs)
        return True

    @notes_change
    def _rename_in_generator_order(self, *, kind, old, new):
        order = self._settings[SetlistSetting.GENERATOR_ORDER]
        if order:
            self._settings[SetlistSetting.GENERATOR_ORDER] = [{kind: new} if entry == {kind: old} else entry for entry in order]

    def referring_parts(self):
        """Return its chains, which name generators, and its songs, which name everything else."""
        return [*self._section(Section.CHAINS).values(), *self.get_songs()]

    def copy_item(self, *, section, name, new):
        """Add a copy of an item under a new name, at the end of its section, and return the copy."""
        item = self._section(section).get(name).copy()
        self._section(section).add(name=new, item=item)
        if section in GENERATOR_KINDS_OF_SECTIONS and self._settings[SetlistSetting.GENERATOR_ORDER]:
            # On the Generators page a copy comes straight after what it copies, as on every list.
            kind = GENERATOR_KINDS_OF_SECTIONS[section]
            pairs = [pair for pair in self.ordered_generators() if pair != (kind, new)]
            pairs.insert(pairs.index((kind, name)) + 1, (kind, new))
            self.set_generator_order(pairs)
        return item

    # Another set's songs taken in, which the song wizard does with the set it made.

    def take_in(self, other):
        """Take in every song of another set with all the songs use, and return the songs' names here, in order.

        The other set is changed to fit first and is of no use after: a thing of its whose name
        this set uses for something different is renamed there as a duplicate is, and everything
        that names it follows, so that nothing of this set is touched or replaced. A thing that
        is the same in both, such as an instrument both play, is shared and not added twice. A
        song always gets a name of its own.
        """
        for section in SECTIONS_TAKEN_IN:
            for name in other.get_item_names(section):
                if section != Section.SONGS and self.has_item(section=section, name=name) and self._same(section=section, name=name, other=other):
                    continue
                taken = self.get_item_names(section)
                if is_taken(name=name, taken=taken):
                    other.rename_item(section=section, old=name, new=copy_name(name=name, taken=[*taken, *other.get_item_names(section)]))
        songs = other.get_song_names()
        added = other.to_data()
        data = dict(self.kept_data())
        for section in SECTIONS_TAKEN_IN:
            new = {name: item for name, item in (added.get(section) or {}).items() if not self.has_item(section=section, name=name)}
            if new:
                data[section] = {**(data.get(section) or {}), **new}
        self.restore(data)
        for name in songs:
            # Filled in like a loaded song, so that a song taken in saves every setting too, and an undo and a redo leave the same data.
            self.get_song(name).fill_in_defaults()
        return songs

    def song_is_untouched(self, name):
        """Return whether a song is as a new set's song or a newly added song is, with nothing done to it, so that the song
        wizard may fill it in place of adding a song beside it."""
        song = self.get_song(name).to_data()
        new = Setlist.new()
        new.fill_in_defaults()
        first = new.first_song_name()
        if song == new.get_song(first).to_data():
            # A new set's song plays the starter pattern, which must be as it started too.
            patterns = new.get_pattern_names()
            return all(self.has_pattern(pattern) and self.get_item(section=Section.PATTERNS, name=pattern).to_data() == new.get_item(section=Section.PATTERNS, name=pattern).to_data() for pattern in patterns)
        added = copy_name(name=name, taken=new.get_song_names())
        new.add_new_song(added)
        new.get_song(added).fill_in_defaults()
        return song == new.get_song(added).to_data()

    def replace_song(self, *, name, other, new=None):
        """Replace a song entirely, in its place, with the one song of another set and all that song uses, which the song wizard does.

        Whatever the replaced song used that nothing else uses goes with it, its patterns, generators
        and chains, so that a song replaced again and again leaves nothing behind. What another song
        still uses stays, and so does whatever nothing used before. The new song takes the old
        song's name, or a new name when one is given, and its name here is returned.
        """
        place = self.get_song_names().index(name)
        named = self.everything_named()
        used = [(section, item) for section, item in self.named_by_songs() if (section, item) in named]
        self.remove_item(section=Section.SONGS, name=name)
        self._remove_unnamed(used)
        other.rename_item(section=Section.SONGS, old=other.get_song_names()[0], new=new or name)
        taken = self.take_in(other)
        last = len(self.get_song_names()) - 1
        if place != last:
            self.move_item(section=Section.SONGS, place=last, offset=place - last)
        return taken[0]

    def named_by_songs(self):
        """Return every item a song could bring with it, as (section, name): the scales, patterns, generators, chains, grooves and instruments."""
        return [(section, item) for section in SECTIONS_TAKEN_IN if section != Section.SONGS for item in self.get_item_names(section)]

    def remove_unused(self):
        """Take out everything nothing in the set names, so that a set made for one song holds only what the song uses."""
        self._remove_unnamed(self.named_by_songs())

    def _remove_unnamed(self, items):
        """Take out those of some items, each (section, name), that nothing names. A chain goes first and the generators
        only it ran after, so the search goes round until nothing more is left unnamed."""
        while True:
            named = self.everything_named()
            unnamed = [(section, item) for section, item in items if self.has_item(section=section, name=item) and (section, item) not in named]
            if not unnamed:
                return
            for section, item in unnamed:
                self.remove_item(section=section, name=item)

    def everything_named(self):
        """Return everything a song, a scene, a track, a clip or a chain of the set names, as a set of (section, name), found in
        one walk of the set: what is_named() answers for one item, for a search that asks about every item."""
        named = set()
        for song in self.get_songs():
            named |= song.everything_named()
        for name in self.get_chain_names():
            named |= self.get_chain(name).named_items()
        return named

    def is_named(self, *, section, name):
        """Return whether anything in the set names an item of a section: a song, a scene, a track, a clip or a chain."""
        namers = (self.songs_naming, self.scenes_naming, self.tracks_naming, self.clip_slots_naming, self.chains_naming)
        return any(naming(section=section, name=name) for naming in namers)

    def _same(self, *, section, name, other):
        """Return whether this set and another hold the very same thing under a name."""
        return self.get_item(section=section, name=name).to_data() == other.get_item(section=section, name=name).to_data()

    # The songs.

    def has_song(self, name):
        return self._section(Section.SONGS).has(name)

    def get_song(self, name):
        return self._section(Section.SONGS).get(name)

    def get_song_names(self):
        """Return the names of the songs, in the set's order."""
        return self._section(Section.SONGS).names()

    def get_songs(self):
        """Return the songs, in the set's order."""
        return self._section(Section.SONGS).values()

    def add_new_song(self, name):
        """Add an empty song at the end, in the set's first scale if it has one, and return it."""
        song = Song.new(setlist=self)
        self.add_item(section=Section.SONGS, name=name, item=song)
        return song

    def add_started_song(self, name):
        """Add a song with its first track and scene at the end, which the Songs page's + does, and return it."""
        song = Song.started(setlist=self)
        # Filled in like a loaded song, so that a song added in the tracker saves every setting too.
        song.fill_in_defaults()
        self.add_item(section=Section.SONGS, name=name, item=song)
        return song

    def first_song_name(self):
        """Return the name of the first song, or None if the set has none."""
        names = self.get_song_names()
        return names[0] if names else None

    def first_scale_name(self):
        """Return the name of the first scale, which a new song starts in, or None if the set has none."""
        names = self.get_scale_names()
        return names[0] if names else None

    # What uses what across the set, so that the tracker can refuse to delete something still in use.

    # What names an item of a section, anywhere in the set, which is what uses the item. Each kind of
    # object says which of its settings name what (REFERENCES), so these ask the objects and know no section.

    def songs_naming(self, *, section, name):
        """Return the name of each song whose own setting names an item of a section: its scale or its groove."""
        return [song for song in self.get_song_names() if self.get_song(song).names_item(section=section, name=name)]

    def scenes_naming(self, *, section, name):
        """Return (song name, number, scene) for each scene that chose an item of a section, not counting the songs' own choices."""
        return [(song, number, scene) for song in self.get_song_names() for number, scene in self.get_song(song).scenes_naming(section=section, name=name)]

    def tracks_naming(self, *, section, name):
        """Return (song name, track name) for each track that chose an item of a section."""
        return [(song, track) for song in self.get_song_names() for track in self.get_song(song).tracks_naming(section=section, name=name)]

    def clip_slots_naming(self, *, section, name):
        """Return (song name, number, scene, track) for each clip that names an item of a section."""
        return [(song, number, scene, track) for song in self.get_song_names() for number, scene, track in self.get_song(song).clip_slots_naming(section=section, name=name)]

    def chains_naming(self, *, section, name):
        """Return the name of each chain that runs a generator of a section."""
        return [chain for chain in self.get_chain_names() if self.get_chain(chain).names_item(section=section, name=name)]

    def allowed_inc_max_for_pattern(self, *, name, register):
        """Return the narrowest Allowed Inc Max a register has in the songs that play a pattern, or None when no song plays it."""
        songs = dict.fromkeys(song for song, _, _, _ in self.clip_slots_naming(section=Section.PATTERNS, name=name))
        limits = [self.get_song(song).get_register(register).get_allowed_inc_max() for song in songs]
        return min(limits) if limits else None

    def hold_adds_within_limits(self):
        """Bring every pattern's += rows within the narrowest Allowed Inc Max of the songs that play it: lowering a limit changes what used it."""
        for name in self.get_pattern_names():
            pattern = self.get_pattern(name)
            for register, row in file_format.REGISTER_ADD_ROWS.items():
                if not pattern.adds_anything(row):
                    continue
                most = self.allowed_inc_max_for_pattern(name=name, register=register)
                if most is not None and pattern.adds_past(row=row, most=most):
                    pattern.hold_adds(row=row, most=most)

    def scales_for_pattern(self, name):
        """Return the name of every scale a pattern can play in: each clip's own that plays it, or else its scene's, or else its song's."""
        names = []
        for song in self.get_songs():
            for scene in song.get_scenes():
                for track in scene.clip_slots_naming(section=Section.PATTERNS, name=name):
                    names.append(scene.get_clip_slot(track).get_scale_name() or scene.get_scale_name() or song.get_scale_name())
        return [scale for scale in names if scale]

    # Looking up the set's named objects.

    def has_scale(self, name):
        return self._section(Section.SCALES).has(name)

    def get_scale_names(self):
        """Return the names of the set's scales, in the set's order."""
        return self._section(Section.SCALES).names()

    def get_named_scale(self, name):
        return self._section(Section.SCALES).get(name)

    def has_groove(self, name):
        """Return whether a name is a factory groove's or one of the set's own."""
        return is_factory_groove(name) or self._section(Section.GROOVES).has(name)

    def get_groove(self, name):
        """Return a groove by name: a factory groove, or one of the set's own."""
        if is_factory_groove(name):
            return factory_groove(name)
        return self._section(Section.GROOVES).get(name)

    def get_groove_names(self):
        """Return every groove a song can choose: the factory grooves, then the set's own in the set's order."""
        return [*groove.FACTORY_GROOVE_NAMES, *self.get_own_groove_names()]

    def get_own_groove_names(self):
        """Return the names of the set's own grooves, which the file writes, in the set's order."""
        return self._section(Section.GROOVES).names()

    def has_pattern(self, name):
        return self._section(Section.PATTERNS).has(name)

    def get_pattern(self, name):
        return self._section(Section.PATTERNS).get(name)

    def get_pattern_names(self):
        """Return the names of the patterns, in the set's order."""
        return self._section(Section.PATTERNS).names()

    def get_pattern_groups(self):
        """Return the names of the groups the patterns are in, sorted as names are, each once."""
        groups = {self.get_pattern(name).get_group() for name in self.get_pattern_names()}
        return sorted((group for group in groups if group is not None), key=name_order)

    def patterns_in_group(self, group):
        """Return the names of a group's patterns, sorted as names are; None is the patterns in no group."""
        return sorted((name for name in self.get_pattern_names() if self.get_pattern(name).get_group() == group), key=name_order)

    def get_closed_pattern_groups(self):
        """Return the groups the Patterns page shows closed, leaving out any that no pattern is in any more."""
        groups = self.get_pattern_groups()
        return [group for group in groups if group in self._closed_groups]

    @notes_change
    def rename_pattern_group(self, *, old, new):
        """Give a group another name, for every pattern in it, shown closed or open as it was."""
        for name in self.patterns_in_group(old):
            self.get_pattern(name).set_group(new)
        if old in self._closed_groups:
            self._closed_groups = [new if group == old else group for group in self._closed_groups]

    @notes_change
    def ungroup_patterns(self, group):
        """Take every pattern out of a group, deleting none."""
        for name in self.patterns_in_group(group):
            self.get_pattern(name).set_group(None)

    def names_in_copied_group(self, *, group, new):
        """Return the name each pattern of a group takes in a copy of the group under a new name, by the pattern copied, a taken name counting up."""
        taken = list(self.get_pattern_names())
        names = {}
        for name in self.patterns_in_group(group):
            names[name] = unique_name(base=name_in_copied_group(name=name, old=group, new=new), taken=taken)
            taken.append(names[name])
        return names

    @notes_change
    def copy_pattern_group(self, *, group, new):
        """Copy every pattern of a group into a new group, and return the copies' names. A name that would be longer than a name may be refuses the whole copy."""
        names = self.names_in_copied_group(group=group, new=new)
        too_long = [copied for copied in names.values() if len(copied) > set_limits.MAX_NAME_LENGTH]
        if too_long:
            raise ValueError(errors.ERR_GROUP_COPY_NAME_TOO_LONG.format(name=too_long[0], most=set_limits.MAX_NAME_LENGTH))
        for name, copied in names.items():
            self.copy_item(section=Section.PATTERNS, name=name, new=copied).set_group(new)
        return list(names.values())

    @notes_change
    def split_pattern(self, *, name, steps):
        """Make new patterns of a pattern's steps, so many steps each and the last with what is left, and return their names; the pattern itself is left as it is.

        Each part keeps the pattern's settings and group. A part's name longer than a name may be refuses the whole split.
        """
        pattern = self.get_pattern(name)
        starts = range(0, pattern.get_steps(), steps)
        made = split_part_names(name=name, count=len(starts), taken=self.get_pattern_names())
        too_long = [part for part in made if len(part) > set_limits.MAX_NAME_LENGTH]
        if too_long:
            raise ValueError(errors.ERR_GROUP_COPY_NAME_TOO_LONG.format(name=too_long[0], most=set_limits.MAX_NAME_LENGTH))
        for part, start in zip(made, starts):
            self.copy_item(section=Section.PATTERNS, name=name, new=part).take_steps(list(range(start, min(start + steps, pattern.get_steps()))))
        return made

    @notes_change
    def fracture(self, song):
        """Give every clip of a song a pattern of its own, and return the names of the copies made.

        The first clip to play a pattern, reading the scenes from the top and each scene's tracks from the left, keeps the
        pattern; every later clip that plays the same one plays a copy, named as a duplicate is and kept in the pattern's group,
        so that each clip can be edited without changing another. A clip that plays a list of patterns gets a copy of each one
        another clip plays, and a pattern it names twice in its own list stays one pattern.
        """
        seen = set()
        copies = []
        for scene in song.get_scenes():
            for track in song.get_track_names():
                clip_slot = scene.get_clip_slot(track)
                if clip_slot is None:
                    continue
                # A pattern the clip names twice stays one pattern inside the clip: only what another clip plays is copied.
                own = {}
                for name in clip_slot.get_pattern_names():
                    if name in own:
                        continue
                    own[name] = name
                    if name in seen:
                        own[name] = copy_name(name=name, taken=self.get_pattern_names())
                        self.copy_item(section=Section.PATTERNS, name=name, new=own[name])
                        copies.append(own[name])
                seen.update(own.values())
                if any(new != name for name, new in own.items()):
                    clip_slot.set_pattern_names(names=[own[name] for name in clip_slot.get_pattern_names()], song=song)
        return copies

    @notes_change
    def group_patterns_by_track(self, song):
        """Put every pattern of no group that a song plays in the group named after the first track that plays it, as the song wizard and an import do."""
        for scene in song.get_scenes():
            for track in song.get_track_names():
                if not scene.has_clip_slot(track):
                    continue
                for name in scene.get_clip_slot(track).get_pattern_names():
                    if self.get_pattern(name).get_group() is None:
                        self.get_pattern(name).set_group(track)

    def first_track_playing(self, pattern):
        """Return the name of the first track, in any song, with a clip that plays a pattern, or nothing when no clip plays it."""
        for song in self.get_song_names():
            song = self.get_song(song)
            for scene in song.get_scenes():
                for track in song.get_track_names():
                    if scene.has_clip_slot(track) and pattern in scene.get_clip_slot(track).get_pattern_names():
                        return track
        return None

    def is_pattern_group_closed(self, group):
        return group in self._closed_groups

    @notes_change
    def show_pattern_group(self, *, group, closed):
        """Show a group closed or open on the Patterns page. This changes nothing of the set's data: it is neither undone nor an unsaved change."""
        self._closed_groups = [name for name in self._closed_groups if name != group]
        if closed:
            self._closed_groups.append(group)

    def get_open_generator_types(self):
        """Return the kinds of generator the Generators page shows open, in the order kinds are listed, leaving out any the set has no generator of any more."""
        return [kind for kind in file_format.NAMED_GENERATORS if kind in self._open_types and self._section(file_format.NAMED_GENERATORS[kind]).names()]

    def is_generator_type_open(self, kind):
        return kind in self._open_types

    @notes_change
    def show_generator_type(self, *, kind, opened):
        """Show a type of generator open or closed on the Generators page. This changes nothing of the set's data: it is neither undone nor an unsaved change."""
        self._open_types = [held for held in self._open_types if held != kind]
        if opened:
            self._open_types.append(kind)

    def has_generator(self, *, kind, name):
        """Return whether there's a generator of a kind, like arp, with this name."""
        return self._section(file_format.NAMED_GENERATORS[kind]).has(name)

    def get_generator_settings(self, *, kind, name):
        return self._section(file_format.NAMED_GENERATORS[kind]).get(name)

    def get_generator_names(self, kind):
        """Return the names of the generators of a kind, like arp, in the set's order."""
        return self._section(file_format.NAMED_GENERATORS[kind]).names()

    def has_chain(self, name):
        return self._section(Section.CHAINS).has(name)

    def has_instrument(self, name):
        return self._section(Section.INSTRUMENTS).has(name)

    def get_instrument(self, name):
        return self._section(Section.INSTRUMENTS).get(name)

    def get_instrument_names(self):
        return self._section(Section.INSTRUMENTS).names()

    def is_real_time(self):
        """Return whether the set plays in real time through its instruments, the main screen's Real Time switch."""
        return self._setting(name=SetlistSetting.REAL_TIME, default=defaults.DEFAULT_REAL_TIME)

    def get_visualizer(self):
        """Return the visualizer mode Arrange's visualizer key shows first, by its name, unless a song names its own, or None for the first in the list."""
        return self._settings[SetlistSetting.VISUALIZER]

    @notes_change
    def set_visualizer(self, name):
        """Name the visualizer mode shown first, or None for the first in the list; a name that isn't a mode's is None."""
        self._settings[SetlistSetting.VISUALIZER] = sensible_visualizer(name)

    def visualizer_for(self, song):
        """Return the visualizer mode shown first for a song: the song's own, else the set's, else None."""
        return song.get_visualizer() or self.get_visualizer()

    def get_hidden_visualizers(self):
        """Return the names of the visualizer modes left out of Arrange's visualizer key, in the modes' order."""
        hidden = self._settings[SetlistSetting.HIDDEN_VISUALIZERS] or []
        return [name for name in file_format.VISUALIZER_NAMES if name in hidden]

    @notes_change
    def set_visualizer_hidden(self, *, name, hidden):
        """Leave a visualizer mode out of Arrange's visualizer key, or put it back."""
        names = set(self.get_hidden_visualizers())
        if hidden:
            names.add(name)
        else:
            names.discard(name)
        self._settings[SetlistSetting.HIDDEN_VISUALIZERS] = sensible_hidden_visualizers(list(names))

    def get_chain(self, name):
        return self._section(Section.CHAINS).get(name)

    def generator_kind(self, name):
        """Return the kind of the generator of a name, chain for a chain, or None for a name no generator has."""
        return next((kind for kind, section in file_format.LISTED_GENERATORS.items() if self._section(section).has(name)), None)

    def has_generator_named(self, name):
        """Return whether a generator of any kind, a chain among them, has a name."""
        return name in self.every_generator_name()

    def chain_run(self, name):
        """Return the chain a name in a clip's, a scene's or a track's list of generators runs: the chain of that name, or, for a
        generator of another kind, a chain of that generator alone, made for the asking."""
        if self.has_chain(name):
            return self.get_chain(name)
        kind = next(kind for kind, section in file_format.NAMED_GENERATORS.items() if self._section(section).has(name))
        return Chain([(kind, name)])

    def get_chain_names(self):
        """Return the names of the chains, in the set's order."""
        return self._section(Section.CHAINS).names()

