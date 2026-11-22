# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The set file's layout beside the objects' data: what the objects write, turned into the file's lists, and back.

In the file, everything a person names is an item of a list with its name first, every generator of every kind is one list,
each item saying its kind, and a Chain, a clip, a scene and a track name the generators they run, each { name: x }. The objects
keep their named things by name, each kind of generator apart and the chains apart, and so write and read the layout the file
had before it was made of lists (model/file/migrations/ moves an older file to the layout here first). A song's registers
keep their fixed names, AX to DX, as keys, since they are settings of the song and not things a person names.
"""

from llamatron.model.file import corrections
from llamatron.model.file.checks import listed as listed_text, reading
from llamatron.model.file.corrections import Correction
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.schema import generator_plugins
from llamatron.model.schema.file_format import ClipSlotSetting, FileLayout, Section
from llamatron.user_strings import errors, messages

# What the objects call the generators a clip, a scene and a track run, and a scene's clips by track.
OBJECT_CHAINS = 'chains'
OBJECT_SCENE_TRACKS = 'tracks'
# A chain with statements keeps its steps under this in the objects' data.
OBJECT_CHAIN_STEPS = 'steps'
# The objects' layout's key of the generators whose kind no plugin provides, by name, with their kinds: a key no file can hold.
GENERATORS_WITHOUT_PLUGIN = 'generators without a plugin'
# What every clip's, scene's and track's list of the generators and chains it runs is called, one name for the three.
CHAIN_LISTS = ClipSlotSetting.CHAINS
LISTED_SECTIONS = (Section.SCALES, Section.PATTERNS, Section.GROOVES, Section.INSTRUMENTS)


def as_items(mapping, *, key=FileLayout.NAME):
    """Return things kept by name as a list, each item a copy of the thing's settings with its name first under key."""
    return [{key: name, **settings} for name, settings in mapping.items()]


def with_key_replaced(settings, *, old, new, value):
    """Return a copy of settings with one key put in place of another, in its place, holding a value."""
    replaced = {}
    for key, held in settings.items():
        if key == old:
            replaced[new] = value
        else:
            replaced[key] = held
    return replaced


def name_references(names):
    """Return names as the file writes references to things by name, each { name: x }."""
    return [{FileLayout.NAME: name} for name in names]


# From the objects to the file.

def as_file_layout(data):
    """Return the objects' data of a set as the file lays it out."""
    written = {}
    generators = []
    for key, value in data.items():
        kinds = generator_plugins.names_by_section()
        if key in kinds:
            generators += _generator_items(kind=kinds[key], generators=value)
        elif key == Section.CHAINS:
            for name, chain in value.items():
                generators.append(_chain_item(name=name, chain=chain))
        elif key in LISTED_SECTIONS:
            written[key] = as_items(value)
        elif key == Section.SONGS:
            written[key] = _named_items(mapping=value, key=FileLayout.NAME, laid_out=_song_in_file)
        else:
            written[key] = value
    if generators:
        written[FileLayout.GENERATORS] = generators
    return written


def _chain_item(*, name, chain):
    steps = chain
    if isinstance(chain, dict):
        steps = chain[OBJECT_CHAIN_STEPS]
    # Each step is {kind: name}, and the file names the generator alone.
    names = []
    for step in steps:
        names.append(next(iter(step.values())))
    item = {FileLayout.NAME: name, FileLayout.KIND: FileLayout.CHAIN, FileLayout.GENERATORS: name_references(names)}
    if isinstance(chain, dict):
        for key, value in chain.items():
            if key != OBJECT_CHAIN_STEPS:
                item[key] = value
    return item


def _song_in_file(song):
    written = dict(song)
    if isinstance(written.get(Section.TRACKS), dict):
        written[Section.TRACKS] = _named_items(mapping=written[Section.TRACKS], key=FileLayout.NAME, laid_out=_references_in_file)
    if Section.SCENES in written:
        written[Section.SCENES] = [_scene_in_file(scene) for scene in written[Section.SCENES]]
    return written


def _scene_in_file(scene):
    written = _references_in_file(scene)
    if OBJECT_SCENE_TRACKS in written:
        clips = _named_items(mapping=written[OBJECT_SCENE_TRACKS], key=FileLayout.TRACK, laid_out=_references_in_file)
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
            songs = keyed(items=value, section=key)
            read[key] = _each_read(mapping=songs, read=_song_of_file)
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
            if kind != FileLayout.CHAIN and kind not in generator_plugins.sections_by_name() and not isinstance(kind, str):
                raise InvalidValue(errors.ERR_NO_SUCH_KIND.format(name=name, kinds=listed_text([*generator_plugins.sections_by_name(), FileLayout.CHAIN]), value=kind))
            kinds[name] = kind
    read = {}
    for name, settings in by_name.items():
        own = {field: value for field, value in settings.items() if field != FileLayout.KIND}
        if kinds[name] != FileLayout.CHAIN and kinds[name] not in generator_plugins.sections_by_name():
            # A kind no plugin provides, as from a set made where another plugin was installed: the set asks before dropping it.
            read.setdefault(GENERATORS_WITHOUT_PLUGIN, {})[name] = kinds[name]
        elif kinds[name] == FileLayout.CHAIN:
            read.setdefault(Section.CHAINS, {})[name] = _chain_of_file(name=name, settings=own, kinds=kinds)
        else:
            read.setdefault(generator_plugins.sections_by_name()[kinds[name]], {})[name] = own
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
    if not rest:
        return steps
    return {OBJECT_CHAIN_STEPS: steps, **rest}


