#!/usr/bin/env python3
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
"""Takes the tracker's screenshots for GUIDE.md and README.md, as SVG files that GitHub shows.

Run from the top folder:

    .venv/bin/python internal_tools/make_screenshots.py

It opens examples/by_genre/electronic/minimal_techno.yml in the real tracker with no terminal, presses the keys that
reach each screen in SHOTS, and writes docs/screenshots/<name>.svg, replacing the old one.
Textual draws the picture from the screen's own text and styles, so it's exactly what a terminal
of the same size shows. Run it again when a page changes or when asked, and commit the new files.
"""

import asyncio
import re
import pathlib
from dataclasses import dataclass

from llamatron.tui.app import LlamatronApp
from llamatron.tui.document import Document
from llamatron.tui.keys import Key
from llamatron.support.version import VERSION
from llamatron.tui.key_table import first_key
from llamatron.tui import keybindings
from llamatron.tui.screens.generator_pages import GENERATOR_PAGES
from llamatron.composition.file_format import Section

ROOT = pathlib.Path(__file__).resolve().parent.parent
SONG = ROOT / 'examples' / 'by_genre' / 'electronic' / 'minimal_techno.yml'
# minimal_techno has no arpeggiators, so the arpeggiator screens are shown on this one.
ARP_SONG = ROOT / 'examples' / 'learning' / '12_sailor_arpeggiator.yml'
# The demos whose pages show the advanced settings of scenes, clips, tracks and the newer generators.
SWELL_SONG = ROOT / 'examples' / 'learning' / '16_bolero_swell.yml'
STRUM_SONG = ROOT / 'examples' / 'learning' / '13_classic_strum.yml'
EUCLID_SONG = ROOT / 'examples' / 'other' / 'euclidean.yml'
PROGRESSION_SONG = ROOT / 'examples' / 'learning' / '06_chord_progression_generator.yml'
HOCKET_SONG = ROOT / 'examples' / 'learning' / '19_hocket_shanty.yml'
DRIFT_SONG = ROOT / 'examples' / 'by_genre' / 'electronic' / 'mainstreet_hoedown.yml'
DENSITY_SONG = ROOT / 'examples' / 'by_genre' / 'electronic' / 'edm_density.yml'
VOICE_LEADING_SONG = ROOT / 'examples' / 'learning' / '05_voice_leading.yml'
ARTICULATE_SONG = ROOT / 'examples' / 'learning' / '15_acid_articulate.yml'
GLIDE_SONG = ROOT / 'examples' / 'learning' / '14_acid_glide.yml'
RUSH_SONG = ROOT / 'examples' / 'learning' / '14_acid_glide.yml'
# The euclidean demo's shaker, the track with a Euclidean mask, and the progression demo's bass, a clip with a chain, by their places from the left.
EUCLID_TRACK_PLACE = 5
CHAINED_TRACK_PLACE = 4
FOLDER = ROOT / 'docs' / 'screenshots'
SUFFIX = '.svg'
FILE_ENCODING = 'utf-8'
# The terminal the screenshots show: wider than the 80 by 24 every page fits, so that the Arrange grid shows more tracks.
# Wide enough for a 16-step pattern in one block, which the user asked for after seeing them wrap.
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
    # Tab opens the rows under the roll, PgDn jumps from heading to heading (Basics, Chord, Timing, Advanced, CCs, Reg. Apply, Reg. Mod), Space opens the section and Down goes to its first row.
    Shot(name='pattern_editor_advanced', keys=[keybindings.MainPage.PATTERNS, Key.DOWN, Key.DOWN, Key.ENTER, keybindings.PatternEditor.TO_EDITOR, *[Key.PAGE_DOWN] * 4, Key.SPACE, Key.DOWN]),
    # The Chord section's heading is the second: Space opens it, Down reaches the Chord row and Enter opens the Chord Selector, where Right twice reaches the scales and Down and Enter open the flyout of Common.
    Shot(name='chord_selector', keys=[keybindings.MainPage.PATTERNS, Key.DOWN, Key.DOWN, Key.ENTER, keybindings.PatternEditor.TO_EDITOR, Key.PAGE_DOWN, Key.PAGE_DOWN, Key.SPACE, Key.DOWN, Key.ENTER, Key.RIGHT, Key.RIGHT, Key.DOWN, Key.ENTER]),
    Shot(name='pattern_editor_cc', keys=[keybindings.MainPage.PATTERNS, Key.DOWN, Key.DOWN, Key.ENTER, keybindings.PatternEditor.TO_EDITOR, *[Key.PAGE_DOWN] * 5, Key.SPACE, Key.DOWN]),
    Shot(name='pattern_editor_registers', keys=[keybindings.MainPage.PATTERNS, Key.DOWN, Key.DOWN, Key.ENTER, keybindings.PatternEditor.TO_EDITOR, *[Key.PAGE_DOWN] * 6, Key.SPACE, Key.DOWN]),
    Shot(name='pattern_editor_register_changes', keys=[keybindings.MainPage.PATTERNS, Key.DOWN, Key.DOWN, Key.ENTER, keybindings.PatternEditor.TO_EDITOR, *[Key.PAGE_DOWN] * 7, Key.SPACE, Key.DOWN]),
    # With Real Time on, Up from the first scene's name reaches Arrange's corner, and Right the first track's name.
    Shot(name='track_editor', keys=[keybindings.MainPage.ARRANGE, Key.UP, Key.RIGHT, Key.ENTER]),
    Shot(name='generators', keys=[keybindings.MainPage.GENERATORS]),
    Shot(name='arp_editor', generator=Section.ARPS, keys=[], song=ARP_SONG),
    # Offsets is the sixth setting of an arpeggiator, after its Name, and Enter on it opens the offsets editor.
    Shot(name='offsets_editor', generator=Section.ARPS, keys=[Key.DOWN, Key.DOWN, Key.DOWN, Key.DOWN, Key.DOWN, Key.ENTER], song=ARP_SONG),
    Shot(name='auto_ratchet_editor', generator=Section.AUTO_RATCHETS, keys=[]),
    Shot(name='chains', keys=[keybindings.MainPage.CHAINS]),
    Shot(name='chain_editor', keys=[keybindings.MainPage.CHAINS, Key.ENTER]),
    Shot(name='grooves', keys=[keybindings.MainPage.GROOVES]),
    Shot(name='groove_editor', keys=[keybindings.MainPage.GROOVES, Key.DOWN, Key.DOWN, Key.ENTER]),
    Shot(name='registers', keys=[keybindings.MainPage.REGISTERS]),
    Shot(name='arrange', keys=[keybindings.MainPage.ARRANGE]),
    # The details view on the hoedown, whose clips run chains, and Tab locked into the first clip's details, the user's ask for Arrange's page.
    Shot(name='arrange_details', keys=[keybindings.MainPage.ARRANGE, keybindings.ArrangePage.SHOW_DETAILS], song=DRIFT_SONG),
    Shot(name='arrange_details_locked', keys=[keybindings.MainPage.ARRANGE, keybindings.ArrangePage.SHOW_DETAILS, Key.RIGHT, Key.DOWN, keybindings.ArrangePage.INTO_DETAILS],
         song=DRIFT_SONG),
    # Scene View, P on a scene's name, as written and then as played.
    Shot(name='scene_view', keys=[keybindings.MainPage.ARRANGE, keybindings.ArrangePage.SCENE_VIEW], song=DENSITY_SONG),
    Shot(name='scene_view_played', keys=[keybindings.MainPage.ARRANGE, keybindings.ArrangePage.SCENE_VIEW, keybindings.ArrangePage.TO_PLAYED], song=DENSITY_SONG),
    Shot(name='scene', keys=[keybindings.MainPage.ARRANGE, Key.ENTER]),
    Shot(name='clip', keys=[keybindings.MainPage.ARRANGE, Key.RIGHT, Key.ENTER]),
    # The settings pages' sections, opened with PgDn to a heading and Space: a scene's Swell, a clip's Strum, a track's Euclid.
    Shot(name='scene_swell', keys=[keybindings.MainPage.ARRANGE, Key.ENTER, Key.PAGE_DOWN, Key.PAGE_DOWN, Key.SPACE], song=SWELL_SONG),
    Shot(name='scene_density', keys=[keybindings.MainPage.ARRANGE, Key.ENTER, Key.PAGE_DOWN, Key.SPACE], song=DENSITY_SONG),
    Shot(name='clip_strum', keys=[keybindings.MainPage.ARRANGE, Key.DOWN, Key.RIGHT, Key.ENTER, Key.PAGE_DOWN, Key.SPACE], song=STRUM_SONG),
    Shot(name='track_euclid', keys=[keybindings.MainPage.ARRANGE, Key.UP, *[Key.RIGHT] * EUCLID_TRACK_PLACE, Key.ENTER, Key.PAGE_DOWN, Key.SPACE], song=EUCLID_SONG),
    Shot(name='instruments', keys=[keybindings.MainPage.INSTRUMENTS]),
    Shot(name='instrument_editor', keys=[keybindings.MainPage.INSTRUMENTS, Key.ENTER]),
    Shot(name='progression_editor', generator=Section.PROGRESSIONS, keys=[], song=PROGRESSION_SONG),
    Shot(name='chords_editor', generator=Section.PROGRESSIONS, keys=[Key.DOWN, Key.DOWN, Key.ENTER], song=PROGRESSION_SONG),
    Shot(name='drift_editor', generator=Section.DRIFTS, keys=[], song=DRIFT_SONG),
    Shot(name='hocket_editor', generator=Section.HOCKETS, keys=[], song=HOCKET_SONG),
    Shot(name='voice_leading_editor', generator=Section.VOICE_LEADINGS, keys=[], song=VOICE_LEADING_SONG),
    Shot(name='strum_editor', generator=Section.STRUMS, keys=[], song=STRUM_SONG),
    Shot(name='euclid_editor', generator=Section.EUCLIDS, keys=[], song=EUCLID_SONG),
    Shot(name='density_editor', generator=Section.DENSITIES, keys=[], song=DENSITY_SONG),
    Shot(name='swell_editor', generator=Section.SWELLS, keys=[], song=SWELL_SONG),
    Shot(name='articulate_editor', generator=Section.ARTICULATES, keys=[], song=ARTICULATE_SONG),
    Shot(name='glide_editor', generator=Section.GLIDES, keys=[], song=GLIDE_SONG),
    Shot(name='shorten_editor', generator=Section.SHORTENS, keys=[], song=GLIDE_SONG),
    Shot(name='rush_editor', generator=Section.RUSHES, keys=[], song=RUSH_SONG),
    Shot(name='drag_editor', generator=Section.DRAGS, keys=[], song=RUSH_SONG),
    Shot(name='chain_list', keys=[keybindings.MainPage.ARRANGE, *[Key.RIGHT] * CHAINED_TRACK_PLACE, Key.ENTER, Key.DOWN, Key.DOWN, Key.DOWN, Key.ENTER], song=PROGRESSION_SONG),
]


async def take(shot):
    """Open the song, press the shot's keys and return the screen as SVG."""
    app = LlamatronApp(document=Document.load(str(shot.song)))
    async with app.run_test(size=(COLUMNS, ROWS)) as pilot:
        await pilot.pause()
        if shot.generator is not None:
            await pilot.press(first_key(keybindings.MainPage.GENERATORS))
            await pilot.pause()
            kind = GENERATOR_PAGES[shot.generator].kind
            place = next(place for place, (each, _) in enumerate(app.screen.generators()) if each == kind)
            for _ in range(place):
                await pilot.press(Key.DOWN)
            await pilot.press(Key.ENTER)
            await pilot.pause()
        for name in shot.keys:
            await pilot.press(name if isinstance(name, str) else first_key(name))
            await pilot.pause()
        svg = app.export_screenshot(title=TITLE).replace(VERSION, VERSION_PLACEHOLDER)
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
