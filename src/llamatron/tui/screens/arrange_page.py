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
"""The Arrange page: the current song's scenes as rows, its tracks as columns, and a clip where they meet.

Everything about a song's structure happens here, as in Live's Session View, as the user decided
on 2026-11-07: the track names across the top can be moved onto, so tracks are added, copied,
inserted, moved and deleted on this page, like scenes, and Enter on a track, a scene or a clip
opens its own page. C copies everywhere, as the user asked: a scene or track is copied in place,
and a clip is copied to be pasted with V.

The grid was redrawn on 2026-11-08 as the user sketched it: the track names and the scene column
stay in place while the clips scroll, the corner is blank since the crumbs say where you are, a
double-lined frame marks the clip, scene or track under the cursor in place of reverse video, an
empty clip slot shows + and add only under the cursor, and a bar under each scene shows its length
against the longest scene's and one under each clip its length against its scene's.

This page keeps the cursor, how far the grid has scrolled, the keys and what each key does to
the song. ArrangeDrawing (arrange_drawing.py) draws the grid from them.
"""

import time

from llamatron.composition.file_format import ClipSlotSetting, Section
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.composition.naming import unique_name
from llamatron.tui.text import sorted_names
from llamatron.strings.help import HELP_ARRANGE_PAGE
from llamatron.tui.keys import Key
from llamatron.tui.components.stage_drawing import frame_box, inside_of, visualizer_area
from llamatron.tui.screens.arrange_details import ADD_CHAIN, SCENE_CELL, TRACK_CELL, clip_cell, scene_cell, track_cell
from llamatron.tui.screens.arrange_drawing import ArrangeDrawing
from llamatron.tui.components.inset_window import drawn_over, inside_size
from llamatron.tui.components.scene_view import SceneView
from llamatron.tui.screens.chain_editor import ChainEditor
from llamatron.tui.screens.clip_page import ClipPage
from llamatron.tui.screens.generator_pages import generator_page_of_kind
from llamatron.tui.screens.groove_editor import GrooveEditor
from llamatron.tui.screens.instrument_editor import InstrumentEditor
from llamatron.tui.screens.scale_page import ScalePage
from llamatron.tui.key_table import cursor_moved
from llamatron.tui.screens.page import Page
from llamatron.tui.screens.pattern_editor import PatternEditor
from llamatron.tui.screens.scene_page import ScenePage
from llamatron.tui.screens.shared import play_through, scene_name
from llamatron.tui.screens.track_editor import TrackEditor
from llamatron.tui.uses import grabbers
from llamatron.strings.errors import ERR_NO_CHAINS_TO_ADD
from llamatron.strings.errors import (
    ERR_ADD_A_PATTERN_FIRST, ERR_CANT_DELETE_TITLE, ERR_LAST_SCENE_SHOWN, ERR_LAST_TRACK_SHOWN, ERR_NO_PATTERNS_TITLE, ERR_SCENE_PLAYING_SHOWN, ERR_TRACK_PLAYING_SHOWN,
)
from llamatron.strings.labels import Crumb
from llamatron.strings.names import MSG_TRACK_PATTERN_NAME
from llamatron.strings.messages import MSG_ADD_CHAIN_TITLE, MSG_MOVING, MSG_MOVING_CLIP, MSG_MOVING_SCENE, MSG_MOVING_TRACK
from llamatron.strings.messages import (
    MSG_ALSO_DELETES_CLIPS, MSG_COPIED_CLIP, MSG_DELETE_CLIP_QUESTION, MSG_DELETE_SCENE_QUESTION, MSG_DELETE_TITLE,
    MSG_CLIP_ON_TRACK, MSG_DELETE_TRACK_QUESTION, MSG_GRABBERS_STOP, MSG_PASTED_WITHOUT_GRAB, MSG_PATTERN_FOR_CLIP_TITLE, MSG_PLAYING_CLIP, MSG_PLAYING_FROM,
    MSG_EVERY_VISUALIZER_HIDDEN, MSG_SCENE_NUMBER, MSG_STOPPED, MSG_STOPPED_TRACK,
)
from llamatron.strings.marks import MSG_PLAYING_CLOCK, MSG_SCENE_VIEW_CLOSING, MSG_SCENE_VIEW_TITLE
from llamatron.tui.text import clock
from llamatron.strings.names import MSG_CHAIN_WORD, MSG_GROOVE_WORD, MSG_INSTRUMENT_WORD, MSG_NEW_SCENE_NAME, MSG_NEW_TRACK_NAME, MSG_SCALE_WORD
from llamatron.tui import keybindings
from llamatron.visualizers.modes import MODES, mode_called
from llamatron.tui.drawing import NOTHING


