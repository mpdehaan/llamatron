// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A clip's notes as they sound (the Python realtime/render_process/clip_notes.py), read from its events counted from its
//! scene's start: what the green light after a track's name asks, what the visualizer hears, and what sounds at a moment
//! where a clip is cut.

use crate::realtime::timeline::{Playing, NOTE_OFF, NOTE_ON};

/// A note of a clip as the visualizer hears it: its start and end in seconds from the scene's start, its number and
/// velocity.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct HeardClipNote {
    pub on: f64,
    pub off: f64,
    pub number: i64,
    pub velocity: i64,
}

/// A note's port, channel and number, which say which note off ends it.
type NoteKey = (String, i64, i64);

/// Each note on with its note off, number and velocity, in the order the notes start, keyswitches left out.
pub fn heard_notes(events: &[Playing]) -> Vec<HeardClipNote> {
    let mut notes = Vec::new();
    let mut open: Vec<(NoteKey, (f64, i64))> = Vec::new();
    for event in events.iter().filter(|event| !event.switch) {
        let key = (event.port.clone(), event.channel, event.number);
        if event.kind == NOTE_ON {
            open.retain(|(held, _)| *held != key);
            open.push((key, (event.seconds, event.value)));
        } else if event.kind == NOTE_OFF {
            if let Some(place) = open.iter().position(|(held, _)| *held == key) {
                let (_, (on, velocity)) = open.remove(place);
                notes.push(HeardClipNote {
                    on,
                    off: event.seconds,
                    number: event.number,
                    velocity,
                });
            }
        }
    }
    notes.sort_by(|a, b| {
        (a.on, a.off, a.number, a.velocity)
            .partial_cmp(&(b.on, b.off, b.number, b.velocity))
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    notes
}

/// Whether a note of the clip sounds at a moment counted from the scene's start.
pub fn is_sounding(events: &[Playing], elapsed: f64) -> bool {
    heard_notes(events).iter().any(|note| note.on <= elapsed && note.off > elapsed)
}

/// The notes heard between two moments counted from the scene's start: those that started after since and by until, and
/// those still sounding at until; only notes that have started are heard.
pub fn heard(events: &[Playing], since: f64, until: f64) -> (Vec<HeardClipNote>, Vec<HeardClipNote>) {
    let notes = heard_notes(events);
    let started = notes.iter().filter(|note| note.on > since && note.on <= until).copied().collect();
    let held = notes.iter().filter(|note| note.on <= since && note.off > until).copied().collect();
    (started, held)
}

/// The port, channel and number of every note that has started and not ended at a moment, for cutting the clip there.
pub fn sounding_across(events: &[Playing], elapsed: f64) -> Vec<(String, i64, i64)> {
    let mut notes: Vec<(String, i64, i64)> = Vec::new();
    for event in events {
        if event.seconds >= elapsed {
            break;
        }
        let key = (event.port.clone(), event.channel, event.number);
        if event.kind == NOTE_ON {
            if !notes.contains(&key) {
                notes.push(key);
            }
        } else if event.kind == NOTE_OFF {
            notes.retain(|held| *held != key);
        }
    }
    notes.sort();
    notes
}
