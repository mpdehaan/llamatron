# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""One kind of section's own melody in the song wizard: how high it sits and how busy it is, apart from the whole song's."""

from llamatron.user_strings import errors
from llamatron.wizards.create_song import arranger, melody as melody_writer, wizard_limits, wizard_names


class SectionMelody:
    """What a kind of section, such as the chorus, was given of its own melody: how high it sits and how busy it is, each
    left to the genre and the song until chosen. Reached as melody_ways().of_kind(kind)."""

    __slots__ = ('_choices', '_kind')

    def __init__(self, *, choices, kind):
        self._choices = choices
        self._kind = kind

    def fields(self):
        """Return the fields of the kind's own melody that are heard in the subgenre: how high it sits and how busy it is."""
        if not self._has_melody():
            return []
        return [field for field in wizard_limits.SECTION_MELODY_WAYS if self.ways_offered(field)]

    def _has_melody(self):
        """Return whether the kind of section has a melody of its own to choose: the subgenre writes one there."""
        if not self._choices.is_ready():
            return False
        tunes = self._choices.get_tunes()
        style = self._choices.style()
        return self._kind in tunes.tune_kinds() and self._kind in style[arranger.SECTIONS]

    def ways_offered(self, field):
        """Return the values of a field of the kind's own melody that are heard in the song as it stands: each that makes
        another song than the field left to the genre or the song, and the one chosen."""
        ways = self._choices.melody_ways()
        heard = ways.values_heard(field=field, kind=self._kind)
        chosen = self.get_way(field)
        return [value for value in wizard_limits.SECTION_MELODY_WAYS[field] if value in heard or value == chosen]

    def get_way(self, field):
        """Return what the kind says of its own melody in one field, or None where nothing was chosen."""
        own = self._own()
        chosen = own.get(field)
        if chosen in wizard_limits.SECTION_MELODY_WAYS[field]:
            return chosen
        return None

    def set_way(self, *, field, value):
        """Choose how high the kind's melody sits or how busy it is, or leave it to the genre or the song with None."""
        tunes = self._choices.get_tunes()
        known = field in wizard_limits.SECTION_MELODY_WAYS and (value is None or value in wizard_limits.SECTION_MELODY_WAYS[field])
        if not known or self._kind not in tunes.tune_kinds():
            raise ValueError(errors.ERR_WIZARD_MELODY_WAY.format(field=field, value=(self._kind, value)))
        ways = self._choices.melody_ways()
        ways.keep_chosen(field=field, value=value, kind=self._kind)

    def asks(self):
        """Return what the arranger is asked of the kind's lines: how high they sit and how busy they are, where either was chosen."""
        own = self._own()
        asks = {}
        height = own.get(wizard_names.MELODY_HEIGHT)
        if height in melody_writer.HEIGHTS:
            asks[wizard_names.MELODY_HEIGHT] = height
        busy = own.get(wizard_limits.MELODY_BUSY)
        if busy in wizard_limits.BUSY_POSITIONS:
            asks[melody_writer.LINE_BUSY] = wizard_limits.BUSY_POSITIONS[busy]
        return asks

    def _own(self):
        """Return what was chosen of the kind's own melody, as the song's extras hold it."""
        chosen = self._choices.get_extra(wizard_limits.MELODY_CHOSEN) or {}
        by_kind = chosen.get(melody_writer.BY_KIND, {})
        return by_kind.get(self._kind, {})
