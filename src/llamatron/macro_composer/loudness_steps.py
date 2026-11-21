# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""How big the step in loudness is from one section of a song to the next, and the trade that keeps the step in hand.

A section is lifted in several ways at once: more players, a fuller part, an open cymbal, harder strokes. Each is a fair
way to lift a chorus, and together they multiply, since a part with twice the notes at the same loudness a note is twice
as loud. A player trades: where a player's part grows much denser than the part the player last played, each of its notes
is played a little softer, so that what the player adds up to rises by a set share and no more. A player who comes in is
left alone, and so is whoever carries a melody, which has to stay on top.

What a player adds up to is the loudness of every note the player sounds, for each bar. The trade counts it from what is
written, without playing anything (counted): a clip's pattern says how many notes are written and how loud, and the
generators of the clip's chains that make more notes of a note, a Guitarify's strokes and strings and an arp's steps, say
how many each note becomes. The count is near, never exact, and near is enough to tell a part twice as dense. The same sums
taken from the song as played (measured) are for a report to hold the count against, never for making a song, which has to
stay quick. The drummer's timekeeping cymbals, the closed hat, the open hat and the ride, count as one player, since the
drummer moves from one to another. The trade is written as each clip's own velocity, the scene's velocity lowered.
"""

from llamatron.composition import defaults, file_format, velocity_ramps
from llamatron.composition.checks import time_length
from llamatron.composition.file_format import ChordSymbol, GeneratorKind, Row, Stroke, VelocitySetting
from llamatron.macro_composer import breaks
from llamatron.music.chord import Chord
from llamatron.music.held import Held
from llamatron.music.note import Note
from llamatron.playback.song_renderer import SongRenderer

# The drummer's cymbals that keep time, one player between them.
TIMEKEEPERS = (breaks.HAT, breaks.OPEN, breaks.RIDE)
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
# How many notes a written note becomes where nothing says: a chord with no table of its own has three notes.
USUAL_CHORD_NOTES = 3
# What a guitar sounds of a power chord: the root, the fifth and the root above.
POWER_CHORD_STRINGS = 3
# The strokes that sound nothing, and the ones that sound every string held; any other stroke sounds one string.
SILENT_STROKES = (Stroke.NOTHING,)
WHOLE_STROKES = (Stroke.DOWN, Stroke.UP, Stroke.MUTE, Stroke.STAB)
ONE_NOTE = 1
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


def chord_notes(symbol):
    """How many notes a step sounds as written: one, or its chord's."""
    if symbol is None:
        return ONE_NOTE
    return len(file_format.FIXED_CHORDS[symbol].value) + 1 if symbol in file_format.FIXED_CHORDS else USUAL_CHORD_NOTES


def strings_held(*, symbol, settings):
    """About how many strings a Guitarify holds down for a step: one for a single note, three for a power chord, and for any
    other chord every string the guitar is given."""
    if symbol is None:
        return ONE_NOTE
    return POWER_CHORD_STRINGS if symbol == ChordSymbol.POWER else settings.get_strings()


def lasting(*, steps, count):
    """How many steps each of a pattern's notes lasts: until the note after, the last until the pattern's end."""
    return [after - step for step, after in zip(steps, [*steps[1:], count])]


def strummed(*, symbols, lasts, settings, bar_length):
    """About how many notes a bar a Guitarify makes of a pattern's steps: its bar of strokes, each a whole stroke of the strings
    held, one string, or nothing, over the chords written, each chord for as long as the chord lasts."""
    held = sum(strings_held(symbol=symbol, settings=settings) * steps for symbol, steps in zip(symbols, lasts)) / sum(lasts)
    strokes = settings.get_bar()
    sounded = sum(0 if stroke in SILENT_STROKES else held if stroke in WHOLE_STROKES else ONE_NOTE for stroke in strokes)
    return sounded * float(bar_length / (time_length(settings.get_cell()) * len(strokes)))


