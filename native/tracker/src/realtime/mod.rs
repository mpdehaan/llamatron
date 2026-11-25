// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Real-time playback (the Python realtime/ and interface/tracker/transport.py): a song rendered and laid out as timed MIDI
//! events, launched scene by scene and clip by clip by the player, and sent on time by llamatron-backend, the daemon that
//! holds the MIDI ports, the built-in synths and FluidSynth.

pub mod clip_notes;
pub mod player;
pub mod row_clock;
pub mod score;
pub mod timeline;
