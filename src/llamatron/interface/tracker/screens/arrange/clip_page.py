# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Clip page: one clip: what it plays, how many times, and whether it morphs into another pattern."""

from dataclasses import dataclass
import functools
from rich.text import Text

from llamatron.interface.tracker import drawing, keybindings, themes
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.drawing import Style
from llamatron.interface.tracker.screens.arrange.generators_field import generators_field
from llamatron.interface.tracker.screens.arrange.velocity_fields import velocity_field, velocity_ramp_sections
from llamatron.interface.tracker.screens.generators.shape_fields import shape_section
from llamatron.interface.tracker.screens.generators.strum_fields import strum_section
from llamatron.interface.tracker.screens.shared import statements
from llamatron.interface.tracker.screens.shared.field import Button, ChoiceField, Field, NameField, NumberField, Toggle
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.listening import listen, stop_listening
from llamatron.interface.tracker.screens.shared.shared import columns, scene_name
from llamatron.interface.tracker.screens.shared.statements import register_fields, statement_section
from llamatron.interface.tracker.text import clock, sorted_names
from llamatron.interface.tracker.uses import loop_error_lines
from llamatron.model.objects import clip_slot as clip_slot_values
from llamatron.model.objects.naming import words
from llamatron.model.schema import defaults, file_format, limits
from llamatron.model.schema.file_format import ClipSlotSetting, Section, shape_setting, strum_setting
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
        self.track = renames.get(Section.TRACKS, {}).get(self.track, self.track)

    def crumb_trail(self):
        scene = scene_name(scene=self.document().song().get_scenes()[self.index], index=self.index)
        return (labels_text.Crumb.ARRANGE, labels_text.MSG_CLIP_CRUMB.format(scene=scene, track=self.track))

    def caption(self):
        scene = scene_name(scene=self.document().song().get_scenes()[self.index], index=self.index)
        return labels_text.MSG_EDITING_CAPTION.format(what=labels_text.MSG_CLIP_CAPTION_WORD.upper(), name=labels_text.MSG_CLIP_CAPTION_NAME.format(scene=scene, track=self.track))

    def duration(self):
        return self.document().lengths().clip_seconds(index=self.index, track=self.track)

    def clip_slot(self):
        return self.document().clip_slot(index=self.index, track=self.track)

    def page_keys(self):
        listening = self.bind(self.KEYS.STOP_LISTENING, action=self.stop) if self.is_listening() else self.bind(self.KEYS.LISTEN, action=self.listen)
        result = [self.bind(self.KEYS.ADD_PATTERN, action=self.add_pattern)]
        if isinstance(self.field(), PatternRow):
            result.append(self.bind(self.KEYS.MOVE_PATTERN, action=self.start_moving))
        return [*result, self.bind(self.KEYS.OPEN_PATTERN, action=self.open_pattern), listening]

    def is_listening(self):
        """Return whether the clip plays on its own: through its track's instrument, or through General MIDI while Real Time is off."""
        return self.app.transport.is_clip_playing(index=self.index, track=self.track) or self.app.pattern_preview().playing_clip() == (self.index, self.track)

    def listen(self):
        """Play the clip as its scene would, again and again, through its track's instrument or one picked for this listening."""
        listen(page=self, index=self.index, track=self.track, name=self.clip_slot().get_display_name())

    def stop(self):
        stop_listening(self)

    def open_pattern(self):
        """Open the pattern editor on the clip's pattern, from any field, with this page's crumbs before the pattern's, so that Esc comes back here."""
        row = self.field()
        self.open_pattern_at(row.place if isinstance(row, PatternRow) else 0)

    def open_pattern_at(self, place):
        """Open the pattern editor on one pattern of the clip's list."""
        self.open_editor(section=Section.PATTERNS, name=self.clip_slot().get_pattern_names()[place], opened_from=self, track=self.track)

    def keys(self):
        if self.moving:
            return [self.bind(self.KEYS.DROP, action=self.drop), self.bind(self.KEYS.CARRY, action=self.carry)]
        return super().keys()

    def start_moving(self):
        self.moving = True
        self.carried = False
        self.say_moving()

    def say_moving(self):
        self.say(messages.MSG_MOVING.format(what=messages.MSG_MOVING_ROW.format(name=self.clip_slot().get_pattern_names()[self.field().place])))

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
        def chosen(choice):
            if choice == EXISTING_PATTERN:
                self.pick_pattern(title=labels_text.MSG_PATTERN_LABEL, current=None, then=self.add_named, same_kind=True)
            else:
                self.ask_new_pattern()
        self.ask(dialog=ChoiceDialog(title=labels_text.MSG_ADD_PATTERN_TITLE, options=labels_text.MSG_ADD_PATTERN_CHOICES), then=chosen)

    def add_named(self, name):
        self.set_value(setting=ClipSlotSetting.PATTERNS, value=[*self.clip_slot().get_pattern_names(), name])

    def ask_new_pattern(self):
        """Ask for a new pattern's name, filled in with the track's name and the next free number, make it blank and add it to the list."""
        suggested = self.document().new_name(section=Section.PATTERNS, word=self.track)
        self.ask_text(title=messages.MSG_NEW_PATTERN_PROMPT, value=suggested, then=self.add_new, is_name=True)

    def add_new(self, text):
        name = text.strip()
        document = self.document()
        if not name:
            return
        if document.song().get_setlist().has_pattern(name):
            self.refuse(errors.ERR_NAME_TAKEN.format(label=names_text.MSG_PATTERN_WORD, name=name))
            return
        first = document.song().get_setlist().get_pattern(self.clip_slot().get_pattern_name())
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
        names = self.clip_slot().get_pattern_names()
        rows = [
            PatternRow(
                label=labels_text.MSG_PATTERNS_LABEL if place == 0 else drawing.NOTHING, place=place, adjust=None,
                value=lambda name=name, place=place: marks.MSG_MOVING_OPEN + name + marks.MSG_MOVING_CLOSE if self.is_carrying(place) else name,
                enter=functools.partial(self.open_pattern_at, place), enter_what=legends.What.EDIT,
                clear=functools.partial(self.remove_pattern, place), clear_what=legends.What.REMOVE,
            ) for place, name in enumerate(names)
        ]
        return [*rows, AddRow(label=drawing.NOTHING, value=lambda: marks.MSG_ADD_ROW, adjust=None, enter=self.add_pattern, enter_what=legends.What.ADD)]

    def ends_a_list(self, field):
        return isinstance(field, AddRow)

    def is_carrying(self, place):
        row = self.field()
        return self.moving and isinstance(row, PatternRow) and row.place == place

    def pattern_order_field(self):
        return ChoiceField(page=self, label=labels_text.MSG_PATTERN_ORDER_LABEL, choices=file_format.PATTERN_ORDERS, current=self.clip_slot().get_pattern_order(),
                           names=[labels_text.MSG_PATTERN_ORDER_NAMES[order] for order in file_format.PATTERN_ORDERS],
                           shown=labels_text.MSG_PATTERN_ORDER_NAMES[self.clip_slot().get_pattern_order()],
                           set=lambda order: self.set_value(setting=ClipSlotSetting.PATTERN_ORDER, value=order))

    def set_value(self, *, setting, value):
        """Set one of the clip's settings, or None to leave it out and use its default."""
        self.document().set_clip_slot_setting(index=self.index, track=self.track, setting=setting, value=value)

    def clear(self, setting):
        self.set_value(setting=setting, value=None)

    def pick_pattern(self, *, title, current, then, same_kind=False):
        """Ask for one of the song's patterns, starting on the current one, and pass its name to then. same_kind leaves out the patterns that cannot share the clip's list: drum patterns for a clip of notes, and the other way round."""
        song = self.document().song()
        patterns = sorted_names(song.get_setlist().get_pattern_names())
        if same_kind:
            drum = song.get_setlist().get_pattern(self.clip_slot().get_pattern_name()).is_drum()
            patterns = [name for name in patterns if song.get_setlist().get_pattern(name).is_drum() == drum]
        place = patterns.index(current) if current in patterns else 0
        self.ask(dialog=ChoiceDialog(title=title, options=patterns, current=place), then=lambda item: then(patterns[item]))

    def set_morph_target(self, pattern):
        self.document().set_clip_slot_morph_target(index=self.index, track=self.track, pattern=pattern)

    def clear_morph(self):
        self.document().change_set(self.document().clip_slot(index=self.index, track=self.track).clear_morph)

    def pick_grab_track(self):
        tracks = sorted_names(name for name in self.document().track_names() if name != self.track)
        if not tracks:
            self.tell(errors.ERR_NO_OTHER_TRACKS_TITLE, errors.ERR_ADD_ANOTHER_TRACK)
            return

        def chosen(other):
            if other is None:
                self.clear(ClipSlotSetting.GRAB_TRACK)
                return
            circle = self.document().grab_circle(index=self.index, track=self.track, other=other)
            if circle:
                self.tell(errors.ERR_CIRCULAR_GRAB_TITLE, errors.ERR_GRAB_CIRCLE.format(track=other, circle=marks.MSG_CIRCLE_ARROW.join(circle)), errors.ERR_REMOVE_OTHER_GRAB)
                return
            self.set_value(setting=ClipSlotSetting.GRAB_TRACK, value=other)
        self.pick(title=labels_text.MSG_GRAB_TRACK_LABEL, values=[None, *tracks], shown=[marks.MSG_NONE_SHOWN, *tracks], current=self.clip_slot().get_grab_track(), then=chosen)

    def scale_text(self):
        """Return the clip's own scale, or the scene's it takes, which is the song's when the scene has none."""
        own = self.clip_slot().get_scale_name()
        if own is not None:
            return own
        scene = self.document().song().get_scenes()[self.index]
        return marks.MSG_SCENE_SCALE_SHOWN.format(scale=scene.get_scale_name() or self.document().song().get_scale_name() or messages.MSG_NO_SCALE)

    def pick_scale(self):
        """Ask for one of the song's scales for the clip alone, or the scene's."""
        scales = sorted_names(self.document().song().get_setlist().get_scale_names())
        self.pick(
            title=messages.MSG_CLIP_SCALE_TITLE, values=[None, *scales], shown=[labels_text.MSG_SCENE_OPTION, *scales], current=self.clip_slot().get_scale_name(),
            then=lambda name: self.set_value(setting=ClipSlotSetting.SCALE, value=name),
        )


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
        direction = self.clip_slot().get_direction()
        if direction:
            return words(direction)
        if len(self.clip_slot().get_pattern_names()) > ONE_PATTERN:
            return marks.MSG_EACH_PATTERN_DIRECTION_SHOWN
        pattern = self.document().song().get_setlist().get_pattern(self.clip_slot().get_pattern_name())
        return marks.MSG_PATTERN_DIRECTION_SHOWN.format(direction=words(pattern.get_direction()))

    def set_loop(self, loops):
        """Make the clip loop or play its repeats, and say so when that leaves every clip of the scene looping, since such a scene never ends."""
        self.set_value(setting=ClipSlotSetting.LOOP, value=True if loops else None)
        song = self.document().song()
        if song.scene_never_ends(song.get_scenes()[self.index]):
            self.tell(errors.ERR_LOOP_SCENES_TITLE, *loop_error_lines(self.document().song()))

    def morph_style(self):
        return self.clip_slot().get_morph_style_name() or clip_slot_values.FIRST_MORPH_STYLE

    def step_style(self, offset):
        styles = list(clip_slot_values.MORPH_STYLES)
        place = styles.index(self.morph_style())
        self.set_value(setting=ClipSlotSetting.MORPH_STYLE, value=styles[(place + offset) % len(styles)])

    def fields(self):
        clip_slot = self.clip_slot()
        repeat = clip_slot.get_repeat()
        own_velocity, velocity_above, store_velocity = self.velocity_values()
        result = [
            NameField(value=self.name_text, rename=self.rename, clear=lambda: self.clear(ClipSlotSetting.NAME), clear_what=legends.MSG_USE_PATTERN_NAME_WHAT),
            *self.pattern_rows(),
            Field(label=labels_text.MSG_SCALE_LABEL, value=self.scale_text, adjust=None, enter=self.pick_scale, enter_what=legends.What.CHOOSE,
                  clear=lambda: self.clear(ClipSlotSetting.SCALE), clear_what=legends.MSG_USE_SCENE_SCALE_WHAT),
            generators_field(page=self, names=lambda: self.clip_slot().get_chain_names(),
                         store=lambda names: self.set_value(setting=ClipSlotSetting.CHAINS, value=names or None)),
            self.pattern_order_field(),
            Field(label=labels_text.MSG_DIRECTION_LABEL, value=self.direction_text, adjust=self.step_direction, enter=self.pick_direction, enter_what=legends.What.CHOOSE,
                  clear=lambda: self.clear(ClipSlotSetting.DIRECTION), clear_what=legends.MSG_USE_PATTERN_DIRECTION_WHAT),
            NumberField(page=self, label=labels_text.MSG_REPEAT_LABEL, number=repeat, lowest=limits.MIN_REPEAT, highest=limits.MAX_CLIP_REPEAT, set=self.set_repeat),
            Toggle(label=labels_text.MSG_LOOP_LABEL, on=clip_slot.loops(), set=self.set_loop, shown_on=marks.MSG_LOOP_ON_SHOWN, shown_off=marks.MSG_LOOP_OFF_SHOWN),
        ]
        if repeat > defaults.DEFAULT_REPEAT:
            result.append(Field(label=labels_text.MSG_MORPH_TO_LABEL, value=lambda: clip_slot.get_morph_target() or marks.MSG_NONE_SHOWN, adjust=None,
                                enter=lambda: self.pick_pattern(title=labels_text.MSG_MORPH_TO_LABEL, current=clip_slot.get_morph_target(), then=self.set_morph_target), enter_what=legends.What.CHOOSE,
                                clear=self.clear_morph, clear_what=legends.MSG_NO_MORPH_WHAT))
            if clip_slot.get_morph_target():
                result.append(Field(label=labels_text.MSG_MORPH_DIRECTION_LABEL, value=self.morph_style, adjust=self.step_style, enter=lambda: self.step_style(1), enter_what=legends.What.NEXT))
        result += [
            velocity_field(page=self, own=own_velocity, above=velocity_above, store=store_velocity),
            Field(label=labels_text.MSG_GRAB_TRACK_LABEL, value=lambda: clip_slot.get_grab_track() or marks.MSG_NONE_SHOWN, adjust=None, enter=self.pick_grab_track, enter_what=legends.What.CHOOSE,
                  clear=lambda: self.clear(ClipSlotSetting.GRAB_TRACK), clear_what=legends.MSG_NO_GRAB_WHAT),
            self.follow_action_field(),
            *self.strum_section(),
            *velocity_ramp_sections(page=self, own=own_velocity, above=velocity_above, store=store_velocity),
            *[field for shape in file_format.PLACED_SHAPES for field in self.shape_section(shape)],
            *self.register_sections(),
            # Real-time playback's buttons, which do what L does, drawn below the settings after a blank line as every page's buttons are.
            Button(label=labels_text.MSG_PLAY_LABEL, key_name=legends.KeyName.L, enter=self.listen, enter_what=legends.MSG_LISTEN_WHAT),
            Button(label=labels_text.MSG_STOP_LABEL, key_name=legends.KeyName.L, enter=self.stop, enter_what=legends.MSG_STOP_WHAT),
        ]
        return result

    def strum_section(self):
        """Return the clip's + Strum section: how it strums its chords, over its track's."""
        clip_slot = self.clip_slot()
        strum = self.document().song().get_track(self.track).get_strum()
        taken = labels_text.MSG_STRUM_WORDS.get(strum.direction, strum.direction) if strum is not None else marks.MSG_NONE_SHOWN
        return strum_section(
            page=self, value=lambda part: clip_slot.get_written(strum_setting(part)), first=labels_text.MSG_TRACK_STRUM_CHOICE,
            inherited=marks.MSG_FROM_TRACK_SHOWN.format(value=taken),
            store=lambda part, value: self.document().change_set(self.document().clip_slot(index=self.index, track=self.track).set_strum_setting, part=part, value=value),
        )

    def velocity_values(self):
        """Return what the velocity fields read the clip's own velocity settings with, what gives a blank one from its scene, and what keeps one."""
        clip_slot = self.clip_slot()
        scene = self.document().song().get_scenes()[self.index]
        return clip_slot.get_written, scene.get_written, lambda name, value: self.document().change_set(self.document().clip_slot(index=self.index, track=self.track).set_written, name=name, value=value)

    def register_sections(self):
        """Return the clip's sections about the registers: what it sets them to as it launches, what it adds every time its pattern starts over, and the statements that bypass its generators, and that make it sit out."""
        clip_slot = self.clip_slot()
        document = self.document()
        tables = ((labels_text.MSG_BYPASS_WHEN_LABEL, statements.FIRST_TABLE, ClipSlotSetting.BYPASS_WHEN), (labels_text.MSG_SKIP_WHEN_LABEL, statements.SECOND_TABLE, ClipSlotSetting.SKIP_WHEN))
        return [
            *register_fields(
                page=self, label=labels_text.MSG_SET_REGISTERS_LABEL, name_label=labels_text.MSG_SET_REGISTER_LABEL, values=clip_slot.get_register_sets,
                store=lambda register, value: document.change_set(document.clip_slot(index=self.index, track=self.track).set_register_set, register=register, value=value),
            ),
            *register_fields(
                page=self, label=labels_text.MSG_ADD_REGISTERS_LABEL, name_label=labels_text.MSG_ADD_REGISTER_LABEL, values=clip_slot.get_register_adds,
                store=lambda register, value: document.change_set(document.clip_slot(index=self.index, track=self.track).set_register_add, register=register, value=value),
            ),
            *[field for label, table, name in tables for field in statement_section(
                page=self, label=label, table=table, statements=functools.partial(clip_slot.get_statements, name),
                store=lambda place, statement, name=name: document.change_set(document.clip_slot(index=self.index, track=self.track).set_statement, name=name, place=place, statement=statement),
            )],
        ]

    def shape_section(self, shape):
        """Return a shape's section: how busy, loud or long the clip plays over it, over its scene's."""
        clip_slot = self.clip_slot()
        return shape_section(
            page=self, shape=shape, value=lambda part: clip_slot.get_written(shape_setting(shape=shape, part=part)),
            store=lambda part, value: self.document().change_set(self.document().clip_slot(index=self.index, track=self.track).set_written, name=shape_setting(shape=shape, part=part), value=value),
        )

    def follow_action_field(self):
        """Return the Follow action field: what the clip sends down in real-time playback when its scene is done, shown as the set's default when the clip sets none, with no (default) choice."""
        advance = self.document().get_setlist().follow_action_of(self.clip_slot())
        return ChoiceField(page=self, label=labels_text.MSG_FOLLOW_ACTION_LABEL, choices=file_format.FOLLOW_ACTION_CHOICES, current=advance,
                           names=[labels_text.MSG_FOLLOW_ACTION_NAMES[choice] for choice in file_format.FOLLOW_ACTION_CHOICES],
                           shown=labels_text.MSG_FOLLOW_ACTION_NAMES[advance] if self.clip_slot().get_written_follow_action() is not None
                           else marks.MSG_FROM_SET_SHOWN.format(value=labels_text.MSG_FOLLOW_ACTION_NAMES[advance]),
                           set=lambda value: self.set_value(setting=ClipSlotSetting.FOLLOW_ACTION, value=value))

    def name_text(self):
        """Return the clip's own name, or which pattern it's named for."""
        clip_slot = self.clip_slot()
        return clip_slot.get_name() or marks.MSG_CLIP_NAMED_FOR_PATTERN.format(pattern=clip_slot.get_pattern_name())

    def rename(self):
        """Give the clip a name of its own; a blank goes back to its pattern's name."""
        self.ask_text(title=messages.MSG_CLIP_NAME_PROMPT, value=self.clip_slot().get_name() or drawing.NOTHING, then=lambda text: self.set_value(setting=ClipSlotSetting.NAME, value=text.strip()), is_name=True)

    def remarks(self, width):
        document = self.document()
        clip_slot = self.clip_slot()
        length = clock(document.lengths().clip_seconds(index=self.index, track=self.track))
        lines = [Text(messages.MSG_CLIP_LENGTH_NOTE.format(length=length, scene=clock(document.lengths().scene_seconds(self.index))), style=Style.DIM)]
        if clip_slot.loops():
            lines.append(Text(messages.MSG_LOOP_NOTE, style=Style.DIM))
        elif clip_slot.get_repeat() == defaults.DEFAULT_REPEAT:
            lines.append(Text(messages.MSG_MORPH_HINT_NOTE, style=Style.DIM))
        if clip_slot.get_grab_track() is not None and not any(self.document().has_grab_steps(name) for name in clip_slot.get_pattern_names()):
            lines.append(Text(messages.MSG_GRAB_HINT_NOTE, style=Style.DIM))
        problem = document.lengths().scene_problem(self.index)
        if problem:
            lines.append(Text(messages.MSG_PROBLEM_NOTE.format(problem=problem)[:width]))
        return lines
