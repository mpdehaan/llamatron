// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The sender's engine: holds the events still to send, sends each when its time comes, and knows which notes sound, so
//! that stopping anything silences it (the Python sender's engine.py and scheduled_engine.py, whose behaviour this keeps).
//!
//! Two drivers, as before. Scheduled, where every port takes a moment with each event (CoreMIDI, the built-in synths,
//! FluidSynth): each event is handed to its port HORIZON_SECONDS ahead, stamped with its moment, so that it lands on time
//! however late this thread wakes. What is handed can be taken back: a stop or an edit flushes the ports holding dropped
//! events, hands back what they keep, and undoes, latest first, what handing the dropped ones did to the notes counted as
//! sounding. One instant is uncertain, an event due within GUARD_SECONDS of a flush: a note off is sent there kept or
//! forgotten, since a second one is harmless and a lost one leaves a note stuck. Immediate, elsewhere: each event is sent
//! as its moment comes, the loop sleeping and then spinning up to it.
//!
//! Every event carries its play's tag, its scene and track, so that one clip's events can be dropped from a time on.

use crate::audio::clock;
use crate::sender::outputs::Output;
use std::cmp::Ordering;
use std::collections::{BTreeSet, BinaryHeap, HashMap};

pub const NOTE_OFF: u8 = 0x80;
pub const NOTE_ON: u8 = 0x90;
pub const CONTROL_CHANGE: u8 = 0xB0;
pub const PROGRAM_CHANGE: u8 = 0xC0;
pub const ALL_NOTES_OFF: u8 = 123;
pub const ALL_SOUND_OFF: u8 = 120;
const SILENCING_CONTROLS: [u8; 2] = [ALL_NOTES_OFF, ALL_SOUND_OFF];
const NO_VELOCITY: u8 = 0;
const HIGHEST_NOTE: u8 = 127;
pub const HORIZON_SECONDS: f64 = 0.1;
const GUARD_SECONDS: f64 = 0.001;
/// Note offs and program changes go before note ons at one instant, so that a repeated pitch is never cut by the off of the
/// note before it.
const OFFS_FIRST: u8 = 0;
const ONS_AFTER: u8 = 1;

/// One event: its seconds on the timeline, its play's tag, its port's place, and its channel, kind, number and value.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Sent {
    pub seconds: f64,
    pub tag: u32,
    pub port: usize,
    pub channel: u8,
    pub kind: u8,
    pub number: u8,
    pub value: u8,
}

impl Sent {
    /// The event's bytes: two for a program change, which has no value, three for the rest.
    pub fn data(&self) -> Vec<u8> {
        if self.kind == PROGRAM_CHANGE {
            return vec![self.kind | self.channel, self.number];
        }
        vec![self.kind | self.channel, self.number, self.value]
    }

    fn order(&self) -> u8 {
        if self.kind == NOTE_OFF || self.kind == PROGRAM_CHANGE {
            OFFS_FIRST
        } else {
            ONS_AFTER
        }
    }

    fn key(&self) -> (usize, u8, u8) {
        (self.port, self.channel, self.number)
    }
}

struct Pending {
    order: u8,
    count: u64,
    event: Sent,
}

impl Pending {
    fn key(&self) -> (f64, u8, u64) {
        (self.event.seconds, self.order, self.count)
    }
}

impl PartialEq for Pending {
    fn eq(&self, other: &Self) -> bool {
        self.cmp(other) == Ordering::Equal
    }
}

impl Eq for Pending {}

impl PartialOrd for Pending {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for Pending {
    // Reversed, so that the heap's top is the next event to send.
    fn cmp(&self, other: &Self) -> Ordering {
        let (mine, theirs) = (self.key(), other.key());
        theirs.0.total_cmp(&mine.0).then(theirs.1.cmp(&mine.1)).then(theirs.2.cmp(&mine.2))
    }
}

/// An event handed to its port, with the tag that sounded on its note before it, to undo the handing.
struct Handed {
    event: Sent,
    before: Option<u32>,
}

pub struct SenderEngine {
    outputs: Vec<Output>,
    scheduled: bool,
    pending: BinaryHeap<Pending>,
    count: u64,
    started: Option<f64>,
    sounding: HashMap<(usize, u8, u8), u32>,
    channels_used: BTreeSet<(usize, u8)>,
    handed: Vec<Handed>,
    heard_channels: BTreeSet<(usize, u8)>,
}

impl SenderEngine {
    /// An engine sending through its outputs, scheduled or immediate.
    pub fn new(outputs: Vec<Output>, scheduled: bool) -> SenderEngine {
        SenderEngine {
            outputs,
            scheduled,
            pending: BinaryHeap::new(),
            count: 0,
            started: None,
            sounding: HashMap::new(),
            channels_used: BTreeSet::new(),
            handed: Vec::new(),
            heard_channels: BTreeSet::new(),
        }
    }

