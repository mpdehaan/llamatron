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

from llamatron.macro_composer.melody import HIGHEST_GAUGE, LOWEST_GAUGE
from llamatron.strings.labels import MSG_WIZARD_GAUGE_ENDS, MSG_WIZARD_GAUGE_LABELS, MSG_WIZARD_MELODY_BRANCH, MSG_WIZARD_MELODY_LABEL, MSG_WIZARD_MELODY_SETTING_LABELS, MSG_WIZARD_USUAL_MELODY
from llamatron.strings.marks import MSG_WIZARD_GAUGE_EMPTY, MSG_WIZARD_GAUGE_FULL, MSG_WIZARD_MELODY_GAUGE_SHOWN
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
        return (self.choices().get_melody() or MSG_WIZARD_USUAL_MELODY) if self.offers_styles() else None

    def fields(self):
        if not self.offers_styles():
            return []
        choices = self.choices()
        # The first choice leaves each player's tunes to the style the genre gives the player.
        style = ChoiceField(page=self.page(), label=MSG_WIZARD_MELODY_LABEL, choices=[MSG_WIZARD_USUAL_MELODY, *choices.melody_styles()], current=choices.get_melody() or MSG_WIZARD_USUAL_MELODY,
                            set=self.page().choosing(lambda chosen: choices.set_melody(None if chosen == MSG_WIZARD_USUAL_MELODY else chosen)))
        # The smart melody style's gauges, under the Melody field while the song's tunes are sketched by it.
        return [style, *(self.gauge_field(name) for name in choices.gauges()), *(self.setting_field(name) for name in choices.melody_settings())]

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
