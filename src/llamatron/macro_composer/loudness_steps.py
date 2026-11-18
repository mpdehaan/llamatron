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

"""How big the step in loudness is from one section of a song to the next, and the trade that keeps the step in hand.

A section is lifted in several ways at once: more players, a fuller part, an open cymbal, harder strokes. Each is a fair
way to lift a chorus, and together they multiply, since a part with twice the notes at the same loudness a note is twice
as loud. A player trades: where a player's part grows much denser than the part the player last played, each of its notes
is played a little softer, so that what the player adds up to rises by a set share and no more. A player who comes in is
left alone, and so is whoever carries a melody, which has to stay on top.

What a player adds up to is measured from the song as played: the loudness of every note the player sounds, for each bar.
The drummer's timekeeping cymbals, the closed hat, the open hat and the ride, count as one player, since the drummer moves
from one to another. The trade is written as each clip's own swell, the scene's swell lowered.
"""

from llamatron.composition.file_format import Shape, ShapePart
from llamatron.composition.shapes import UNCHANGED, shape_setting
from llamatron.macro_composer.breaks import HAT, OPEN, RIDE
from llamatron.music.chord import Chord
from llamatron.music.held import Held
from llamatron.music.note import Note
from llamatron.playback.song_renderer import SongRenderer

# The drummer's cymbals that keep time, one player between them.
TIMEKEEPERS = (HAT, OPEN, RIDE)
TIMEKEEPER = 'timekeeping cymbals'
# A part of fewer notes a bar than this is an event now and then, a fill or a crash, and no part to trade.
FEWEST_NOTES_A_BAR = 1
# A part is much denser from this many times the notes a bar, and what the player adds up to may then rise this many times.
MUCH_DENSER = 1.25
LARGEST_STEP = 1.25
# A part is as dense as the part before from this share of the notes a bar.
AS_DENSE = 0.9
# The least a traded note keeps of its loudness, so that a part played after a very thin one is still heard.
LEAST_KEPT = 0.7
WHOLE = 100
A_SEED = 0
NOTES = 0
LOUDNESS = 1
KEPT = 2


def player_of(track):
    """The player a track counts under: the timekeeping cymbals together, any other track itself."""
    return TIMEKEEPER if track in TIMEKEEPERS else track


def velocities(position):
    """How loud each note a position sounds is."""
    if isinstance(position, Note):
        return [position.get_velocity()]
    if isinstance(position, Chord):
        return [note.get_velocity() for note in position.get_notes()]
    if isinstance(position, Held):
        return velocities(position.get_sound())
    return []


def clip_sums(clip):
    """A clip's notes as played through its scene, and their loudness added up."""
    notes = 0
    loudness = 0
    for position in clip.played_notes():
        sounded = velocities(position)
        notes += len(sounded)
        loudness += sum(sounded)
    return notes, loudness


def measured(*, song, seed=A_SEED):
    """What each player adds up to in each scene of a song, as played: a list, one for a scene, of {player: (notes a bar,
    loudness a bar)}, leaving out a muted track and a player who sounds nothing."""
    grid = SongRenderer(song, seed=seed).render()
    bar_length = grid.get_time_signature().bar_length()
    scenes = []
    for row in grid.get_rows():
        players = {}
        bars = float(grid.row_length(row) / bar_length)
        for column in grid.get_columns():
            clip = grid.get_clip(row=row, column=column)
            if clip is None or song.get_track(column.get_name()).is_muted():
                continue
            notes, loudness = clip_sums(clip)
            if notes and bars:
                so_far = players.get(player_of(column.get_name()), (0, 0))
                players[player_of(column.get_name())] = (so_far[NOTES] + notes / bars, so_far[LOUDNESS] + loudness / bars)
        scenes.append(players)
    return scenes


def trade_of(*, before, now):
    """The share of its loudness a player's notes keep, the player's part now against the part the player last played: a
    much denser part trades, a part about as dense keeps the trade of the part before, and a thinner part is played whole."""
    if now[NOTES] > before[NOTES] * MUCH_DENSER:
        return min(1, max(LEAST_KEPT, LARGEST_STEP * before[LOUDNESS] / now[LOUDNESS]))
    if now[NOTES] >= before[NOTES] * AS_DENSE:
        return before[KEPT]
    return 1


def trades(*, scenes, kept=()):
    """The trade of each player in each scene: a list, one for a scene, of {player: share kept}, holding only the players who
    trade. Each part is held against the part the player last played, as traded; the players kept never trade."""
    last = {}
    traded = []
    for players in scenes:
        shares = {}
        for player, sums in players.items():
            if sums[NOTES] < FEWEST_NOTES_A_BAR:
                continue
            share = trade_of(before=last[player], now=sums) if player in last and player not in kept else 1
            if share < 1:
                shares[player] = share
            last[player] = (sums[NOTES], sums[LOUDNESS] * share, share)
        traded.append(shares)
    return traded


def with_trades(*, song, kept=()):
    """Write a song's trades into the song: each clip of a player who trades gets a swell of its own, its scene's lowered."""
    for scene, shares in zip(song.get_scenes(), trades(scenes=measured(song=song), kept=kept)):
        of_scene = scene.get_shape(Shape.SWELL)
        for track in scene.get_track_names():
            share = shares.get(player_of(track))
            if share is None:
                continue
            slot = scene.get_clip_slot(track)
            for part, percent in ((ShapePart.START, of_scene.start if of_scene else UNCHANGED), (ShapePart.END, of_scene.end if of_scene else UNCHANGED)):
                slot.set_shape_setting(name=shape_setting(shape=Shape.SWELL, part=part), value=round(percent * share))


def whole_band(players):
    """What a scene's players add up to together, for each bar."""
    return sum(sums[LOUDNESS] for sums in players.values())


def step(*, before, now):
    """How many times what the band adds up to in one scene the band adds up to in the next, or None after silence."""
    return whole_band(now) / whole_band(before) if whole_band(before) else None
