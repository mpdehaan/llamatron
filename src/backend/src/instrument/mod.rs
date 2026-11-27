// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A built-in instrument, compiled from its spec: the patch that plays its voices through their swappable parts, as the
//! Instrument page shows them (the oscillators, envelopes, filters, modulation and effects, each a module of its own), and
//! the Amp each voice ends in.

pub mod amp;
pub mod patch;
