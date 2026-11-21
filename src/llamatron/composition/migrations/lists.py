# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Files saved before 1.0.591 kept every named thing as a mapping keyed by its name, each kind of generator in a section of its
own and the chains apart, and a clip, a scene and a track named the chains they ran.

Everything named becomes an item of a list, its name first; the generators of every kind and the chains become one list, each
item saying its kind, a chain becoming a generator of the kind chain; a scene's clips, kept by track, become a list of items
naming their tracks; and a reference to a generator becomes its name alone, { name: x }. A name that two kinds shared is
settled by the naming rules: the later keeps going under the next free name, as bass-2, and every reference follows. A clip's
older single chain becomes a list of one.
"""

from llamatron.composition import naming
from llamatron.composition.migrations.helpers import as_items, name_references, with_key_replaced

SINCE = '1.0.591'
# The sections of named things that become lists, and those of a song.
LISTED_SECTIONS = ('scales', 'patterns', 'grooves', 'instruments')
SONGS = 'songs'
TRACKS = 'tracks'
SCENES = 'scenes'
# Each kind of generator, and the section that held it.
SECTIONS_OF_KINDS = {
    'arp': 'arps', 'auto_ratchet': 'auto_ratchets', 'drift': 'drifts', 'progression': 'progressions', 'voice_leading': 'voice_leadings',
    'strum': 'strums', 'euclid': 'euclids', 'density': 'densities', 'swell': 'swells', 'articulate': 'articulates', 'glide': 'glides',
    'shorten': 'shortens', 'rush': 'rushes', 'drag': 'drags', 'hocket': 'hockets', 'guitarify': 'guitarifies', 'follow_chords': 'follow_chords',
    'phrasing': 'phrasings', 'musician': 'musicians',
}
KINDS_OF_SECTIONS = {section: kind for kind, section in SECTIONS_OF_KINDS.items()}
# The chains, what a clip, a scene and a track named them under, and a clip's older single chain.
CHAINS = 'chains'
CHAIN = 'chain'
# A chain with statements held its steps under this.
STEPS = 'steps'
# The new layout's names.
NAME = 'name'
KIND = 'kind'
GENERATORS = 'generators'
CLIPS = 'clips'
TRACK = 'track'


def is_before(data):
    """Return whether a file is in the layout before lists: some section of named things is a mapping by name, or a generator or a
    chain is kept in a section of its kind."""
    keyed = any(isinstance(data.get(section), dict) for section in (*LISTED_SECTIONS, SONGS))
    return keyed or any(section in data for section in (*SECTIONS_OF_KINDS.values(), CHAINS))


def moved(*, data, conversion):
    listed = {}
    generators = []
    taken = []
    # Each generator's new name by its kind and old name, and each chain's by its old name.
    renamed = {}
    renamed_chains = {}
    for key, value in data.items():
        if key in KINDS_OF_SECTIONS and isinstance(value, dict):
            kind = KINDS_OF_SECTIONS[key]
            for name, settings in value.items():
                renamed[(kind, name)] = _free_name(name=name, kind=kind, taken=taken, conversion=conversion)
                generators.append({NAME: renamed[(kind, name)], KIND: kind, **(settings if isinstance(settings, dict) else {})})
        elif key in LISTED_SECTIONS:
            listed[key] = as_items(value)
        else:
            listed[key] = value
    for name, chain in (listed.pop(CHAINS, None) or {}).items():
        renamed_chains[name] = _free_name(name=name, kind=CHAIN, taken=taken, conversion=conversion)
        generators.append(_chain_item(name=renamed_chains[name], chain=chain, renamed=renamed))
    if generators:
        listed[GENERATORS] = generators
    if isinstance(listed.get(SONGS), dict):
        listed[SONGS] = [{NAME: name, **_song_listed(song=song, renamed=renamed_chains)} for name, song in listed[SONGS].items()]
    return listed


def _free_name(*, name, kind, taken, conversion):
    """Return a generator's name, or the next free one by the naming rules where a generator of another kind came first with it."""
    new = naming.unique_name(base=name, taken=taken)
    taken.append(new)
    if new != name:
        conversion.note_rename(kind=kind, old=name, new=new)
    return new


def _chain_item(*, name, chain, renamed):
    """Return a chain, a list of steps each { kind: name } or those steps with statements, as an item of the generators."""
    steps = chain.get(STEPS) if isinstance(chain, dict) else chain
    if isinstance(steps, list):
        steps = [renamed.get(_step_of(step), _step_of(step)[1]) if _step_of(step) else step for step in steps]
    item = {NAME: name, KIND: CHAIN, GENERATORS: name_references(steps)}
    if isinstance(chain, dict):
        item.update({key: value for key, value in chain.items() if key != STEPS})
    return item


def _step_of(step):
    """Return a chain's step as (kind, name), or None for anything else, which the reader refuses."""
    return next(iter(step.items())) if isinstance(step, dict) and len(step) == 1 else None


def _song_listed(*, song, renamed):
    if not isinstance(song, dict):
        return song
    listed = dict(song)
    if isinstance(listed.get(TRACKS), dict) and all(isinstance(track, dict) for track in listed[TRACKS].values()):
        listed[TRACKS] = [{NAME: name, **_references_listed(settings=track, renamed=renamed)} for name, track in listed[TRACKS].items()]
    if isinstance(listed.get(SCENES), list):
        listed[SCENES] = [_scene_listed(scene=scene, renamed=renamed) for scene in listed[SCENES]]
    return listed


def _scene_listed(*, scene, renamed):
    if not isinstance(scene, dict):
        return scene
    listed = _references_listed(settings=scene, renamed=renamed)
    clips = listed.get(TRACKS)
    if isinstance(clips, dict) and all(isinstance(clip, dict) for clip in clips.values()):
        clips = [{TRACK: track, **_references_listed(settings=clip, renamed=renamed)} for track, clip in clips.items()]
        listed = with_key_replaced(listed, old=TRACKS, new=CLIPS, value=clips)
    return listed


def _references_listed(*, settings, renamed):
    """Return a clip's, a scene's or a track's settings with the chains it ran written as the generators it runs."""
    listed = dict(settings)
    if CHAIN in listed and CHAINS not in listed:
        listed = with_key_replaced(listed, old=CHAIN, new=CHAINS, value=[listed[CHAIN]])
    if CHAINS in listed:
        names = listed[CHAINS]
        names = [renamed.get(name, name) for name in names] if isinstance(names, list) else names
        listed = with_key_replaced(listed, old=CHAINS, new=GENERATORS, value=name_references(names))
    return listed
