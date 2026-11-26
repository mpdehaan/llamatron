# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The fade of one section of the song wizard's form: a section that opens the song fades in, one that closes it fades out."""

from llamatron.wizards.create_song import song_plan, wizard_limits, wizard_names

# A section's fade: whether it fades, the level it fades from or to, and the bars the fade takes.
FADE_FIELDS = (wizard_names.SONG_PLAN_FADES, wizard_names.FADE_LEVEL, wizard_names.FADE_OVER)


def without_fade(own):
    """Return what a section says of its own, leaving out its fade."""
    return {field: value for field, value in own.items() if field not in FADE_FIELDS}


class SectionFade:
    """The fade of one section of the form, by the section's place: whether the section can fade in or out, the fields of
    its fade, and what it says of its own with its fade worked out. Reached as choices.section(place).fade()."""

    __slots__ = ('_choices', '_place')

    def __init__(self, *, choices, place):
        self._choices = choices
        self._place = place

    def way(self):
        """Return how a section can fade: in, for a section that opens the song before its first tune; out, for one that closes
        the song after its last; and None for any other and for a held chord."""
        section = self._choices.section(self._place)
        if section.is_held():
            return None
        form = self._choices.get_song_form()
        if self._place < form.head_count():
            return wizard_limits.FADE_IN
        closing_from = len(form.section_entries()) - form.tail_count()
        if self._place >= closing_from:
            return wizard_limits.FADE_OUT
        return None

    def fields(self):
        """Return the fields of a section's fade, in the order shown: the switch where the section can fade, and while it is on,
        the level the fade starts from or ends at, and the bars the fade takes, the first of the section for a fade in and the last for a fade out."""
        if self.way() is None:
            return []
        section = self._choices.section(self._place)
        if not section.own(field=wizard_names.SONG_PLAN_FADES):
            return [wizard_names.SONG_PLAN_FADES]
        return list(FADE_FIELDS)

    def with_way(self, *, own):
        """Return what a section says of its own, with whether its fade is a fade in and the bars the fade takes, never more than
        the section has. A section that does not fade, or that was moved to where none does, says nothing of a fade."""
        way = self.way()
        if not own.get(wizard_names.SONG_PLAN_FADES) or way is None:
            return without_fade(own)
        faded = dict(own)
        if way == wizard_limits.FADE_IN:
            faded[song_plan.FADES_IN] = True
        section = self._choices.section(self._place)
        bars = section.bars()
        faded[wizard_names.FADE_OVER] = min(own.get(wizard_names.FADE_OVER, bars), bars)
        return faded

    def from_plan(self, field):
        """Return a section's fade as it is given none: no fade, from silence, over the whole section."""
        if field == wizard_names.SONG_PLAN_FADES:
            return False
        if field == wizard_names.FADE_LEVEL:
            return wizard_names.FADED
        section = self._choices.section(self._place)
        return section.bars()
