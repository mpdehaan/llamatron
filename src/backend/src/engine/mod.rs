// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The engine: notes scheduled at exact samples, played by the instruments' voices, mixed a chunk at a time and made safe.
//!
//! Everything here counts samples from the start of the stream, so that a note's place is a whole number and never
//! drifts; a note begins on its exact sample within its chunk, so a song's timing is as exact as the clock it was
//! scheduled by, whatever the chunk size. The engine is owned by the audio callback (or by the offline render, which plays
//! it the same way into a file) and allocates nothing while it plays: everything it holds is made ahead, and what it lets
//! go of is handed to the housekeeper to free, never freed in the callback.

pub mod safety;

use crate::drums::Hit;
use crate::fluid::Fluid;
use crate::voice::modulation::MOST_FRAMES;
use crate::voice::patch::{Patch, Voice};
use safety::OutputGuard;
use std::cmp::Ordering;
use std::collections::BinaryHeap;

pub const NOTE_ON: i64 = 0;
pub const NOTE_OFF: i64 = 1;
/// How far after a note's start its last note's end may fall and still count as ending first, not overlapping.
const OVERLAP_TOLERANCE_SECONDS: f64 = 0.003;
pub const ALL_OFF: i64 = 2;
pub const FORGET: i64 = 3;
pub const SCENE_STARTED: i64 = 4;
/// A MIDI CC for an instrument: its number in the pitch's place, its value, 0 to 127, in the velocity's.
pub const CONTROL: i64 = 5;
pub const MOST_INSTRUMENTS: usize = 1024;
pub const MOST_VOICES: usize = 512;
pub const MOST_EVENTS: usize = 1 << 16;

/// What the engine lets go of, for the housekeeper to free off the audio thread; nothing reads it, it is only dropped.
#[allow(dead_code)]
pub enum Trash {
    Hit(Hit),
    Patch(Box<Patch>),
    Fluid(Box<Fluid>),
}

/// A MIDI message for FluidSynth at its sample.
pub struct MidiEvent {
    pub sample: i64,
    pub order: u64,
    pub status: u8,
    pub first: u8,
    pub second: u8,
}

impl PartialEq for MidiEvent {
    fn eq(&self, other: &Self) -> bool {
        (self.sample, self.order) == (other.sample, other.order)
    }
}

impl Eq for MidiEvent {}

impl PartialOrd for MidiEvent {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for MidiEvent {
    // Reversed, so that the heap's top is the earliest message, those of one sample in the order they came.
    fn cmp(&self, other: &Self) -> Ordering {
        (other.sample, other.order).cmp(&(self.sample, self.order))
    }
}

/// Where the engine puts what it lets go of: the housekeeper's queue, or nowhere (offline, where freeing is harmless).
pub type Bin = Option<rtrb::Producer<Trash>>;

/// One event at its sample.
pub struct Event {
    pub sample: i64,
    pub order: u64,
    pub kind: i64,
    pub instrument: usize,
    pub pitch: f64,
    pub velocity: f64,
    pub hit: Option<Hit>,
}

impl Event {
    /// A note's end comes before a note's start on one sample, then the order they arrived in.
    fn key(&self) -> (i64, bool, u64) {
        (self.sample, self.kind != NOTE_OFF, self.order)
    }
}

impl PartialEq for Event {
    fn eq(&self, other: &Self) -> bool {
        self.key() == other.key()
    }
}

impl Eq for Event {}

impl PartialOrd for Event {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for Event {
    // Reversed, so that the heap's top is the earliest event.
    fn cmp(&self, other: &Self) -> Ordering {
        other.key().cmp(&self.key())
    }
}

/// What the engine counts for the tracker's timing statistics.
#[derive(Clone, Copy, Default)]
pub struct Counts {
    pub late: u64,
    pub runaways: u64,
    pub dropped_notes: u64,
    pub voices: u64,
}

pub struct Engine {
    pub rate: f64,
    instruments: Vec<Option<Box<Patch>>>,
    events: BinaryHeap<Event>,
    fluid: Option<Box<Fluid>>,
    midi: BinaryHeap<MidiEvent>,
    fluid_scratch: Vec<f32>,
    pub right_guard: OutputGuard,
    voices: Vec<Voice>,
    order: u64,
    next_voice: u64,
    pub guard: OutputGuard,
    pub counts: Counts,
    bin: Bin,
}

impl Engine {
    pub fn new(rate: f64, bin: Bin) -> Engine {
        Engine {
            rate,
            instruments: (0..MOST_INSTRUMENTS).map(|_| None).collect(),
            events: BinaryHeap::with_capacity(MOST_EVENTS),
            fluid: None,
            midi: BinaryHeap::with_capacity(MOST_EVENTS),
            fluid_scratch: vec![0.0; 2 * MOST_FRAMES],
            right_guard: OutputGuard::new(rate),
            voices: Vec::with_capacity(MOST_VOICES),
            order: 0,
            next_voice: 0,
            guard: OutputGuard::new(rate),
            counts: Counts::default(),
            bin,
        }
    }

