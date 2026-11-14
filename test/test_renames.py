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

"""Renaming any object never breaks a song: everything that refers to it by name follows, the
song still reads back as a file, and it renders the same notes.

Each class says once, in REFERENCES, which of its settings hold the name of an item of which
section, and both the rename and the question of what uses an item read that, so the last class
here checks that what is declared is real and that the two can't disagree, in every example.
"""

import unittest

from llamatron.composition.clip_slot import ClipSlot
from llamatron.composition.chain import Chain
from llamatron.composition.defaults import DEFAULT_GROOVE
from llamatron.composition.generator_settings import HocketSetting, HocketSettings
from llamatron.composition.file_format import ClipSlotSetting, GeneratorKind, Row, SceneSetting, Section, SongSetting, TrackSetting
from llamatron.composition.named_scale import scale_type_name
from llamatron.composition.scene import Scene
from llamatron.composition.sections import SETLIST_SECTIONS, SONG_SECTIONS
from llamatron.composition.setlist import Setlist
from llamatron.composition.song import Song
from llamatron.composition.track import Track
from llamatron.music.note import NoteName
from llamatron.music.scale import ScaleType
from llamatron.tui.document import Document
from llamatron.tui.uses import grabbers, uses_of
from llamatron.support.example_sets import example_sets
from rendering import render_song
from test_llama_data import every_subclass

# Every song is rendered with this seed, so that two renders of one that has none still compare.
SEED = 1

# The sections whose items are renamed, and what refers to each: the song and scenes name a
# scale, clip slots name patterns, tracks and chains, chains name arps and AutoRatchets, and the
# song, scenes and tracks name grooves.
RENAMED_SECTIONS = [Section.SCALES, Section.PATTERNS, Section.TRACKS, Section.ARPS, Section.AUTO_RATCHETS, Section.CHAINS, Section.GROOVES, Section.SONGS]
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
SETTINGS_OF = {ClipSlot: ClipSlotSetting, Scene: SceneSetting, Song: SongSetting, Track: TrackSetting, HocketSettings: HocketSetting}
# One name given to a pattern, a scale, a chain, a groove, an arp, an AutoRatchet and a track at once.
SHARED = 'shared'
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
        owner = document.song() if section in SONG_SECTIONS else document.setlist()
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
    document.set_step_value(name=TUNE, row=Row.DEGREE, step=FIRST, value=DEGREE)
    document.add_pattern(name=ANSWER, steps=STEPS)
    document.set_step_value(name=ANSWER, row=Row.DEGREE, step=FIRST, value=DEGREE)
    document.set_step_value(name=ANSWER, row=Row.GRAB, step=FIRST, value=True)
    document.add_track(LEAD)
    document.add_track(BASS)
    document.add_generator(section=Section.ARPS, name=CLIMBER)
    document.add_generator(section=Section.AUTO_RATCHETS, name=ROLLS)
    document.add_chain(NAMED)
    document.add_chain_step(chain=NAMED, kind=GeneratorKind.ARP, name=CLIMBER)
    document.add_chain_step(chain=NAMED, kind=GeneratorKind.AUTO_RATCHET, name=ROLLS)
    document.add_scene(index=FIRST, name=VERSE)
    document.add_clip_slot(index=FIRST, track=LEAD, pattern=TUNE)
    document.set_clip_slot_repeat(index=FIRST, track=LEAD, repeat=TWO_REPEATS)
    document.set_clip_slot_morph_target(index=FIRST, track=LEAD, pattern=ANSWER)
    document.add_clip_slot(index=FIRST, track=BASS, pattern=ANSWER)
    document.set_clip_slot_setting(index=FIRST, track=BASS, setting=ClipSlotSetting.GRAB_TRACK, value=LEAD)
    document.set_clip_slot_setting(index=FIRST, track=BASS, setting=ClipSlotSetting.CHAIN, value=NAMED)
    document.add_scene(index=SECOND, name=CHORUS)
    document.set_scene_scale(index=SECOND, name=OTHER)
    document.add_groove(SHUFFLE)
    document.set_groove_cell(name=SHUFFLE, step=SECOND, amount=SWING)
    document.set_groove_name(SHUFFLE)
    document.set_scene_groove(index=SECOND, choice=SHUFFLE)
    document.set_track_groove(name=BASS, choice=SHUFFLE)
    document.add_clip_slot(index=SECOND, track=LEAD, pattern=TUNE)
    return document


