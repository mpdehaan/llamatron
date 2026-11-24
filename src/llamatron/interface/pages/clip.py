# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""One clip's page as a presenter: its name, its list of patterns with the + row that adds one, then its tabs (ClipTabs), and
the Listen button its page draws."""

from dataclasses import dataclass
import functools

from llamatron.interface.forms.nodes import ChoiceField, Field, NameField, NumberField, Toggle
from llamatron.interface.forms.tab_box import TabBox
from llamatron.interface.forms.text import columns, shown_name, sorted_names
from llamatron.interface.pages.arrange_tabs import ClipTabs
from llamatron.interface.pages.uses import loop_error_lines
from llamatron.model.objects.naming import words
from llamatron.model.schema import defaults, file_format, limits
from llamatron.model.schema.file_format import ClipSlotSetting, Section
from llamatron.user_strings import errors, labels as labels_text, legends, marks, messages, names as names_text

# The choices of the dialog that adds a pattern: one the song has, or a new one; and the first choice a picker opens on.
EXISTING_PATTERN = 0
FIRST_CHOICE = 0
# A clip plays at least one pattern.
ONE_PATTERN = 1
# What a row other than the list's first shows for its label, and what a blank name typed leaves.
NO_LABEL = ''
NO_NAME = ''


@dataclass(slots=True, kw_only=True)
class PatternRow(Field):
    """One pattern of a clip's list on the clip page: place is its place in the list."""

    place: int = 0


@dataclass(slots=True, kw_only=True)
class AddRow(Field):
    """The + row under a clip's list of patterns, which adds one."""


