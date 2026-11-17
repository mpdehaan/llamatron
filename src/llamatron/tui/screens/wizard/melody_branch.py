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
"""The wizard's Melody branch, under Composition: the melody style the song's tunes are written by, and the smart style's gauges."""

from llamatron.macro_composer import phrasing
from llamatron.macro_composer.melody import HIGHEST_GAUGE, LOWEST_GAUGE
from llamatron.macro_composer.wizard_choices import PHRASING_OFFERED
from llamatron.strings.labels import MSG_WIZARD_EARLY_SHOWN, MSG_WIZARD_GAUGE_ENDS, MSG_WIZARD_GAUGE_LABELS, MSG_WIZARD_PHRASING_LABEL, MSG_WIZARD_PHRASING_WAY_LABELS, MSG_WIZARD_MELODY_BRANCH, MSG_WIZARD_MELODY_LABEL, MSG_WIZARD_MELODY_SETTING_LABELS, MSG_WIZARD_USUAL_MELODY
from llamatron.strings.marks import MSG_WIZARD_GAUGE_EMPTY, MSG_WIZARD_GAUGE_FULL, MSG_WIZARD_GENRE_MELODY_SHOWN, MSG_WIZARD_MELODY_GAUGE_SHOWN
from llamatron.strings.messages import MSG_WIZARD_LISTEN_TUNE
from llamatron.tui.screens.shared.field import ChoiceField, NumberField, Toggle
from llamatron.tui.screens.wizard.song_ways_branch import A_CHOICE, SongWaysBranch


class MelodyBranch(SongWaysBranch):
    """The song's melody style, the gauges of the smart style and the settings of the style in use; a style for each kind of section is to come."""

    __slots__ = ()

    def name(self):
        return MSG_WIZARD_MELODY_BRANCH

    def traits(self):
        return []

    def offers_styles(self):
        return self.choices().is_ready() and len(self.choices().melody_styles()) >= A_CHOICE

    def summary(self):
        return self.shown() if self.offers_styles() else None

    def shown(self):
        """Return the melody style as the field shows it: the one chosen, or the genre's own marked as the genre's."""
        choices = self.choices()
        return choices.get_melody() or MSG_WIZARD_GENRE_MELODY_SHOWN.format(style=choices.genre_melody())

    def fields(self):
        choices = self.choices()
        if not self.offers_styles():
            return self.phrasing_fields()
        # The first choice leaves the tunes to the style the genre sketches its own by, which the field names; a style that
        # would sketch as the genre's does is not offered again by its name.
        style = ChoiceField(page=self.page(), label=MSG_WIZARD_MELODY_LABEL, choices=[MSG_WIZARD_USUAL_MELODY, *choices.melody_styles()], current=choices.get_melody() or MSG_WIZARD_USUAL_MELODY, shown=self.shown(),
                            set=self.page().choosing(lambda chosen: choices.set_melody(None if chosen == MSG_WIZARD_USUAL_MELODY else chosen)))
        # The smart melody style's gauges, under the Melody field while the song's tunes are sketched by it.
        return [style, *(self.gauge_field(name) for name in choices.gauges()), *(self.setting_field(name) for name in choices.melody_settings()), *self.phrasing_fields()]

    def phrasing_fields(self):
        """Return the fields of how a planned song's lines breathe, in a song in four: the switch, and under it how long the breaths are,
        which lines of a section are the shorter and how many lines in four have a note come early."""
        choices = self.choices()
        page = self.page()
        if not choices.is_ready() or not choices.has_song_plan() or not choices.counts_in_four():
            return []
        fields = [Toggle(label=MSG_WIZARD_PHRASING_LABEL, on=choices.has_phrasing(), set=page.choosing(choices.set_phrasing))]
        if not choices.has_phrasing():
            return fields

        def setter(name):
            return page.choosing(lambda value: choices.set_phrasing_way(name=name, value=value))
        return [*fields,
                *(ChoiceField(page=page, label=MSG_WIZARD_PHRASING_WAY_LABELS[name], choices=list(PHRASING_OFFERED[name]), current=choices.phrasing_way(name), set=setter(name)) for name in (phrasing.BREATH, phrasing.LINE_LENGTHS)),
                NumberField(page=page, label=MSG_WIZARD_PHRASING_WAY_LABELS[phrasing.EARLY_NOTES], number=choices.phrasing_way(phrasing.EARLY_NOTES), lowest=phrasing.FEWEST_EARLY, highest=phrasing.MOST_EARLY,
                            shown=MSG_WIZARD_EARLY_SHOWN.format(count=choices.phrasing_way(phrasing.EARLY_NOTES), of=phrasing.MOST_EARLY), set=setter(phrasing.EARLY_NOTES))]

    def listens(self):
        choices = self.choices()
        if not choices.is_ready() or choices.tune_player() is None or choices.tune_scene() is None:
            return None
        return MSG_WIZARD_LISTEN_TUNE, choices.tune_scene(), choices.tune_player()

    def setting_field(self, name):
        """Return the field of one setting of the melody style in use: a switch, or a number stepped or typed."""
        choices = self.choices()
        to_value = self.page().choosing(lambda value: choices.set_melody_setting(name=name, value=value))
        if choices.melody_setting_is_switch(name):
            return Toggle(label=MSG_WIZARD_MELODY_SETTING_LABELS[name], on=choices.get_melody_setting(name), set=to_value)
        lowest, highest = choices.melody_setting_range(name)
        return NumberField(page=self.page(), label=MSG_WIZARD_MELODY_SETTING_LABELS[name], number=choices.get_melody_setting(name), lowest=lowest, highest=highest, set=to_value)

    def gauge_field(self, name):
        """Return the field of one gauge of the smart melody style: a number stepped or typed, drawn as a horizontal gauge
        beside what its two ends mean."""
        choices = self.choices()
        position = choices.get_gauge(name)
        low, high = MSG_WIZARD_GAUGE_ENDS[name]
        gauge = MSG_WIZARD_GAUGE_FULL * position + MSG_WIZARD_GAUGE_EMPTY * (HIGHEST_GAUGE - position)
        return NumberField(page=self.page(), label=MSG_WIZARD_GAUGE_LABELS[name], number=position, shown=MSG_WIZARD_MELODY_GAUGE_SHOWN.format(gauge=gauge, low=low, high=high),
                           lowest=LOWEST_GAUGE, highest=HIGHEST_GAUGE, set=self.page().choosing(lambda value: choices.set_gauge(name=name, position=value)))
