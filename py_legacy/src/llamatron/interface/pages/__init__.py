# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The pages as presenters: what each page shows and does, as a form of the forms' nodes (interface/forms/), built from the
set as it is now, with nothing of how it looks or of Textual. The tracker shows a presenter's form on a page of its own, which
hands it the page to ask through and what only the tracker can do, such as opening a set.

- generators, generator_kinds: the Generators page, every generator under a heading for its type, and every kind of
  generator with its section and what it is called.
- folder_list: the Open page, a folder's folders and the files it shows.
- generator_list, chain: the list of generators a Generators field opens, and the chain editor's steps.
- pattern_list: the Patterns page, its tabs by group and each tab's rows.
- scale_list, instrument_list, groove_list, song_list: the Scales, Instruments, Grooves and Songs pages, each its columns,
  its rows as plain values, the place ENTER opens and what adding does.
- places: where a page is, as a value, which the tracker's site map turns into its page.
- asking: asking for what a field needs beyond a line of text, such as a time signature.
- clip: the clip page, one clip's patterns and settings.
- draws: the Draws page, the song's eight draws over their strips.
- file_global: the File/Global page, the set's own settings.
- generator, page_view_fields: one of the set's generators' page, its view's settings, and those fields made for a page that
  asks for their dialogs.
- instrument: one instrument's page, where it plays and how loud.
- scale: one scale's page, its name, root and kind, and its notes.
- scene: the Scene page, one scene's settings.
- song: the Song page, one song's settings.
- track: the Track editor, one track's settings and its built-in generators.
- time_field, octave_field, velocity_fields, shape_fields, drift_values, section_table: the fields several pages share, a
  time, an octave, a velocity and its ramps, a shape, a drift's values and a table of a section's values.
- generator_names, generators_field, groove_choice: a generator's name as lists show it, the Generators field, which asks
  its page to open the list that edits it, and a scene's or a track's Groove.
- statements: Bypass When, a table of statements about the draws, and a scene's or a clip's sets and adds.
- view_fields, built_in_tab, arrange_tabs, built_in_place: a generator's settings from its view, a built-in generator's
  tab, a clip's tabs, and where a built-in generator is; progression_field, restart_field, guitar_bar_field: a generator's
  progression, Restart and guitar bar.
- uses: what uses a pattern, a scale or a generator, what grabs, and the scenes that never end.
- visualizer_fields: the fields that choose the visualizer's modes, which the File/Global and Song pages share.
"""