class ClipPresenter:
    """What a clip's page shows and does, for the clip of the current song at a scene's place and a track. Its page does what
    only the tracker can: asking (ask_choice, ask_text, pick, tell, refuse), whether a pattern of the list is carried in move
    mode (is_carrying), its Listen button, and the page actions a built-in generator's tab and the Generators field ask of it."""

    __slots__ = ('_page', '_document', '_index', '_track')

    def __init__(self, *, page, document, index, track):
        self._page = page
        self._document = document
        self._index = index
        self._track = track

    def get_page(self):
        return self._page

    def get_document(self):
        return self._document

    def get_index(self):
        return self._index

    def get_track(self):
        return self._track

    def clip_slot(self):
        return self._document.clip_slot(index=self._index, track=self._track)

    def scene(self):
        """Return the scene the clip is in."""
        song = self._document.song()
        scenes = song.get_scenes()
        return scenes[self._index]

    def form(self):
        """Return the page's form: the clip's name, its list of patterns, its tabs, then the Listen button."""
        return [
            NameField(value=self.name_text, rename=self.rename, clear=functools.partial(self.clear, ClipSlotSetting.NAME), clear_what=legends.MSG_FROM_PATTERN_WHAT),
            *self.pattern_rows(),
            TabBox(tabs=ClipTabs(self).tabs()),
            self._page.listen_button(),
        ]

    def set_value(self, *, setting, value):
        """Set one of the clip's settings, or None to leave it out and use its default."""
        self._document.set_clip_slot_setting(index=self._index, track=self._track, setting=setting, value=value)

    def clear(self, setting):
        self.set_value(setting=setting, value=None)

    def name_text(self):
        """Return the clip's own name, or which pattern it's named for."""
        clip_slot = self.clip_slot()
        name = clip_slot.get_name()
        if name:
            return shown_name(name)
        return marks.MSG_CLIP_NAMED_FOR_PATTERN.format(pattern=clip_slot.get_pattern_name())

    def rename(self):
        """Give the clip a name of its own; a blank goes back to its pattern's name."""
        clip_slot = self.clip_slot()
        self._page.ask_long_name(title=messages.MSG_CLIP_NAME_PROMPT.format(track=self.get_track()), value=clip_slot.get_name() or NO_NAME, then=self._renamed, longest=limits.MAX_CLIP_NAME_LENGTH)

    def pattern_rows(self):
        """Return the clip's list of patterns as rows, the first with the list's label, and the + row that adds one."""
        clip_slot = self.clip_slot()
        rows = []
        for place, name in enumerate(clip_slot.get_pattern_names()):
            rows.append(self._pattern_row(place=place, name=name))
        rows.append(AddRow(label=NO_LABEL, value=lambda: marks.MSG_NEW_ROW, adjust=None, enter=self.add_pattern, enter_what=legends.What.ADD))
        return rows

    def add_pattern(self):
        """Ask whether to add a pattern the song has or a new one, and put it at the end of the clip's list."""
        self._page.ask_choice(title=labels_text.MSG_ADD_PATTERN_TITLE, options=labels_text.MSG_ADD_PATTERN_CHOICES, current=FIRST_CHOICE, then=self._kind_of_pattern_chosen)

    def add_named(self, name):
        clip_slot = self.clip_slot()
        self.set_value(setting=ClipSlotSetting.PATTERNS, value=[*clip_slot.get_pattern_names(), name])

    def ask_new_pattern(self):
        """Ask for a new pattern's name, filled in with the track's name and the next free number, make it blank and add it to the list."""
        suggested = self._document.new_name(section=Section.PATTERNS, word=self._track)
        self._page.ask_text(title=messages.MSG_NEW_PATTERN_PROMPT, value=suggested, then=self.add_new, is_name=True)

    def add_new(self, text):
        name = text.strip()
        if not name:
            return
        if self._setlist().has_pattern(name):
            self._page.refuse(errors.ERR_NAME_TAKEN.format(label=names_text.MSG_PATTERN_WORD, name=name))
            return
        first = self._first_pattern()
        self._document.add_pattern(name=name, group=self._track, drum=first.is_drum(), scale_length=first.get_scale_length())
        self._document.continue_edit()
        self.add_named(name)

    def remove_pattern(self, place):
        """Take a pattern out of the clip's list, which deletes no pattern; the last one stays, since a clip plays something."""
        names = self.clip_slot().get_pattern_names()
        if len(names) == ONE_PATTERN:
            self._page.refuse(errors.ERR_CLIP_NEEDS_A_PATTERN)
            return
        del names[place]
        self.set_value(setting=ClipSlotSetting.PATTERNS, value=names)

    def pick_pattern(self, *, title, current, then, same_kind=False):
        """Ask for one of the song's patterns, starting on the current one, and pass its name to then. same_kind leaves out the
        patterns that cannot share the clip's list: drum patterns for a clip of notes, and the other way round."""
        patterns = sorted_names(self._setlist().get_pattern_names())
        if same_kind:
            patterns = self._of_the_clip_s_kind(patterns)
        place = FIRST_CHOICE
        if current in patterns:
            place = patterns.index(current)
        self._page.ask_choice(title=title, options=patterns, current=place, then=lambda item: then(patterns[item]))

    def pattern_order_field(self):
        order = self.clip_slot().get_pattern_order()
        names = []
        for choice in file_format.PATTERN_ORDERS:
            names.append(labels_text.MSG_PATTERN_ORDER_NAMES[choice])
        set_order = functools.partial(self.set_value, setting=ClipSlotSetting.PATTERN_ORDER)
        return ChoiceField(page=self._page, label=labels_text.MSG_PATTERN_ORDER_LABEL, choices=file_format.PATTERN_ORDERS, current=order,
                           names=names, shown=labels_text.MSG_PATTERN_ORDER_NAMES[order], set=lambda value: set_order(value=value))

    def playing_fields(self):
        """Return the fields of how the clip plays its patterns: the direction, the repeats, the loop, and the morph where the
        clip repeats."""
        clip_slot = self.clip_slot()
        repeat = clip_slot.get_repeat()
        result = [
            Field(label=labels_text.MSG_DIRECTION_LABEL, value=self.direction_text, adjust=self.step_direction, enter=self.pick_direction,
                  enter_what=legends.What.CHOOSE, clear=functools.partial(self.clear, ClipSlotSetting.DIRECTION),
                  clear_what=legends.MSG_FROM_PATTERN_WHAT),
            NumberField(page=self._page, label=labels_text.MSG_REPEAT_LABEL, number=repeat, lowest=limits.MIN_REPEAT, highest=limits.MAX_CLIP_REPEAT,
                        set=self.set_repeat),
            Toggle(label=labels_text.MSG_LOOP_LABEL, on=clip_slot.loops(), set=self.set_loop),
        ]
        if repeat > defaults.DEFAULT_REPEAT:
            result.append(Field(label=labels_text.MSG_MORPH_TO_LABEL, value=self._morph_shown, adjust=None, enter=self._pick_morph_target,
                                enter_what=legends.What.CHOOSE, clear=self.clear_morph, clear_what=marks.MSG_NONE_SHOWN))
            if clip_slot.get_morph_target():
                result.append(Field(label=labels_text.MSG_MORPH_DIRECTION_LABEL, value=self.morph_style, adjust=self.step_style,
                                    enter=functools.partial(self.step_style, 1), enter_what=legends.What.NEXT))
        return result

    def follow_action_field(self):
        """Return the Follow action field: what the clip sends down in real-time playback when its scene is done, shown as the
        set's default when the clip sets none, with no (default) choice."""
        clip_slot = self.clip_slot()
        advance = self._document.get_setlist().follow_action_of(clip_slot)
        names = []
        for choice in file_format.FOLLOW_ACTION_CHOICES:
            names.append(labels_text.MSG_FOLLOW_ACTION_NAMES[choice])
        shown = labels_text.MSG_FOLLOW_ACTION_NAMES[advance]
        if clip_slot.get_written_follow_action() is None:
            shown = marks.MSG_FROM_SET_SHOWN.format(value=shown)
        return ChoiceField(page=self._page, label=labels_text.MSG_FOLLOW_ACTION_LABEL, choices=file_format.FOLLOW_ACTION_CHOICES, current=advance,
                           names=names, shown=shown, set=functools.partial(self._set_named, setting=ClipSlotSetting.FOLLOW_ACTION))

    def set_morph_target(self, pattern):
        self._document.set_clip_slot_morph_target(index=self._index, track=self._track, pattern=pattern)

    def clear_morph(self):
        clip_slot = self.clip_slot()
        self._document.change_set(clip_slot.clear_morph)

    def morph_style(self):
        return self.clip_slot().morph_style_in_effect()

    def step_style(self, offset):
        style = self.clip_slot().morph_style_after(offset)
        self.set_value(setting=ClipSlotSetting.MORPH_STYLE, value=style)

    def pick_grab_track(self):
        tracks = []
        for name in self._document.track_names():
            if name != self._track:
                tracks.append(name)
        tracks = sorted_names(tracks)
        if not tracks:
            self._page.tell(errors.ERR_NO_OTHER_TRACKS_TITLE, errors.ERR_ADD_ANOTHER_TRACK)
            return
        clip_slot = self.clip_slot()
        self._page.pick(title=labels_text.MSG_GRAB_TRACK_LABEL, values=[None, *tracks], shown=[marks.MSG_NONE_SHOWN, *tracks],
                        current=clip_slot.get_grab_track(), then=self._grab_track_chosen)

    def scale_text(self):
        """Return the clip's own scale, or the scene's it takes, which is the song's when the scene has none."""
        own = self.clip_slot().get_scale_name()
        if own is not None:
            return own
        song = self._document.song()
        scale = self.scene().get_scale_name() or song.get_scale_name() or messages.MSG_NO_SCALE
        return marks.MSG_SCENE_SCALE_SHOWN.format(scale=scale)

    def pick_scale(self):
        """Ask for one of the song's scales for the clip alone, or the scene's."""
        scales = sorted_names(self._setlist().get_scale_names())
        clip_slot = self.clip_slot()
        self._page.pick(
            title=messages.MSG_CLIP_SCALE_TITLE, values=[None, *scales], shown=[labels_text.MSG_SCENE_OPTION, *scales],
            current=clip_slot.get_scale_name(), then=functools.partial(self._set_named, setting=ClipSlotSetting.SCALE),
        )

    def set_repeat(self, value):
        self._document.set_clip_slot_repeat(index=self._index, track=self._track, repeat=value)

    def set_direction(self, direction):
        self.set_value(setting=ClipSlotSetting.DIRECTION, value=direction)

    def step_direction(self, offset):
        options = [None, *file_format.DIRECTIONS]
        place = options.index(self.clip_slot().get_direction())
        self.set_direction(options[(place + offset) % len(options)])

    def pick_direction(self):
        options = [None, *file_format.DIRECTIONS]
        shown = columns([
            (labels_text.MSG_PATTERN_DIRECTION_OPTION, legends.MSG_PATTERN_DIRECTION_WHAT),
            *[(words(name), labels_text.MSG_DIRECTION_NAMES[name]) for name in file_format.DIRECTIONS],
        ])
        self._page.pick(title=messages.MSG_PLAY_DIRECTION_TITLE, values=options, shown=shown, current=self.clip_slot().get_direction(), then=self.set_direction)

    def direction_text(self):
        clip_slot = self.clip_slot()
        direction = clip_slot.get_direction()
        if direction:
            return words(direction)
        if len(clip_slot.get_pattern_names()) > ONE_PATTERN:
            return marks.MSG_EACH_PATTERN_DIRECTION_SHOWN
        pattern = self._first_pattern()
        return marks.MSG_PATTERN_DIRECTION_SHOWN.format(direction=words(pattern.get_direction()))

    def set_loop(self, loops):
        """Make the clip loop or play its repeats, and say so when that leaves every clip of the scene looping, since such a
        scene never ends."""
        value = None
        if loops:
            value = True
        self.set_value(setting=ClipSlotSetting.LOOP, value=value)
        song = self._document.song()
        if song.scene_never_ends(self.scene()):
            self._page.tell(errors.ERR_LOOP_SCENES_TITLE, *loop_error_lines(song))

    def _renamed(self, text):
        self.set_value(setting=ClipSlotSetting.NAME, value=text.strip())

    def _pattern_row(self, *, place, name):
        """Return the row of one pattern of the clip's list."""
        label = NO_LABEL
        if place == 0:
            label = labels_text.MSG_PATTERNS_LABEL
        return PatternRow(
            label=label, place=place, adjust=None, value=functools.partial(self._pattern_shown, name=name, place=place),
            enter=functools.partial(self._page.open_pattern_at, place), enter_what=legends.What.EDIT,
            clear=functools.partial(self.remove_pattern, place), clear_what=legends.What.REMOVE,
        )

    def _pattern_shown(self, *, name, place):
        """Return a pattern's name as its row shows it, between the marks of move mode while it is carried."""
        if self._page.is_carrying(place):
            return marks.MSG_MOVING_OPEN + name + marks.MSG_MOVING_CLOSE
        return name

    def _kind_of_pattern_chosen(self, choice):
        """Pick a pattern the song has, or ask for a new one's name."""
        if choice == EXISTING_PATTERN:
            self.pick_pattern(title=labels_text.MSG_PATTERN_LABEL, current=None, then=self.add_named, same_kind=True)
        else:
            self.ask_new_pattern()

    def _of_the_clip_s_kind(self, patterns):
        """Return the patterns of the same kind as the clip's first, drum patterns or patterns of notes."""
        setlist = self._setlist()
        drum = self._first_pattern().is_drum()
        same = []
        for name in patterns:
            pattern = setlist.get_pattern(name)
            if pattern.is_drum() == drum:
                same.append(name)
        return same

    def _set_named(self, value, *, setting):
        """Set one of the clip's settings to a value picked."""
        self.set_value(setting=setting, value=value)

    def _morph_shown(self):
        return self.clip_slot().get_morph_target() or marks.MSG_NONE_SHOWN

    def _pick_morph_target(self):
        """Ask for the pattern the clip morphs into."""
        clip_slot = self.clip_slot()
        self.pick_pattern(title=labels_text.MSG_MORPH_TO_LABEL, current=clip_slot.get_morph_target(), then=self.set_morph_target)

    def _grab_track_chosen(self, other):
        """Have the clip grab from the track picked, or from none, refusing a grab that would go round in a circle."""
        if other is None:
            self.clear(ClipSlotSetting.GRAB_TRACK)
            return
        circle = self._document.grab_circle(index=self._index, track=self._track, other=other)
        if circle:
            shown = marks.MSG_CIRCLE_ARROW.join(circle)
            self._page.tell(errors.ERR_CIRCULAR_GRAB_TITLE, errors.ERR_GRAB_CIRCLE.format(track=other, circle=shown), errors.ERR_REMOVE_OTHER_GRAB)
            return
        self.set_value(setting=ClipSlotSetting.GRAB_TRACK, value=other)

    def _setlist(self):
        """Return the set the clip's song belongs to."""
        song = self._document.song()
        return song.get_setlist()

    def _first_pattern(self):
        """Return the first pattern of the clip's list."""
        clip_slot = self.clip_slot()
        return self._setlist().get_pattern(clip_slot.get_pattern_name())
