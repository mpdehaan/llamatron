# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Renaming any object never breaks a song: everything that refers to it by name follows, the
song still reads back as a file, and it renders the same notes.

Each class says once, in REFERENCES, which of its settings hold the name of an item of which
section, and both the rename and the question of what uses an item read that, so the last class
here checks that what is declared is real and that the two can't disagree, in every example.
"""

import unittest

from llamatron.engine.generators import arp as arp_plugin, auto_ratchet as auto_ratchet_plugin
from llamatron.engine.generators.chords.model import ChordsSetting, ChordsSettings
from llamatron.engine.generators.hocket.model import HocketSetting, HocketSettings
from llamatron.engine.generators.musician.model import MusicianSetting, MusicianSettings
from llamatron.interface.tracker.document import Document
from llamatron.interface.tracker.uses import grabbers, uses_of
from llamatron.model.file.example_sets import example_sets
from llamatron.model.objects import sections as sections_values
from llamatron.model.objects.chain import Chain
from llamatron.model.objects.clip_slot import ClipSlot
from llamatron.model.objects.llama_data import references_of
from llamatron.model.objects.named_scale import scale_type_name
from llamatron.model.objects.scene import Scene
from llamatron.model.objects.setlist import Setlist
from llamatron.model.objects.song import Song
from llamatron.model.objects.track import Track
from llamatron.model.schema import defaults, generator_plugins
from llamatron.model.schema.file_format import ClipSlotSetting, PatternSetting, Row, SceneSetting, Section, SongSetting, TrackSetting
from llamatron.model.values.note import NoteName
from llamatron.model.values.scale import ScaleType
from tests.model.test_llama_data import every_subclass
from tests.support.rendering import render_song

# Every song is rendered with this seed, so that two renders of one that has none still compare.
SEED = 1

# The sections whose items are renamed, and what refers to each: the song and scenes name a
# scale, clip slots name patterns, tracks and chains, chains name arps and AutoRatchets, and the
# song, scenes and tracks name grooves.
RENAMED_SECTIONS = [Section.SCALES, Section.PATTERNS, Section.TRACKS, arp_plugin.SECTION, auto_ratchet_plugin.SECTION, Section.CHAINS, Section.GROOVES, Section.SONGS]
RENAMED = '{name} renamed'
# Probability and random directions are rolled from the song's seed, the scene and the track's
# name (ClipSlotPlayer), so renaming a track changes what they roll. Whether that should stay so is
# an open question, so the examples, which use probability, keep their track names here.
SECTIONS_THAT_LEAVE_THE_NOTES_ALONE = [section for section in RENAMED_SECTIONS if section != Section.TRACKS]
# The song the first tests build, with every kind of reference in it.
MAIN = 'main'
OTHER = 'other'
TUNE = 'tune'
ANSWER = 'answer'
LEAD = 'lead'
BASS = 'bass'
CLIMBER = 'climber'
ROLLS = 'rolls'
NAMED = 'named'
VERSE = 'verse'
CHORUS = 'chorus'
SHUFFLE = 'shuffle'
SWING = 16
STEPS = 4
FIRST = 0
SECOND = 1
DEGREE = 1
TWO_REPEATS = 2
# How many places use the tune after the renames: a clip slot in each scene; and one use of the rest.
TUNE_USES = 2
ONE_USE = 1
# The song, a scene and a track choose the shuffle.
GROOVE_USES = 3
EXAMPLES = example_sets()
# The classes that declare which of their settings name things, and where each keeps its settings' names. A chain names
# generators by its steps, which aren't settings, so it answers for itself.
SETTINGS_OF = {ClipSlot: ClipSlotSetting, Scene: SceneSetting, Song: SongSetting, Track: TrackSetting, HocketSettings: HocketSetting, ChordsSettings: ChordsSetting, MusicianSettings: MusicianSetting}
# One name given to a pattern, a scale, a chain, a groove, an arp, an AutoRatchet and a track at once.
SHARED = 'shared'
# The arp's and the AutoRatchet's names, which a set file lists beside the chain's, where no two generators share a name.
SHARED_ARP = 'shared arp'
SHARED_RATCHET = 'shared ratchet'
RENAMED_SCALE = 'the scale renamed'
RENAMED_ARP = 'the arp renamed'


def played(grid):
    """Return what every clip of a grid plays, by position, without any names."""
    return [
        [(None if clip is None else (clip.played_notes(), clip.get_controls())) for track in grid.get_columns() for clip in [grid.get_clip(row=scene, column=track)]]
        for scene in grid.get_rows()
    ]


def rename_everything(*, document, sections=RENAMED_SECTIONS):
    """Rename every item of every named section, and return the new name of each."""
    renamed = {}
    for section in sections:
        # The set holds the shared sections and the songs, and the current song its own tracks.
        owner = document.song() if section in sections_values.SONG_SECTIONS else document.get_setlist()
        for name in owner.get_item_names(section):
            new = RENAMED.format(name=name)
            if section == Section.SONGS:
                # The document follows the current song by name, so a song is renamed through it.
                document.rename_named(section=Section.SONGS, old=name, new=new)
            else:
                owner.rename_item(section=section, old=name, new=new)
            renamed[section, name] = new
    document.changed()
    return renamed


def song_with_every_reference():
    document = Document()
    document.add_scale(name=OTHER, root=NoteName.F, kind=scale_type_name(ScaleType.MINOR))
    document.add_pattern(name=TUNE, steps=STEPS)
    document.change_pattern(document.pattern(TUNE).set_value, row=Row.DEGREE, step=FIRST, value=DEGREE)
    document.add_pattern(name=ANSWER, steps=STEPS)
    document.change_pattern(document.pattern(ANSWER).set_value, row=Row.DEGREE, step=FIRST, value=DEGREE)
    document.change_pattern(document.pattern(ANSWER).set_value, row=Row.GRAB, step=FIRST, value=True)
    document.add_track(LEAD)
    document.add_track(BASS)
    document.add_generator(section=arp_plugin.SECTION, name=CLIMBER)
    document.add_generator(section=auto_ratchet_plugin.SECTION, name=ROLLS)
    document.add_chain(NAMED)
    document.change_set(document.get_setlist().get_chain(NAMED).add_step, kind=arp_plugin.NAME, name=CLIMBER, setlist=document.get_setlist())
    document.change_set(document.get_setlist().get_chain(NAMED).add_step, kind=auto_ratchet_plugin.NAME, name=ROLLS, setlist=document.get_setlist())
    document.add_scene(index=FIRST, name=VERSE)
    document.add_clip_slot(index=FIRST, track=LEAD, pattern=TUNE)
    document.set_clip_slot_repeat(index=FIRST, track=LEAD, repeat=TWO_REPEATS)
    document.set_clip_slot_morph_target(index=FIRST, track=LEAD, pattern=ANSWER)
    document.add_clip_slot(index=FIRST, track=BASS, pattern=ANSWER)
    document.set_clip_slot_setting(index=FIRST, track=BASS, setting=ClipSlotSetting.GRAB_TRACK, value=LEAD)
    document.set_clip_slot_setting(index=FIRST, track=BASS, setting=ClipSlotSetting.CHAINS, value=[NAMED])
    document.add_scene(index=SECOND, name=CHORUS)
    document.change_set(document.song().get_scene(SECOND).set_scale_name, name=OTHER, song=document.song())
    document.add_groove(SHUFFLE)
    document.change_set(document.get_setlist().get_groove(SHUFFLE).set_cell, step=SECOND, value=SWING)
    document.change_set(document.song().set_groove_name, SHUFFLE)
    document.change_set(document.song().get_scene(SECOND).set_groove_choice, choice=SHUFFLE, song=document.song())
    document.change_set(document.song().get_track(BASS).set_groove_choice, choice=SHUFFLE, song=document.song())
    document.add_clip_slot(index=SECOND, track=LEAD, pattern=TUNE)
    return document


class TestRenamesFollowEveryReference(unittest.TestCase):

    def setUp(self):
        self.document = song_with_every_reference()
        self.before = played(render_song(self.document.song(), seed=SEED))
        self.renamed = rename_everything(document=self.document)

    def test_the_set_still_reads_back_as_a_file(self):
        data = self.document.get_setlist().to_data()
        self.assertEqual(Setlist.from_data(data=data).to_data(), data)

    def test_the_song_plays_the_same_notes(self):
        self.assertEqual(played(render_song(self.document.song(), seed=SEED)), self.before)

    def test_every_use_names_the_new_name(self):
        song = self.document.song()
        self.assertEqual(song.get_scale_name(), self.renamed[Section.SCALES, Document().song().get_scale_name()])
        self.assertEqual(song.get_scene(SECOND).get_scale_name(), self.renamed[Section.SCALES, OTHER])
        self.assertEqual(song.get_groove_name(), self.renamed[Section.GROOVES, SHUFFLE])
        self.assertEqual(song.get_scene(SECOND).get_groove_choice(), self.renamed[Section.GROOVES, SHUFFLE])
        self.assertEqual(song.get_track(self.renamed[Section.TRACKS, BASS]).get_groove_choice(), self.renamed[Section.GROOVES, SHUFFLE])
        lead = song.get_scene(FIRST).get_clip_slot(self.renamed[Section.TRACKS, LEAD])
        bass = song.get_scene(FIRST).get_clip_slot(self.renamed[Section.TRACKS, BASS])
        self.assertEqual(lead.get_pattern_name(), self.renamed[Section.PATTERNS, TUNE])
        self.assertEqual(lead.get_morph_target(), self.renamed[Section.PATTERNS, ANSWER])
        self.assertEqual(bass.get_grab_track(), self.renamed[Section.TRACKS, LEAD])
        self.assertEqual(bass.get_chain_names(), [self.renamed[Section.CHAINS, NAMED]])
        chain = song.get_setlist().get_chain(self.renamed[Section.CHAINS, NAMED])
        self.assertEqual(
            [step.name for step in chain.get_steps()],
            [self.renamed[arp_plugin.SECTION, CLIMBER], self.renamed[auto_ratchet_plugin.SECTION, ROLLS]],
        )

    def test_the_uses_the_tracker_lists_follow_too(self):
        new_tune = self.renamed[Section.PATTERNS, TUNE]
        setlist = self.document.get_setlist()
        self.assertEqual(len(uses_of(setlist=setlist, section=Section.PATTERNS, name=new_tune)), TUNE_USES)
        self.assertEqual(uses_of(setlist=setlist, section=Section.PATTERNS, name=TUNE), [])
        self.assertEqual(len(grabbers(song=self.document.song(), song_name=self.document.get_current_song_name(), track=self.renamed[Section.TRACKS, LEAD])), ONE_USE)
        self.assertEqual(len(uses_of(setlist=setlist, section=arp_plugin.SECTION, name=self.renamed[arp_plugin.SECTION, CLIMBER])), ONE_USE)
        self.assertEqual(len(uses_of(setlist=setlist, section=Section.SCALES, name=self.renamed[Section.SCALES, OTHER])), ONE_USE)
        self.assertEqual(len(uses_of(setlist=setlist, section=Section.GROOVES, name=self.renamed[Section.GROOVES, SHUFFLE])), GROOVE_USES)

    def test_old_names_are_gone_from_the_file(self):
        data = self.document.get_setlist().to_data()
        # A pattern's group is text of its own, which names no track even where a new set's group is spelled like its first track.
        data[Section.PATTERNS] = {name: {setting: value for setting, value in pattern.items() if setting != PatternSetting.GROUP} for name, pattern in data[Section.PATTERNS].items()}
        text = str(data)
        for (section, name), new in self.renamed.items():
            with self.subTest(section=section, name=name):
                self.assertNotIn(repr(name), text)
                self.assertIn(repr(new), text)


def constants_of(holder):
    """Return the values of a class that only holds constants."""
    return {value for name, value in vars(holder).items() if not name.startswith('_')}


def song_with_one_name_for_everything():
    """Return a document in which a pattern, a scale, a chain, a groove and a track share one name, and one clip names them all; the
    chain's arp and AutoRatchet, which a set file lists beside the chain, have names of their own."""
    document = Document()
    document.add_scale(name=SHARED, root=NoteName.F, kind=scale_type_name(ScaleType.MINOR))
    document.add_pattern(name=SHARED, steps=STEPS)
    document.add_pattern(name=TUNE, steps=STEPS)
    document.add_track(SHARED)
    document.add_track(BASS)
    document.add_generator(section=arp_plugin.SECTION, name=SHARED_ARP)
    document.add_generator(section=auto_ratchet_plugin.SECTION, name=SHARED_RATCHET)
    document.add_chain(SHARED)
    document.change_set(document.get_setlist().get_chain(SHARED).add_step, kind=arp_plugin.NAME, name=SHARED_ARP, setlist=document.get_setlist())
    document.change_set(document.get_setlist().get_chain(SHARED).add_step, kind=auto_ratchet_plugin.NAME, name=SHARED_RATCHET, setlist=document.get_setlist())
    document.add_groove(SHARED)
    document.add_scene(index=FIRST, name=SHARED)
    document.change_set(document.song().get_scene(FIRST).set_scale_name, name=SHARED, song=document.song())
    document.change_set(document.song().get_scene(FIRST).set_groove_choice, choice=SHARED, song=document.song())
    document.add_clip_slot(index=FIRST, track=BASS, pattern=SHARED)
    document.set_clip_slot_setting(index=FIRST, track=BASS, setting=ClipSlotSetting.CHAINS, value=[SHARED])
    document.set_clip_slot_setting(index=FIRST, track=BASS, setting=ClipSlotSetting.GRAB_TRACK, value=SHARED)
    document.add_clip_slot(index=FIRST, track=SHARED, pattern=TUNE)
    return document


