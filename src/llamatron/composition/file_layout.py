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

"""The set file's layout beside the objects' data: what the objects write, turned into the file's lists, and back.

In the file, everything a person names is an item of a list with its name first, every generator of every kind is one list,
each item saying its kind, and a Chain, a clip, a scene and a track name the generators they run, each { name: x }. The objects
keep their named things by name, each kind of generator apart and the chains apart, and so write and read the layout the file
had before it was made of lists (composition/migrations/ moves an older file to the layout here first). A song's registers
keep their fixed names, AX to DX, as keys, since they are settings of the song and not things a person names.
"""

from llamatron.composition import file_format
from llamatron.composition.checks import listed as listed_text, reading
from llamatron.composition.file_format import FileLayout, Section
from llamatron.composition.invalid_value import InvalidValue
from llamatron.strings import errors

# What the objects call the generators a clip, a scene and a track run, and a scene's clips by track.
OBJECT_CHAINS = 'chains'
OBJECT_SCENE_TRACKS = 'tracks'
# A chain with statements keeps its steps under this in the objects' data.
OBJECT_CHAIN_STEPS = 'steps'
LISTED_SECTIONS = (Section.SCALES, Section.PATTERNS, Section.GROOVES, Section.INSTRUMENTS)
SECTIONS_OF_KINDS = {section: kind for kind, section in file_format.NAMED_GENERATORS.items()}


def as_items(mapping, *, key=FileLayout.NAME):
    """Return things kept by name as a list, each item a copy of the thing's settings with its name first under key."""
    return [{key: name, **settings} for name, settings in mapping.items()]


def with_key_replaced(settings, *, old, new, value):
    """Return a copy of settings with one key put in place of another, in its place, holding a value."""
    return {(new if key == old else key): (value if key == old else held) for key, held in settings.items()}


def name_references(names):
    """Return names as the file writes references to things by name, each { name: x }."""
    return [{FileLayout.NAME: name} for name in names]


# From the objects to the file.

def as_file_layout(data):
    """Return the objects' data of a set as the file lays it out."""
    written = {}
    generators = []
    for key, value in data.items():
        if key in SECTIONS_OF_KINDS:
            generators += [{FileLayout.NAME: name, FileLayout.KIND: SECTIONS_OF_KINDS[key], **settings} for name, settings in value.items()]
        elif key == Section.CHAINS:
            generators += [_chain_item(name=name, chain=chain) for name, chain in value.items()]
        elif key in LISTED_SECTIONS:
            written[key] = as_items(value)
        elif key == Section.SONGS:
            written[key] = [{FileLayout.NAME: name, **_song_in_file(song)} for name, song in value.items()]
        else:
            written[key] = value
    if generators:
        written[FileLayout.GENERATORS] = generators
    return written


def _chain_item(*, name, chain):
    steps = chain[OBJECT_CHAIN_STEPS] if isinstance(chain, dict) else chain
    item = {FileLayout.NAME: name, FileLayout.KIND: FileLayout.CHAIN, FileLayout.GENERATORS: name_references([next(iter(step.values())) for step in steps])}
    if isinstance(chain, dict):
        item.update({key: value for key, value in chain.items() if key != OBJECT_CHAIN_STEPS})
    return item


def _song_in_file(song):
    written = dict(song)
    if isinstance(written.get(Section.TRACKS), dict):
        written[Section.TRACKS] = [{FileLayout.NAME: name, **_references_in_file(track)} for name, track in written[Section.TRACKS].items()]
    if Section.SCENES in written:
        written[Section.SCENES] = [_scene_in_file(scene) for scene in written[Section.SCENES]]
    return written


def _scene_in_file(scene):
    written = _references_in_file(scene)
    if OBJECT_SCENE_TRACKS in written:
        clips = [{FileLayout.TRACK: track, **_references_in_file(clip)} for track, clip in written[OBJECT_SCENE_TRACKS].items()]
        written = with_key_replaced(written, old=OBJECT_SCENE_TRACKS, new=FileLayout.CLIPS, value=clips)
    return written


def _references_in_file(settings):
    if OBJECT_CHAINS not in settings:
        return dict(settings)
    return with_key_replaced(settings, old=OBJECT_CHAINS, new=FileLayout.GENERATORS, value=name_references(settings[OBJECT_CHAINS]))


# From the file to the objects.

