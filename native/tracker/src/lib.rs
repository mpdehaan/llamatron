// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! llamatron2's tracker: the text UI's pages, dialogs and keys, ported from the Python package interface/tracker/ and held
//! to it by the screen tour (internal_tools/compare_llamatron2.py's screens step). It is built as state, actions, update and
//! view: each page holds its state, its keys name its actions, a key press updates it, and its view is lines of styled text.

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
pub mod history;
pub mod instrument_sound;
pub mod keys;
pub mod keyswitches;
pub mod lengths;
pub mod named_edits;
pub mod page;
pub mod patterns;
pub mod screens;
pub mod settings;
pub mod sound_spec;
pub mod style;
pub mod terminal;
pub mod text;
pub mod themes;
pub mod tour;
pub mod uses;
pub mod voice_leading;
pub mod wav;

pub use generated::keybindings;