    fn throw_away(&mut self, trash: Trash) {
        if let Some(bin) = &mut self.bin {
            // A full bin frees here, which only a flood of edits could cause.
            let _ = bin.push(trash);
        }
    }

    /// Put an instrument in place, its old self thrown away; its sounding notes play on with the new one.
    pub fn set_instrument(&mut self, number: usize, patch: Box<Patch>) {
        let Some(slot) = self.instruments.get_mut(number) else { return };
        if let Some(old) = slot.replace(patch) {
            self.throw_away(Trash::Patch(old));
        }
    }

    /// Put FluidSynth in place, its old self thrown away.
    pub fn set_fluid(&mut self, fluid: Box<Fluid>) {
        if let Some(old) = self.fluid.replace(fluid) {
            self.throw_away(Trash::Fluid(old));
        }
    }

    /// Schedule a MIDI message for FluidSynth at an exact sample.
    pub fn schedule_midi(&mut self, mut event: MidiEvent) {
        if self.midi.len() >= MOST_EVENTS {
            self.counts.dropped_notes += 1;
            return;
        }
        self.order += 1;
        event.order = self.order;
        self.midi.push(event);
    }

    /// Take back every MIDI message for FluidSynth still to play from a sample on, as a MIDI port's flush does.
    pub fn forget_midi(&mut self, sample: i64) {
        self.midi.retain(|event| event.sample < sample);
    }

    /// Count a fault on both channels' guards, so that the latch holds the whole output.
    fn fault(&mut self) {
        self.guard.fault();
        self.right_guard.fault();
    }

    /// Schedule an event at an exact sample.
    pub fn schedule(&mut self, mut event: Event) {
        if self.events.len() >= MOST_EVENTS {
            self.counts.dropped_notes += 1;
            if let Some(hit) = event.hit.take() {
                self.throw_away(Trash::Hit(hit));
            }
            return;
        }
        self.order += 1;
        event.order = self.order;
        self.events.push(event);
    }

    /// Take back every event still to play from a sample on, of the instruments numbered first to last.
    pub fn forget(&mut self, first: usize, last: usize, sample: i64) {
        let mut kept = std::mem::take(&mut self.events).into_vec();
        let mut place = 0;
        while place < kept.len() {
            let event = &kept[place];
            if (first..=last).contains(&event.instrument) && event.sample >= sample {
                let mut gone = kept.swap_remove(place);
                if let Some(hit) = gone.hit.take() {
                    self.throw_away(Trash::Hit(hit));
                }
            } else {
                place += 1;
            }
        }
        self.events = BinaryHeap::from(kept);
    }

    /// Forget every event, stop every voice at once, and clear the output's latch.
    pub fn silence(&mut self) {
        let mut events = std::mem::take(&mut self.events).into_vec();
        for mut event in events.drain(..) {
            if let Some(hit) = event.hit.take() {
                self.throw_away(Trash::Hit(hit));
            }
        }
        self.events = BinaryHeap::from(events);
        while let Some(mut voice) = self.voices.pop() {
            if let Some(hit) = voice.hit.take() {
                self.throw_away(Trash::Hit(hit));
            }
        }
        self.midi.clear();
        if let Some(fluid) = self.fluid.as_mut() {
            fluid.silence();
        }
        self.guard.clear();
        self.right_guard.clear();
    }

    /// The mix of the chunk starting at a sample into its two channels, every event due in it begun on its sample: the
    /// built-in instruments in the middle, FluidSynth's sounds where its General MIDI pans them, each channel made safe.
    pub fn render(&mut self, start: i64, left: &mut [f32], right: &mut [f32]) {
        let frames = left.len().min(right.len()).min(MOST_FRAMES);
        self.render_built_in(start, &mut left[..frames]);
        right[..frames].copy_from_slice(&left[..frames]);
        self.render_fluid(start, &mut left[..frames], &mut right[..frames]);
        self.guard.guard(&mut left[..frames]);
        self.right_guard.guard(&mut right[..frames]);
    }