# How often the visualizer draws a frame while it shows, in seconds, and how long a mode's name shows when it changes, the user's choice of 2026-11-10.
FRAME_SECONDS = 0.05
NAME_SECONDS = 8.0
# The row of track names above the first scene, which the cursor can move onto.
HEADER_ROW = -1
# The scene names are column 0, and the tracks count from 1.
SCENE_COLUMN = 0
FIRST_SCENE_NUMBER = 1
FIRST_TRACK_COLUMN = 1
# The number a blank pattern named after its track starts from, as lead 1.
FIRST_PATTERN_NUMBER = 1
# What Move mode can carry, the user's design.
MOVING_SCENE = 'scene'
MOVING_TRACK = 'track'
MOVING_CLIP = 'clip'
# How far each arrow carries a clip: scenes down, then tracks right.
CLIP_STEPS = {Key.UP: (-1, 0), Key.DOWN: (1, 0), Key.LEFT: (0, -1), Key.RIGHT: (0, 1)}
# The pages a line of details opens, by the section it names, with the word for the thing in the crumbs; a generator's is found by its kind.
DETAIL_PAGES = {
    Section.CHAINS: (ChainEditor, MSG_CHAIN_WORD), Section.SCALES: (ScalePage, MSG_SCALE_WORD),
    Section.INSTRUMENTS: (InstrumentEditor, MSG_INSTRUMENT_WORD), Section.GROOVES: (GrooveEditor, MSG_GROOVE_WORD),
}


