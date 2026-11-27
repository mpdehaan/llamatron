// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A built-in instrument's voice of swappable parts, as the Instrument page shows them: the oscillators and their wavetables,
//! the three envelopes, the filter or low-pass gate, the LFOs and the mod matrix, the effects, and the patch that plays them
//! together.

pub mod acid;
pub mod amp;
pub mod asheville;
pub mod blep;
pub mod bucket_brigade;
pub mod drive;
pub mod effects;
pub mod envelopes;
pub mod filters;
pub mod gate;
pub mod modulation;
pub mod multitap;
pub mod oscillators;
pub mod oversample;
pub mod patch;
pub mod sallen_key;
pub mod tables;
