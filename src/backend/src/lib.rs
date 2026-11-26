// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! llamatron's backend: the built-in synths, FluidSynth, the MIDI sender and the sound card, which llamatron runs on
//! threads of its own, and which the llamatron-backend program runs for any other front end.

pub mod audio;
pub mod daemon;
pub mod drums;
pub mod dsp;
pub mod engine;
pub mod fluid;
pub mod protocol;
pub mod sender;
pub mod voice;