class ArrangePage(Page):

    KEYS = keybindings.ArrangePage
    crumbs = (Crumb.ARRANGE,)
    HELP = HELP_ARRANGE_PAGE

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
        # A batch video's stage (tui/batch_stage.py), which draws the whole screen while it runs, or None.
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
        # Scene View, an Inset Window over the page (tui/components/scene_view.py), or None.
        self.inset = None
        # Move mode, the user's design: what M picked up, MOVING_SCENE, MOVING_TRACK or MOVING_CLIP, or None, and whether it has been
        # carried yet, so that one move is one undo step.
        self.moving = None
        self.carried = False
        # What draws the grid from the cursor and the scroll kept here.
        self.drawing = ArrangeDrawing(self)

    def duration(self):
        return self.document().lengths().song_seconds()

    def time_text(self):
        """Return the time at the right of the crumbs: where the song is while it plays, and how long it is, or its length alone."""
        position = self.transport().song_position()
        if position is None:
            return super().time_text()
        return MSG_PLAYING_CLOCK.format(at=clock(position), total=clock(self.transport().song_seconds()))

    def transport(self):
        return self.app.transport

    def real_time_on(self):
        """Return whether the set's Real Time switch is on, which is when the page has its play buttons and the corner."""
        return self.document().setlist().is_real_time()

    def scenes(self):
        return self.document().song().get_scenes()

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

    def clamp(self):
        self.row = max(min(self.row, len(self.scenes())), HEADER_ROW)
        if self.on_plus_row():
            self.column = SCENE_COLUMN
        elif self.on_header():
            self.column = max(min(self.column, len(self.tracks()) + FIRST_TRACK_COLUMN), SCENE_COLUMN if self.real_time_on() else FIRST_TRACK_COLUMN)
        else:
            self.column = max(min(self.column, len(self.tracks())), SCENE_COLUMN)

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
                keys.append(self.bind(self.KEYS.PICK_DETAIL, action=self.pick, wants_key=True))
                target = self.picked_target()
                if target is not None and target.kind == ADD_CHAIN:
                    keys.append(self.bind(self.KEYS.ADD_CHAIN, action=self.add_chain_to_cell))
                else:
                    keys.append(self.bind(self.KEYS.OPEN_DETAIL, action=self.open_picked))
                if target is not None and target.kind == Section.CHAINS:
                    keys.append(self.bind(self.KEYS.REMOVE_CHAIN, action=self.remove_chain_from_cell))
            return keys + [self.bind(self.KEYS.CLOSE_DETAILS, action=self.close_details)]
        result = [self.bind(self.KEYS.BACK, action=self.go_back), self.bind(self.KEYS.MOVE, action=self.move, wants_key=True)]
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
        return result

    # The details view, the user's design: D shows under every bar the chains, the generators and the settings that aren't their
    # defaults, and D again hides them. Every key works in it as in the usual view, and the choice is kept for the session.

    def shows_details(self):
        """Return whether the grid shows its details view: chosen with R, and never under the visualizer or a batch video's stage."""
        return self.app.shows_arrange_details and self.visualizer is None and self.stage is None

    def toggle_details(self):
        """Show the details view, or the usual one again."""
        self.app.shows_arrange_details = not self.app.shows_arrange_details
        self.stop_picking()
        self.top = 0
        self.left = 0

    # Scene View, an Inset Window over the page, the user's design: P opens it on a scene's name, and P or Esc closes it.

    def open_scene_view(self):
        self.inset = SceneView(document=self.document(), index=self.row)

    def close_inset(self):
        self.inset = None

    def inset_keys(self):
        """Return the keys while Scene View shows: P closes it, the arrows move its cursor, PgUp and PgDn jump a bar, V switches its view, - and = zoom, [ and ] scroll its sidebar, and Esc closes it too, as Esc closes the topmost thing everywhere."""
        switch = self.KEYS.TO_PLAYED if self.inset.is_written() else self.KEYS.TO_WRITTEN
        return [
            self.bind(self.KEYS.ESCAPE_INSET, action=self.close_inset),
            self.bind(self.KEYS.CLOSE_INSET, action=self.close_inset),
            self.bind(self.KEYS.INSET_MOVE, action=self.inset.move, wants_key=True),
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
        if self.document().clip_slot(index=self.row, track=self.track()) is None:
            return None
        return clip_cell(index=self.row, track=self.track())

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
        self.picked = None if count == 0 else min(self.picked or 0, count - 1)
        return True

    def picked_line(self):
        """Return the place among the cursor's cell's lines of details of the one picked, which the drawing puts in brackets, or None."""
        return self.pickable()[self.picked] if self.picking() and self.picked is not None else None

    def start_picking(self):
        """Open the cursor's cell's details, if the details view isn't showing them, and lock into the cell, on its first line naming something if it has one."""
        self.locked = True
        self.picked = 0 if self.pickable() else None
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

    def pick(self, name):
        self.picked = cursor_moved(place=self.picked, name=name, count=len(self.pickable()))

    def picked_target(self):
        """Return what the picked line names, or None."""
        place = self.picked_line()
        return None if place is None else self.drawing.details_at_cursor()[place].target

    def cell_chain_names(self):
        """Return the chains the cursor's cell runs, a clip's, a scene's or a track's, in order."""
        cell = self.cursor_cell()
        song = self.document().song()
        if cell[0] == TRACK_CELL:
            return list(song.get_track(cell[1]).get_chain_names())
        if cell[0] == SCENE_CELL:
            return list(song.get_scenes()[cell[1]].get_chain_names())
        return list(self.document().clip_slot(index=cell[1], track=cell[2]).get_chain_names())

    def set_cell_chain_names(self, names):
        """Set the chains the cursor's cell runs, through the setter of a clip, a scene or a track."""
        cell = self.cursor_cell()
        if cell[0] == TRACK_CELL:
            self.document().set_track_chains(name=cell[1], names=names)
        elif cell[0] == SCENE_CELL:
            self.document().set_scene_chains(index=cell[1], names=names)
        else:
            self.document().set_clip_slot_setting(index=cell[1], track=cell[2], setting=ClipSlotSetting.CHAINS, value=names)

    def add_chain_to_cell(self):
        """Ask for one of the set's chains and add it to the cursor's cell alone, after the chains it runs, the user's design."""
        chains = sorted_names(self.document().song().get_chain_names())
        if not chains:
            self.refuse(ERR_NO_CHAINS_TO_ADD)
            return
        names = self.cell_chain_names()

        def chosen(place):
            self.set_cell_chain_names([*names, chains[place]])
        self.ask(dialog=ChoiceDialog(title=MSG_ADD_CHAIN_TITLE, options=chains), then=chosen)

    def remove_chain_from_cell(self):
        """Take the picked chain out of the cursor's cell alone, the chain staying in the set, the user's design."""
        names = self.cell_chain_names()
        del names[self.picked_target().place]
        self.set_cell_chain_names(names)

    def open_picked(self):
        """Open the page of what the picked line names, a chain's, a generator's, a scale's, an instrument's or a groove's, its crumbs after Arrange's."""
        target = self.drawing.details_at_cursor()[self.picked_line()].target
        if target.kind in DETAIL_PAGES:
            page, word = DETAIL_PAGES[target.kind]
        else:
            listing = generator_page_of_kind(target.kind)
            page, word = listing.EDITOR, listing.label
        self.show_page(page(holder=self.holder, name=target.name).opened_from(page=self, word=word))

    # The visualizer over the clip area, with Real Time on (visualizers/).

    def shown_modes(self):
        """Return the visualizer modes the key steps through, every mode but those the set hides, in order."""
        hidden = self.document().setlist().get_hidden_visualizers()
        return [mode for mode in MODES if mode.OPTION not in hidden]

    def first_mode(self):
        """Return the mode the visualizer key shows first: the song's choice, else the set's, when it isn't hidden, and otherwise the first shown."""
        shown = self.shown_modes()
        setlist = self.document().setlist()
        chosen = mode_called(setlist.visualizer_for(self.document().song()) or NOTHING)
        return chosen if chosen in shown else shown[0]

    def next_visualizer(self):
        """Show the first mode, or the next one shown, or the clips again after the last."""
        shown = self.shown_modes()
        if not shown:
            self.say(MSG_EVERY_VISUALIZER_HIDDEN)
            return
        if self.visualizer is None:
            self.show_visualizer(self.first_mode())
            return
        place = shown.index(type(self.visualizer)) + 1 if type(self.visualizer) in shown else len(shown)
        if place < len(shown):
            self.show_visualizer(shown[place])
        else:
            self.hide_visualizer()

    def step_visualizer(self, direction):
        """Show the mode before or after the one showing among those shown, going round, as [ and ] step through a cycle of choices."""
        shown = self.shown_modes()
        if not shown:
            return
        place = shown.index(type(self.visualizer)) if type(self.visualizer) in shown else 0
        self.show_visualizer(shown[(place + direction) % len(shown)])

    def show_visualizer(self, mode):
        """Show a visualizer mode over the clip area, drawing a frame every FRAME_SECONDS while it shows."""
        self.visualizer = mode.made_for(hidden=self.document().setlist().get_hidden_visualizers())
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
            self.bind(self.KEYS.TRACK_SETTINGS, action=lambda: self.show_page(TrackEditor(holder=self.holder, name=self.track()))),
            self.bind(self.KEYS.COPY_TRACK, action=self.copy_track),
            self.bind(self.KEYS.INSERT_TRACK, action=self.insert_track),
            self.bind(self.KEYS.MOVE_TRACK, action=lambda: self.start_moving(MOVING_TRACK)),
            self.bind(self.KEYS.DELETE_TRACK, action=self.delete_track),
        ]

    def scene_row_keys(self):
        """Return the keys on a scene's row: its name's, or its clip slot's, then the ones the whole row shares."""
        result = [self.bind(self.KEYS.ADD_SCENE, action=self.add_scene)]
        if self.on_scene_name():
            result += self.play_scene_keys()
            result += [
                self.bind(self.KEYS.SCENE_SETTINGS, action=lambda: self.show_page(ScenePage(holder=self.holder, index=self.row))),
                self.bind(self.KEYS.SCENE_VIEW, action=self.open_scene_view),
                self.bind(self.KEYS.MOVE_SCENE, action=lambda: self.start_moving(MOVING_SCENE)),
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
                    self.bind(self.KEYS.EDIT_CLIP, action=lambda: self.show_page(ClipPage(holder=self.holder, index=self.row, track=self.track()))),
                    self.bind(self.KEYS.OPEN_PATTERN, action=lambda: self.open_pattern(clip_slot)),
                    self.bind(self.KEYS.MOVE_CLIP, action=lambda: self.start_moving(MOVING_CLIP)),
                    self.bind(self.KEYS.COPY_CLIP, action=self.copy_clip),
                    self.bind(self.KEYS.DELETE_CLIP, action=self.delete_clip),
                ]
            if self.copied is not None:
                result.append(self.bind(self.KEYS.PASTE_CLIP, action=self.paste_clip))
        result.append(self.bind(self.KEYS.INSERT_SCENE, action=self.insert_scene))
        return result

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
        scene = MSG_SCENE_NUMBER.format(number=FIRST_SCENE_NUMBER)
        play_through(page=self, play=self.transport().play_song, what=scene, said=MSG_PLAYING_FROM.format(scene=scene))

    def play_scene(self):
        index = self.row
        scene = MSG_SCENE_NUMBER.format(number=index + FIRST_SCENE_NUMBER)
        play_through(page=self, play=lambda: self.transport().play_scene(index=index), what=scene, said=MSG_PLAYING_FROM.format(scene=scene))

    def play_clip(self):
        index = self.row
        track = self.track()
        clip = MSG_CLIP_ON_TRACK.format(name=self.document().clip_slot(index=index, track=track).get_display_name(), track=track)
        play_through(page=self, play=lambda: self.transport().play_clip(index=index, track=track), what=clip, said=MSG_PLAYING_CLIP.format(clip=clip))

    def stop_playing_all(self):
        self.transport().stop_all()
        self.say(MSG_STOPPED)

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
        self.say(MSG_STOPPED_TRACK.format(track=self.track()))

    def move(self, name):
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
        return self.drawing.body(width=width, height=height)

    def with_inset(self, *, screen, width, height):
        """Return the screen with Scene View's Inset Window laid over it."""
        inner_width, inner_height = inside_size(width=width, height=height)
        title = MSG_SCENE_VIEW_TITLE.format(scene=scene_name(scene=self.scenes()[self.inset.index()], index=self.inset.index()))
        closing = MSG_SCENE_VIEW_CLOSING.format(key=self.KEYS.CLOSE_INSET[1], what=self.KEYS.CLOSE_INSET[2])
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
        playing = self.transport().playing_scenes()
        return self.stage.screen(arrange=screen, width=width, height=height, now=now, frame=frame, clips=clips, seconds_per_beat=heard.seconds_per_beat,
                                 scene=max(playing) if playing else None)

    def name_to_show(self, now):
        """Return the visualizer's name to show at a moment, for NAME_SECONDS after it changes, by a key or by a mode of modes moving on, or None."""
        name = self.visualizer.shown_name()
        if name != self._name_shown:
            self._name_shown = name
            self._name_since = now
        return name if now - self._name_since < NAME_SECONDS else None

    # Scenes.

    def new_scene_name(self):
        names = {scene.get_name() for scene in self.scenes()}
        return unique_name(base=MSG_NEW_SCENE_NAME.format(number=len(self.scenes()) + 1), taken=names)

    def add_scene(self):
        index = len(self.scenes()) if self.on_plus_row() else self.row + 1
        self.document().add_scene(index=index, name=self.new_scene_name())
        self.row = index
        self.column = SCENE_COLUMN

    def insert_scene(self):
        """Put a blank scene before the one the cursor is on, and stay on it."""
        self.document().add_scene(index=self.row, name=self.new_scene_name())

    def copy_scene(self):
        """Add a copy of the scene with its clips right below it, and move onto it."""
        self.document().copy_scene(self.row)
        self.row += 1

    def delete_scene(self):
        if len(self.scenes()) <= 1:
            self.tell(ERR_CANT_DELETE_TITLE, ERR_LAST_SCENE_SHOWN)
            return
        scene = self.scenes()[self.row]
        count = len(scene.get_track_names())
        if count and self.transport().is_playing():
            self.tell(ERR_CANT_DELETE_TITLE, ERR_SCENE_PLAYING_SHOWN)
            return
        message = [MSG_DELETE_SCENE_QUESTION.format(name=scene_name(scene=scene, index=self.row))]
        if count:
            message.append(MSG_ALSO_DELETES_CLIPS.format(count=count))
        self.ask(dialog=ConfirmDialog(title=MSG_DELETE_TITLE, messages=message), then=lambda _: self.document().delete_scene(self.row))

    # Move mode, the user's design: M on a scene's name, a track's name or a clip picks it up, the arrows carry it, a clip only into an
    # empty cell (the user's rule), and Enter, Esc or M drops it where it is. The box around it is green while it's carried.

    def start_moving(self, what):
        self.moving = what
        self.carried = False
        self.say_moving()

    def say_moving(self):
        if self.moving == MOVING_SCENE:
            what = MSG_MOVING_SCENE.format(name=scene_name(scene=self.scenes()[self.row], index=self.row))
        elif self.moving == MOVING_TRACK:
            what = MSG_MOVING_TRACK.format(name=self.track())
        else:
            what = MSG_MOVING_CLIP.format(name=self.document().clip_slot(index=self.row, track=self.track()).get_display_name())
        self.say(MSG_MOVING.format(what=what))

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
                    self.say(MSG_PASTED_WITHOUT_GRAB.format(track=dropped))
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
        return unique_name(base=MSG_NEW_TRACK_NAME.format(number=len(tracks) + 1), taken=tracks)

    def add_track(self):
        """Add a track after the last one, and move onto it."""
        self.document().add_track(self.new_track_name())
        self.row = HEADER_ROW
        self.column = len(self.tracks()) - 1 + FIRST_TRACK_COLUMN

    def insert_track(self):
        """Put a blank track before the one the cursor is on, and stay on it."""
        self.document().insert_track(name=self.new_track_name(), place=self.track_place())

    def copy_track(self):
        """Add a copy of the track with its clips to its right, and move onto it."""
        self.document().copy_named(section=Section.TRACKS, name=self.track())
        self.column += 1

    def delete_track(self):
        if len(self.tracks()) <= 1:
            self.tell(ERR_CANT_DELETE_TITLE, ERR_LAST_TRACK_SHOWN)
            return
        name = self.track()
        document = self.document()
        message = [MSG_DELETE_TRACK_QUESTION.format(name=name)]
        clips = document.song().track_clip_count(name)
        if clips and self.transport().is_playing():
            self.tell(ERR_CANT_DELETE_TITLE, ERR_TRACK_PLAYING_SHOWN)
            return
        if clips:
            message.append(MSG_ALSO_DELETES_CLIPS.format(count=clips))
        grabbing = grabbers(song=document.song(), song_name=document.current_song_name(), track=name)
        if grabbing:
            message.append(MSG_GRABBERS_STOP.format(count=len(grabbing)))
        self.ask(dialog=ConfirmDialog(title=MSG_DELETE_TITLE, messages=message), then=lambda _: document.delete_named(section=Section.TRACKS, name=name))

    def shift_track(self, offset):
        """Move the cursor's track one place left or right, the cursor going with it."""
        if self.document().move_named(section=Section.TRACKS, place=self.track_place(), offset=offset):
            self.column += offset

    # Clips.

    def add_clip(self):
        patterns = sorted_names(self.document().song().get_pattern_names())
        if not patterns:
            self.tell(ERR_NO_PATTERNS_TITLE, ERR_ADD_A_PATTERN_FIRST)
            return
        row = self.row
        track = self.track()

        # The clip is added and Arrange stays, the user's rule: Enter on the clip again opens it.
        def chosen(place):
            self.document().add_clip_slot(index=row, track=track, pattern=patterns[place])
        self.ask(dialog=ChoiceDialog(title=MSG_PATTERN_FOR_CLIP_TITLE, options=patterns), then=chosen)

    def blank_pattern(self):
        """Make a blank pattern named after the cursor's track, a drum pattern on a drum track, put a clip of it in the empty cell and open it, the user's design."""
        track = self.track()
        taken = self.document().song().get_pattern_names()
        number = FIRST_PATTERN_NUMBER
        while MSG_TRACK_PATTERN_NAME.format(track=track, number=number) in taken:
            number += 1
        name = MSG_TRACK_PATTERN_NAME.format(track=track, number=number)
        self.document().add_pattern(name=name)
        if self.document().song().get_track(track).is_drum():
            self.document().set_drum(name=name, drum=True)
        self.document().add_clip_slot(index=self.row, track=track, pattern=name)
        self.open_pattern(self.document().clip_slot(index=self.row, track=track))

    def open_pattern(self, clip_slot):
        """Open the pattern editor on the clip's pattern, with this page's crumbs before the pattern's, so that Esc comes back here."""
        self.show_page(PatternEditor(holder=self.holder, name=clip_slot.get_pattern_name(), opened_from=self))

    def copy_clip(self):
        self.copied = self.document().clip_slot(index=self.row, track=self.track()).copy()
        self.say(MSG_COPIED_CLIP)

    def paste_clip(self):
        dropped = self.document().paste_clip_slot(index=self.row, track=self.track(), copied=self.copied)
        if dropped is not None:
            self.say(MSG_PASTED_WITHOUT_GRAB.format(track=dropped))

    def delete_clip(self):
        track = self.track()
        row = self.row
        self.ask(dialog=ConfirmDialog(title=MSG_DELETE_TITLE, messages=[MSG_DELETE_CLIP_QUESTION.format(track=track)]), then=lambda _: self.document().delete_clip_slot(index=row, track=track))