    /// Take a reading of the clock as the timeline's zero.
    pub fn start(&mut self, at: f64) {
        self.started = Some(at);
    }

    pub fn is_started(&self) -> bool {
        self.started.is_some()
    }

    /// How many seconds the timeline has run.
    pub fn elapsed(&self) -> f64 {
        clock::now() - self.started.unwrap_or_else(clock::now)
    }

    /// Queue events, in any order, to be sent at their seconds.
    pub fn add(&mut self, events: Vec<Sent>) {
        for event in events {
            self.count += 1;
            self.pending.push(Pending {
                order: event.order(),
                count: self.count,
                event,
            });
        }
    }

    fn next_due(&self) -> Option<f64> {
        self.pending.peek().map(|pending| pending.event.seconds)
    }

    /// When the loop next has something to do: the next event's moment, or the horizon before it when scheduled.
    pub fn next_action(&self) -> Option<f64> {
        let due = self.next_due()?;
        if self.scheduled {
            return Some(due - HORIZON_SECONDS);
        }
        Some(due)
    }

    /// Whether the loop spins up to the next action, for an event sent the moment it is due.
    pub fn spins(&self) -> bool {
        !self.scheduled
    }

    /// Send, or hand, every event whose time has come.
    pub fn send_due(&mut self) {
        let now = self.elapsed();
        if !self.scheduled {
            self.send_until(now);
            return;
        }
        if self.handed.first().is_some_and(|handed| handed.event.seconds < now - GUARD_SECONDS) {
            self.let_go_before(now);
        }
        self.send_until(now + HORIZON_SECONDS);
    }

    fn send_until(&mut self, seconds: f64) {
        while self.pending.peek().is_some_and(|pending| pending.event.seconds <= seconds) {
            let Some(pending) = self.pending.pop() else { break };
            self.send(pending.event);
        }
    }

    /// Forget a tag's queued events from a time on, leaving what sounds alone.
    pub fn forget(&mut self, tag: u32, after: f64) {
        self.pending.retain(|pending| !(pending.event.tag == tag && pending.event.seconds >= after));
        if self.scheduled {
            self.take_back(|event| event.tag == tag && event.seconds >= after);
        }
    }

    /// Forget a tag's events and silence its sounding notes.
    pub fn stop_tag(&mut self, tag: u32) {
        if self.scheduled {
            self.take_back(|event| event.tag == tag);
        }
        self.pending.retain(|pending| pending.event.tag != tag);
        let keys: Vec<(usize, u8, u8)> = self.sounding.iter().filter(|(_, sounding)| **sounding == tag).map(|(key, _)| *key).collect();
        for key in keys {
            self.note_off(key);
        }
    }

    /// Forget everything, silence every sounding note, and send all notes off and all sound off on every channel used.
    pub fn stop_all(&mut self) {
        if self.scheduled {
            let now = self.elapsed();
            self.let_go_before(now);
            let handed_channels: BTreeSet<(usize, u8)> = self
                .handed
                .iter()
                .filter(|handed| handed.event.seconds <= now)
                .map(|handed| (handed.event.port, handed.event.channel))
                .collect();
            self.channels_used = self.heard_channels.union(&handed_channels).copied().collect();
            self.take_back(|_| true);
            self.heard_channels.clear();
        }
        self.pending.clear();
        let keys: Vec<(usize, u8, u8)> = self.sounding.keys().copied().collect();
        for key in keys {
            self.note_off(key);
        }
        for (port, channel) in std::mem::take(&mut self.channels_used) {
            for number in SILENCING_CONTROLS {
                self.outputs[port].send(&[CONTROL_CHANGE | channel, number, 0]);
            }
        }
    }

    /// A note off for every note, then all notes off and all sound off, on each (port, channel): the emergency stop.
    pub fn silence(&mut self, channels: &[(usize, u8)]) {
        for (port, channel) in channels {
            if *port >= self.outputs.len() {
                continue;
            }
            for number in 0..=HIGHEST_NOTE {
                self.sounding.remove(&(*port, *channel, number));
                self.outputs[*port].send(&[NOTE_OFF | channel, number, NO_VELOCITY]);
            }
            for number in SILENCING_CONTROLS {
                self.outputs[*port].send(&[CONTROL_CHANGE | channel, number, 0]);
            }
        }
        if self.scheduled {
            let now = self.elapsed();
            let later: Vec<Sent> = self
                .handed
                .iter()
                .filter(|handed| handed.event.seconds > now && channels.contains(&(handed.event.port, handed.event.channel)))
                .map(|handed| handed.event)
                .collect();
            for event in later {
                self.note_sounding(&event);
            }
        }
    }