class TestReferencesAreDeclaredOnce(unittest.TestCase):

    def test_every_declared_reference_is_a_setting_of_its_class_and_names_a_section(self):
        declaring = {kind for kind in every_subclass() if kind.REFERENCES or kind.CHAINS_NAMED_BY}
        self.assertEqual(declaring, set(SETTINGS_OF))
        sections = constants_of(Section) | set(generator_plugins.names_by_section())
        for kind, settings in SETTINGS_OF.items():
            for section, named in references_of(kind).items():
                with self.subTest(kind=kind.__name__, section=section):
                    self.assertIn(section, sections)
                    self.assertTrue(named)
                    self.assertLessEqual(set(named), constants_of(settings))

    def test_a_rename_follows_the_section_and_not_the_name_alone(self):
        document = song_with_one_name_for_everything()
        setlist = document.get_setlist()
        setlist.rename_item(section=Section.SCALES, old=SHARED, new=RENAMED_SCALE)
        scene = document.song().get_scene(FIRST)
        clip = scene.get_clip_slot(BASS)
        self.assertEqual(scene.get_scale_name(), RENAMED_SCALE)
        # Everything else that was called the same is still called that.
        self.assertEqual(scene.get_groove_choice(), SHARED)
        self.assertEqual((clip.get_pattern_name(), clip.get_chain_names(), clip.get_grab_track()), (SHARED, [SHARED], SHARED))
        setlist.rename_item(section=arp_plugin.SECTION, old=SHARED_ARP, new=RENAMED_ARP)
        self.assertEqual([(step.kind, step.name) for step in setlist.get_chain(SHARED).get_steps()], [(arp_plugin.NAME, RENAMED_ARP), (auto_ratchet_plugin.NAME, SHARED_RATCHET)])
        self.assertEqual(Setlist.from_data(data=setlist.to_data()).to_data(), setlist.to_data())

    def test_a_rename_changes_only_what_named_the_item(self):
        document = song_with_one_name_for_everything()
        scene = document.song().get_scene(FIRST)
        naming = scene.get_clip_slot(BASS)
        other = scene.get_clip_slot(SHARED)
        chain = document.get_setlist().get_chain(SHARED)
        kept = other.kept_data()
        revisions = (other.get_revision(), chain.get_revision(), scene.get_revision(), document.song().get_revision())
        was = naming.get_revision()
        document.get_setlist().rename_item(section=Section.PATTERNS, old=SHARED, new=ANSWER)
        self.assertEqual(naming.get_pattern_name(), ANSWER)
        self.assertNotEqual(naming.get_revision(), was)
        # The clip that plays another pattern, the chain, the scene's own settings and the song's are as they were.
        self.assertEqual((other.get_revision(), chain.get_revision(), scene.get_revision(), document.song().get_revision()), revisions)
        self.assertIs(other.kept_data(), kept)

    def test_a_renamed_tracks_clip_keeps_its_place_and_grabs_follow(self):
        document = song_with_one_name_for_everything()
        song = document.song()
        scene = song.get_scene(FIRST)
        order = scene.get_track_names()
        song.rename_item(section=Section.TRACKS, old=SHARED, new=LEAD)
        self.assertEqual(scene.get_track_names(), [LEAD if track == SHARED else track for track in order])
        self.assertEqual(scene.get_clip_slot(BASS).get_grab_track(), LEAD)
        self.assertEqual(scene.clip_slots_naming(section=Section.TRACKS, name=LEAD), [BASS])
        # The pattern, the chain and the rest that shared the track's old name keep it.
        self.assertEqual(scene.get_clip_slot(BASS).get_pattern_name(), SHARED)
        self.assertEqual(scene.get_scale_name(), SHARED)

    def test_each_kind_of_object_answers_for_its_own_settings(self):
        document = song_with_one_name_for_everything()
        song = document.song()
        scene = song.get_scene(FIRST)
        clip = scene.get_clip_slot(BASS)
        for section in (Section.PATTERNS, Section.CHAINS, Section.TRACKS):
            with self.subTest(section=section):
                self.assertTrue(clip.names_item(section=section, name=SHARED))
                self.assertFalse(clip.names_item(section=section, name=TUNE))
                self.assertFalse(scene.names_item(section=section, name=SHARED))
        self.assertFalse(clip.names_item(section=Section.SCALES, name=SHARED))
        self.assertTrue(scene.names_item(section=Section.SCALES, name=SHARED))
        self.assertTrue(scene.names_item(section=Section.GROOVES, name=SHARED))
        chain = document.get_setlist().get_chain(SHARED)
        self.assertTrue(chain.names_item(section=arp_plugin.SECTION, name=SHARED_ARP))
        self.assertTrue(chain.names_item(section=auto_ratchet_plugin.SECTION, name=SHARED_RATCHET))
        self.assertFalse(chain.names_item(section=arp_plugin.SECTION, name=SHARED_RATCHET))
        self.assertFalse(chain.names_item(section=arp_plugin.SECTION, name=TUNE))
        self.assertFalse(chain.names_item(section=Section.PATTERNS, name=SHARED))
        self.assertIsInstance(chain, Chain)

    def test_a_clip_that_morphs_to_a_pattern_names_it_too(self):
        document = song_with_every_reference()
        self.assertEqual(document.song().get_scene(FIRST).clip_slots_naming(section=Section.PATTERNS, name=ANSWER), [LEAD, BASS])
        self.assertEqual(document.song().get_scene(SECOND).clip_slots_naming(section=Section.PATTERNS, name=ANSWER), [])

    def test_a_song_with_no_groove_of_its_own_names_the_default_groove(self):
        document = song_with_one_name_for_everything()
        song = document.song()
        self.assertTrue(song.names_item(section=Section.GROOVES, name=defaults.DEFAULT_GROOVE))
        self.assertEqual(uses_of(setlist=document.get_setlist(), section=Section.GROOVES, name=defaults.DEFAULT_GROOVE), uses_of(setlist=Document().get_setlist(), section=Section.GROOVES, name=defaults.DEFAULT_GROOVE))
        document.change_set(document.song().set_groove_name, SHARED)
        self.assertFalse(song.names_item(section=Section.GROOVES, name=defaults.DEFAULT_GROOVE))
        self.assertTrue(song.names_item(section=Section.GROOVES, name=SHARED))
        self.assertEqual(uses_of(setlist=document.get_setlist(), section=Section.GROOVES, name=defaults.DEFAULT_GROOVE), [])

    def test_uses_are_listed_songs_first_then_scenes_tracks_clips_and_chains(self):
        document = song_with_every_reference()
        song_name = document.get_current_song_name()
        uses = uses_of(setlist=document.get_setlist(), section=Section.GROOVES, name=SHUFFLE)
        self.assertEqual(len(uses), GROOVE_USES)
        self.assertIn(song_name, uses[FIRST])
        self.assertIn(CHORUS, uses[SECOND])
        self.assertIn(BASS, uses[-1])
        # Nothing names a song, and nothing in a set names a track but the clips of the track's own song.
        self.assertEqual(uses_of(setlist=document.get_setlist(), section=Section.SONGS, name=song_name), [])
        self.assertEqual(len(grabbers(song=document.song(), song_name=song_name, track=LEAD)), ONE_USE)

    def test_in_every_example_what_uses_an_item_is_what_its_rename_changes(self):
        shared = [section for section in sections_values.setlist_sections() if section != Section.SONGS]
        for path in EXAMPLES:
            document = Document.load(path)
            setlist = document.get_setlist()
            for section in shared:
                for name in setlist.get_item_names(section):
                    with self.subTest(path=path, section=section, name=name):
                        uses = len(uses_of(setlist=setlist, section=section, name=name))
                        new = RENAMED.format(name=name)
                        setlist.rename_item(section=section, old=name, new=new)
                        self.assertEqual(uses_of(setlist=setlist, section=section, name=name), [])
                        self.assertEqual(len(uses_of(setlist=setlist, section=section, name=new)), uses)
            for song_name in setlist.get_song_names():
                song = setlist.get_song(song_name)
                for track in song.get_track_names():
                    with self.subTest(path=path, song=song_name, track=track):
                        uses = len(grabbers(song=song, song_name=song_name, track=track))
                        new = RENAMED.format(name=track)
                        song.rename_item(section=Section.TRACKS, old=track, new=new)
                        self.assertEqual(grabbers(song=song, song_name=song_name, track=track), [])
                        self.assertEqual(len(grabbers(song=song, song_name=song_name, track=new)), uses)
            self.assertEqual(Setlist.from_data(data=setlist.to_data()).to_data(), setlist.to_data())



def check_renames(*, test, path):
    """An example plays the same after every rename that leaves the notes alone."""
    document = Document.load(path)
    before = played(render_song(document.song(), seed=SEED))
    rename_everything(document=document, sections=SECTIONS_THAT_LEAVE_THE_NOTES_ALONE)
    reloaded = Setlist.from_data(data=document.get_setlist().to_data())
    test.assertEqual(played(render_song(reloaded.get_song(document.get_current_song_name()), seed=SEED)), before)


if __name__ == '__main__':
    unittest.main()
