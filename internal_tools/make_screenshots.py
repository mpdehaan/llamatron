#!/usr/bin/env python3
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Takes the tracker's screenshots for GUIDE.md and README.md, as SVG files that GitHub shows.

Run from the top folder:

    .venv/bin/python internal_tools/make_screenshots.py

It opens examples/by_genre/electronic/minimal_techno.yml in the real tracker with no terminal, presses the keys that
reach each screen in SHOTS, and writes docs/screenshots/<name>.svg, replacing the old one.
Textual draws the picture from the screen's own text and styles, so it's exactly what a terminal
of the same size shows. Run it again when a page changes or when asked, and commit the new files.
"""

import asyncio
from dataclasses import dataclass
import pathlib
import re

from llamatron.engine.generators import arp as arp_plugin, chords as chords_plugin, drift as drift_plugin, hocket as hocket_plugin, shapes as shapes_plugin
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.app import LlamatronApp
from llamatron.interface.tracker.document import Document
from llamatron.interface.tracker.key_table import first_key
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.generators import generator_pages
from llamatron.model.file import version
from llamatron.model.objects.sections import Section
from llamatron.user_strings import labels

ROOT = pathlib.Path(__file__).resolve().parent.parent
SONG = ROOT / 'examples' / 'by_genre' / 'electronic' / 'minimal_techno.yml'
# minimal_techno has no arpeggiators, so the arpeggiator screens are shown on the chain demo, whose arpeggiators stay in the
# set's list, and on its arpeggiator with offsets.
ARP_SONG = ROOT / 'examples' / 'learning' / '15_complex_gifts_chain.yml'
SHOWN_ARP = 'trill_in_thirds'
# The chain demo's chain the chain editor's shot shows.
SHOWN_CHAIN = 'shred'
# Offsets' place among an arpeggiator's settings, counted from its Name.
OFFSETS_PLACE = 6
# The demos whose pages show the advanced settings of scenes, clips, tracks and the newer generators.
SWELL_SONG = ROOT / 'examples' / 'learning' / '14_bolero_swell.yml'
PROGRESSION_SONG = ROOT / 'examples' / 'learning' / '06_chord_progression_generator.yml'
# The Chords generator of that song the Chords shots show, in Progression mode.
SHOWN_PROGRESSION = 'pop'
# The Chords field's place among a Chords generator's settings, counted from its Name.
CHORDS_PLACE = 4
HOCKET_SONG = ROOT / 'examples' / 'learning' / '17_hocket_shanty.yml'
DRIFT_SONG = ROOT / 'examples' / 'by_genre' / 'rock' / 'volcano.yml'
DENSITY_SONG = ROOT / 'examples' / 'by_genre' / 'electronic' / 'edm_density.yml'
GLIDE_SONG = ROOT / 'examples' / 'learning' / '12_acid_glide.yml'
# Where the acid glide's first clip with its Timing tab on stands: the second scene, and the acid track, fourth from the left.
GLIDE_TRACK_PLACE = 4
# The Timing tab's place on the clip page's row of tabs, after Basics, Chords, Arp, Guitarify and User.
TIMING_TAB_PLACE = 5
# The progression demo's pad in its "pop, voice-led" scene, a clip with a chain, by its scene's place from the top and its
# track's from the left, and the User tab, which lists its chains, by its place on the clip page's row of tabs.
CHAINED_SCENE_PLACE = 5
CHAINED_TRACK_PLACE = 5
USER_TAB_PLACE = 4
FOLDER = ROOT / 'docs' / 'screenshots'
# What the song wizard's shots choose, and the player and the section whose panels are shown.
WIZARD_GENRE = 'rock'
WIZARD_SUBGENRE = 'folk rock'
# The panel of the melody of one kind of section in that subgenre.
WIZARD_SECTION_MELODY = 'Chorus'
WIZARD_SEED = 7
WIZARD_PLAYER = 'rhythm guitar'
WIZARD_SECTION = 'verse-1'
SUFFIX = '.svg'
FILE_ENCODING = 'utf-8'
# The terminal the screenshots show: wider than the 80 by 24 every page fits, so that the Arrange grid shows more tracks.
# Wide enough for a 16-step pattern in one block, since a narrower shot wrapped them.
COLUMNS = 112
ROWS = 32
# The name in the picture's title bar.
TITLE = 'llamatron'
MSG_WROTE = 'wrote {path}'
# Written in place of the version, so that a version bump alone changes no screenshot.
VERSION_PLACEHOLDER = '$VERSION'
# Rich names the SVG's styles after a hash of the whole screen, version included, so a bump alone would change every file;
# the shot's name takes the hash's place so that only a page that changed changes.
HASHED_ID = r'terminal-\d+'
SHOT_ID = 'terminal-{name}'


@dataclass(slots=True, kw_only=True)
class Shot:
    """One screenshot: its file name, the keys that reach the screen from the main screen, and the song it shows."""

    name: str
    keys: list
    song: pathlib.Path = SONG
    # A generator section whose first generator the Generators page opens before the keys are pressed, since where it sits on
    # the one list depends on the song.
    generator: str = None
    # The name of the generator of that section to open, or None for its first.
    generator_name: str = None
    # A panel of the song wizard, by its name in the wizard's tree: the wizard is opened, the wizard's genre, subgenre and seed are
    # chosen so that the shot is the same every time, and the tree's cursor goes to the panel.
    wizard: str = None


SHOTS = [
    Shot(name='main', keys=[]),
    Shot(name='file', keys=[keybindings.MainPage.FILE]),
    Shot(name='songs', keys=[keybindings.MainPage.SONGS]),
    Shot(name='song', keys=[keybindings.MainPage.SONGS, Key.ENTER]),
    Shot(name='scales', keys=[keybindings.MainPage.SCALES]),
    Shot(name='scale', keys=[keybindings.MainPage.SCALES, Key.ENTER]),
    Shot(name='patterns', keys=[keybindings.MainPage.PATTERNS]),
    # The third pattern of the song is a bass line, which shows more rows than a drum pattern.
    Shot(name='pattern_editor', keys=[keybindings.MainPage.PATTERNS, Key.DOWN, Key.DOWN, Key.ENTER]),
    Shot(name='pattern_editor_rows', keys=[keybindings.MainPage.PATTERNS, Key.DOWN, Key.DOWN, Key.ENTER, keybindings.PatternEditor.TO_EDITOR]),
    # Tab opens the rows under the roll, PgDn jumps from heading to heading (Basics, Chord, Timing, Advanced, CCs, Use Registers, Set Registers), Space opens the section and Down goes to its first row.
    Shot(name='pattern_editor_advanced', keys=[keybindings.MainPage.PATTERNS, Key.DOWN, Key.DOWN, Key.ENTER, keybindings.PatternEditor.TO_EDITOR, *[Key.PAGE_DOWN] * 4, Key.SPACE, Key.DOWN]),
    # The Chord section's heading is the second: Space opens it, Down reaches the Chord row and Enter opens the Chord Selector, where Right three times reaches the scales and Down and Enter open the flyout of Common.
    Shot(name='chord_selector', keys=[keybindings.MainPage.PATTERNS, Key.DOWN, Key.DOWN, Key.ENTER, keybindings.PatternEditor.TO_EDITOR, Key.PAGE_DOWN, Key.PAGE_DOWN, Key.SPACE, Key.DOWN, Key.ENTER, Key.RIGHT, Key.RIGHT, Key.RIGHT, Key.DOWN, Key.ENTER]),
    Shot(name='pattern_editor_cc', keys=[keybindings.MainPage.PATTERNS, Key.DOWN, Key.DOWN, Key.ENTER, keybindings.PatternEditor.TO_EDITOR, *[Key.PAGE_DOWN] * 5, Key.SPACE, Key.DOWN]),
    Shot(name='pattern_editor_registers', keys=[keybindings.MainPage.PATTERNS, Key.DOWN, Key.DOWN, Key.ENTER, keybindings.PatternEditor.TO_EDITOR, *[Key.PAGE_DOWN] * 6, Key.SPACE, Key.DOWN]),
    Shot(name='pattern_editor_register_changes', keys=[keybindings.MainPage.PATTERNS, Key.DOWN, Key.DOWN, Key.ENTER, keybindings.PatternEditor.TO_EDITOR, *[Key.PAGE_DOWN] * 7, Key.SPACE, Key.DOWN]),
    # With Real Time on, Up from the first scene's name reaches Arrange's corner, and Right the first track's name.
    Shot(name='track_editor', keys=[keybindings.MainPage.ARRANGE, Key.UP, Key.RIGHT, Key.ENTER]),
    # Space opens the Arpeggiator group, the first on the Generators page.
    Shot(name='generators', keys=[keybindings.MainPage.GENERATORS, Key.SPACE], song=ARP_SONG),
    Shot(name='arp_editor', generator=arp_plugin.SECTION, generator_name=SHOWN_ARP, keys=[], song=ARP_SONG),
    # Offsets is the sixth setting of an arpeggiator after its Name, and Enter on it opens the offsets editor.
    Shot(name='offsets_editor', generator=arp_plugin.SECTION, generator_name=SHOWN_ARP, keys=[*[Key.DOWN] * OFFSETS_PLACE, Key.ENTER], song=ARP_SONG),
    Shot(name='chain_editor', generator=Section.CHAINS, generator_name=SHOWN_CHAIN, keys=[], song=ARP_SONG),
    Shot(name='grooves', keys=[keybindings.MainPage.GROOVES]),
    Shot(name='groove_editor', keys=[keybindings.MainPage.GROOVES, Key.DOWN, Key.DOWN, Key.ENTER]),
    Shot(name='registers', keys=[keybindings.MainPage.REGISTERS]),
    Shot(name='arrange', keys=[keybindings.MainPage.ARRANGE]),
    # The details view on the hoedown, whose clips run chains, and Tab locked into the first clip's details, for Arrange's page.
    Shot(name='arrange_details', keys=[keybindings.MainPage.ARRANGE, keybindings.ArrangePage.SHOW_DETAILS], song=DRIFT_SONG),
    Shot(name='arrange_details_locked', keys=[keybindings.MainPage.ARRANGE, keybindings.ArrangePage.SHOW_DETAILS, Key.RIGHT, Key.DOWN, keybindings.ArrangePage.INTO_DETAILS],
         song=DRIFT_SONG),
    # Scene View, P on a scene's name, as written and then as played.
    Shot(name='scene_view', keys=[keybindings.MainPage.ARRANGE, keybindings.ArrangePage.SCENE_VIEW], song=DENSITY_SONG),
    Shot(name='scene_view_played', keys=[keybindings.MainPage.ARRANGE, keybindings.ArrangePage.SCENE_VIEW, keybindings.ArrangePage.TO_PLAYED], song=DENSITY_SONG),
    Shot(name='scene', keys=[keybindings.MainPage.ARRANGE, Key.ENTER]),
    Shot(name='clip', keys=[keybindings.MainPage.ARRANGE, Key.RIGHT, Key.ENTER]),
    # The settings pages' sections, opened with PgDn to a heading and Space: a scene's Velocity Ramp In, past its two tempo ramps and a clip's Strum.
    Shot(name='scene_swell', keys=[keybindings.MainPage.ARRANGE, Key.ENTER, Key.PAGE_DOWN, Key.PAGE_DOWN, Key.PAGE_DOWN, Key.SPACE], song=SWELL_SONG),
    Shot(name='scene_density', keys=[keybindings.MainPage.ARRANGE, Key.ENTER, Key.PAGE_DOWN, Key.SPACE], song=DENSITY_SONG),
    Shot(name='instruments', keys=[keybindings.MainPage.INSTRUMENTS]),
    Shot(name='instrument_editor', keys=[keybindings.MainPage.INSTRUMENTS, Key.ENTER]),
    Shot(name='chords_generator', generator=chords_plugin.SECTION, generator_name=SHOWN_PROGRESSION, keys=[], song=PROGRESSION_SONG),
    Shot(name='chords_editor', generator=chords_plugin.SECTION, generator_name=SHOWN_PROGRESSION, keys=[*[Key.DOWN] * CHORDS_PLACE, Key.ENTER], song=PROGRESSION_SONG),
    Shot(name='drift_editor', generator=drift_plugin.SECTION, keys=[], song=DRIFT_SONG),
    Shot(name='hocket_editor', generator=hocket_plugin.SECTION, keys=[], song=HOCKET_SONG),
    Shot(name='shapes_editor', generator=shapes_plugin.SECTION, keys=[], song=SWELL_SONG),
    # A clip's Timing tab: Down to the second scene, Right to the acid track's clip, ENTER opens it, Tab goes to the row of tabs
    # and Right reaches Timing.
    Shot(name='timing_editor', keys=[keybindings.MainPage.ARRANGE, Key.DOWN, *[Key.RIGHT] * GLIDE_TRACK_PLACE, Key.ENTER,
                                     keybindings.FieldPage.TO_TABS, *[Key.RIGHT] * TIMING_TAB_PLACE], song=GLIDE_SONG),
    Shot(name='chain_list', keys=[keybindings.MainPage.ARRANGE, *[Key.DOWN] * CHAINED_SCENE_PLACE, *[Key.RIGHT] * CHAINED_TRACK_PLACE, Key.ENTER,
                                 keybindings.FieldPage.TO_TABS, *[Key.RIGHT] * USER_TAB_PLACE], song=PROGRESSION_SONG),
    Shot(name='wizard_genre', wizard=labels.MSG_WIZARD_GENRE_BRANCH, keys=[]),
    Shot(name='wizard_band', wizard=labels.MSG_WIZARD_BAND_BRANCH, keys=[]),
    Shot(name='wizard_player', wizard=WIZARD_PLAYER, keys=[]),
    Shot(name='wizard_chords', wizard=labels.MSG_WIZARD_CHORDS_BRANCH, keys=[]),
    Shot(name='wizard_melody', wizard=labels.MSG_WIZARD_MELODY_BRANCH, keys=[]),
    Shot(name='wizard_hooks', wizard=labels.MSG_WIZARD_HOOKS_BRANCH, keys=[]),
    Shot(name='wizard_section_melody', wizard=WIZARD_SECTION_MELODY, keys=[]),
    # The first player's heading opened on each, to show the rows under it.
    Shot(name='wizard_riffs', wizard=labels.MSG_WIZARD_RIFFS_BRANCH, keys=[keybindings.WizardPage.INTO_FIELDS, keybindings.FieldPage.TOGGLE]),
    Shot(name='wizard_riff_assign', wizard=labels.MSG_WIZARD_RIFF_ASSIGN_BRANCH, keys=[keybindings.WizardPage.INTO_FIELDS, keybindings.FieldPage.TOGGLE]),
    Shot(name='wizard_section_players', wizard=labels.MSG_WIZARD_SECTION_PLAYERS_BRANCH, keys=[keybindings.WizardPage.INTO_FIELDS, keybindings.FieldPage.TOGGLE]),
    Shot(name='wizard_form', wizard=labels.MSG_WIZARD_FORM_BRANCH, keys=[]),
    Shot(name='wizard_section', wizard=WIZARD_SECTION, keys=[]),
    Shot(name='wizard_apply', wizard=labels.MSG_WIZARD_CREATE_BRANCH, keys=[]),
]


async def open_wizard_panel(*, app, pilot, panel):
    """Open the song wizard, choose the genre, subgenre and seed every wizard shot shares, and put the tree's cursor on a panel."""
    await pilot.press(first_key(keybindings.MainPage.WIZARD))
    await pilot.pause()
    choices = app.screen.get_choices()
    choices.set_genre(WIZARD_GENRE)
    choices.set_subgenre(WIZARD_SUBGENRE)
    choices.set_seed(WIZARD_SEED)
    # A key each way draws the tree again with what was chosen.
    await pilot.press(Key.DOWN)
    await pilot.press(Key.UP)
    place = [branch.name() for _, branch in app.screen.rows()].index(panel)
    for _ in range(place):
        await pilot.press(Key.DOWN)
    await pilot.pause()


