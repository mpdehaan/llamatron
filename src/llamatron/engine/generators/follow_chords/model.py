# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The settings of the follow chords generator: their names, their checks and their defaults, as a set file holds them."""

from llamatron.caching.revised import notes_change
from llamatron.engine.generators.follow_chords.generator import FollowChords
from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.model.schema.file_format import Section
from llamatron.model.schema.setting import described, Text
from llamatron.user_strings import errors

class FollowChordsSetting:
    """A Follow Chords' settings, as a file names them: the track whose chords it follows."""

    CHORDS_FROM = 'chords_from'


class FollowChordsSettings(GeneratorSettings):
    """A Follow Chords' settings: the track whose chords a clip's notes are moved to.

    The Realizer hands the generator the chords that track plays in the clip's scene, after that
    track's own chains, so the settings hold only the track's name, and a rename of that track follows.
    """

    __slots__ = ()

    GENERATOR = FollowChords
    SETTINGS = described(Text(name=FollowChordsSetting.CHORDS_FROM, error=errors.ERR_NOT_TEXT))
    REFERENCES = {Section.TRACKS: (FollowChordsSetting.CHORDS_FROM,)}

    @classmethod
    def new(cls):
        """Return the settings a new Follow Chords starts with: no track, so that it moves nothing until one is chosen."""
        return cls({})

    def get_chords_from(self):
        """Return the name of the track whose chords it follows, or None for none."""
        return self.get_written(FollowChordsSetting.CHORDS_FROM)

    def names_item(self, *, section, name):
        return section == Section.TRACKS and self.get_chords_from() == name

    @notes_change
    def _rename_own_references(self, *, section, old, new):
        self._settings[FollowChordsSetting.CHORDS_FROM] = new