    /// Stop everything and close the outputs.
    pub fn close(&mut self) {
        self.stop_all();
        for output in self.outputs.iter_mut() {
            output.close();
        }
    }

    /// What each recording output was given, in the order of the ports: every (seconds, bytes).
    pub fn recordings(&self) -> Vec<Vec<(f64, Vec<u8>)>> {
        self.outputs.iter().map(Output::recorded).collect()
    }

    fn send(&mut self, event: Sent) {
        if self.scheduled {
            self.handed.push(Handed {
                event,
                before: self.sounding.get(&event.key()).copied(),
            });
            self.note_sounding(&event);
            let at = self.started.unwrap_or(0.0) + event.seconds;
            self.outputs[event.port].send_at(&event.data(), at);
            return;
        }
        self.note_sounding(&event);
        self.channels_used.insert((event.port, event.channel));
        self.outputs[event.port].send(&event.data());
    }

    fn note_sounding(&mut self, event: &Sent) {
        if event.kind == NOTE_ON {
            self.sounding.insert(event.key(), event.tag);
        } else if event.kind == NOTE_OFF {
            self.sounding.remove(&event.key());
        }
    }

    fn note_off(&mut self, key: (usize, u8, u8)) {
        let (port, channel, number) = key;
        self.sounding.remove(&key);
        self.outputs[port].send(&[NOTE_OFF | channel, number, NO_VELOCITY]);
    }

    /// Let go of the handed events that have surely gone out, those due more than GUARD_SECONDS before now.
    fn let_go_before(&mut self, now: f64) {
        let mut kept = Vec::with_capacity(self.handed.len());
        for handed in self.handed.drain(..) {
            if handed.event.seconds >= now - GUARD_SECONDS {
                kept.push(handed);
            } else {
                self.heard_channels.insert((handed.event.port, handed.event.channel));
            }
        }
        self.handed = kept;
    }

    /// Flush the ports holding a handed event dropped, hand back again what is kept there, and undo, latest first, what
    /// handing the dropped events did.
    fn take_back(&mut self, drops: impl Fn(&Sent) -> bool) {
        let now = self.elapsed();
        self.let_go_before(now);
        let (dropped, kept): (Vec<Handed>, Vec<Handed>) = self.handed.drain(..).partition(|handed| drops(&handed.event));
        self.handed = kept;
        if dropped.is_empty() {
            return;
        }
        let ports: BTreeSet<usize> = dropped.iter().map(|handed| handed.event.port).collect();
        for port in &ports {
            self.outputs[*port].flush();
        }
        let started = self.started.unwrap_or(0.0);
        for handed in &self.handed {
            let event = handed.event;
            if ports.contains(&event.port) && (event.seconds > now + GUARD_SECONDS || event.kind == NOTE_OFF) {
                self.outputs[event.port].send_at(&event.data(), started + event.seconds);
            }
        }
        for handed in dropped.iter().rev() {
            self.undo(handed, now);
        }
    }

    /// Undo what handing a dropped event did to the notes sounding, and send a note off for a note on or off of the
    /// uncertain instant.
    fn undo(&mut self, handed: &Handed, now: f64) {
        let event = handed.event;
        let key = event.key();
        // A forgotten note on that still counts as sounding, or a forgotten note off whose note no longer does and whose moment
        // is surely still to come, gives the note back the tag it had before.
        let started_it = event.kind == NOTE_ON && self.sounding.get(&key) == Some(&event.tag);
        let ended_it = event.kind == NOTE_OFF && !self.sounding.contains_key(&key) && event.seconds > now + GUARD_SECONDS;
        if started_it || ended_it {
            self.restore_sounding(key, handed.before);
        }
        if (event.kind == NOTE_ON || event.kind == NOTE_OFF) && event.seconds <= now + GUARD_SECONDS {
            self.outputs[event.port].send(&[NOTE_OFF | event.channel, event.number, NO_VELOCITY]);
        }
    }

    fn restore_sounding(&mut self, key: (usize, u8, u8), tag: Option<u32>) {
        match tag {
            Some(tag) => {
                self.sounding.insert(key, tag);
            }
            None => {
                self.sounding.remove(&key);
            }
        }
    }
}
