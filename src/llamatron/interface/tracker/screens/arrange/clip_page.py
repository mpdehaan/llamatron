# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Clip page: one clip: what it plays, how many times, and whether it morphs into another pattern."""

from dataclasses import dataclass
import functools
from rich.text import Text

from llamatron.interface.forms.nodes import Button, ChoiceField, Field, NameField, NumberField, Toggle
from llamatron.interface.tracker import drawing, keybindings, themes
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.drawing import Style
from llamatron.interface.tracker.screens.shared.arrange_tabs import ClipTabs
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.listening import listen, stop_listening
from llamatron.interface.tracker.screens.shared.shared import columns, scene_name
from llamatron.interface.tracker.screens.shared.tab_box import TabBox
from llamatron.interface.tracker.text import clock, sorted_names
from llamatron.interface.tracker.uses import loop_error_lines
from llamatron.model.objects import clip_slot as clip_slot_values
from llamatron.model.objects.naming import words
from llamatron.model.schema import defaults, file_format, limits
from llamatron.model.schema.file_format import ClipSlotSetting, Section
from llamatron.user_strings import errors, help as help_text, labels as labels_text, legends, marks, messages, names as names_text

EXISTING_PATTERN = 0
ONE_PATTERN = 1


@dataclass(slots=True, kw_only=True)
class PatternRow(Field):
    """One pattern of a clip's list on the clip page: place is its place in the list."""

    place: int = 0


@dataclass(slots=True, kw_only=True)
class AddRow(Field):
    """The + row under a clip's list of patterns, which adds one."""


