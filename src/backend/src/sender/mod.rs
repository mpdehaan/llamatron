// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The real-time sender: the tracker's events, sent on time through MIDI ports, the built-in synths and FluidSynth, on a
//! thread of its own (the Python Realtime Sender Process, which this replaces). The engine (engine.rs) holds the events and
//! knows what sounds; the outputs (outputs.rs) are the ports; this module is the thread's loop and the records the tracker
//! sends events as.

pub mod engine;
pub mod outputs;

#[cfg(target_os = "macos")]
pub mod coremidi;

use crate::audio::clock;
use engine::{SenderEngine, Sent};
use std::sync::mpsc::{Receiver, RecvTimeoutError, Sender};
use std::time::Duration;

/// How long before an event is due the immediate loop stops sleeping and spins, and how long it sleeps at a time until then.
const SPIN_SECONDS: f64 = 0.0015;
const SLEEP_SLICE_SECONDS: f64 = 0.0005;
/// The records' version, first in each batch, and a record's size: seconds, tag, port, channel, kind, number, value, as the
/// tracker packs them.
const RECORDS_VERSION: u8 = 1;
const RECORD_BYTES: usize = 17;
/// Where each field of a record starts: the seconds, a double of eight bytes, first; the tag, four bytes, after them;
/// then a byte each for the port, the channel, the kind, the number and the value.
const SECONDS_BYTES: usize = 8;
const TAG_AT: usize = SECONDS_BYTES;
const TAG_BYTES: usize = 4;
const PORT_AT: usize = TAG_AT + TAG_BYTES;
const CHANNEL_AT: usize = PORT_AT + 1;
const KIND_AT: usize = CHANNEL_AT + 1;
const NUMBER_AT: usize = KIND_AT + 1;
const VALUE_AT: usize = NUMBER_AT + 1;

/// What the reader asks of the sender's thread.
pub enum SenderCommand {
    Start(Option<f64>),
    Add(Vec<Sent>),
    Forget { tag: u32, after: f64 },
    StopTag(u32),
    StopAll,
    Silence(Vec<(usize, u8)>),
    Close(Sender<Closed>),
}

/// What closing hands back: the moment the timeline was started at, and with recording what each port was given.
pub struct Closed {
    pub started: Option<f64>,
    pub recordings: Vec<Vec<(f64, Vec<u8>)>>,
}

/// The events a batch of records holds, or none for a batch of another version.
pub fn events_of(records: &[u8]) -> Vec<Sent> {
    let Some((version, body)) = records.split_first() else { return Vec::new() };
    if *version != RECORDS_VERSION {
        log::warn!("records of version {version}, which this daemon does not read");
        return Vec::new();
    }
    body.as_chunks::<RECORD_BYTES>()
        .0
        .iter()
        .map(|record| {
            let mut seconds = [0u8; SECONDS_BYTES];
            seconds.copy_from_slice(&record[..TAG_AT]);
            let mut tag = [0u8; TAG_BYTES];
            tag.copy_from_slice(&record[TAG_AT..PORT_AT]);
            Sent {
                seconds: f64::from_le_bytes(seconds),
                tag: u32::from_le_bytes(tag),
                port: record[PORT_AT] as usize,
                channel: record[CHANNEL_AT],
                kind: record[KIND_AT],
                number: record[NUMBER_AT],
                value: record[VALUE_AT],
            }
        })
        .collect()
}

