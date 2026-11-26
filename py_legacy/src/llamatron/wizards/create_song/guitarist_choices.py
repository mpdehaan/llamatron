# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The song wizard's choice of one guitarist or two: a band whose one guitarist plays the chords and takes the solo, the
chords stopping where the solo plays, shown as one player."""

from llamatron.user_strings import errors
from llamatron.wizards.create_song import arranger, wizard_limits
from llamatron.wizards.create_song.choices_part import ChoicesPart


class GuitaristChoices(ChoicesPart):
    """How many guitarists the band has: two, one for the chords and one for the solo, or one who plays both, where the
    genre says which two players the one would be. Reached as choices.guitarists()."""

    __slots__ = ('_count',)

    def __init__(self, *, choices):
        ChoicesPart.__init__(self, choices=choices)
        self.reset()

    def reset(self):
        """Go back to two guitarists."""
        self._count = wizard_limits.TWO_GUITARISTS

    def to_data(self):
        """Return what a song saves of the guitarists, as plain data a song file saves: only what was chosen."""
        if self._count == wizard_limits.TWO_GUITARISTS:
            return {}
        return {wizard_limits.GUITARISTS_SAVED: self._count}

    def restore(self, saved):
        """Restore how many guitarists a song saved, leaving it out where it no longer fits."""
        count = saved.value(wizard_limits.GUITARISTS_SAVED)
        if count:
            saved.apply(self.set_count, count)

    def counted(self):
        """Return the setting another genre forgets, under a name of its own, so that two songs can be compared setting by setting."""
        return {(wizard_limits.GENRE_SETTING, wizard_limits.GUITARISTS_SAVED): self._count}

    def one_plays(self):
        """Return which two players one guitarist plays, and the way the solo is played on the guitar, as the genre says, or None."""
        if not self._choices.is_ready():
            return None
        style = self._choices.style()
        return style.get(wizard_limits.ONE_GUITARIST)

    def get_count(self):
        return self._count

    def has_one(self):
        """Return whether one guitarist plays both the chords and the solo."""
        return self._count == wizard_limits.ONE_GUITARIST_COUNT

    def offers_one(self):
        """Return whether the band can have one guitarist: the genre says which two players the one would be, and the solo can
        be a guitar's."""
        one = self.one_plays()
        if not one:
            return False
        chords_player = self._choices.player(one[wizard_limits.CHORDS_PLAYER])
        if not chords_player.can_play():
            return False
        soloist = one[wizard_limits.SOLO_PLAYER]
        solo_player = self._choices.player(soloist)
        band = self._choices.get_band()
        trait = band.role_named(soloist)[arranger.TRAIT]
        return one[wizard_limits.SOLO_WAY] in solo_player.ways(trait=trait)

    def set_count(self, count):
        """Choose two guitarists or one. One guitarist takes the solo on the guitar, whatever took it before."""
        if isinstance(count, bool) or count not in wizard_limits.GUITARIST_COUNTS or (count == wizard_limits.ONE_GUITARIST_COUNT and not self.offers_one()):
            raise ValueError(errors.ERR_WIZARD_GUITARISTS.format(value=count))
        self._count = count
        if count == wizard_limits.ONE_GUITARIST_COUNT:
            self._give_one_the_solo()

    def _give_one_the_solo(self):
        """Have the one guitarist take the solo on the guitar: the solo's player comes back if left out, playing the guitar's way."""
        one = self.one_plays()
        soloist = one[wizard_limits.SOLO_PLAYER]
        band = self._choices.get_band()
        band.take_back(soloist)
        trait = band.role_named(soloist)[arranger.TRAIT]
        band.keep_way(trait=trait, value=one[wizard_limits.SOLO_WAY])

    def hidden_player(self):
        """Return the player of the solo where one guitarist plays both parts, whom the screen does not show apart, or None."""
        if not self.has_one():
            return None
        one = self.one_plays()
        return one[wizard_limits.SOLO_PLAYER]

    def plays_in_section(self, plays):
        """Return who plays in a section where one guitarist plays both parts: the chords stop where the solo plays; or None
        where the section is played as it is."""
        if not self.has_one():
            return None
        one = self.one_plays()
        chords_player = one[wizard_limits.CHORDS_PLAYER]
        if one[wizard_limits.SOLO_PLAYER] not in plays or chords_player not in plays:
            return None
        return [role for role in plays if role != chords_player]