class ClipPage(FieldPage):
    """One clip: what it plays, how many times, and whether it morphs into another pattern."""

    THEME = themes.FROM_ARRANGE

    KEYS = keybindings.ClipPage

    HELP = help_text.HELP_CLIP_PAGE

    def __init__(self, *, holder, index, track):
        super().__init__(holder)
        self.index = index
        # Move mode: whether M has picked up the pattern under the cursor, and whether it has been carried yet, so that one move is one undo step.
        self.moving = False
        self.carried = False
        self.track = track

    def still_exists(self):
        song = self.document().song()
        return self.index < len(song.get_scenes()) and song.has_track(self.track) and self.clip_slot() is not None

    def follow_renames(self, renames):
        track_renames = renames.get(Section.TRACKS, {})
        self.track = track_renames.get(self.track, self.track)

    def crumb_trail(self):
        scene = scene_name(scene=self._scene(), index=self.index)
        return (labels_text.Crumb.ARRANGE, labels_text.MSG_CLIP_CRUMB.format(scene=scene, track=self.track))

    def caption(self):
        scene = scene_name(scene=self._scene(), index=self.index)
        name = labels_text.MSG_CLIP_CAPTION_NAME.format(scene=scene, track=self.track)
        what = labels_text.MSG_CLIP_CAPTION_WORD.upper()
        return labels_text.MSG_EDITING_CAPTION.format(what=what, name=name)

    def duration(self):
        lengths = self.document().lengths()
        return lengths.clip_seconds(index=self.index, track=self.track)

    def clip_slot(self):
        return self.document().clip_slot(index=self.index, track=self.track)

    def page_keys(self):
        if self.is_listening():
            listening = self.bind(self.KEYS.STOP_LISTENING, action=self.stop)
        else:
            listening = self.bind(self.KEYS.LISTEN, action=self.listen)
        result = [self.bind(self.KEYS.ADD_PATTERN, action=self.add_pattern)]
        if isinstance(self.field(), PatternRow):
            result.append(self.bind(self.KEYS.MOVE_PATTERN, action=self.start_moving))
        return [*result, self.bind(self.KEYS.OPEN_PATTERN, action=self.open_pattern), listening]

    def fields_depend_on(self):
        """Return what the fields read besides the set: whether the clip plays on its own, which names the Listen button."""
        return (self.is_listening(),)

    def is_listening(self):
        """Return whether the clip plays on its own: through its track's instrument, or through General MIDI while Real Time is
        off."""
        if self.app.transport.is_clip_playing(index=self.index, track=self.track):
            return True
        preview = self.app.pattern_preview()
        return preview.playing_clip() == (self.index, self.track)

    def listen(self):
        """Play the clip as its scene would, again and again, through its track's instrument or one picked for this listening."""
        clip_slot = self.clip_slot()
        listen(page=self, index=self.index, track=self.track, name=clip_slot.get_display_name())

    def stop(self):
        stop_listening(self)

    def open_pattern(self):
        """Open the pattern editor on the clip's pattern, from any field, with this page's crumbs before the pattern's, so that
        ESC comes back here."""
        row = self.field()
        place = 0
        if isinstance(row, PatternRow):
            place = row.place
        self.open_pattern_at(place)

    def open_pattern_at(self, place):
        """Open the pattern editor on one pattern of the clip's list."""
        clip_slot = self.clip_slot()
        names = clip_slot.get_pattern_names()
        self.open_editor(section=Section.PATTERNS, name=names[place], opened_from=self, track=self.track)

    def keys(self):
        if self.moving:
            return [self.bind(self.KEYS.DROP, action=self.drop), self.bind(self.KEYS.CARRY, action=self.carry)]
        return super().keys()

    def start_moving(self):
        self.moving = True
        self.carried = False
        self.say_moving()

    def say_moving(self):
        clip_slot = self.clip_slot()
        names = clip_slot.get_pattern_names()
        row = messages.MSG_MOVING_ROW.format(name=names[self.field().place])
        self.say(messages.MSG_MOVING.format(what=row))

    def carry(self, offset):
        """Carry the picked-up pattern one place up or down its list, every carry of one move making one undo step."""
        names = self.clip_slot().get_pattern_names()
        place = self.field().place
        to = place + offset
        if not 0 <= to < len(names):
            return
        if self.carried:
            self.document().continue_edit()
        self.carried = True
        names[place], names[to] = names[to], names[place]
        self.set_value(setting=ClipSlotSetting.PATTERNS, value=names)
        self.cursor.shift(offset)
        self.say_moving()

    def drop(self):
        self.moving = False

    def add_pattern(self):
        """Ask whether to add a pattern the song has or a new one, and put it at the end of the clip's list."""
        dialog = ChoiceDialog(title=labels_text.MSG_ADD_PATTERN_TITLE, options=labels_text.MSG_ADD_PATTERN_CHOICES)
        self.ask(dialog=dialog, then=self._kind_of_pattern_chosen)

    def _kind_of_pattern_chosen(self, choice):
        """Pick a pattern the song has, or ask for a new one's name."""
        if choice == EXISTING_PATTERN:
            self.pick_pattern(title=labels_text.MSG_PATTERN_LABEL, current=None, then=self.add_named, same_kind=True)
        else:
            self.ask_new_pattern()

    def add_named(self, name):
        clip_slot = self.clip_slot()
        self.set_value(setting=ClipSlotSetting.PATTERNS, value=[*clip_slot.get_pattern_names(), name])

    def ask_new_pattern(self):
        """Ask for a new pattern's name, filled in with the track's name and the next free number, make it blank and add it to the list."""
        suggested = self.document().new_name(section=Section.PATTERNS, word=self.track)
        self.ask_text(title=messages.MSG_NEW_PATTERN_PROMPT, value=suggested, then=self.add_new, is_name=True)

    def add_new(self, text):
        name = text.strip()
        document = self.document()
        if not name:
            return
        if self._setlist().has_pattern(name):
            self.refuse(errors.ERR_NAME_TAKEN.format(label=names_text.MSG_PATTERN_WORD, name=name))
            return
        first = self._first_pattern()
        document.add_pattern(name=name, group=self.track, drum=first.is_drum(), scale_length=first.get_scale_length())
        document.continue_edit()
        self.add_named(name)

    def remove_pattern(self, place):
        """Take a pattern out of the clip's list, which deletes no pattern; the last one stays, since a clip plays something."""
        names = self.clip_slot().get_pattern_names()
        if len(names) == ONE_PATTERN:
            self.refuse(errors.ERR_CLIP_NEEDS_A_PATTERN)
            return
        del names[place]
        self.set_value(setting=ClipSlotSetting.PATTERNS, value=names)

    def pattern_rows(self):
        """Return the clip's list of patterns as rows, the first with the list's label, and the + row that adds one."""
        clip_slot = self.clip_slot()
        rows = []
        for place, name in enumerate(clip_slot.get_pattern_names()):
            rows.append(self._pattern_row(place=place, name=name))
        rows.append(AddRow(label=drawing.NOTHING, value=lambda: marks.MSG_NEW_ROW, adjust=None, enter=self.add_pattern, enter_what=legends.What.ADD))
        return rows

    def _pattern_row(self, *, place, name):
        """Return the row of one pattern of the clip's list."""
        label = drawing.NOTHING
        if place == 0:
            label = labels_text.MSG_PATTERNS_LABEL
        return PatternRow(
            label=label, place=place, adjust=None, value=functools.partial(self._pattern_shown, name=name, place=place),
            enter=functools.partial(self.open_pattern_at, place), enter_what=legends.What.EDIT,
            clear=functools.partial(self.remove_pattern, place), clear_what=legends.What.REMOVE,
        )

    def _pattern_shown(self, *, name, place):
        """Return a pattern's name as its row shows it, between the marks of move mode while it is carried."""
        if self.is_carrying(place):
            return marks.MSG_MOVING_OPEN + name + marks.MSG_MOVING_CLOSE
        return name

    def ends_a_list(self, field):
        return isinstance(field, AddRow)

    def is_carrying(self, place):
        row = self.field()
        return self.moving and isinstance(row, PatternRow) and row.place == place

    def pattern_order_field(self):
        clip_slot = self.clip_slot()
        order = clip_slot.get_pattern_order()
        names = []
        for choice in file_format.PATTERN_ORDERS:
            names.append(labels_text.MSG_PATTERN_ORDER_NAMES[choice])
        set_order = functools.partial(self.set_value, setting=ClipSlotSetting.PATTERN_ORDER)
        return ChoiceField(page=self, label=labels_text.MSG_PATTERN_ORDER_LABEL, choices=file_format.PATTERN_ORDERS, current=order,
                           names=names, shown=labels_text.MSG_PATTERN_ORDER_NAMES[order], set=lambda value: set_order(value=value))

    def set_value(self, *, setting, value):
        """Set one of the clip's settings, or None to leave it out and use its default."""
        self.document().set_clip_slot_setting(index=self.index, track=self.track, setting=setting, value=value)

    def clear(self, setting):
        self.set_value(setting=setting, value=None)

    def pick_pattern(self, *, title, current, then, same_kind=False):
        """Ask for one of the song's patterns, starting on the current one, and pass its name to then. same_kind leaves out the
        patterns that cannot share the clip's list: drum patterns for a clip of notes, and the other way round."""
        setlist = self._setlist()
        patterns = sorted_names(setlist.get_pattern_names())
        if same_kind:
            patterns = self._of_the_clip_s_kind(patterns)
        place = 0
        if current in patterns:
            place = patterns.index(current)
        dialog = ChoiceDialog(title=title, options=patterns, current=place)
        self.ask(dialog=dialog, then=lambda item: then(patterns[item]))

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

    def set_morph_target(self, pattern):
        self.document().set_clip_slot_morph_target(index=self.index, track=self.track, pattern=pattern)

    def clear_morph(self):
        clip_slot = self.clip_slot()
        self.document().change_set(clip_slot.clear_morph)

    def pick_grab_track(self):
        tracks = []
        for name in self.document().track_names():
            if name != self.track:
                tracks.append(name)
        tracks = sorted_names(tracks)
        if not tracks:
            self.tell(errors.ERR_NO_OTHER_TRACKS_TITLE, errors.ERR_ADD_ANOTHER_TRACK)
            return
        clip_slot = self.clip_slot()
        self.pick(title=labels_text.MSG_GRAB_TRACK_LABEL, values=[None, *tracks], shown=[marks.MSG_NONE_SHOWN, *tracks],
                  current=clip_slot.get_grab_track(), then=self._grab_track_chosen)

    def _grab_track_chosen(self, other):
        """Have the clip grab from the track picked, or from none, refusing a grab that would go round in a circle."""
        if other is None:
            self.clear(ClipSlotSetting.GRAB_TRACK)
            return
        circle = self.document().grab_circle(index=self.index, track=self.track, other=other)
        if circle:
            shown = marks.MSG_CIRCLE_ARROW.join(circle)
            self.tell(errors.ERR_CIRCULAR_GRAB_TITLE, errors.ERR_GRAB_CIRCLE.format(track=other, circle=shown), errors.ERR_REMOVE_OTHER_GRAB)
            return
        self.set_value(setting=ClipSlotSetting.GRAB_TRACK, value=other)

    def scale_text(self):
        """Return the clip's own scale, or the scene's it takes, which is the song's when the scene has none."""
        clip_slot = self.clip_slot()
        own = clip_slot.get_scale_name()
        if own is not None:
            return own
        song = self.document().song()
        scale = self._scene().get_scale_name() or song.get_scale_name() or messages.MSG_NO_SCALE
        return marks.MSG_SCENE_SCALE_SHOWN.format(scale=scale)

    def pick_scale(self):
        """Ask for one of the song's scales for the clip alone, or the scene's."""
        setlist = self._setlist()
        scales = sorted_names(setlist.get_scale_names())
        clip_slot = self.clip_slot()
        self.pick(
            title=messages.MSG_CLIP_SCALE_TITLE, values=[None, *scales], shown=[labels_text.MSG_SCENE_OPTION, *scales],
            current=clip_slot.get_scale_name(), then=functools.partial(self._set_named, setting=ClipSlotSetting.SCALE),
        )

    def _set_named(self, value, *, setting):
        """Set one of the clip's settings to a value picked."""
        self.set_value(setting=setting, value=value)


    def set_repeat(self, value):
        self.document().set_clip_slot_repeat(index=self.index, track=self.track, repeat=value)

    def set_direction(self, direction):
        self.set_value(setting=ClipSlotSetting.DIRECTION, value=direction)

    def step_direction(self, offset):
        options = [None, *file_format.DIRECTIONS]
        place = options.index(self.clip_slot().get_direction())
        self.set_direction(options[(place + offset) % len(options)])

    def pick_direction(self):
        options = [None, *file_format.DIRECTIONS]
        labels = columns([
            (labels_text.MSG_PATTERN_DIRECTION_OPTION, legends.MSG_PATTERN_DIRECTION_WHAT),
            *[(words(name), labels_text.MSG_DIRECTION_NAMES[name]) for name in file_format.DIRECTIONS],
        ])
        self.pick(title=messages.MSG_PLAY_DIRECTION_TITLE, values=options, shown=labels, current=self.clip_slot().get_direction(), then=self.set_direction)

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
        song = self.document().song()
        if song.scene_never_ends(self._scene()):
            self.tell(errors.ERR_LOOP_SCENES_TITLE, *loop_error_lines(song))

    def morph_style(self):
        return self.clip_slot().get_morph_style_name() or clip_slot_values.FIRST_MORPH_STYLE

    def step_style(self, offset):
        styles = list(clip_slot_values.MORPH_STYLES)
        place = styles.index(self.morph_style())
        self.set_value(setting=ClipSlotSetting.MORPH_STYLE, value=styles[(place + offset) % len(styles)])

    def fields(self):
        result = [
            NameField(value=self.name_text, rename=self.rename, clear=functools.partial(self.clear, ClipSlotSetting.NAME), clear_what=legends.MSG_USE_PATTERN_NAME_WHAT),
            *self.pattern_rows(),
            TabBox(tabs=ClipTabs(self).tabs()),
        ]
        result.append(self.listen_button())
        return result

    def listen_button(self):
        """Return the Listen button, drawn below the settings after a blank line as every page's buttons are, which does what L
        does: it starts listening to the clip, or stops it while the clip plays."""
        # Both names take the room of the longer, so that the button never changes its width as it changes its name.
        width = max(len(labels_text.MSG_LISTEN_LABEL), len(labels_text.MSG_STOP_LISTENING_LABEL))
        if self.is_listening():
            return Button(label=labels_text.MSG_STOP_LISTENING_LABEL.center(width), key_name=legends.KeyName.L, enter=self.stop, enter_what=legends.MSG_STOP_LISTENING_WHAT)
        return Button(label=labels_text.MSG_LISTEN_LABEL.center(width), key_name=legends.KeyName.L, enter=self.listen, enter_what=legends.MSG_LISTEN_WHAT)

    def playing_fields(self):
        """Return the fields of how the clip plays its patterns: the direction, the repeats, the loop, and the morph where the
        clip repeats."""
        clip_slot = self.clip_slot()
        repeat = clip_slot.get_repeat()
        result = [
            Field(label=labels_text.MSG_DIRECTION_LABEL, value=self.direction_text, adjust=self.step_direction, enter=self.pick_direction,
                  enter_what=legends.What.CHOOSE, clear=functools.partial(self.clear, ClipSlotSetting.DIRECTION),
                  clear_what=legends.MSG_USE_PATTERN_DIRECTION_WHAT),
            NumberField(page=self, label=labels_text.MSG_REPEAT_LABEL, number=repeat, lowest=limits.MIN_REPEAT, highest=limits.MAX_CLIP_REPEAT,
                        set=self.set_repeat),
            Toggle(label=labels_text.MSG_LOOP_LABEL, on=clip_slot.loops(), set=self.set_loop),
        ]
        if repeat > defaults.DEFAULT_REPEAT:
            result.append(Field(label=labels_text.MSG_MORPH_TO_LABEL, value=self._morph_shown, adjust=None, enter=self._pick_morph_target,
                                enter_what=legends.What.CHOOSE, clear=self.clear_morph, clear_what=legends.MSG_NO_MORPH_WHAT))
            if clip_slot.get_morph_target():
                result.append(Field(label=labels_text.MSG_MORPH_DIRECTION_LABEL, value=self.morph_style, adjust=self.step_style,
                                    enter=functools.partial(self.step_style, 1), enter_what=legends.What.NEXT))
        return result

    def _morph_shown(self):
        clip_slot = self.clip_slot()
        return clip_slot.get_morph_target() or marks.MSG_NONE_SHOWN

    def _pick_morph_target(self):
        """Ask for the pattern the clip morphs into."""
        clip_slot = self.clip_slot()
        self.pick_pattern(title=labels_text.MSG_MORPH_TO_LABEL, current=clip_slot.get_morph_target(), then=self.set_morph_target)

    def follow_action_field(self):
        """Return the Follow action field: what the clip sends down in real-time playback when its scene is done, shown as the
        set's default when the clip sets none, with no (default) choice."""
        clip_slot = self.clip_slot()
        setlist = self.document().get_setlist()
        advance = setlist.follow_action_of(clip_slot)
        names = []
        for choice in file_format.FOLLOW_ACTION_CHOICES:
            names.append(labels_text.MSG_FOLLOW_ACTION_NAMES[choice])
        shown = labels_text.MSG_FOLLOW_ACTION_NAMES[advance]
        if clip_slot.get_written_follow_action() is None:
            shown = marks.MSG_FROM_SET_SHOWN.format(value=shown)
        return ChoiceField(page=self, label=labels_text.MSG_FOLLOW_ACTION_LABEL, choices=file_format.FOLLOW_ACTION_CHOICES, current=advance,
                           names=names, shown=shown, set=functools.partial(self._set_named, setting=ClipSlotSetting.FOLLOW_ACTION))

    def name_text(self):
        """Return the clip's own name, or which pattern it's named for."""
        clip_slot = self.clip_slot()
        return clip_slot.get_name() or marks.MSG_CLIP_NAMED_FOR_PATTERN.format(pattern=clip_slot.get_pattern_name())

    def rename(self):
        """Give the clip a name of its own; a blank goes back to its pattern's name."""
        clip_slot = self.clip_slot()
        self.ask_text(title=messages.MSG_CLIP_NAME_PROMPT, value=clip_slot.get_name() or drawing.NOTHING, then=self._renamed, is_name=True)

    def _renamed(self, text):
        self.set_value(setting=ClipSlotSetting.NAME, value=text.strip())

    def remarks(self, width):
        document = self.document()
        lengths = document.lengths()
        clip_slot = self.clip_slot()
        length = clock(lengths.clip_seconds(index=self.index, track=self.track))
        scene_length = clock(lengths.scene_seconds(self.index))
        lines = [Text(messages.MSG_CLIP_LENGTH_NOTE.format(length=length, scene=scene_length), style=Style.DIM)]
        if clip_slot.loops():
            lines.append(Text(messages.MSG_LOOP_NOTE, style=Style.DIM))
        elif clip_slot.get_repeat() == defaults.DEFAULT_REPEAT:
            lines.append(Text(messages.MSG_MORPH_HINT_NOTE, style=Style.DIM))
        if clip_slot.get_grab_track() is not None and not self._grabs_anywhere():
            lines.append(Text(messages.MSG_GRAB_HINT_NOTE, style=Style.DIM))
        problem = lengths.scene_problem(self.index)
        if problem:
            lines.append(Text(messages.MSG_PROBLEM_NOTE.format(problem=problem)[:width]))
        return lines

    def _grabs_anywhere(self):
        """Return whether any pattern of the clip's list has a step that grabs."""
        clip_slot = self.clip_slot()
        document = self.document()
        for name in clip_slot.get_pattern_names():
            if document.has_grab_steps(name):
                return True
        return False

    def _scene(self):
        """Return the scene the clip is in."""
        song = self.document().song()
        scenes = song.get_scenes()
        return scenes[self.index]

    def _setlist(self):
        """Return the set the clip's song belongs to."""
        song = self.document().song()
        return song.get_setlist()

    def _first_pattern(self):
        """Return the first pattern of the clip's list."""
        clip_slot = self.clip_slot()
        setlist = self._setlist()
        return setlist.get_pattern(clip_slot.get_pattern_name())