/// The sender's thread: send each event when its time comes, taking the reader's commands as they arrive, until told to
/// close or the reader goes, when every sounding note is stopped first, so that nothing is left stuck on a synthesizer.
pub fn run(mut engine: SenderEngine, commands: Receiver<SenderCommand>, delay: f64) {
    let mut started = None;
    loop {
        let due = engine.next_action();
        let mut wait = None;
        if let (Some(due), true) = (due, engine.is_started()) {
            let left = due - engine.elapsed();
            if !engine.spins() {
                if left <= 0.0 {
                    engine.send_due();
                    continue;
                }
                wait = Some(left);
            } else {
                if left <= SPIN_SECONDS {
                    while engine.elapsed() < due {
                        std::hint::spin_loop();
                    }
                    engine.send_due();
                    continue;
                }
                wait = Some((left - SPIN_SECONDS).min(SLEEP_SLICE_SECONDS));
            }
        }
        let command = match wait {
            None => commands.recv().ok(),
            Some(seconds) => match commands.recv_timeout(Duration::from_secs_f64(seconds)) {
                Ok(command) => Some(command),
                Err(RecvTimeoutError::Timeout) => continue,
                Err(RecvTimeoutError::Disconnected) => None,
            },
        };
        let Some(command) = command else {
            engine.close();
            return;
        };
        match command {
            SenderCommand::Start(at) => {
                let at = at.unwrap_or_else(clock::now);
                started = Some(at);
                // Every port's timeline starts the built-in synths' delay later, so that MIDI waits for built-in sound.
                engine.start(at + delay);
            }
            SenderCommand::Add(events) => engine.add(events),
            SenderCommand::Forget { tag, after } => engine.forget(tag, after),
            SenderCommand::StopTag(tag) => engine.stop_tag(tag),
            SenderCommand::StopAll => engine.stop_all(),
            SenderCommand::Silence(channels) => engine.silence(&channels),
            SenderCommand::Close(answer) => {
                engine.close();
                let _ = answer.send(Closed {
                    started,
                    recordings: engine.recordings(),
                });
                return;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use engine::{NOTE_OFF, NOTE_ON};
    use outputs::Output;

    /// The made-up note the tests send: its tag, channel, pitch and velocity, and when it starts in the record test.
    const TAG: u32 = 7;
    const CHANNEL: u8 = 2;
    const PITCH: u8 = 60;
    const VELOCITY: u8 = 100;
    const STARTS: f64 = 1.5;

    /// A record as the tracker packs it, of the made-up note's tag, port 0, channel and velocity.
    fn record(seconds: f64, kind: u8, number: u8) -> Vec<u8> {
        let mut bytes = seconds.to_le_bytes().to_vec();
        bytes.extend_from_slice(&TAG.to_le_bytes());
        bytes.extend_from_slice(&[0, CHANNEL, kind, number, VELOCITY]);
        bytes
    }

    #[test]
    fn records_read_back_as_the_tracker_packed_them() {
        let mut batch = vec![RECORDS_VERSION];
        batch.extend(record(STARTS, NOTE_ON, PITCH));
        let events = events_of(&batch);
        assert_eq!(
            events,
            vec![Sent {
                seconds: STARTS,
                tag: TAG,
                port: 0,
                channel: CHANNEL,
                kind: NOTE_ON,
                number: PITCH,
                value: VELOCITY
            }]
        );
    }

    #[test]
    fn a_stop_silences_a_sounding_note_and_forgets_what_is_still_to_come() {
        let mut engine = SenderEngine::new(
            vec![Output::Recording {
                sent: Vec::new(),
                scheduled: false,
            }],
            false,
        );
        engine.start(clock::now() - 1.0);
        engine.add(vec![Sent {
            seconds: 0.0,
            tag: 1,
            port: 0,
            channel: 0,
            kind: NOTE_ON,
            number: PITCH,
            value: VELOCITY,
        }]);
        let long_after = 50.0;
        engine.add(vec![Sent {
            seconds: long_after,
            tag: 1,
            port: 0,
            channel: 0,
            kind: NOTE_OFF,
            number: PITCH,
            value: 0,
        }]);
        engine.send_due();
        engine.stop_tag(1);
        let sent: Vec<Vec<u8>> = engine.recordings()[0].iter().map(|item| item.1.clone()).collect();
        assert_eq!(sent, vec![vec![NOTE_ON, PITCH, VELOCITY], vec![NOTE_OFF, PITCH, 0]]);
        assert_eq!(engine.next_action(), None);
    }
}
