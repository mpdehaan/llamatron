// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The ports the sender sends through, each taking an event now or stamped with a moment ahead, and taking back what it
//! holds whose moment has not come:
//!
//! - Recording: keeps every message with its moment, for the tests and the recorders, as the Python sender's recording
//!   outputs do; the scheduled kind forgets on a flush what was still to come.
//! - Built in: sixteen built-in instruments a port, one a channel, played by the daemon's own engine; a note's moment
//!   reaches the engine less the delay every instrument is held back by, since the timeline starts that delay later.
//! - FluidSynth: its MIDI played by the daemon's own FluidSynth, likewise.
//! - CoreMIDI, on macOS: a destination of the computer's, each event stamped with the moment CoreMIDI delivers it; taken
//!   back by giving the port up and opening another, never by CoreMIDI's own flush, which reaches another program's
//!   destination as a system reset.
//! - midir, elsewhere: a destination sent each event as its moment comes.

use crate::audio::clock;
use crate::audio::player::{self, Command, Commands};
use crate::daemon::HitStore;
use crate::engine::{ALL_OFF, NOTE_OFF as ENGINE_NOTE_OFF, NOTE_ON as ENGINE_NOTE_ON, SCENE_STARTED as ENGINE_SCENE_STARTED};
use crate::sender::engine::{ALL_NOTES_OFF, ALL_SOUND_OFF, CONTROL_CHANGE, NOTE_OFF, NOTE_ON};
use std::sync::{Arc, Mutex};

const KIND_MASK: u8 = 0xF0;
const CHANNEL_MASK: u8 = 0x0F;
/// The controller the timeline marks a clip's start with for a built-in instrument, which restarts its LFOs.
const SCENE_STARTED: u8 = 102;
pub const INSTRUMENTS_PER_PORT: usize = 16;
const MIDI_BYTES: usize = 3;

/// What a built-in or FluidSynth port shares with the rest of the daemon: the player and the drums' hits.
#[derive(Clone)]
pub struct Shared {
    pub commands: Commands,
    pub hits: Arc<Mutex<HitStore>>,
    pub delay: f64,
    pub rate: f64,
}

impl Shared {
    fn send(&self, command: Command) {
        player::send(&self.commands, command);
    }

    fn forget_after(&self) -> f64 {
        clock::now() - self.delay
    }
}

pub enum Output {
    Recording {
        sent: Vec<(f64, Vec<u8>)>,
        scheduled: bool,
    },
    BuiltIn {
        first: usize,
        shared: Shared,
    },
    Fluid {
        shared: Shared,
    },
    #[cfg(target_os = "macos")]
    CoreMidi(crate::sender::coremidi::CoreMidiOutput),
    #[cfg(not(target_os = "macos"))]
    Midir(midir::MidiOutputConnection),
}

impl Output {
    /// Send a message now.
    pub fn send(&mut self, data: &[u8]) {
        match self {
            Output::Recording { sent, .. } => sent.push((clock::now(), data.to_vec())),
            #[cfg(target_os = "macos")]
            Output::CoreMidi(port) => port.send_now(data),
            #[cfg(not(target_os = "macos"))]
            Output::Midir(connection) => {
                if let Err(problem) = connection.send(data) {
                    log::warn!("a MIDI message could not be sent: {problem}");
                }
            }
            _ => self.send_at(data, clock::now()),
        }
    }

    /// Hand a message over to be sent at a reading of the clock, or at once when that moment has passed.
    pub fn send_at(&mut self, data: &[u8], at: f64) {
        match self {
            Output::Recording { sent, scheduled } => {
                let moment = if *scheduled { at.max(clock::now()) } else { clock::now() };
                sent.push((moment, data.to_vec()));
            }
            Output::BuiltIn { first, shared } => built_in_note(*first, shared, data, at),
            Output::Fluid { shared } => {
                let [status, first, second] = padded(data);
                shared.send(Command::Midi {
                    when: at - shared.delay,
                    status,
                    first,
                    second,
                });
            }
            #[cfg(target_os = "macos")]
            Output::CoreMidi(port) => port.send_at(data, at),
            #[cfg(not(target_os = "macos"))]
            Output::Midir(_) => self.send(data),
        }
    }

    /// Take back every message held whose moment has not come.
    pub fn flush(&mut self) {
        match self {
            Output::Recording { sent, .. } => {
                let now = clock::now();
                sent.retain(|item| item.0 <= now);
            }
            Output::BuiltIn { first, shared } => {
                let last = *first + INSTRUMENTS_PER_PORT - 1;
                shared.send(Command::Forget {
                    when: shared.forget_after(),
                    first: *first,
                    last,
                });
            }
            Output::Fluid { shared } => shared.send(Command::ForgetMidi { when: shared.forget_after() }),
            #[cfg(target_os = "macos")]
            Output::CoreMidi(port) => port.flush(),
            #[cfg(not(target_os = "macos"))]
            Output::Midir(_) => {}
        }
    }

    /// Close the port; a recording keeps only what was delivered, in the order of its moments.
    pub fn close(&mut self) {
        if let Output::Recording { sent, scheduled: true } = self {
            let now = clock::now();
            sent.retain(|item| item.0 <= now);
            sent.sort_by(|first, second| first.0.total_cmp(&second.0));
        }
    }

    /// What a recording output was given, empty for any other.
    pub fn recorded(&self) -> Vec<(f64, Vec<u8>)> {
        match self {
            Output::Recording { sent, .. } => sent.clone(),
            _ => Vec::new(),
        }
    }
}

/// A MIDI message as the built-in instruments take a note: a start, an end, every note of the instrument ending, or its
/// clip starting; any other message, such as a program change, they do not play.
fn built_in_note(first: usize, shared: &Shared, data: &[u8], at: f64) {
    let [status, number, value] = padded(data);
    let kind = status & KIND_MASK;
    let instrument = first + (status & CHANNEL_MASK) as usize;
    let when = at - shared.delay;
    let (engine_kind, pitch, velocity) = match kind {
        NOTE_ON if value > 0 => (ENGINE_NOTE_ON, number as f64, value as f64),
        NOTE_ON | NOTE_OFF => (ENGINE_NOTE_OFF, number as f64, 0.0),
        CONTROL_CHANGE if number == ALL_NOTES_OFF || number == ALL_SOUND_OFF => (ALL_OFF, 0.0, 0.0),
        CONTROL_CHANGE if number == SCENE_STARTED => (ENGINE_SCENE_STARTED, 0.0, 0.0),
        _ => return,
    };
    let mut hit = None;
    if engine_kind == ENGINE_NOTE_ON {
        if let Ok(mut hits) = shared.hits.lock() {
            hit = hits.hit(instrument, pitch, velocity, shared.rate);
        }
    }
    shared.send(Command::Note {
        when,
        kind: engine_kind,
        instrument,
        pitch,
        velocity,
        hit,
    });
}

/// A message's three bytes, a two-byte one, such as a program change, given a zero third.
fn padded(data: &[u8]) -> [u8; MIDI_BYTES] {
    let mut bytes = [0u8; MIDI_BYTES];
    for (place, byte) in data.iter().take(MIDI_BYTES).enumerate() {
        bytes[place] = *byte;
    }
    bytes
}