    /// FluidSynth's part of the chunk, added to both channels: rendered up to each MIDI message's sample, the message played
    /// there, then on to the next, so that each lands on its sample to FluidSynth's own block of 64.
    fn render_fluid(&mut self, start: i64, left: &mut [f32], right: &mut [f32]) {
        let frames = left.len();
        let end = start + frames as i64;
        let Some(fluid) = self.fluid.as_mut() else {
            self.midi.retain(|event| event.sample >= end);
            return;
        };
        let mut done = 0;
        while self.midi.peek().is_some_and(|event| event.sample < end) {
            let Some(event) = self.midi.pop() else { break };
            let place = ((event.sample - start).max(0) as usize).min(frames);
            if place > done {
                fluid.render(&mut left[done..place], &mut right[done..place], &mut self.fluid_scratch);
                done = place;
            }
            fluid.play(event.status, event.first, event.second);
        }
        if done < frames {
            fluid.render(&mut left[done..], &mut right[done..], &mut self.fluid_scratch);
        }
    }

    /// The built-in instruments' mono mix of the chunk.
    fn render_built_in(&mut self, start: i64, mix: &mut [f32]) {
        let frames = mix.len();
        mix.fill(0.0);
        let end = start + frames as i64;
        while self.events.peek().is_some_and(|event| event.sample < end) {
            let Some(mut event) = self.events.pop() else { break };
            if event.sample < start {
                if event.kind == NOTE_ON {
                    self.counts.late += 1;
                }
                event.sample = start;
            }
            self.begin(event);
        }
        for patch in self.instruments.iter_mut().flatten() {
            patch.used = false;
            patch.buffer[..frames].fill(0.0);
            patch.ready(frames);
        }
        self.play_voices(start, frames);
        self.mix_instruments(&mut mix[..frames]);
        self.counts.voices = self.voices.len() as u64;
    }

    fn play_voices(&mut self, start: i64, frames: usize) {
        let mut place = 0;
        while place < self.voices.len() {
            let instrument = self.voices[place].instrument;
            let alive = match self.instruments[instrument].as_mut() {
                Some(patch) => patch.play(&mut self.voices[place], start, frames),
                None => false,
            };
            if alive {
                place += 1;
            } else {
                // Order matters for stealing the oldest, so the voices after it move up.
                let mut voice = self.voices.remove(place);
                if let Some(hit) = voice.hit.take() {
                    self.throw_away(Trash::Hit(hit));
                }
            }
        }
    }

    fn mix_instruments(&mut self, mix: &mut [f32]) {
        let frames = mix.len();
        for number in 0..self.instruments.len() {
            let Some(patch) = self.instruments[number].as_mut() else { continue };
            if !patch.used {
                continue;
            }
            if safety::is_runaway(&patch.buffer[..frames]) {
                self.recover(number);
                continue;
            }
            patch.finish(frames);
            if safety::is_runaway(&patch.buffer[..frames]) {
                self.recover(number);
                continue;
            }
            let volume = patch.volume as f32;
            for (sample, played) in mix.iter_mut().zip(patch.buffer.iter()) {
                *sample += played * volume;
            }
        }
    }

    /// Silence a runaway instrument: its notes dropped and its filters and effects back at rest.
    fn recover(&mut self, number: usize) {
        self.counts.runaways += 1;
        self.fault();
        let mut place = 0;
        while place < self.voices.len() {
            if self.voices[place].instrument == number {
                let mut voice = self.voices.remove(place);
                if let Some(hit) = voice.hit.take() {
                    self.throw_away(Trash::Hit(hit));
                }
            } else {
                place += 1;
            }
        }
        if let Some(patch) = self.instruments[number].as_mut() {
            patch.reset();
        }
    }