async def take(shot):
    """Open the song, press the shot's keys and return the screen as SVG."""
    app = LlamatronApp(document=Document.load(str(shot.song)))
    async with app.run_test(size=(COLUMNS, ROWS)) as pilot:
        await pilot.pause()
        if shot.generator is not None:
            await pilot.press(first_key(keybindings.MainPage.GENERATORS))
            await pilot.pause()
            kind = generator_pages.LISTED_PAGES[shot.generator].kind
            found = next((each, name) for each, name in app.screen.generators() if each == kind and shot.generator_name in (None, name))
            app.screen.put_cursor_on(kind=found[0], name=found[1])
            await pilot.press(Key.ENTER)
            await pilot.pause()
        if shot.wizard is not None:
            await open_wizard_panel(app=app, pilot=pilot, panel=shot.wizard)
        for name in shot.keys:
            await pilot.press(name if isinstance(name, str) else first_key(name))
            await pilot.pause()
        svg = app.export_screenshot(title=TITLE).replace(version.VERSION, VERSION_PLACEHOLDER)
        return re.sub(HASHED_ID, SHOT_ID.format(name=shot.name), svg)


async def take_all():
    FOLDER.mkdir(parents=True, exist_ok=True)
    for shot in SHOTS:
        path = FOLDER / (shot.name + SUFFIX)
        path.write_text(await take(shot), encoding=FILE_ENCODING)
        print(MSG_WROTE.format(path=path.relative_to(ROOT)))


def main():
    asyncio.run(take_all())


if __name__ == '__main__':
    main()
