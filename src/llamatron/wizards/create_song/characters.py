# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A player's character: gauges, each from 0 to 20, that say how the player of an instrument plays.

A style template says how an instrument is played at four levels of complexity. A character names a place along each gauge, and
the player is put together from the levels: each field of a level belongs to one gauge, and the gauge's place says which level's
value of the field the player takes. A field that is a number, or timings in numbers, is blended between the levels, so that
every place of its gauge differs. A level on its own is a preset: every gauge at that level's place, which gives the level as
the template writes it."""

from llamatron.wizards.create_song import melody

# The fields of a level, as a style template writes them.
SAYS = 'says'
TIMING = 'timing'
UNEVEN = 'uneven'
ADDS = 'adds'
VARIES = 'varies'
FILL = 'fill'
FILL_EVERY = 'fill_every'
BUSY = 'busy'
GUITARIFY_OF_PLAYER = 'guitarify'
# The gauges.
NOTES = 'notes'
VARIETY = 'variety'
TOUCH = 'touch'
LOOSE = 'timing'
FILLS = 'fills'
STRUMMING = 'strumming'
RANGE = 'range'
GAUGES = (NOTES, VARIETY, TOUCH, LOOSE, FILLS, STRUMMING, RANGE)
# The gauge each field of a level belongs to; what a level says of itself goes with no gauge, and is the preset's alone.
GAUGE_OF_FIELD = {ADDS: NOTES, BUSY: NOTES, VARIES: VARIETY, UNEVEN: TOUCH, TIMING: LOOSE, FILL: FILLS, FILL_EVERY: FILLS, GUITARIFY_OF_PLAYER: STRUMMING, melody.SPAN: RANGE}
# The fields blended between the levels; how often a fill comes is a number too, of bars, and is taken whole from its level.
BLENDED = (UNEVEN, TIMING, melody.SPAN)
LOWEST = 0
HIGHEST = 20
# The levels, each a band of a gauge's places, and the place a level's preset stands at, in the middle of its band.
LEVELS = (1, 2, 3, 4)
PLACES_IN_BAND = 5
PRESET_PLACE = {1: 2, 2: 7, 3: 12, 4: 17}
# What two gauges' places are joined by where a character that is no preset must be named.
CUSTOM_LABEL = 'custom {}'


def level_at(place):
    """The level whose band a gauge's place is in."""
    return min(LEVELS[-1], place // PLACES_IN_BAND + 1)


def preset(level):
    """The character that is a level: every gauge at the level's place."""
    return {gauge: PRESET_PLACE[level] for gauge in GAUGES}


def character_of(given):
    """A character from what a song gives for an instrument: a level, or the places of some gauges, the rest standing where the plainest level's do."""
    if isinstance(given, dict):
        return {**preset(LEVELS[0]), **given}
    return preset(given)


def level_of(character):
    """The level a character is the preset of, or None for a character that is no preset."""
    for level in LEVELS:
        if character == preset(level):
            return level
    return None


def label_of(character):
    """What a character is told from another by, in a part's name: its level, or its gauges' places."""
    level = level_of(character)
    return level if level is not None else CUSTOM_LABEL.format('-'.join(str(character[gauge]) for gauge in GAUGES))


def held_to(*, character, allowed):
    """A character in a section that allows the instrument only so high a level: each gauge above the level's band stands at the level's place."""
    if allowed is None:
        return character
    return {gauge: PRESET_PLACE[allowed] if level_at(place) > allowed else place for gauge, place in character.items()}


def gauges_of(levels):
    """The gauges an instrument has in a style: those a field of any of its levels belongs to, in the gauges' order."""
    fields = {field for level in levels.values() for field in level}
    used = {GAUGE_OF_FIELD.get(field) for field in fields}
    return [gauge for gauge in GAUGES if gauge in used]


def blended(*, low, high, share):
    """A value between two levels' values, a share of the way from the lower: numbers are blended, and timings, which hold numbers by name, name by name; a missing number is zero, and none falls below zero."""
    if isinstance(low, dict) or isinstance(high, dict):
        low = low or {}
        high = high or {}
        names = dict.fromkeys([*low, *high])
        made = {name: blended(low=low.get(name), high=high.get(name), share=share) for name in names}
        return {name: value for name, value in made.items() if value}
    return max(0, round((low or 0) + ((high or 0) - (low or 0)) * share))


def blend_at(*, levels, field, place):
    """A blended field at a gauge's place: the level's own value at a preset's place, and between two presets a blend of the two levels'. Below the
    plainest preset the value falls toward nothing, and above the highest it goes on as far again as the last step up."""
    values = {level: levels.get(level, {}).get(field) for level in LEVELS}
    first = PRESET_PLACE[LEVELS[0]]
    last = PRESET_PLACE[LEVELS[-1]]
    if place <= first:
        nothing = values[LEVELS[0]] if field == melody.SPAN else None
        return blended(low=nothing, high=values[LEVELS[0]], share=place / first)
    if place >= last:
        return blended(low=values[LEVELS[-2]], high=values[LEVELS[-1]], share=1 + (place - last) / PLACES_IN_BAND)
    lower = max(level for level in LEVELS if PRESET_PLACE[level] <= place)
    return blended(low=values[lower], high=values[lower + 1], share=(place - PRESET_PLACE[lower]) / PLACES_IN_BAND)


def player_of(*, levels, character):
    """The player of an instrument, put together from the style's levels by a character: nothing where the style has no levels for the instrument."""
    if not levels or character is None:
        return {}
    level = level_of(character)
    if level is not None:
        return levels.get(level, {})
    player = {}
    for field in [field for at in LEVELS for field in levels.get(at, {})]:
        gauge = GAUGE_OF_FIELD.get(field)
        if gauge is None or field in player:
            continue
        place = character[gauge]
        value = blend_at(levels=levels, field=field, place=place) if field in BLENDED else levels.get(level_at(place), {}).get(field)
        if value:
            player[field] = value
    return player