    fn begin(&mut self, mut event: Event) {
        let instrument = event.instrument;
        if self.instruments.get(instrument).is_none_or(Option::is_none) {
            if let Some(hit) = event.hit.take() {
                self.throw_away(Trash::Hit(hit));
            }
            return;
        }
        match event.kind {
            NOTE_ON => self.note_on(event),
            NOTE_OFF => {
                for voice in self.voices.iter_mut() {
                    if voice.instrument == instrument && voice.pitch == event.pitch && voice.release_at.is_none() && voice.hit.is_none() {
                        voice.release_at = Some(event.sample);
                    }
                }
            }
            ALL_OFF => {
                for voice in self.voices.iter_mut().filter(|voice| voice.instrument == instrument) {
                    if voice.hit.is_some() && voice.cut_at.is_none() {
                        voice.cut_at = Some(event.sample);
                    } else if voice.hit.is_none() && voice.release_at.is_none() {
                        voice.release_at = Some(event.sample);
                    }
                }
            }
            SCENE_STARTED => {
                if let Some(patch) = self.instruments[instrument].as_mut() {
                    patch.lfos.scene_started();
                }
            }
            CONTROL => {
                if let Some(patch) = self.instruments[instrument].as_mut() {
                    patch.set_control(event.pitch as usize, event.velocity);
                }
            }
            _ => {}
        }
    }

    fn note_on(&mut self, mut event: Event) {
        let instrument = event.instrument;
        let Some(mut patch) = self.instruments[instrument].take() else { return };
        // A one-voice instrument with Glide on slides to a note that starts while its last is still held, at its Glide
        // time, its envelopes going on, as a monosynth plays legato; a note that starts as the last ends is struck afresh.
        if patch.glides && patch.voices == 1 && patch.drum().is_none() {
            let held = self
                .voices
                .iter()
                .position(|voice| voice.instrument == instrument && voice.release_at.is_none() && voice.cut_at.is_none());
            if let Some(place) = held {
                let pitch = self.voices[place].pitch;
                if self.end_due_with(instrument, pitch, event.sample) {
                    self.voices[place].release_at = Some(event.sample);
                } else {
                    patch.slide_to(&mut self.voices[place], event.pitch, event.sample);
                    self.instruments[instrument] = Some(patch);
                    return;
                }
            }
        }
        if self.voices.len() >= MOST_VOICES {
            self.counts.dropped_notes += 1;
            if let Some(hit) = event.hit.take() {
                self.throw_away(Trash::Hit(hit));
            }
            self.instruments[instrument] = Some(patch);
            return;
        }
        self.next_voice += 1;
        let mut voice = Voice::new(self.next_voice, instrument, event.pitch, event.sample, event.velocity / 127.0, event.hit.take());
        if voice.hit.is_some() {
            self.cut_drums(&patch, instrument, event.sample);
            patch.lfos.note_on();
        } else {
            self.steal(patch.voices, instrument, event.sample);
            patch.begin(&mut voice);
        }
        self.voices.push(voice);
        self.instruments[instrument] = Some(patch);
    }

    /// Whether a held note's end is due with a new note's start, within OVERLAP_TOLERANCE_SECONDS after it, and so taken
    /// out of the queue as having come first. Live, each message's moment becomes a sample by the clock of the audio
    /// callback that takes it, so an end and the next start written for one instant can land a few samples apart, the
    /// end after the start; a note gliding into the next overlaps it by far more, a 128th note.
    fn end_due_with(&mut self, instrument: usize, pitch: f64, sample: i64) -> bool {
        let latest = sample + (OVERLAP_TOLERANCE_SECONDS * self.rate).round() as i64;
        let is_end = |event: &Event| event.kind == NOTE_OFF && event.instrument == instrument && event.pitch == pitch && event.sample <= latest;
        if !self.events.iter().any(is_end) {
            return false;
        }
        let mut events = std::mem::take(&mut self.events).into_vec();
        if let Some(place) = events.iter().position(is_end) {
            events.swap_remove(place);
        }
        self.events = BinaryHeap::from(events);
        true
    }

    /// Cut the drum's own last hit, unless its hits overlap, and every hit of its choke group, each fading out.
    fn cut_drums(&mut self, patch: &Patch, instrument: usize, sample: i64) {
        let Some(drum) = patch.drum() else { return };
        for voice in self.voices.iter_mut() {
            if voice.cut_at.is_some() || voice.hit.is_none() {
                continue;
            }
            let same = voice.instrument == instrument && !drum.overlap;
            let other_choke = self
                .instruments
                .get(voice.instrument)
                .and_then(|slot| slot.as_ref())
                .and_then(|other| other.drum())
                .and_then(|other| other.choke);
            let choked = drum.choke.is_some() && other_choke == drum.choke && voice.instrument != instrument;
            if same || choked {
                voice.cut_at = Some(sample);
            }
        }
    }

