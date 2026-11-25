// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The daemon's edge with the sound card and the computer: the output stream and its callback (player.rs), the clock notes
//! are timed on (clock.rs), and WAV files (wav.rs).

pub mod clock;
pub mod player;
pub mod wav;
