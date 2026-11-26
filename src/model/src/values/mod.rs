// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The music values (the Python model/values/): notes, rests, degrees, chords, scales, time signatures and what a place in a
//! clip holds, all immutable.

pub mod chord;
pub mod generated;
pub mod note;
pub mod position;
pub mod scale;
pub mod time_signature;
