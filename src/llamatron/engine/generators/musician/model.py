# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The settings of the musician generator: their names, their checks and their defaults, as a set file holds them."""

from llamatron.caching.revised import notes_change
from llamatron.engine.generators.musician import generator as musician, schema
from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.model.file import corrections
from llamatron.model.file.checks import listed, pass_over_unknown, reading, refuse_unknown
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects.llama_data import or_default, own_copy
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import Section
from llamatron.model.schema.setting import check_settings, Checked, Choice, described, Flag, Text, WholeNumber
from llamatron.user_strings import errors


def usual_notes(instrument):
    """Return how long an instrument's musician plays its notes unless set: as written or short."""
    return musician.MUSICIANS[instrument].USUAL_NOTES


def usual_gives_way(instrument):
    """Return how far an instrument's musician gives way to the others unless set."""
    return musician.MUSICIANS[instrument].USUAL_GIVES_WAY

class MusicianSetting:
    """A musician's settings, as a file names them."""

    INSTRUMENT = 'instrument'
    CHORDS_FROM = 'chords_from'
    TUNE_FROM = 'tune_from'
    ACTIVITY = 'activity'
    LOUDNESS = 'loudness'
    LOOSENESS = 'looseness'
    GIVES_WAY = 'gives_way'
    ACCENTS = 'accents'
    NOTES = 'notes'
    RANGE = 'range'
    BY_SECTION = 'by_section'


# What a kind of section has of its own for a musician: whether the musician plays there, and how the part is played.
MUSICIAN_BY_SECTION = described(
    Flag(name=schema.PLAYS, error=errors.ERR_MUSICIAN_PLAYS_NOT_TRUE_OR_FALSE),
    Choice(name=schema.PLAYED, choices=schema.FORMS, default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE),
)


# What a musician does with each setting left out, but for how it gives way and holds its notes, which its instrument says.
MUSICIAN_DEFAULTS = {
    MusicianSetting.INSTRUMENT: schema.RHYTHM_GUITARIST, MusicianSetting.ACTIVITY: schema.AS_WRITTEN, MusicianSetting.LOUDNESS: musician.USUAL_LOUDNESS,
    MusicianSetting.LOOSENESS: schema.TIGHT, MusicianSetting.ACCENTS: schema.NO_ACCENTS, MusicianSetting.RANGE: schema.AS_WRITTEN,
}


MUSICIAN_SECTION_DEFAULTS = {schema.PLAYS: True, schema.PLAYED: schema.WHOLE}


def check_musician_by_section(value):
    """Raise InvalidValue unless a value is settings by kind of section, each whether a musician plays there and how the part is played."""
    if not isinstance(value, dict) or any(section not in file_format.SECTION_KINDS or not isinstance(own, dict) for section, own in value.items()):
        raise InvalidValue(errors.ERR_BAD_BY_SECTION.format(choices=listed(file_format.SECTION_KINDS), value=value))
    for own in value.values():
        refuse_unknown(data=own, allowed=MUSICIAN_BY_SECTION)
        check_settings(settings=MUSICIAN_BY_SECTION, data=own)