def _names_of(references):
    """Return the names a list of { name: x } holds, or raise InvalidValue for anything else."""
    if not isinstance(references, list):
        raise InvalidValue(errors.ERR_EXPECTED_NAMES.format(value=references))
    names = []
    for reference in references:
        if not isinstance(reference, dict) or set(reference) != {FileLayout.NAME}:
            raise InvalidValue(errors.ERR_EXPECTED_NAMES.format(value=references))
        names.append(reference[FileLayout.NAME])
    return names


def _song_of_file(song):
    if not isinstance(song, dict):
        return song
    read = dict(song)
    if Section.TRACKS in read:
        tracks = keyed(items=read[Section.TRACKS], section=Section.TRACKS)
        read[Section.TRACKS] = _each_read(mapping=tracks, read=_references_of_file)
    if isinstance(read.get(Section.SCENES), list):
        read[Section.SCENES] = [_scene_of_file(scene) for scene in read[Section.SCENES]]
    return read


def _scene_of_file(scene):
    if not isinstance(scene, dict):
        return scene
    read = _references_of_file(scene)
    if FileLayout.CLIPS in read:
        clips = keyed(items=read[FileLayout.CLIPS], section=FileLayout.CLIPS, key=FileLayout.TRACK)
        read = with_key_replaced(read, old=FileLayout.CLIPS, new=OBJECT_SCENE_TRACKS, value=_each_read(mapping=clips, read=_references_of_file))
    return read


def _references_of_file(settings):
    if not isinstance(settings, dict) or FileLayout.GENERATORS not in settings:
        return settings
    with reading(FileLayout.GENERATORS):
        names = _names_of(settings[FileLayout.GENERATORS])
    return with_key_replaced(settings, old=FileLayout.GENERATORS, new=OBJECT_CHAINS, value=names)


class GeneratorWithoutPlugin(Correction):
    """A generator whose kind no plugin provides, as a set made where another plugin was installed holds: applying it takes the
    generator out of the set's data with every use of it, each chain's step and each clip's, scene's and track's naming of it,
    so that saving the set leaves it out.

    holder is the set's data in the objects' layout, found that layout's key of the generators without a plugin, and name and
    kind the generator's.
    """

    __slots__ = ()

    def __init__(self, *, holder, key, name, kind):
        super().__init__(holder=holder, key=key, name=name, found=kind, used=corrections.LEFT_OUT)

    def apply(self):
        """Take the generator out of the set's data, with each use of it."""
        without = self._holder[self._key]
        del without[self._name]
        if not without:
            del self._holder[self._key]
        for chain in (self._holder.get(Section.CHAINS) or {}).values():
            steps = chain
            if isinstance(chain, dict):
                steps = chain.get(OBJECT_CHAIN_STEPS, [])
            steps[:] = [step for step in steps if step != {self._found: self._name}]
        _drop_from_chain_lists(data=self._holder.get(Section.SONGS), name=self._name)

    def described(self):
        """Return one line saying which generator has no plugin and that it goes, with every use."""
        return messages.MSG_CORRECTED_NO_PLUGIN.format(name=self._name, kind=self._found)


def _drop_from_chain_lists(*, data, name):
    """Take a name out of every list of chains in a part of a set's data: each clip's, scene's and track's."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key == CHAIN_LISTS and isinstance(value, list):
                value[:] = [held for held in value if held != name]
            else:
                _drop_from_chain_lists(data=value, name=name)
    elif isinstance(data, list):
        for value in data:
            _drop_from_chain_lists(data=value, name=name)


def _generator_items(*, kind, generators):
    """Return one kind's generators as the file lists them, each with its name and kind first."""
    items = []
    for name, settings in generators.items():
        items.append({FileLayout.NAME: name, FileLayout.KIND: kind, **settings})
    return items


def _named_items(*, mapping, key, laid_out):
    """Return things kept by name as the file lists them, each laid out as the file writes it, with its name first under key."""
    items = []
    for name, settings in mapping.items():
        items.append({key: name, **laid_out(settings)})
    return items


def _each_read(*, mapping, read):
    """Return things kept by name with each read from the file's layout into the objects'."""
    read_items = {}
    for name, settings in mapping.items():
        read_items[name] = read(settings)
    return read_items