def as_object_layout(data):
    """Return a set file's data, in the layout written now, as the objects read it, or raise SongFileError for a list that is not
    one of named items, a name used twice, or a generator of no kind."""
    if not isinstance(data, dict):
        return data
    read = {}
    for key, value in data.items():
        if key in LISTED_SECTIONS:
            read[key] = keyed(items=value, section=key)
        elif key == FileLayout.GENERATORS:
            read.update(_generators_by_kind(value))
        elif key == Section.SONGS:
            read[key] = {name: _song_of_file(song) for name, song in keyed(items=value, section=key).items()}
        else:
            read[key] = value
    return read


def keyed(*, items, section, key=FileLayout.NAME):
    """Return a list of named items as the objects keep them, by name, each without its name, or raise SongFileError."""
    with reading(section):
        if not isinstance(items, list):
            raise InvalidValue(errors.ERR_EXPECTED_ITEMS.format(value=items))
        by_name = {}
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get(key), str):
                raise InvalidValue(errors.ERR_ITEM_NEEDS_NAME.format(value=item))
            if item[key] in by_name:
                raise InvalidValue(errors.ERR_NAMED_TWICE.format(name=item[key]))
            by_name[item[key]] = {field: value for field, value in item.items() if field != key}
        return by_name


def _generators_by_kind(items):
    """Return the list of generators as the objects keep them: each kind's under its section, and the chains, whose steps name each
    generator with its kind."""
    by_name = keyed(items=items, section=FileLayout.GENERATORS)
    kinds = {}
    with reading(FileLayout.GENERATORS):
        for name, settings in by_name.items():
            kind = settings.get(FileLayout.KIND)
            if kind != FileLayout.CHAIN and kind not in file_format.NAMED_GENERATORS:
                raise InvalidValue(errors.ERR_NO_SUCH_KIND.format(name=name, kinds=listed_text([*file_format.NAMED_GENERATORS, FileLayout.CHAIN]), value=kind))
            kinds[name] = kind
    read = {}
    for name, settings in by_name.items():
        own = {field: value for field, value in settings.items() if field != FileLayout.KIND}
        if kinds[name] == FileLayout.CHAIN:
            read.setdefault(Section.CHAINS, {})[name] = _chain_of_file(name=name, settings=own, kinds=kinds)
        else:
            read.setdefault(file_format.NAMED_GENERATORS[kinds[name]], {})[name] = own
    return read


def _chain_of_file(*, name, settings, kinds):
    with reading(FileLayout.GENERATORS):
        steps = []
        for step in _names_of(settings.get(FileLayout.GENERATORS, [])):
            if step not in kinds:
                raise InvalidValue(errors.ERR_NO_GENERATOR_CALLED.format(name=step))
            if kinds[step] == FileLayout.CHAIN:
                raise InvalidValue(errors.ERR_CHAIN_IN_CHAIN.format(name=name, step=step))
            steps.append({kinds[step]: step})
    rest = {field: value for field, value in settings.items() if field != FileLayout.GENERATORS}
    return {OBJECT_CHAIN_STEPS: steps, **rest} if rest else steps


def _names_of(references):
    """Return the names a list of { name: x } holds, or raise InvalidValue for anything else."""
    if not isinstance(references, list) or not all(isinstance(reference, dict) and set(reference) == {FileLayout.NAME} for reference in references):
        raise InvalidValue(errors.ERR_EXPECTED_NAMES.format(value=references))
    return [reference[FileLayout.NAME] for reference in references]


def _song_of_file(song):
    if not isinstance(song, dict):
        return song
    read = dict(song)
    if Section.TRACKS in read:
        read[Section.TRACKS] = {name: _references_of_file(track) for name, track in keyed(items=read[Section.TRACKS], section=Section.TRACKS).items()}
    if isinstance(read.get(Section.SCENES), list):
        read[Section.SCENES] = [_scene_of_file(scene) for scene in read[Section.SCENES]]
    return read


def _scene_of_file(scene):
    if not isinstance(scene, dict):
        return scene
    read = _references_of_file(scene)
    if FileLayout.CLIPS in read:
        clips = keyed(items=read[FileLayout.CLIPS], section=FileLayout.CLIPS, key=FileLayout.TRACK)
        read = with_key_replaced(read, old=FileLayout.CLIPS, new=OBJECT_SCENE_TRACKS, value={track: _references_of_file(clip) for track, clip in clips.items()})
    return read


def _references_of_file(settings):
    if not isinstance(settings, dict) or FileLayout.GENERATORS not in settings:
        return settings
    with reading(FileLayout.GENERATORS):
        names = _names_of(settings[FileLayout.GENERATORS])
    return with_key_replaced(settings, old=FileLayout.GENERATORS, new=OBJECT_CHAINS, value=names)
