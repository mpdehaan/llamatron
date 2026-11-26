// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! llamatron's tracker: the text UI's pages, dialogs and keys, the document it edits with undo, and real-time playback.

pub mod app;
pub mod chord_text;
pub mod chord_tones;
pub mod components;
pub mod document;
pub mod drawing;
pub mod everywhere;
pub mod exporting;
pub mod forms;
pub mod generated;
pub mod heard_chords;
pub mod history;
pub mod instrument_sound;
pub mod keys;
pub mod keyswitches;
pub mod lengths;
pub mod msgpack;
pub mod named_edits;
pub mod page;
pub mod patterns;
pub mod realtime;
pub mod scene_notes;
pub mod screens;
pub mod settings;
pub mod sound_spec;
pub mod style;
pub mod svg;
pub mod terminal;
pub mod text;
pub mod themes;
pub mod tour;
pub mod uses;
pub mod version;
pub mod visualizers;
pub mod voice_leading;
pub mod wav;

pub use generated::keybindings;
