# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The settings of the hocket generator: their names, their checks and their defaults, as a set file holds them."""

from llamatron.caching.revised import notes_change
from llamatron.engine.generators import settings_base
from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import Section
from llamatron.model.schema.setting import described, Text
from llamatron.user_strings import errors

# Each generator a chain step can name, and the class that holds its settings.
class HocketSetting:
    """A Hocket's settings, as a file names them: the track whose notes it shares out."""

    RESTART = file_format.GENERATOR_RESTART

    SOURCE = 'source'


class HocketSettings(GeneratorSettings):
    """A Hocket's settings: the source track whose notes the hocketing tracks take turns at, and its Restart.

    Like a drift, it runs on no clip's notes itself: the Realizer works out each scene's turns
    once from the source track's clip, and hands each hocketing clip its notes, which the
    exporters' timing adds to the clip's own (engine/timing/timing.py), so GENERATOR is None. The
    source names a track of the song it plays in, and a rename of that track follows.
    """

    __slots__ = ()

    GENERATOR = None
    SETTINGS = described(Text(name=HocketSetting.SOURCE, error=errors.ERR_NOT_TEXT), settings_base.RESTART_SETTING)
    REFERENCES = {Section.TRACKS: (HocketSetting.SOURCE,)}

    @classmethod
    def new(cls):
        """Return the settings a new Hocket starts with: no source, so that it hands out nothing until one is chosen."""
        return cls({})

    def get_source(self):
        """Return the name of the track whose notes it shares out, or None for none."""
        return self.get_written(HocketSetting.SOURCE)

    def names_item(self, *, section, name):
        return section == Section.TRACKS and self.get_source() == name

    @notes_change
    def _rename_own_references(self, *, section, old, new):
        self._settings[HocketSetting.SOURCE] = new