class TestRenamesFollowEveryReference(unittest.TestCase):

    def setUp(self):
        self.document = song_with_every_reference()
        self.before = played(render_song(self.document.song(), seed=SEED))
        self.renamed = rename_everything(document=self.document)

    def test_the_set_still_reads_back_as_a_file(self):
        data = self.document.setlist().to_data()
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
        chain = song.get_chain(self.renamed[Section.CHAINS, NAMED])
        self.assertEqual(
            [step.name for step in chain.get_steps()],
            [self.renamed[Section.ARPS, CLIMBER], self.renamed[Section.AUTO_RATCHETS, ROLLS]],
        )

    def test_the_uses_the_tracker_lists_follow_too(self):
        new_tune = self.renamed[Section.PATTERNS, TUNE]
        setlist = self.document.setlist()
        self.assertEqual(len(uses_of(setlist=setlist, section=Section.PATTERNS, name=new_tune)), TUNE_USES)
        self.assertEqual(uses_of(setlist=setlist, section=Section.PATTERNS, name=TUNE), [])
        self.assertEqual(len(grabbers(song=self.document.song(), song_name=self.document.current_song_name(), track=self.renamed[Section.TRACKS, LEAD])), ONE_USE)
        self.assertEqual(len(uses_of(setlist=setlist, section=Section.ARPS, name=self.renamed[Section.ARPS, CLIMBER])), ONE_USE)
        self.assertEqual(len(uses_of(setlist=setlist, section=Section.SCALES, name=self.renamed[Section.SCALES, OTHER])), ONE_USE)
        self.assertEqual(len(uses_of(setlist=setlist, section=Section.GROOVES, name=self.renamed[Section.GROOVES, SHUFFLE])), GROOVE_USES)

    def test_old_names_are_gone_from_the_file(self):
        text = str(self.document.setlist().to_data())
        for (section, name), new in self.renamed.items():
            with self.subTest(section=section, name=name):
                self.assertNotIn(repr(name), text)
                self.assertIn(repr(new), text)


class TestEveryExampleSurvivesRenamingEverything(unittest.TestCase):

    def test_every_example_plays_the_same_after_every_rename(self):
        for path in EXAMPLES:
            with self.subTest(path=path):
                document = Document.load(path)
                before = played(render_song(document.song(), seed=SEED))
                rename_everything(document=document, sections=SECTIONS_THAT_LEAVE_THE_NOTES_ALONE)
                reloaded = Setlist.from_data(data=document.setlist().to_data())
                self.assertEqual(played(render_song(reloaded.get_song(document.current_song_name()), seed=SEED)), before)


def constants_of(holder):
    """Return the values of a class that only holds constants."""
    return {value for name, value in vars(holder).items() if not name.startswith('_')}


def song_with_one_name_for_everything():
    """Return a document in which a pattern, a scale, a chain, a groove, an arp, an AutoRatchet and a track share one name, and one clip names them all."""
    document = Document()
    document.add_scale(name=SHARED, root=NoteName.F, kind=scale_type_name(ScaleType.MINOR))
    document.add_pattern(name=SHARED, steps=STEPS)
    document.add_pattern(name=TUNE, steps=STEPS)
    document.add_track(SHARED)
    document.add_track(BASS)
    document.add_generator(section=Section.ARPS, name=SHARED)
    document.add_generator(section=Section.AUTO_RATCHETS, name=SHARED)
    document.add_chain(SHARED)
    document.add_chain_step(chain=SHARED, kind=GeneratorKind.ARP, name=SHARED)
    document.add_chain_step(chain=SHARED, kind=GeneratorKind.AUTO_RATCHET, name=SHARED)
    document.add_groove(SHARED)
    document.add_scene(index=FIRST, name=SHARED)
    document.set_scene_scale(index=FIRST, name=SHARED)
    document.set_scene_groove(index=FIRST, choice=SHARED)
    document.add_clip_slot(index=FIRST, track=BASS, pattern=SHARED)
    document.set_clip_slot_setting(index=FIRST, track=BASS, setting=ClipSlotSetting.CHAIN, value=SHARED)
    document.set_clip_slot_setting(index=FIRST, track=BASS, setting=ClipSlotSetting.GRAB_TRACK, value=SHARED)
    document.add_clip_slot(index=FIRST, track=SHARED, pattern=TUNE)
    return document