class MusicianSettings(GeneratorSettings):
    """A musician's settings: the instrument, the tracks the chords and the tune are read from, the player's touch, and what each kind of section has of its own.

    The Realizer hands the generator what is round its clip, the scene's kind of section and the
    chords and the tune of the tracks named, so the settings hold only the tracks' names, which a
    rename of either track follows, and are asked for the generator of one clip (generator_for).
    """

    __slots__ = ()

    GENERATOR = musician.Musician
    SETTINGS = described(
        Choice(name=MusicianSetting.INSTRUMENT, choices=schema.INSTRUMENTS, default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE),
        Text(name=MusicianSetting.CHORDS_FROM, error=errors.ERR_NOT_TEXT),
        Text(name=MusicianSetting.TUNE_FROM, error=errors.ERR_NOT_TEXT),
        Choice(name=MusicianSetting.ACTIVITY, choices=schema.ACTIVITIES, default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE),
        WholeNumber(name=MusicianSetting.LOUDNESS, lowest=schema.QUIETEST, highest=schema.LOUDEST, error=errors.ERR_BAD_SHAPE_PERCENT),
        WholeNumber(name=MusicianSetting.LOOSENESS, lowest=schema.TIGHT, highest=schema.LOOSEST, error=errors.ERR_BAD_SHAPE_PERCENT),
        Choice(name=MusicianSetting.GIVES_WAY, choices=schema.GIVES_WAY, default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE),
        Choice(name=MusicianSetting.ACCENTS, choices=schema.ACCENTS, default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE),
        Choice(name=MusicianSetting.NOTES, choices=schema.NOTE_LENGTHS, default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE),
        Choice(name=MusicianSetting.RANGE, choices=schema.RANGES, default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE),
        Checked(name=MusicianSetting.BY_SECTION, check=check_musician_by_section),
    )
    REFERENCES = {Section.TRACKS: (MusicianSetting.CHORDS_FROM, MusicianSetting.TUNE_FROM)}

    @classmethod
    def pass_over_unknown_names(cls, data):
        """Take out every name the musician doesn't have, a kind of section and its own settings for one included, so that a file
        saved before one was taken away, or by a later version, still opens."""
        super().pass_over_unknown_names(data)
        by_section = data.get(MusicianSetting.BY_SECTION)
        if isinstance(by_section, dict):
            pass_over_unknown(data=by_section, allowed=file_format.SECTION_KINDS)
            for own in by_section.values():
                if isinstance(own, dict):
                    pass_over_unknown(data=own, allowed=MUSICIAN_BY_SECTION)

    @classmethod
    def new(cls):
        """Return the settings a new musician starts with: a rhythm guitarist who reads no track yet and plays every section whole."""
        return cls({})

    def musician_class(self):
        """Return the class of the musician who plays the instrument."""
        return musician.MUSICIANS[self.get_own(MusicianSetting.INSTRUMENT)]

    def get_own(self, name):
        """Return one of the musician's settings, or what the musician does with the setting left out, which for how the musician gives way and holds its notes is the instrument's."""
        if name == MusicianSetting.GIVES_WAY:
            return or_default(value=self.get_written(name), default=self.musician_class().USUAL_GIVES_WAY)
        if name == MusicianSetting.NOTES:
            return or_default(value=self.get_written(name), default=self.musician_class().USUAL_NOTES)
        return or_default(value=self.get_written(name), default=MUSICIAN_DEFAULTS[name])

    def follows_instrument(self, name):
        """Return whether a setting is left to the instrument: how the musician gives way or holds its notes, with nothing written for it."""
        return self.get_written(name) is None

    def get_chords_from(self):
        """Return the name of the track whose chords the musician follows, or None for none."""
        return self.get_written(MusicianSetting.CHORDS_FROM)

    def get_tune_from(self):
        """Return the name of the track that carries the tune the musician plays round, or None for none."""
        return self.get_written(MusicianSetting.TUNE_FROM)

    def get_section_own(self, *, section, name):
        """Return what a kind of section says of its own for one setting, or None where it says nothing."""
        return (self.get_written(MusicianSetting.BY_SECTION) or {}).get(section, {}).get(name)

    def get_for(self, *, section, name):
        """Return whether the musician plays in a kind of section, or how the part is played there: the section's own, or else playing it whole."""
        own = self.get_section_own(section=section, name=name)
        if own is None:
            return MUSICIAN_SECTION_DEFAULTS[name]
        return own

    @notes_change
    def set_section_own(self, *, section, name, value):
        """Set what a kind of section says of its own for one setting, checked as a file's is, or None for what a section does unasked."""
        by_section = own_copy(self.get_written(MusicianSetting.BY_SECTION) or {})
        own = by_section.setdefault(section, {})
        if value is None:
            own.pop(name, None)
        else:
            own[name] = value
        by_section = {kind: values for kind, values in by_section.items() if values}
        check_musician_by_section(by_section)
        if by_section:
            self._settings[MusicianSetting.BY_SECTION] = by_section
        else:
            self._settings.pop(MusicianSetting.BY_SECTION, None)

    def names_item(self, *, section, name):
        return section == Section.TRACKS and name in (self.get_chords_from(), self.get_tune_from())

    @notes_change
    def _rename_own_references(self, *, section, old, new):
        for setting in self.REFERENCES[section]:
            if self._settings.get(setting) == old:
                self._settings[setting] = new

    def generator_for(self, *, where, bar, beat, surroundings, seed):
        """Return the musician of one clip: with bars and beats of a length, what is round the clip, and the seed a loose player's loudness is drawn from."""
        with reading(where):
            self.check_data(self._settings)
        return self.musician_class()(
            bar=bar, beat=beat, surroundings=surroundings, activity=self.get_own(MusicianSetting.ACTIVITY), loudness=self.get_own(MusicianSetting.LOUDNESS),
            looseness=self.get_own(MusicianSetting.LOOSENESS), gives_way=self.get_own(MusicianSetting.GIVES_WAY), accents=self.get_own(MusicianSetting.ACCENTS),
            notes=self.get_own(MusicianSetting.NOTES), range=self.get_own(MusicianSetting.RANGE), by_section=own_copy(self.get_written(MusicianSetting.BY_SECTION) or {}), seed=seed,
        )
