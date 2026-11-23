# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The tab of a built-in generator on a clip's or a track's page: the inside of the generator's own page, its view's fields, for the
built-in the clip or the track holds, the page that shows the tab asking for every dialog. ENTER on a part, such as a Chords
generator's progression, opens that part's page on the built-in."""

from llamatron.interface.tracker.screens.shared.field import Button
from llamatron.interface.tracker.screens.shared.generator_statements_page import GeneratorStatementsPage
from llamatron.interface.tracker.screens.shared.shared import scene_name
from llamatron.interface.tracker.screens.shared.tab_box import TabColumn
from llamatron.interface.tracker.screens.shared.view_fields import ViewFields
from llamatron.model.file.checks import listed
from llamatron.model.schema import generator_plugins
from llamatron.user_strings import labels, legends, messages

# The most clips a track's built-in tab names among those whose own built-in stands in for it.
MOST_NAMED = 3


class BuiltInTab(ViewFields):
    """What makes a built-in generator's tab: page is the clip's or the track's page that shows it, and place the BuiltInPlace of
    the generator. SECTION, item and holder are what the fields and the parts' pages ask of a generator's page: the section of the
    generator's kind, what the kind is called, and the page's holder."""

    __slots__ = ('_page', '_place', '_plugin', 'SECTION', 'item', 'holder')

    def __init__(self, *, page, place):
        self._page = page
        self._place = place
        self._plugin = generator_plugins.plugins()[place.kind]
        self.SECTION = self._plugin.section
        self.item = self._plugin.strings.MSG_LABEL
        self.holder = page.holder

    def tab(self):
        """Return the generator's tab: Enabled and its Mode across the top, then its columns, marked on or off, then the button
        that opens its statements, with what stands in for what: a clip's built-in that is on over its track's, and a track's
        under its clips' that are on."""
        tab = self.view_tab(label=self._plugin.strings.MSG_TAB_LABEL)
        tab.columns.append(TabColumn(heading=None, fields=[self._bypass_when_button()], under=True))
        tab.remarks = self._overrides()
        return tab

    def view(self):
        return self._plugin.view

    def _bypass_when_button(self):
        """Return the button that opens the generator's statements about the draws, saying how many it holds."""
        settings = self.settings()
        count = len(settings.get_bypass_when())
        return Button(label=labels.MSG_BYPASS_WHEN_BUTTON.format(count=count), enter=self._open_bypass_when, enter_what=legends.What.EDIT)

    def _open_bypass_when(self):
        self.open_part(GeneratorStatementsPage, section=self.SECTION)

    def _overrides(self):
        """Return the remark saying what stands in for what, or none: on a clip's tab, that it overrides the track's, both being
        on; on a track's, the clips whose own is on, the first few named."""
        place = self._place
        song = self._page.document().song()
        word = self._plugin.strings.MSG_TAB_LABEL.lower()
        if not place.is_the_tracks():
            clip_on = self.settings().is_enabled()
            if clip_on and song.get_track(place.track).has_built_in_on(place.kind):
                return [messages.MSG_BUILT_IN_OVERRIDES_TRACKS.format(word=word)]
            return []
        overriding = []
        for index, scene in enumerate(song.get_scenes()):
            clip_slot = scene.get_clip_slot(place.track)
            if clip_slot is not None and clip_slot.has_built_in_on(place.kind):
                overriding.append(messages.MSG_BUILT_IN_OVERRIDING_CLIP.format(scene=scene_name(scene=scene, index=index), track=place.track))
        if not overriding:
            return []
        template = messages.MSG_BUILT_IN_OVERRIDDEN
        if len(overriding) == 1:
            template = messages.MSG_BUILT_IN_OVERRIDDEN_ONCE
        return [template.format(word=word, count=len(overriding), clips=listed(overriding[:MOST_NAMED]))]

    def settings(self):
        """Return the built-in generator's settings, which keep every change in the clip or the track holding them."""
        return self._page.document().built_in(self._place)

    def store(self, *, setting, value):
        """Keep one setting by its file name, checked as reading a file checks it, or None to leave it out of the file."""
        document = self._page.document()
        document.change_set(self.settings().set_setting, name=setting, value=value)

    def open_part(self, page_class, **given):
        """Open the page of a part of the built-in generator, such as its offsets, its crumbs following the clip's or the track's."""
        page = page_class(holder=self.holder, name=self.item, built_in=self._place, **given)
        self._page.show_page(page.opened_from(page=self._page, word=labels.MSG_BUILT_IN_WORD))

    def document(self):
        return self._page.document()

    def heading(self, **given):
        return self._page.heading(**given)

    def ask(self, **given):
        return self._page.ask(**given)

    def ask_choice(self, **given):
        return self._page.ask_choice(**given)

    def ask_number(self, **given):
        return self._page.ask_number(**given)

    def ask_text(self, **given):
        return self._page.ask_text(**given)

    def refuse(self, text):
        return self._page.refuse(text)

    def show_page(self, page):
        return self._page.show_page(page)
