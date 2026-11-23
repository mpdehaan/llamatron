# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The boxes of tabs of the pages of Arrange's things. The clip page's: Settings, then the tabs that are not generators,
Velocity first, then the generators in the order they run, the built-ins and last the clip's own list under Generators.
The Scene page and the clip page share the Reset Draws tab."""

import functools

from llamatron.interface.tracker.document_parts.built_in_place import BuiltInPlace
from llamatron.interface.tracker.screens.shared.built_in_tab import BuiltInTab
from llamatron.interface.tracker.screens.shared.field import Field, Toggle
from llamatron.interface.tracker.screens.shared.generators_field import generators_field
from llamatron.interface.tracker.screens.shared.shape_fields import shape_section
from llamatron.interface.tracker.screens.shared.tab_box import columns_of_sections, Tab, TabColumn, without_headings
from llamatron.interface.tracker.screens.shared.velocity_fields import velocity_field, velocity_ramp_sections
from llamatron.model.schema import file_format, generator_plugins
from llamatron.model.schema.file_format import ClipSlotSetting, shape_setting
from llamatron.user_strings import labels as labels_text, legends, marks



def built_in_tabs(*, page, track, scene, kinds):
    """Return the tabs of the built-in generators of some kinds a track holds, or its clip in a scene, scene being
    OF_THE_TRACK for the track's own, in order."""
    tabs = []
    for kind in kinds:
        place = BuiltInPlace(track=track, scene=scene, kind=kind)
        tabs.append(BuiltInTab(page=page, place=place).tab())
    return tabs


def reset_draws_tab(*, page, holder):
    """Return the Reset Draws tab of a scene or a clip, holder, which resets draws as it first starts: a toggle for each draw
    that holds a value in the song, or a remark that none does."""
    song = page.document().song()
    names = song.draws_with_values()
    toggles = []
    for name in names:
        toggles.append(Toggle(label=labels_text.MSG_RESET_LABEL.format(name=name), on=name in holder.get_reset_draw_names(),
                              set=functools.partial(_set_reset_draw, page=page, holder=holder, draw=name)))
    remarks = []
    if not names:
        remarks.append(labels_text.MSG_NO_DRAWS_CONFIGURED)
    return Tab(label=labels_text.MSG_RESET_DRAWS_TAB, columns=[TabColumn(heading=None, fields=toggles)], remarks=remarks)


def fields_tab(*, label, fields):
    """Return a tab of one column of fields with no heading, a section's heading among them left out."""
    return Tab(label=label, columns=[TabColumn(heading=None, fields=without_headings(fields))])


class ClipTabs:
    """What makes the clip page's tabs: page is the clip page, which says which clip, and asks for every dialog."""

    __slots__ = ('_page',)

    def __init__(self, page):
        self._page = page

    def tabs(self):
        """Return the clip's tabs: Settings, the tabs that are not generators, then the generators in the order they run."""
        page = self._page
        shapes = []
        for shape in file_format.PLACED_SHAPES:
            shapes += self._shape_section(shape)
        own, above, store = self._velocity_values()
        return [
            self._basics_tab(),
            Tab(label=labels_text.MSG_VELOCITY_TAB, columns=columns_of_sections(velocity_ramp_sections(page=page, own=own, above=above, store=store))),
            Tab(label=labels_text.MSG_SHAPES_TAB, columns=columns_of_sections(shapes)),
            reset_draws_tab(page=page, holder=self._clip_slot()),
            *self._built_in_tabs(generator_plugins.built_in_kinds()),
            fields_tab(label=labels_text.MSG_USER_TAB, fields=[generators_field(page=page, names=self._chain_names, store=self._set_chain_names)]),
        ]

    def _basics_tab(self):
        """Return the Basics tab: Order, how the clip plays its patterns, and General, its scale, velocity and grab."""
        page = self._page
        own, above, store = self._velocity_values()
        order = [page.pattern_order_field(), *page.playing_fields(), page.follow_action_field()]
        general = [
            Field(label=labels_text.MSG_SCALE_LABEL, value=page.scale_text, adjust=None, enter=page.pick_scale, enter_what=legends.What.CHOOSE,
                  clear=functools.partial(page.clear, ClipSlotSetting.SCALE), clear_what=legends.MSG_USE_SCENE_SCALE_WHAT),
            velocity_field(page=page, own=own, above=above, store=store),
            Field(label=labels_text.MSG_GRAB_TRACK_LABEL, value=self._grab_shown, adjust=None, enter=page.pick_grab_track, enter_what=legends.What.CHOOSE,
                  clear=functools.partial(page.clear, ClipSlotSetting.GRAB_TRACK), clear_what=legends.MSG_NO_GRAB_WHAT),
        ]
        return Tab(label=labels_text.MSG_SETTINGS_TAB, columns=[
            TabColumn(heading=labels_text.MSG_ORDER_HEADING, fields=order), TabColumn(heading=labels_text.MSG_PLAYING_HEADING, fields=general),
        ])

    def _built_in_tabs(self, kinds):
        """Return the tabs of the clip's built-in generators of some kinds, in order."""
        page = self._page
        return built_in_tabs(page=page, track=page.track, scene=page.index, kinds=kinds)

    def _shape_section(self, shape):
        """Return a shape's section: how busy or long the clip plays over it, over its scene's."""
        clip_slot = self._clip_slot()

        def value(part):
            return clip_slot.get_written(shape_setting(shape=shape, part=part))

        def store(part, value):
            self._set_written(name=shape_setting(shape=shape, part=part), value=value)
        return shape_section(page=self._page, shape=shape, value=value, store=store)

    def _velocity_values(self):
        """Return what the velocity fields read the clip's own velocity settings with, what gives a blank one from its scene,
        and what keeps one."""
        page = self._page
        song = page.document().song()
        scene = song.get_scenes()[page.index]
        return self._clip_slot().get_written, scene.get_written, lambda name, value: self._set_written(name=name, value=value)

    def _clip_slot(self):
        return self._page.clip_slot()

    def _chain_names(self):
        clip_slot = self._clip_slot()
        return clip_slot.get_chain_names()

    def _set_chain_names(self, names):
        """Give the clip the chains named, or none."""
        self._page.set_value(setting=ClipSlotSetting.CHAINS, value=names or None)

    def _grab_shown(self):
        clip_slot = self._clip_slot()
        return clip_slot.get_grab_track() or marks.MSG_NONE_SHOWN

    def _set_written(self, *, name, value):
        clip_slot = self._clip_slot()
        self._page.document().change_set(clip_slot.set_written, name=name, value=value)


def _set_reset_draw(on, *, page, holder, draw):
    """Make a scene or a clip reset a draw as it first starts, or stop it, as one edit of the set."""
    page.document().change_set(holder.set_reset_draw, draw=draw, on=on)