def clip_count(*, song, slot, bar_length):
    """About how many notes a bar a clip sounds, and how loud a note of its pattern is written, from the pattern and the clip's
    chains alone: (notes a bar, loudness of a note), or None for a clip that sounds nothing."""
    pattern = song.get_pattern(slot.get_pattern_name())
    steps = pattern.get_note_steps()
    if not steps:
        return None
    symbols = [pattern.get_value(row=Row.CHORD, step=step) for step in steps]
    written = [pattern.get_value(row=Row.VELOCITY, step=step) for step in steps]
    loudness = sum(defaults.DEFAULT_VELOCITY if velocity is None else velocity for velocity in written) / len(written)
    bars = float(pattern.get_steps() * (pattern.get_step_size() or song.get_step_size()) / bar_length)
    notes = sum(chord_notes(symbol) for symbol in symbols) / bars
    for name in slot.get_chain_names():
        for step in song.chain_run(name).get_steps():
            if step.kind == GeneratorKind.GUITARIFY:
                notes = strummed(symbols=symbols, lasts=lasting(steps=steps, count=pattern.get_steps()), settings=song.get_generator_settings(kind=step.kind, name=step.name), bar_length=bar_length)
            elif step.kind == GeneratorKind.ARP:
                notes = float(bar_length / time_length(song.get_generator_settings(kind=step.kind, name=step.name).get_step()))
    return notes, loudness


def counted(*, song):
    """What each player adds up to in each scene of a song, counted from what is written: a list, one for a scene, of {player:
    (notes a bar, loudness a bar)}, leaving out a muted track and a player who sounds nothing. A clip that plays once through a
    longer scene counts for the share of the scene the clip lasts."""
    bar_length = song.get_time_signature().bar_length()
    scenes = []
    for scene in song.get_scenes():
        share = scene.get_velocity().typical() / WHOLE
        players = {}
        for track in scene.get_track_names():
            slot = scene.get_clip_slot(track)
            found = None if song.get_track(track).is_muted() else clip_count(song=song, slot=slot, bar_length=bar_length)
            if found is None:
                continue
            notes = found[NOTES] * (1 if slot.loops() else lasting_share(song=song, scene=scene, slot=slot))
            so_far = players.get(player_of(track), (0, 0))
            players[player_of(track)] = (so_far[NOTES] + notes, so_far[LOUDNESS] + notes * found[LOUDNESS] * share)
        scenes.append(players)
    return scenes


def pattern_length(*, song, slot):
    """How long a clip's pattern lasts played through as often as the clip repeats it, in whole notes."""
    pattern = song.get_pattern(slot.get_pattern_name())
    return pattern.get_steps() * (pattern.get_step_size() or song.get_step_size()) * (slot.get_repeat() or 1)


def lasting_share(*, song, scene, slot):
    """The share of a scene a clip that does not loop lasts: its length against the longest such clip of the scene."""
    longest = max(pattern_length(song=song, slot=scene.get_clip_slot(track)) for track in scene.get_track_names() if not scene.get_clip_slot(track).loops())
    return float(pattern_length(song=song, slot=slot) / longest)


def measured(*, song, seed=A_SEED):
    """What each player adds up to in each scene of a song, as played: the sums counted() gives, taken from every note sounded.
    Playing takes several times as long as writing the song, so this is for a report and a test to hold the count against."""
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
    """Write a song's trades into the song: each clip of a player who trades gets a velocity of its own, its scene's lowered, and each end its scene's ramps give lowered the same."""
    for scene, shares in zip(song.get_scenes(), trades(scenes=counted(song=song), kept=kept)):
        of_scene = scene.get_velocity_settings()
        for track in scene.get_track_names():
            share = shares.get(player_of(track))
            if share is None:
                continue
            slot = scene.get_clip_slot(track)
            for name in file_format.VELOCITY_SETTINGS:
                percent = velocity_ramps.AS_WRITTEN if name == VelocitySetting.LEVEL and of_scene[name] is None else of_scene[name]
                if name not in velocity_ramps.BAR_COUNTS and percent is not None:
                    slot.set_written(name=name, value=round(percent * share))


def whole_band(players):
    """What a scene's players add up to together, for each bar."""
    return sum(sums[LOUDNESS] for sums in players.values())


def step(*, before, now):
    """How many times what the band adds up to in one scene the band adds up to in the next, or None after silence."""
    return whole_band(now) / whole_band(before) if whole_band(before) else None