class TestReferencesAreDeclaredOnce(unittest.TestCase):

    def test_every_declared_reference_is_a_setting_of_its_class_and_names_a_section(self):
        declaring = {kind for kind in every_subclass() if kind.REFERENCES}
        self.assertEqual(declaring, set(SETTINGS_OF))
        sections = constants_of(Section)
        for kind, settings in SETTINGS_OF.items():
            for section, named in kind.REFERENCES.items():
                with self.subTest(kind=kind.__name__, section=section):
                    self.assertIn(section, sections)
                    self.assertTrue(named)
                    self.assertLessEqual(set(named), constants_of(settings))

    def test_a_rename_follows_the_section_and_not_the_name_alone(self):
        document = song_with_one_name_for_everything()
        setlist = document.setlist()
        setlist.rename_item(section=Section.SCALES, old=SHARED, new=RENAMED_SCALE)
        scene = document.song().get_scene(FIRST)
        clip = scene.get_clip_slot(BASS)
        self.assertEqual(scene.get_scale_name(), RENAMED_SCALE)
        # Everything else that was called the same is still called that.
        self.assertEqual(scene.get_groove_choice(), SHARED)
        self.assertEqual((clip.get_pattern_name(), clip.get_chain_names(), clip.get_grab_track()), (SHARED, [SHARED], SHARED))
        setlist.rename_item(section=Section.ARPS, old=SHARED, new=RENAMED_ARP)
        self.assertEqual([(step.kind, step.name) for step in setlist.get_chain(SHARED).get_steps()], [(GeneratorKind.ARP, RENAMED_ARP), (GeneratorKind.AUTO_RATCHET, SHARED)])
        self.assertEqual(Setlist.from_data(data=setlist.to_data()).to_data(), setlist.to_data())

    def test_a_rename_changes_only_what_named_the_item(self):
        document = song_with_one_name_for_everything()
        scene = document.song().get_scene(FIRST)
        naming = scene.get_clip_slot(BASS)
        other = scene.get_clip_slot(SHARED)
        chain = document.setlist().get_chain(SHARED)
        kept = other.kept_data()
        revisions = (other.revision(), chain.revision(), scene.revision(), document.song().revision())
        was = naming.revision()
        document.setlist().rename_item(section=Section.PATTERNS, old=SHARED, new=ANSWER)
        self.assertEqual(naming.get_pattern_name(), ANSWER)
        self.assertNotEqual(naming.revision(), was)
        # The clip that plays another pattern, the chain, the scene's own settings and the song's are as they were.
        self.assertEqual((other.revision(), chain.revision(), scene.revision(), document.song().revision()), revisions)
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
        chain = document.setlist().get_chain(SHARED)
        self.assertTrue(chain.names_item(section=Section.ARPS, name=SHARED))
        self.assertTrue(chain.names_item(section=Section.AUTO_RATCHETS, name=SHARED))
        self.assertFalse(chain.names_item(section=Section.ARPS, name=TUNE))
        self.assertFalse(chain.names_item(section=Section.PATTERNS, name=SHARED))
        self.assertIsInstance(chain, Chain)

    def test_a_clip_that_morphs_to_a_pattern_names_it_too(self):
        document = song_with_every_reference()
        self.assertEqual(document.song().get_scene(FIRST).clip_slots_naming(section=Section.PATTERNS, name=ANSWER), [LEAD, BASS])
        self.assertEqual(document.song().get_scene(SECOND).clip_slots_naming(section=Section.PATTERNS, name=ANSWER), [])

    def test_a_song_with_no_groove_of_its_own_names_the_default_groove(self):
        document = song_with_one_name_for_everything()
        song = document.song()
        self.assertTrue(song.names_item(section=Section.GROOVES, name=DEFAULT_GROOVE))
        self.assertEqual(uses_of(setlist=document.setlist(), section=Section.GROOVES, name=DEFAULT_GROOVE), uses_of(setlist=Document().setlist(), section=Section.GROOVES, name=DEFAULT_GROOVE))
        document.set_groove_name(SHARED)
        self.assertFalse(song.names_item(section=Section.GROOVES, name=DEFAULT_GROOVE))
        self.assertTrue(song.names_item(section=Section.GROOVES, name=SHARED))
        self.assertEqual(uses_of(setlist=document.setlist(), section=Section.GROOVES, name=DEFAULT_GROOVE), [])

    def test_uses_are_listed_songs_first_then_scenes_tracks_clips_and_chains(self):
        document = song_with_every_reference()
        song_name = document.current_song_name()
        uses = uses_of(setlist=document.setlist(), section=Section.GROOVES, name=SHUFFLE)
        self.assertEqual(len(uses), GROOVE_USES)
        self.assertIn(song_name, uses[FIRST])
        self.assertIn(CHORUS, uses[SECOND])
        self.assertIn(BASS, uses[-1])
        # Nothing names a song, and nothing in a set names a track but the clips of the track's own song.
        self.assertEqual(uses_of(setlist=document.setlist(), section=Section.SONGS, name=song_name), [])
        self.assertEqual(len(grabbers(song=document.song(), song_name=song_name, track=LEAD)), ONE_USE)

    def test_in_every_example_what_uses_an_item_is_what_its_rename_changes(self):
        shared = [section for section in SETLIST_SECTIONS if section != Section.SONGS]
        for path in EXAMPLES:
            document = Document.load(path)
            setlist = document.setlist()
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


if __name__ == '__main__':
    unittest.main()
