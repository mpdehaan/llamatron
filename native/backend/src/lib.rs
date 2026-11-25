// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! llamatron's backend as a library: the built-in synths, FluidSynth, the MIDI sender and the sound card, which
//! llamatron2 runs on threads of its own process, and which the llamatron-backend program runs for the Python tracker and
//! any other front end, speaking MessagePack over its standard input and output. The architecture is described for people
//! in docs/BACKEND.md.

pub mod audio;
pub mod daemon;
pub mod drums;
pub mod dsp;
pub mod engine;
pub mod fluid;
pub mod protocol;
pub mod sender;
pub mod voice;