    /// Cut the oldest voices of an instrument past its count of voices, so that a mono instrument plays one note.
    fn steal(&mut self, most: usize, instrument: usize, sample: i64) {
        let mut sounding = self
            .voices
            .iter()
            .filter(|voice| voice.instrument == instrument && voice.cut_at.is_none())
            .count();
        for voice in self.voices.iter_mut() {
            if sounding < most {
                break;
            }
            if voice.instrument == instrument && voice.cut_at.is_none() {
                voice.cut_at = Some(sample);
                sounding -= 1;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rmpv::Value;

    fn basic() -> Box<Patch> {
        basic_with_voices(4)
    }

    fn basic_with_voices(voices: i64) -> Box<Patch> {
        let oscillators = Value::Map(vec![
            ("type".into(), "basic".into()),
            ("oscillators".into(), Value::Array(vec![Value::Array(vec!["saw".into(), 0.into(), 1.0.into()])])),
        ]);
        let envelope = Value::Map(vec![
            ("type".into(), "adsr".into()),
            ("attack".into(), 0.001.into()),
            ("release".into(), 0.05.into()),
        ]);
        let spec = Value::Map(vec![
            ("oscillators".into(), oscillators),
            ("envelopes".into(), Value::Array(vec![envelope.clone(), envelope.clone(), envelope])),
            ("voices".into(), voices.into()),
            ("glide".into(), 0.06.into()),
        ]);
        Box::new(Patch::compiled(&spec, 48000.0))
    }

    fn note(sample: i64, kind: i64, pitch: f64) -> Event {
        Event {
            sample,
            order: 0,
            kind,
            instrument: 0,
            pitch,
            velocity: 100.0,
            hit: None,
        }
    }

    #[test]
    fn a_note_begins_on_its_exact_sample() {
        let mut engine = Engine::new(48000.0, None);
        engine.set_instrument(0, basic());
        engine.schedule(note(70, NOTE_ON, 60.0));
        let mut mix = vec![0.0; 128];
        let mut right = vec![0.0; 128];
        engine.render(0, &mut mix, &mut right);
        // The guard's high pass lets nothing through before the note, and the note sounds from its sample.
        assert!(mix[..70].iter().all(|sample| *sample == 0.0));
        assert!(mix[72..].iter().any(|sample| *sample != 0.0));
    }

    #[test]
    fn a_released_note_falls_silent_and_its_voice_is_freed() {
        let mut engine = Engine::new(48000.0, None);
        engine.set_instrument(0, basic());
        engine.schedule(note(0, NOTE_ON, 60.0));
        engine.schedule(note(4800, NOTE_OFF, 60.0));
        let (mut left, mut right) = (vec![0.0; 128], vec![0.0; 128]);
        for chunk in 0..200 {
            engine.render(chunk * 128, &mut left, &mut right);
        }
        assert_eq!(engine.voices.len(), 0);
    }

    /// A one-voice instrument slides only into a note that overlaps the last: an end that lands a few samples after the
    /// next start, as the live clocks can put it, still strikes the next note afresh, while a gliding note's overlap slides.
    #[test]
    fn a_one_voice_instrument_slides_only_into_a_real_overlap() {
        let (start, next, low, high) = (0, 4800, 48.0, 55.0);
        let sounding_voice = |late: i64| {
            let mut engine = Engine::new(48000.0, None);
            engine.set_instrument(0, basic_with_voices(1));
            engine.schedule(note(start, NOTE_ON, low));
            engine.schedule(note(next, NOTE_ON, high));
            engine.schedule(note(next + late, NOTE_OFF, low));
            let (mut left, mut right) = (vec![0.0; 128], vec![0.0; 128]);
            for chunk in 0..40 {
                engine.render(chunk * 128, &mut left, &mut right);
            }
            engine.voices.iter().filter(|voice| voice.cut_at.is_none()).map(|voice| voice.id).max()
        };
        let (jitter, overlap, first_voice) = (20, 1000, Some(1));
        assert_ne!(sounding_voice(jitter), first_voice, "struck afresh on a voice of its own");
        assert_eq!(sounding_voice(overlap), first_voice, "slid on the first note's voice");
    }
}
