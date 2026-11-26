# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The song wizard's choices of the player beside the tune: who answers the player who has the tune, what the answering player
does in each section, and how busy the player is."""

from llamatron.user_strings import errors
from llamatron.wizards.create_song import arranger, interplay as interplay_values, wizard_limits, wizard_names
from llamatron.wizards.create_song.choices_part import ChoicesPart


class InterplayChoices(ChoicesPart):
    """What was chosen of the player beside the tune: who answers the tune, the one thing the answering player does in every
    section or else the genre's plan, and how busy the player is. A song saved before answering could be chosen has none of
    it, and keeps to what was made then."""

    __slots__ = ('_offered', '_answerer', '_way', '_busy')

    def __init__(self, *, choices):
        ChoicesPart.__init__(self, choices=choices)
        self.reset()

    def reset(self):
        """Go back to a song with nobody beside the tune."""
        self.forget()

    def forget(self):
        """Forget who answers the tune, what the player does and how busy, as a song saved before answering could be chosen has none."""
        self._offered = False
        self._answerer = None
        self._way = None
        self._busy = None

    def take_usual(self):
        """Take how a new song starts: answered by the genre's answering player, going by the genre's plan, as busy as the genre says."""
        self._offered = True
        self._answerer = self._usual_answerer()
        self._way = None
        self._busy = self._usual_busy()

    # What a song saves of the player beside the tune, and what the player adds to the song made.

    def to_data(self):
        """Return what a song saves of the player beside the tune, as plain data, or nothing where answering is not offered."""
        if not self._offered:
            return {}
        beside = {wizard_limits.BY: self._answerer, wizard_limits.WAY: self._way, wizard_limits.BUSY_BESIDE: self._busy}
        return {wizard_limits.BESIDE_SAVED: beside}

    def restore(self, saved):
        """Restore the player beside the tune a song saved, leaving it out where it no longer fits."""
        beside = saved.value(wizard_limits.BESIDE_SAVED)
        if isinstance(beside, dict):
            saved.apply(self._restore_beside, beside=beside)

    def _restore_beside(self, *, beside):
        by = beside.get(wizard_limits.BY)
        way = beside.get(wizard_limits.WAY)
        busy = beside.get(wizard_limits.BUSY_BESIDE, self._usual_busy())
        band = self._choices.get_band()
        # Who answers is saved as chosen even where the player cannot answer now, as the solo's player hidden by one guitarist, and answers again once the player can.
        if (by is not None and by not in band.roles()) or (way is not None and way not in interplay_values.WAYS):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_ANSWERER.format(value=by))
        self._refuse_busy(busy)
        self._offered = True
        self._answerer = by
        self._way = way
        self._busy = busy

    def counted(self):
        """Return the setting another genre forgets, under a name of its own, so that two songs can be compared setting by setting."""
        beside = self.to_data().get(wizard_limits.BESIDE_SAVED)
        return {(wizard_limits.GENRE_SETTING, wizard_limits.BESIDE_SAVED): beside}

    def add_picks(self, picks):
        """Add the song's player beside the tune to its picks, with what the player does in each section of the form in order:
        nothing for a song saved before answering could be chosen, or for a genre nobody answers in."""
        usual = self._usual_answerer()
        if not self._offered or usual is None:
            return
        player = self._choices.player(usual)
        if not player.is_in():
            return
        picks[arranger.BESIDE] = {arranger.ROLE: usual, arranger.BESIDE_BUSY: self._busy, arranger.BESIDE_WAYS: self._ways_of_sections()}

    def _ways_of_sections(self):
        """Return what the player beside the tune does in each section of the form, in order: where nobody answers, the player waits."""
        answered = self.answered_by() is not None
        form = self._choices.get_song_form()
        section_count = len(form.section_entries())
        ways = []
        for place in range(section_count):
            section = self._choices.section(place)
            if answered and section.has_role():
                ways.append(section.role())
            else:
                ways.append(interplay_values.WAITS)
        return ways

    # Who answers the tune.

    def answerers(self):
        """Return the players who may answer the tune: the genre's answering player while in the band, and none where the song
        keeps to what was made before answering could be chosen."""
        usual = self._usual_answerer()
        if not self._offered or usual is None:
            return []
        player = self._choices.player(usual)
        if not player.is_in():
            return []
        return [usual]

    def answered_by(self):
        """Return the player who answers the tune, or None where nobody does."""
        if self._answerer not in self.answerers():
            return None
        return self._answerer

    def set_answered_by(self, role):
        """Choose who answers the tune, or nobody with None."""
        if not self._offered or (role is not None and role not in self.answerers()):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_ANSWERER.format(value=role))
        self._answerer = role

    # What the answering player does: one thing in every section, or the genre's plan section by section.

    def ways_beside(self):
        """Return what a player beside the tune may do in a section, in order."""
        return list(interplay_values.WAYS)

    def get_role_plan(self):
        """Return the one thing the answering player does in every section, or None where the player goes by the genre's plan."""
        return self._way

    def set_role_plan(self, way):
        """Have the answering player do one thing in every section, or go by the genre's plan with None. Either drops what single sections were given."""
        if self.answered_by() is None or (way is not None and way not in interplay_values.WAYS):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_WAY_BESIDE.format(value=way))
        self._way = way
        form = self._choices.get_song_form()
        form.forget_section_beside()

    def planned_role(self, place):
        """Return what the plan has the answering player do in a section: the one thing chosen for every section, or what the
        genre's plan says of the section's kind, and waiting where the plan says nothing."""
        if self._way is not None:
            return self._way
        section = self._choices.section(place)
        plan = self._genre_plan()
        return plan.get(section.kind(), interplay_values.WAITS)

    # How busy the answering player is.

    def has_fills_busy(self):
        """Return whether how busy the answering player is can be chosen: somebody answers."""
        return self.answered_by() is not None

    def get_fills_busy(self):
        return self._busy

    def set_fills_busy(self, busy):
        if not self.has_fills_busy():
            raise ValueError(errors.ERR_WIZARD_FILLS_BUSY.format(low=wizard_names.INTERPLAY_LEAST_BUSY, high=wizard_names.INTERPLAY_MOST_BUSY, value=busy))
        self._refuse_busy(busy)
        self._busy = busy

    @staticmethod
    def _refuse_busy(busy):
        """Refuse how busy the answering player is unless it is an integer in the range a page offers."""
        is_integer = isinstance(busy, int) and not isinstance(busy, bool)
        if not is_integer or not wizard_names.INTERPLAY_LEAST_BUSY <= busy <= wizard_names.INTERPLAY_MOST_BUSY:
            raise ValueError(errors.ERR_WIZARD_FILLS_BUSY.format(low=wizard_names.INTERPLAY_LEAST_BUSY, high=wizard_names.INTERPLAY_MOST_BUSY, value=busy))

    # What the genre says of playing beside the tune.

    def _genre_interplay(self):
        """Return what the genre says of playing beside the tune: a plan of what is done in each kind of section, with a plan of
        its own for some subgenres, and how busy."""
        if not self._choices.is_ready():
            return {}
        style = self._choices.style()
        return style.get(wizard_limits.INTERPLAY, {})

    def _genre_plan(self):
        """Return what the genre's plan has the answering player do in each kind of section, the subgenre's own plan first."""
        interplay = self._genre_interplay()
        plan = dict(interplay.get(wizard_limits.PLAN, {}))
        by_subgenre = interplay.get(wizard_limits.BY_SUBGENRE, {})
        plan.update(by_subgenre.get(self._choices.get_subgenre(), {}))
        return plan

    def _usual_busy(self):
        """Return how busy the genre has the answering player."""
        interplay = self._genre_interplay()
        return interplay.get(wizard_limits.BUSY_BESIDE, interplay_values.USUAL_BUSY)

    def _usual_answerer(self):
        """Return the player the genre has answer the tune, where the player can play in the subgenre, or None."""
        role = self.genre_answerer()
        band = self._choices.get_band()
        if role is None or role not in band.roles_shown():
            return None
        player = self._choices.player(role)
        if not player.can_play():
            return None
        return role

    def genre_answerer(self):
        """Return the player the genre's roles mark as the one who answers the tune, or None."""
        if not self._choices.is_ready():
            return None
        style = self._choices.style()
        for entry in style[arranger.ROLES]:
            if entry.get(arranger.ANSWERS):
                return entry[arranger.ROLE]
        return None
