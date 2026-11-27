// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! llamatron's engine: the realizer that plays a song into clips, its generators, and the timing that turns a clip's
//! positions into notes with exact times.

pub mod chord_source;
pub mod clip;
pub mod clip_player;
pub mod drift;
pub mod error;
pub mod generators;
pub mod grab_source;
pub mod groove;
pub mod keyswitch;
pub mod morph;
pub mod order;
pub mod pattern_player;
pub mod positions;
pub mod realizer;
pub mod registers;
pub mod shapes;
pub mod sound;
pub mod statements;
pub mod tables;
pub mod timing;
pub mod tune_source;
