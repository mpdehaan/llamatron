# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Arrange page: the current song's scenes as rows, its tracks as columns, and a clip where they meet.

Everything about a song's structure happens here, as in Live's Session View:
the track names across the top can be moved onto, so tracks are added, copied,
inserted, moved and deleted on this page, like scenes, and Enter on a track, a scene or a clip
opens its own page. C copies everywhere: a scene or track is copied in place,
and a clip is copied to be pasted with V.

The grid: the track names and the scene column
stay in place while the clips scroll, the corner is blank since the crumbs say where you are, a
double-lined frame marks the clip, scene or track under the cursor in place of reverse video, an
empty clip slot shows + and add only under the cursor, and a bar under each scene shows its length
against the longest scene's and one under each clip its length against its scene's.

This page keeps the cursor, how far the grid has scrolled, the keys and what each key does to
the song. ArrangeDrawing (arrange_drawing.py) draws the grid from them.
"""

import functools
from rich.text import Text
import time
from typing import NamedTuple

from llamatron.interface.forms import moves
from llamatron.interface.forms.cursor import NoSuchPlace
from llamatron.interface.forms.text import sorted_names
from llamatron.interface.tracker import drawing, keybindings
from llamatron.interface.tracker.components.inset_window import drawn_over, inside_size
from llamatron.interface.tracker.components.scene_view import SceneView
from llamatron.interface.tracker.components.stage_drawing import frame_box, inside_of, visualizer_area
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.drawing import laid_over, padded, Style
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.arrange import arrange_details
from llamatron.interface.tracker.screens.arrange.arrange_details import clip_cell, scene_cell, track_cell
from llamatron.interface.tracker.screens.arrange.arrange_drawing import ArrangeDrawing
from llamatron.interface.tracker.screens.arrange.clip_page import ClipPage
from llamatron.interface.tracker.screens.arrange.scene_page import ScenePage
from llamatron.interface.tracker.screens.generators.generator_pages import generator_page_of_kind
from llamatron.interface.tracker.screens.shared.generator_names import generators_to_add, listed_generator
from llamatron.interface.tracker.screens.shared.page import Page
from llamatron.interface.tracker.screens.shared.shared import play_through, scene_name
from llamatron.interface.tracker.uses import grabbers
from llamatron.interface.visualizers import modes
from llamatron.interface.visualizers.modes import mode_called
from llamatron.model.objects.naming import new_name
from llamatron.model.schema.file_format import ClipSlotSetting, Section
from llamatron.user_strings import errors, help as help_text, labels, marks, messages, names as names_text


# How often the visualizer draws a frame while it shows, in seconds, and how long a mode's name shows when it changes.
FRAME_SECONDS = 0.05
NAME_SECONDS = 8.0
# How many lines above the bottom of a batch video's frame a scene's announcement is drawn.
ANNOUNCED_ROWS_UP = 2
# The row of track names above the first scene, which the cursor can move onto.
HEADER_ROW = -1
# The scene names are column 0, and the tracks count from 1.
SCENE_COLUMN = 0
FIRST_SCENE_NUMBER = 1
FIRST_TRACK_COLUMN = 1
# The first choice of an empty cell's picker, which makes a new blank pattern, before the existing patterns.
NEW_PATTERN_PLACE = 0
# The number a blank pattern named after its track starts from, as lead 1.
# What Move mode can carry.
MOVING_SCENE = 'scene'
MOVING_TRACK = 'track'
MOVING_CLIP = 'clip'
# How far each arrow carries a clip: scenes down, then tracks right.
CLIP_STEPS = {Key.UP: (-1, 0), Key.DOWN: (1, 0), Key.LEFT: (0, -1), Key.RIGHT: (0, 1)}
# The word in the crumbs for what a line of details opens, by the section the line names; a generator's is found by its kind.
DETAIL_WORDS = {
    Section.CHAINS: names_text.MSG_CHAIN_WORD, Section.SCALES: names_text.MSG_SCALE_WORD,
    Section.INSTRUMENTS: names_text.MSG_INSTRUMENT_WORD, Section.GROOVES: names_text.MSG_GROOVE_WORD,
}


def announced(*, lines, text, inside):
    """Return a batch video's screen with a scene's announcement laid over it in reverse video, centred near the bottom of the frame's inside, or as it is with nothing to announce or no room."""
    row = inside.bottom - ANNOUNCED_ROWS_UP
    if text is None or row <= inside.top or row >= len(lines):
        return lines
    piece = Text(padded(text), style=Style.REVERSE)
    start = inside.left + max((inside.right - inside.left + 1 - piece.cell_len) // 2, 0)
    shown = list(lines)
    shown[row] = laid_over(line=lines[row], start=start, piece=piece)
    return shown


class ArrangePlace(NamedTuple):
    """A place Arrange's cursor can be: a clip, by its scene's place and its track's name; a scene's name, with no track; a track's name, with no scene; the corner, with neither."""

    scene: int = None
    track: str = None

class ArrangePage(Page):

    """Arrange: the song's scenes as rows and its tracks as columns, each cell a clip, where a song is laid out and played."""

    KEYS = keybindings.ArrangePage
    crumbs = (labels.Crumb.ARRANGE,)
    HELP = help_text.HELP_ARRANGE_PAGE

    def __init__(self, holder):
        super().__init__(holder)
        # The visualizer mode over the clip area, or None for the clips, the timer that draws its frames, and when it began.
        self.visualizer = None
        self._frame_timer = None
        self._visualizer_began = None
        # The player's clock when the visualizer last heard the notes, so that each frame hears what started since.
        self._heard_since = None
        # The name the visualizer last showed, and since when, so that a change shows the new name for NAME_SECONDS.
        self._name_shown = None
        self._name_since = None
        # The scene last announced, and since when, so that a launch that announces shows each scene's name for NAME_SECONDS as it starts.
        self._scene_announced = None
        self._scene_since = None
        # A batch video's stage (interface/tracker/batch_stage.py), which draws the whole screen while it runs, or None.
        self.stage = None
        self.row = 0
        self.column = SCENE_COLUMN
        self.top = 0
        self.left = 0
        self.copied = None
        # Whether Tab has locked into the cursor's cell, the place among its lines naming something that is picked, or None when it names
        # nothing, and in the usual view the cell Tab opened, which alone shows its details until Tab again.
        self.locked = False
        self.picked = None
        self.opened_cell = None
        # Scene View, an Inset Window over the page (interface/tracker/components/scene_view.py), or None.
        self.inset = None
        # Move mode: what M picked up, MOVING_SCENE, MOVING_TRACK or MOVING_CLIP, or None, and whether it has been
        # carried yet, so that one move is one undo step.
        self.moving = None
        self.carried = False
        # What draws the grid from the cursor and the scroll kept here.
        self.drawing = ArrangeDrawing(self)

    def duration(self):
        lengths = self.document().lengths()
        return lengths.song_seconds()

    def time_text(self):
        """Return the time at the right of the crumbs: where the song is while it plays, and how long it is, or its length alone."""
        return self.playing_clock() or super().time_text()

    def transport(self):
        return self.app.transport

    def real_time_on(self):
        """Return whether the set's Real Time switch is on, which is when the page has its play buttons and the corner."""
        setlist = self.document().get_setlist()
        return setlist.is_real_time()

    def scenes(self):
        song = self.document().song()
        return song.get_scenes()

    def tracks(self):
        return self.document().track_names()

    # Where the cursor is: the header of track names, a scene's name, a clip slot, or one of the two + places.

    def on_header(self):
        return self.row == HEADER_ROW

    def on_corner(self):
        """Return whether the cursor is on the corner over the scene names, where Space plays the song from the top, reachable while Real Time is on."""
        return self.on_header() and self.column == SCENE_COLUMN

    def on_track_plus(self):
        """Return whether the cursor is on the + after the last track name, where a track is added."""
        return self.on_header() and self.column == len(self.tracks()) + FIRST_TRACK_COLUMN

    def on_track_name(self):
        return self.on_header() and not self.on_track_plus() and not self.on_corner()

    def on_scene_name(self):
        return not self.on_header() and self.column == SCENE_COLUMN

    def on_plus_row(self):
        return self.row == len(self.scenes())

    def on_clip_slot(self):
        return not self.on_header() and not self.on_plus_row() and self.in_a_track_column()

    def in_a_track_column(self):
        """Return whether the cursor is in a track's column or on the + after the last, rather than in the scene column."""
        return self.column != SCENE_COLUMN

    def track_place(self):
        """Return the place in the track list of the column the cursor is in."""
        return self.column - FIRST_TRACK_COLUMN

    def track(self):
        return self.tracks()[self.track_place()]

    def under_cursor(self):
        """Return what the cursor is on, as an ArrangePlace: a clip, a scene's name, a track's name or the corner. None on either +."""
        if self.on_plus_row() or self.on_track_plus():
            return None
        scene = None
        if not self.on_header():
            scene = self.row
        track = None
        if self.in_a_track_column():
            track = self.track()
        return ArrangePlace(scene=scene, track=track)

    def key_toward(self, target):
        """Return the arrow that brings the cursor nearer an ArrangePlace, or None when the cursor is on it.

        The + row has the scene column alone, so the cursor leaves it upward first; from the header it goes down to
        the scene's row before going along it, since the header's scene column is reached only while Real Time is on.
        """
        if target.track is not None and target.track not in self.tracks():
            raise NoSuchPlace(screen=self, target=target)
        if target.scene is not None and not HEADER_ROW < target.scene < len(self.scenes()):
            raise NoSuchPlace(screen=self, target=target)
        row = HEADER_ROW
        if target.scene is not None:
            row = target.scene
        column = SCENE_COLUMN
        if target.track is not None:
            column = self.tracks().index(target.track) + FIRST_TRACK_COLUMN
        if self.on_plus_row():
            return Key.UP
        if self.on_header() and row != HEADER_ROW:
            return Key.DOWN
        return moves.toward(here=self.column, there=column, back=Key.LEFT, forward=Key.RIGHT) or moves.toward(here=self.row, there=row)

    def clamp(self):
        self.row = max(min(self.row, len(self.scenes())), HEADER_ROW)
        if self.on_plus_row():
            self.column = SCENE_COLUMN
        elif self.on_header():
            self.column = max(min(self.column, len(self.tracks()) + FIRST_TRACK_COLUMN), self.first_header_column())
        else:
            self.column = max(min(self.column, len(self.tracks())), SCENE_COLUMN)

    def first_header_column(self):
        """Return the first column the cursor reaches on the header: the corner while Real Time is on, the first track's name otherwise."""
        if self.real_time_on():
            return SCENE_COLUMN
        return FIRST_TRACK_COLUMN

    def keys(self):
        self.clamp()
        if self.visualizer is not None:
            return [
                self.bind(self.KEYS.TO_CLIPS, action=self.hide_visualizer), self.bind(self.KEYS.STEP_VISUALIZER, action=self.step_visualizer),
                self.bind(self.KEYS.VISUALIZER, action=self.next_visualizer),
            ]
        if self.moving is not None:
            return self.moving_keys()
        if self.inset is not None:
            return self.inset_keys()
        if self.picking():
            keys = [self.bind(self.KEYS.ESCAPE_CELL, action=self.stop_picking), self.bind(self.KEYS.OUT_OF_DETAILS, action=self.stop_picking)]
            if self.pickable():
                keys.append(self.bind(self.KEYS.PICK_DETAIL, action=self.move_picked, wants_key=True))
                target = self.picked_target()
                if target is not None and target.kind == arrange_details.ADD_CHAIN:
                    keys.append(self.bind(self.KEYS.ADD_CHAIN, action=self.add_chain_to_cell))
                else:
                    keys.append(self.bind(self.KEYS.OPEN_DETAIL, action=self.open_picked))
                if target is not None and target.kind == Section.CHAINS:
                    keys.append(self.bind(self.KEYS.REMOVE_CHAIN, action=self.remove_chain_from_cell))
            return keys + [self.bind(self.KEYS.CLOSE_DETAILS, action=self.close_details)]
        result = [self.bind(self.KEYS.BACK, action=self.go_back), self.bind(self.KEYS.MOVE, action=self.move_cursor, wants_key=True)]
        if self.on_header():
            result += self.header_keys()
        elif self.on_plus_row():
            result += [self.bind(self.KEYS.ADD_SCENE, action=self.add_scene), self.bind(self.KEYS.ADD_SCENE_HERE, action=self.add_scene)]
        else:
            result += self.scene_row_keys()
        if self.cursor_cell() is not None:
            result.append(self.bind(self.KEYS.INTO_DETAILS, action=self.start_picking))
        if self.app.shows_arrange_details:
            result.append(self.bind(self.KEYS.HIDE_DETAILS, action=self.toggle_details))
        else:
            result.append(self.bind(self.KEYS.SHOW_DETAILS, action=self.toggle_details))
        if self.real_time_on():
            result.append(self.bind(self.KEYS.VISUALIZER, action=self.next_visualizer))
        result.append(self.bind(self.KEYS.FRACTURE, action=self.ask_to_fracture))
        return result

    # The details view: D shows under every bar the chains, the generators and the settings that aren't their
    # defaults, and D again hides them. Every key works in it as in the usual view, and the choice is kept for the session.

    def shows_details(self):
        """Return whether the grid shows its details view: chosen with R, and never under the visualizer or a batch video's stage."""
        return self.app.shows_arrange_details and self.visualizer is None and self.stage is None

    def ask_to_fracture(self):
        """Ask before giving every clip of the song a pattern of its own, which a finished song wants so that its sections can be edited apart."""
        self.confirm(title=messages.MSG_FRACTURE_TITLE, lines=[messages.MSG_FRACTURE_QUESTION], then=self.fracture)

    def fracture(self):
        document = self.document()
        setlist = document.get_setlist()
        copies = document.change_set(setlist.fracture, document.song())
        if copies:
            self.say(messages.MSG_FRACTURED.format(count=len(copies)))
        else:
            self.say(messages.MSG_NOTHING_TO_FRACTURE)

    def toggle_details(self):
        """Show the details view, or the usual one again."""
        self.app.shows_arrange_details = not self.app.shows_arrange_details
        self.stop_picking()
        self.top = 0
        self.left = 0

    # Scene View, an Inset Window over the page: P opens it on a scene's name, and P or Esc closes it.

    def open_scene_view(self):
        self.inset = SceneView(document=self.document(), index=self.row)

    def close_inset(self):
        self.inset = None

    def inset_keys(self):
        """Return the keys while Scene View shows: P closes it, the arrows move its cursor, PgUp and PgDn jump a bar, V switches its view, - and = zoom, [ and ] scroll its sidebar, and Esc closes it too, as Esc closes the topmost thing everywhere."""
        switch = self.KEYS.TO_WRITTEN
        if self.inset.is_written():
            switch = self.KEYS.TO_PLAYED
        return [
            self.bind(self.KEYS.ESCAPE_INSET, action=self.close_inset),
            self.bind(self.KEYS.CLOSE_INSET, action=self.close_inset),
            self.bind(self.KEYS.INSET_MOVE, action=self.inset.move_cursor, wants_key=True),
            self.bind(self.KEYS.INSET_BARS, action=self.inset.jump_bar),
            self.bind(switch, action=self.inset.switch),
            self.bind(self.KEYS.INSET_ZOOM, action=self.inset.zoom_by),
            self.bind(self.KEYS.INSET_SCROLL, action=self.inset.scroll_sidebar),
        ]

    def cursor_cell(self):
        """Return the cell the cursor is on, a track's name, a scene's name or a clip slot, as arrange_details names cells, or None on the corner and the + places."""
        if self.on_track_name():
            return track_cell(self.track())
        if self.on_header() or self.on_plus_row():
            return None
        if self.on_scene_name():
            return scene_cell(self.row)
        track = self.track()
        if self.document().clip_slot(index=self.row, track=track) is None:
            return None
        return clip_cell(index=self.row, track=track)

    def pickable(self):
        """Return the places among the cursor's cell's lines of details of those that name something with a page of its own, which Tab can pick."""
        return [place for place, line in enumerate(self.drawing.details_at_cursor()) if line.target is not None]

    def picking(self):
        """Return whether Tab has locked into the cursor's cell, keeping what is picked within the lines there are now, since an edit can take some away or add the first."""
        if not self.locked:
            return False
        if self.cursor_cell() is None:
            self.stop_picking()
            return False
        count = len(self.pickable())
        if count == 0:
            self.picked = None
        else:
            self.picked = min(self.picked or 0, count - 1)
        return True

    def picked_line(self):
        """Return the place among the cursor's cell's lines of details of the one picked, which the drawing puts in brackets, or None."""
        if not self.picking() or self.picked is None:
            return None
        return self.pickable()[self.picked]

    def start_picking(self):
        """Open the cursor's cell's details, if the details view isn't showing them, and lock into the cell, on its first line naming something if it has one."""
        self.locked = True
        self.picked = None
        if self.pickable():
            self.picked = 0
        if not self.shows_details():
            self.opened_cell = self.cursor_cell()

    def stop_picking(self):
        """Leave the cell, closing its details in the usual view."""
        self.locked = False
        self.picked = None
        self.opened_cell = None

    def close_details(self):
        """Leave the cell and close every detail, the details view among them, as R does while locked into a cell."""
        self.stop_picking()
        if self.app.shows_arrange_details:
            self.toggle_details()

    def move_picked(self, name):
        """Move the cursor among the details of the cell locked into, stopping at each end."""
        self.picked = moves.moved(place=self.picked, name=name, count=len(self.pickable()))

    def picked_target(self):
        """Return what the picked line names, or None."""
        place = self.picked_line()
        if place is None:
            return None
        details = self.drawing.details_at_cursor()
        return details[place].target

    def cell_chain_names(self):
        """Return the chains the cursor's cell runs, a clip's, a scene's or a track's, in order."""
        cell = self.cursor_cell()
        song = self.document().song()
        if cell[0] == arrange_details.TRACK_CELL:
            return list(song.get_track(cell[1]).get_chain_names())
        if cell[0] == arrange_details.SCENE_CELL:
            return list(song.get_scenes()[cell[1]].get_chain_names())
        clip_slot = self.document().clip_slot(index=cell[1], track=cell[2])
        return list(clip_slot.get_chain_names())

    def set_cell_chain_names(self, names):
        """Set the chains the cursor's cell runs, through the setter of a clip, a scene or a track."""
        cell = self.cursor_cell()
        document = self.document()
        song = document.song()
        if cell[0] == arrange_details.TRACK_CELL:
            track = song.get_track(cell[1])
            document.change_set(track.set_chain_names, names=names, song=song)
        elif cell[0] == arrange_details.SCENE_CELL:
            scene = song.get_scene(cell[1])
            document.change_set(scene.set_chain_names, names=names, song=song)
        else:
            self.document().set_clip_slot_setting(index=cell[1], track=cell[2], setting=ClipSlotSetting.CHAINS, value=names)

    def add_chain_to_cell(self):
        """Ask for one of the set's chains and add it to the cursor's cell alone, after the chains it runs."""
        setlist = self.document().get_setlist()
        offered = [name for _, name in generators_to_add(setlist)]
        if not offered:
            self.refuse(errors.ERR_NO_GENERATORS_TO_ADD)
            return
        names = self.cell_chain_names()

        def chosen(place):
            self.set_cell_chain_names([*names, offered[place]])
        options = []
        for name in offered:
            options.append(listed_generator(setlist=setlist, name=name))
        self.ask(dialog=ChoiceDialog(title=messages.MSG_ADD_GENERATOR_TITLE, options=options), then=chosen)

    def remove_chain_from_cell(self):
        """Take the picked chain out of the cursor's cell alone, the chain staying in the set."""
        names = self.cell_chain_names()
        del names[self.picked_target().place]
        self.set_cell_chain_names(names)

    def open_picked(self):
        """Open the page of what the picked line names, a chain's, a generator's, a scale's, an instrument's or a groove's, its crumbs after Arrange's."""
        details = self.drawing.details_at_cursor()
        target = details[self.picked_line()].target
        if target.kind in DETAIL_WORDS:
            self.open_editor(section=target.kind, name=target.name, word=DETAIL_WORDS[target.kind])
        else:
            listing = generator_page_of_kind(target.kind)
            self.open_editor(section=listing.section, name=target.name, word=listing.label)

    # The visualizer over the clip area, with Real Time on (visualizers/).

    def shown_modes(self):
        """Return the visualizer modes the key steps through, every mode but those the set hides, in order."""
        setlist = self.document().get_setlist()
        hidden = setlist.get_hidden_visualizers()
        return [mode for mode in modes.MODES if mode.OPTION not in hidden]

    def first_mode(self):
        """Return the mode the visualizer key shows first: the song's choice, else the set's, when it isn't hidden, and otherwise the first shown."""
        shown = self.shown_modes()
        setlist = self.document().get_setlist()
        chosen = mode_called(setlist.visualizer_for(self.document().song()) or drawing.NOTHING)
        if chosen in shown:
            return chosen
        return shown[0]

    def next_visualizer(self):
        """Show the first mode, or the next one shown, or the clips again after the last."""
        shown = self.shown_modes()
        if not shown:
            self.say(messages.MSG_EVERY_VISUALIZER_HIDDEN)
            return
        if self.visualizer is None:
            self.show_visualizer(self.first_mode())
            return
        place = len(shown)
        if type(self.visualizer) in shown:
            place = shown.index(type(self.visualizer)) + 1
        if place < len(shown):
            self.show_visualizer(shown[place])
        else:
            self.hide_visualizer()

    def step_visualizer(self, direction):
        """Show the mode before or after the one showing among those shown, going round, as [ and ] step through a cycle of choices."""
        shown = self.shown_modes()
        if not shown:
            return
        place = 0
        if type(self.visualizer) in shown:
            place = shown.index(type(self.visualizer))
        self.show_visualizer(shown[(place + direction) % len(shown)])

    def show_visualizer(self, mode):
        """Show a visualizer mode over the clip area, drawing a frame every FRAME_SECONDS while it shows."""
        setlist = self.document().get_setlist()
        self.visualizer = mode.made_for(hidden=setlist.get_hidden_visualizers())
        self._visualizer_began = time.monotonic()
        if self._frame_timer is None:
            self._frame_timer = self.set_interval(FRAME_SECONDS, self.draw)

    def hide_visualizer(self):
        """Bring the clips back, and stop drawing frames."""
        self.visualizer = None
        if self._frame_timer is not None:
            self._frame_timer.stop()
            self._frame_timer = None

    def header_keys(self):
        """Return the keys on the row of track names: play on the corner, adding on the +, and everything else on a name."""
        if self.on_corner():
            if self.transport().is_playing():
                return [self.bind(self.KEYS.STOP_PLAYING, action=self.stop_from_the_corner)]
            return [self.bind(self.KEYS.PLAY_SONG, action=self.play_song)]
        if self.on_track_plus():
            return [self.bind(self.KEYS.ADD_TRACK, action=self.add_track), self.bind(self.KEYS.ADD_TRACK_HERE, action=self.add_track)]
        return [
            self.bind(self.KEYS.ADD_TRACK, action=self.add_track),
            self.bind(self.KEYS.TRACK_SETTINGS, action=self.open_track_editor),
            self.bind(self.KEYS.COPY_TRACK, action=self.copy_track),
            self.bind(self.KEYS.INSERT_TRACK, action=self.insert_track),
            self.bind(self.KEYS.MOVE_TRACK, action=functools.partial(self.start_moving, MOVING_TRACK)),
            self.bind(self.KEYS.DELETE_TRACK, action=self.delete_track),
        ]

    def scene_row_keys(self):
        """Return the keys on a scene's row: its name's, or its clip slot's, then the ones the whole row shares."""
        result = [self.bind(self.KEYS.ADD_SCENE, action=self.add_scene)]
        if self.on_scene_name():
            result += self.play_scene_keys()
            result += [
                self.bind(self.KEYS.SCENE_SETTINGS, action=self.open_scene_page),
                self.bind(self.KEYS.SCENE_VIEW, action=self.open_scene_view),
                self.bind(self.KEYS.MOVE_SCENE, action=functools.partial(self.start_moving, MOVING_SCENE)),
                self.bind(self.KEYS.COPY_SCENE, action=self.copy_scene),
                self.bind(self.KEYS.DELETE_SCENE, action=self.delete_scene),
            ]
        else:
            clip_slot = self.document().clip_slot(index=self.row, track=self.track())
            if clip_slot is None:
                result.append(self.bind(self.KEYS.ADD_CLIP, action=self.add_clip))
                result.append(self.bind(self.KEYS.BLANK_PATTERN, action=self.blank_pattern))
            else:
                result += self.play_clip_keys()
                result += [
                    self.bind(self.KEYS.EDIT_CLIP, action=self.open_clip_page),
                    self.bind(self.KEYS.OPEN_PATTERN, action=functools.partial(self.open_pattern, clip_slot)),
                    self.bind(self.KEYS.MOVE_CLIP, action=functools.partial(self.start_moving, MOVING_CLIP)),
                    self.bind(self.KEYS.COPY_CLIP, action=self.copy_clip),
                    self.bind(self.KEYS.DELETE_CLIP, action=self.delete_clip),
                ]
            if self.copied is not None:
                result.append(self.bind(self.KEYS.PASTE_CLIP, action=self.paste_clip))
        result.append(self.bind(self.KEYS.INSERT_SCENE, action=self.insert_scene))
        return result

    def open_track_editor(self):
        self.open_editor(section=Section.TRACKS, name=self.track())

    def open_scene_page(self):
        self.show_page(ScenePage(holder=self.holder, index=self.row))

    def open_clip_page(self):
        self.show_page(ClipPage(holder=self.holder, index=self.row, track=self.track()))

    def play_scene_keys(self):
        """Return Space on a scene's name while Real Time is on: stop everything when the scene plays, and play from the scene otherwise."""
        if not self.real_time_on():
            return []
        if self.row in self.transport().playing_scenes():
            return [self.bind(self.KEYS.STOP_PLAYING, action=self.stop_playing_all)]
        return [self.bind(self.KEYS.PLAY_SCENE, action=self.play_scene)]

    def play_clip_keys(self):
        """Return Space on a clip while Real Time is on: stop the clip when it plays, and play it on its own otherwise."""
        if not self.real_time_on():
            return []
        if self.transport().is_clip_playing(index=self.row, track=self.track()):
            return [self.bind(self.KEYS.STOP_CLIP, action=self.stop_clip)]
        return [self.bind(self.KEYS.PLAY_CLIP, action=self.play_clip)]

    def play_song(self):
        scene = messages.MSG_SCENE_NUMBER.format(number=FIRST_SCENE_NUMBER)
        play_through(page=self, play=self.transport().play_song, what=scene, said=messages.MSG_PLAYING_FROM.format(scene=scene))

    def play_scene(self):
        index = self.row
        scene = messages.MSG_SCENE_NUMBER.format(number=index + FIRST_SCENE_NUMBER)
        play = functools.partial(self.transport().play_scene, index=index)
        play_through(page=self, play=play, what=scene, said=messages.MSG_PLAYING_FROM.format(scene=scene))

    def play_clip(self):
        index = self.row
        track = self.track()
        clip_slot = self.document().clip_slot(index=index, track=track)
        clip = messages.MSG_CLIP_ON_TRACK.format(name=clip_slot.get_display_name(), track=track)
        play = functools.partial(self.transport().play_clip, index=index, track=track)
        play_through(page=self, play=play, what=clip, said=messages.MSG_PLAYING_CLIP.format(clip=clip))

    def stop_playing_all(self):
        self.transport().stop_all()
        self.say(messages.MSG_STOPPED)

    def stop_from_the_corner(self):
        """Stop everything, as Space on the corner does, which also ends an interactive take being recorded."""
        self.stop_playing_all()
        self.app.end_take()

    def go_to_corner(self):
        """Put the cursor on the corner over the scene names, where Space plays the song, which an interactive take opens on."""
        self.row = HEADER_ROW
        self.column = SCENE_COLUMN

    def go_back(self):
        """Go back, stopping what plays, or, in an interactive take being recorded, stop and end the take, so that the video never shows the main screen."""
        if self.app.launch.interactive:
            self.stop_playing()
            self.app.end_take()
            return
        super().go_back()

    def stop_clip(self):
        self.transport().stop_clip(self.track())
        self.say(messages.MSG_STOPPED_TRACK.format(track=self.track()))

    def move_cursor(self, name):
        if name == Key.UP:
            self.row -= 1
        elif name == Key.DOWN:
            self.row += 1
        elif name == Key.LEFT:
            self.column -= 1
        else:
            self.column += 1
        self.clamp()

    def body(self, *, width, height):
        self.clamp()
        if self.visualizer is not None and self.stage is None:
            heard_at, heard = self.transport().heard(since=self._heard_since)
            self._heard_since = heard_at
            now = time.monotonic()
            lines = self.drawing.visualized_body(width=width, height=height, mode=self.visualizer, now=now - self._visualizer_began, heard=heard)
            return self.drawing.with_name(lines=lines, name=self.name_to_show(now))
        lines = self.drawing.body(width=width, height=height)
        if self.app.launch.announce and self.stage is None:
            return self.drawing.with_name(lines=lines, name=self.scene_to_announce(time.monotonic()))
        return lines

    def with_inset(self, *, screen, width, height):
        """Return the screen with Scene View's Inset Window laid over it."""
        inner_width, inner_height = inside_size(width=width, height=height)
        title = marks.MSG_SCENE_VIEW_TITLE.format(scene=scene_name(scene=self.scenes()[self.inset.get_index()], index=self.inset.get_index()))
        closing = marks.MSG_SCENE_VIEW_CLOSING.format(key=self.KEYS.CLOSE_INSET.name, what=self.KEYS.CLOSE_INSET.what)
        return drawn_over(screen=screen, width=width, height=height, title=title, inside=self.inset.lines(width=inner_width, height=inner_height),
                          colour=self.inset.border_colour(), closing=closing)

    def staged_screen(self, *, screen, width, height):
        """Return the whole screen a batch video's stage draws over the page's lines, the visualizer filling the frame once the song plays, Scene View's Inset Window over it while that shows, or the screen as it is."""
        if self.inset is not None:
            return self.with_inset(screen=screen, width=width, height=height)
        if self.stage is None:
            return screen
        now = time.monotonic()
        heard_at, heard = self.transport().heard(since=self._heard_since)
        self._heard_since = heard_at
        frame = None
        if self.visualizer is not None and self.stage.shows_visualizer(now):
            area = visualizer_area(width=width, height=height)
            frame = self.visualizer.frame(width=max(area.right - area.left + 1, 0), height=max(area.bottom - area.top + 1, 0), now=now - self._visualizer_began, heard=heard)
        clips = None
        if self.stage.shows_clips(now):
            inside = inside_of(frame_box(width=width, height=height))
            clips = self.page_lines(width=max(inside.right - inside.left + 1, 1), height=max(inside.bottom - inside.top + 1, 1))
        staged = self.stage.screen(arrange=screen, width=width, height=height, now=now, frame=frame, clips=clips, seconds_per_beat=heard.seconds_per_beat,
                                   scene=self.playing_scene())
        if self.app.launch.announce and not self.stage.is_black():
            return announced(lines=staged, text=self.scene_to_announce(now), inside=inside_of(frame_box(width=width, height=height)))
        return staged

    def name_to_show(self, now):
        """Return the visualizer's name to show at a moment, for NAME_SECONDS after it changes, by a key or by a mode of modes moving on, or None."""
        if self.app.launch.announce:
            return self.scene_to_announce(now)
        name = self.visualizer.shown_name()
        if name != self._name_shown:
            self._name_shown = name
            self._name_since = now
        if now - self._name_since >= NAME_SECONDS:
            return None
        return name

    def playing_scene(self):
        """Return the index of the scene that plays, the lowest on the page when a start by hand left two playing, or None."""
        playing = self.transport().playing_scenes()
        if not playing:
            return None
        return max(playing)

    def boxes_playing_scene(self):
        return self.app.launch.boxes_playing_scene()

    def scene_to_announce(self, now):
        """Return the playing scene's announcement at a moment, for NAME_SECONDS after the scene starts, or None: a scene playing again announces nothing."""
        index = self.playing_scene()
        if index is None:
            self._scene_announced = None
            return None
        if index != self._scene_announced:
            self._scene_announced = index
            self._scene_since = now
        if now - self._scene_since >= NAME_SECONDS:
            return None
        return marks.MSG_SCENE_ANNOUNCED.format(name=scene_name(scene=self.scenes()[index], index=index))

    # Scenes.

    def new_scene_name(self):
        taken = set()
        for scene in self.scenes():
            name = scene.get_name()
            if name is not None:
                taken.add(name)
        return new_name(word=names_text.MSG_NEW_SCENE_WORD, taken=list(taken))

    def add_scene(self):
        index = self.row + 1
        if self.on_plus_row():
            index = len(self.scenes())
        self.document().add_scene(index=index, name=self.new_scene_name())
        self.row = index
        self.column = SCENE_COLUMN

    def insert_scene(self):
        """Put a blank scene before the one the cursor is on, and stay on it."""
        self.document().add_scene(index=self.row, name=self.new_scene_name())

    def copy_scene(self):
        """Ask whether a copy of the scene shares its patterns or gets copies of them, then add the copy with its clips right below it, and move onto it."""
        row = self.row
        name = scene_name(scene=self.scenes()[row], index=row)
        title = messages.MSG_COPY_SCENE_TITLE.format(name=name)
        self.ask_how_patterns_copy(title=title, then=functools.partial(self.copied_scene, row=row))

    def copied_scene(self, own, *, row):
        """Copy the scene to just below it, giving the copy's clips patterns of their own when own is true, and move onto it."""
        document = self.document()
        document.copy_scene(row)
        if own:
            song = document.song()
            copy = song.get_scene(row + 1)
            clip_slots = []
            for track in copy.get_track_names():
                clip_slots.append(copy.get_clip_slot(track))
            document.give_own_patterns(clip_slots)
        self.row = row + 1

    def ask_how_patterns_copy(self, *, title, then):
        """Ask whether a copy shares the patterns its clips play or gets copies of them, and pass then whether it gets copies."""
        self.pick(title=title, values=[False, True], shown=labels.MSG_COPY_PATTERNS_CHOICES, then=then)

    def delete_scene(self):
        if len(self.scenes()) <= 1:
            self.tell(errors.ERR_CANT_DELETE_TITLE, errors.ERR_LAST_SCENE_SHOWN)
            return
        scene = self.scenes()[self.row]
        count = len(scene.get_track_names())
        if count and self.transport().is_playing():
            self.tell(errors.ERR_CANT_DELETE_TITLE, errors.ERR_SCENE_PLAYING_SHOWN)
            return
        message = [messages.MSG_DELETE_SCENE_QUESTION.format(name=scene_name(scene=scene, index=self.row))]
        if count:
            message.append(messages.MSG_ALSO_DELETES_CLIPS.format(count=count))
        self.confirm_delete(lines=message, then=self.remove_scene)

    def remove_scene(self):
        """Take the cursor's scene out of the song, as one edit of the set."""
        song = self.document().song()
        self.document().change_set(song.remove_scene, self.row)

    # Move mode: M on a scene's name, a track's name or a clip picks it up, the arrows carry it, a clip only into an
    # empty cell, and Enter, Esc or M drops it where it is. The box around it is green while it's carried.

    def start_moving(self, what):
        self.moving = what
        self.carried = False
        self.say_moving()

    def say_moving(self):
        if self.moving == MOVING_SCENE:
            scene = self.scenes()[self.row]
            what = messages.MSG_MOVING_SCENE.format(name=scene_name(scene=scene, index=self.row))
        elif self.moving == MOVING_TRACK:
            what = messages.MSG_MOVING_TRACK.format(name=self.track())
        else:
            clip_slot = self.document().clip_slot(index=self.row, track=self.track())
            what = messages.MSG_MOVING_CLIP.format(name=clip_slot.get_display_name())
        self.say(messages.MSG_MOVING.format(what=what))

    def moving_keys(self):
        """Return the keys while something is carried: Enter, Esc or M drops it, and the arrows that carry it."""
        carry = {MOVING_SCENE: self.KEYS.CARRY_SCENE, MOVING_TRACK: self.KEYS.CARRY_TRACK}
        if self.moving == MOVING_CLIP:
            carrying = self.bind(self.KEYS.CARRY_CLIP, action=self.carry_clip, wants_key=True)
        else:
            carrying = self.bind(carry[self.moving], action=self.carry)
        return [self.bind(self.KEYS.DROP, action=self.drop), carrying]

    def carried_once(self):
        """Note a carry, merging every carry after the first into one undo step with it."""
        if self.carried:
            self.document().continue_edit()
        self.carried = True

    def carry(self, offset):
        """Carry the picked-up scene up or down, or the picked-up track left or right, one place."""
        self.carried_once()
        if self.moving == MOVING_SCENE:
            self.shift_scene(offset)
        else:
            self.shift_track(offset)
        self.say_moving()

    def carry_clip(self, name):
        """Carry the picked-up clip to the nearest empty cell the arrow points to, passing over cells that hold clips; with none, it stays."""
        rows, columns = CLIP_STEPS[name]
        tracks = self.tracks()
        row = self.row + rows
        place = self.track_place() + columns
        while 0 <= row < len(self.scenes()) and 0 <= place < len(tracks):
            if self.document().clip_slot(index=row, track=tracks[place]) is None:
                self.carried_once()
                dropped = self.document().move_clip_slot(index=self.row, track=self.track(), to_index=row, to_track=tracks[place])
                self.row = row
                self.column = place + FIRST_TRACK_COLUMN
                if dropped is not None:
                    self.say(messages.MSG_PASTED_WITHOUT_GRAB.format(track=dropped))
                    return
                break
            row += rows
            place += columns
        self.say_moving()

    def drop(self):
        self.moving = None

    def shift_scene(self, offset):
        """Move the cursor's scene one place up or down, the cursor going with it."""
        if self.document().move_scene(index=self.row, offset=offset):
            self.row += offset

    # Tracks.

    def new_track_name(self):
        """Return the name for a new track, numbered like a new scene, which its settings page renames."""
        tracks = self.tracks()
        return new_name(word=names_text.MSG_NEW_TRACK_WORD, taken=tracks)

    def add_track(self):
        """Add a track after the last one, and move onto it."""
        self.document().add_track(self.new_track_name())
        self.row = HEADER_ROW
        self.column = len(self.tracks()) - 1 + FIRST_TRACK_COLUMN

    def insert_track(self):
        """Put a blank track before the one the cursor is on, and stay on it."""
        self.document().insert_track(name=self.new_track_name(), place=self.track_place())

    def copy_track(self):
        """Ask whether a copy of the track shares its patterns or gets copies of them, then add the copy with its clips to its right, and move onto it."""
        name = self.track()
        column = self.column
        title = messages.MSG_COPY_TRACK_TITLE.format(name=name)
        self.ask_how_patterns_copy(title=title, then=functools.partial(self.copied_track, name=name, column=column))

    def copied_track(self, own, *, name, column):
        """Copy the track to its right, giving the copy's clips patterns of their own when own is true, and move onto it."""
        document = self.document()
        copy = document.copy_named(section=Section.TRACKS, name=name)
        if own:
            song = document.song()
            clip_slots = []
            for scene in song.get_scenes():
                if scene.has_clip_slot(copy):
                    clip_slots.append(scene.get_clip_slot(copy))
            document.give_own_patterns(clip_slots)
        self.column = column + 1

    def delete_track(self):
        if len(self.tracks()) <= 1:
            self.tell(errors.ERR_CANT_DELETE_TITLE, errors.ERR_LAST_TRACK_SHOWN)
            return
        name = self.track()
        document = self.document()
        message = [messages.MSG_DELETE_TRACK_QUESTION.format(name=name)]
        clips = document.song().track_clip_count(name)
        if clips and self.transport().is_playing():
            self.tell(errors.ERR_CANT_DELETE_TITLE, errors.ERR_TRACK_PLAYING_SHOWN)
            return
        if clips:
            message.append(messages.MSG_ALSO_DELETES_CLIPS.format(count=clips))
        grabbing = grabbers(song=document.song(), song_name=document.get_current_song_name(), track=name)
        if grabbing:
            message.append(messages.MSG_GRABBERS_STOP.format(count=len(grabbing)))
        self.confirm_delete(lines=message, then=functools.partial(document.delete_named, section=Section.TRACKS, name=name))

    def shift_track(self, offset):
        """Move the cursor's track one place left or right, the cursor going with it."""
        if self.document().move_named(section=Section.TRACKS, place=self.track_place(), offset=offset):
            self.column += offset

    # Clips.

    def add_clip(self):
        """Ask what the empty cell's clip plays: a new blank pattern, first, as B makes one, or an existing pattern."""
        setlist = self.document().get_setlist()
        patterns = sorted_names(setlist.get_pattern_names())
        row = self.row
        track = self.track()

        # A new pattern opens in the pattern editor; with an existing one the clip is added and Arrange stays, and Enter on the
        # clip again opens it.
        def chosen(place):
            if place == NEW_PATTERN_PLACE:
                self.blank_pattern()
                return
            self.document().add_clip_slot(index=row, track=track, pattern=patterns[place - 1])
        options = [messages.MSG_NEW_PATTERN_CHOICE, *patterns]
        self.ask(dialog=ChoiceDialog(title=messages.MSG_PATTERN_FOR_CLIP_TITLE, options=options), then=chosen)

    def blank_pattern(self):
        """Make a blank pattern named after the cursor's track, a drum pattern on a drum track, put a clip of it in the empty cell and open it."""
        track = self.track()
        document = self.document()
        name = document.new_name(section=Section.PATTERNS, word=track)
        # A pattern made on a clip goes in the group named after the clip's track.
        song = document.song()
        drum = song.get_track(track).is_drum()
        document.add_pattern(name=name, group=track, drum=drum)
        document.add_clip_slot(index=self.row, track=track, pattern=name)
        if not drum:
            # The pattern is written for a scale as large as the one its clip plays under.
            pattern = document.pattern(name)
            document.change_pattern(pattern.set_scale_length, document.scale_length_for_pattern(name))
        clip_slot = document.clip_slot(index=self.row, track=track)
        self.open_pattern(clip_slot)

    def open_pattern(self, clip_slot):
        """Open the pattern editor on the clip's pattern, with this page's crumbs before the pattern's, so that Esc comes back here."""
        self.open_editor(section=Section.PATTERNS, name=clip_slot.get_pattern_name(), opened_from=self, track=self.track())

    def copy_clip(self):
        clip_slot = self.document().clip_slot(index=self.row, track=self.track())
        self.copied = clip_slot.copy()
        self.say(messages.MSG_COPIED_CLIP)

    def paste_clip(self):
        dropped = self.document().paste_clip_slot(index=self.row, track=self.track(), copied=self.copied)
        if dropped is not None:
            self.say(messages.MSG_PASTED_WITHOUT_GRAB.format(track=dropped))

    def delete_clip(self):
        track = self.track()
        row = self.row
        question = messages.MSG_DELETE_CLIP_QUESTION.format(track=track)
        self.confirm_delete(lines=[question], then=functools.partial(self.remove_clip, row=row, track=track))

    def remove_clip(self, *, row, track):
        """Take a clip out of its scene, as one edit of the set."""
        song = self.document().song()
        scene = song.get_scene(row)
        self.document().change_set(scene.remove_clip_slot, track)
