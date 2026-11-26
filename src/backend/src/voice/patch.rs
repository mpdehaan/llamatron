// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A compiled instrument and its sounding notes.
//!
//! A voice of parts runs a sample at a time: its envelopes; the matrix, from the envelopes, the LFOs, its velocity, key and a
//! random value; the oscillator, its pitch moved by glide, Env3 through Pitch env and the matrix; its filter, its cutoff
//! moved by Env2 through the Env amount (and an acid accent's extra depth), key tracking and the matrix; and the amp, Env1
//! times its velocity, moved by the matrix. A filter is each note's own, or the instrument's, shared by every note and moved
//! by the newest, as a paraphonic synth's is; a low-pass gate is always the note's own and is its amp, lit by Env1.
//!
//! A drum instrument's notes replay hits rendered ahead on the reader thread (drums.rs), cutting the last hit unless they
//! overlap, and choking the others of their group.
//!
//! Everything here is compiled on the reader thread; the audio callback only plays, allocating nothing.

use crate::drums::Hit;
use crate::dsp::Random;
use crate::protocol::values::{field, list, number, truth, word};
use crate::voice::effects::{self, Effect};
use crate::voice::envelopes::{self, EnvelopeMemory, EnvelopePart, EnvelopeState, NoteTime};
use crate::voice::filters::{FilterPart, FilterState, GateNote, GatePart, ENVELOPE_OCTAVES};
use crate::voice::modulation::{LfoBank, ModMatrix, Moved, Source, Sources, LFO_COUNT, MOST_FRAMES};
use crate::voice::oscillators::{self, Moves, OscillatorPart, OscillatorState};
use rmpv::Value;

const MIDDLE_C: f64 = 60.0;
const KEY_SPAN: f64 = 60.0;
const MOST_AMP: f64 = 2.0;
const RANDOM_SEED: u64 = 101;
const CUT_FADE_SECONDS: f64 = 0.003;
pub const LONGEST_RING_SECONDS: f64 = 30.0;
const RECIPES_TUNED_AT: f64 = 60.0;
pub const VELOCITY_STEP: i64 = 8;

/// A sounding note.
pub struct Voice {
    pub id: u64,
    pub instrument: usize,
    pub pitch: f64,
    pub start: i64,
    pub age: usize,
    pub release_at: Option<i64>,
    pub cut_at: Option<i64>,
    pub level: f64,
    pub silent: bool,
    pub hit: Option<Hit>,
    oscillator: OscillatorState,
    envelopes: [EnvelopeState; 3],
    filter: FilterState,
    glide_from: f64,
    glide_at: i64,
    random: f64,
    accent_depth: f64,
    short_decay: Option<f64>,
    /// Whether the voice's release has been told to its instrument's envelope memories.
    release_told: bool,
}

impl Voice {
    pub fn new(id: u64, instrument: usize, pitch: f64, start: i64, level: f64, hit: Option<Hit>) -> Voice {
        Voice {
            id,
            instrument,
            pitch,
            start,
            age: 0,
            release_at: None,
            cut_at: None,
            level,
            silent: false,
            hit,
            oscillator: OscillatorState::default(),
            envelopes: [EnvelopeState::default(); 3],
            filter: FilterState::default(),
            glide_from: pitch,
            glide_at: start,
            random: 0.0,
            accent_depth: 0.0,
            short_decay: None,
            release_told: false,
        }
    }
}

/// A voice of parts.
pub struct Modular {
    oscillator: OscillatorPart,
    pitch_env: f64,
    envelopes: [EnvelopePart; 3],
    memory: [EnvelopeMemory; 3],
    filter: Option<FilterPart>,
    gate: Option<GatePart>,
    own_filter: bool,
    shared: FilterState,
    shared_octaves: Vec<f64>,
    shared_resonance: Vec<f64>,
    last_octaves: f64,
    last_resonance: f64,
    matrix: ModMatrix,
    reads_env2: bool,
    matrix_reads_env2: bool,
    reads_env3: bool,
    last_pitch: Option<f64>,
    newest: u64,
    random: Random,
}

#[derive(Clone)]
/// A drum: its choke group and whether its hits overlap, and the note its recipes play at their own pitch on.
pub struct Drum {
    pub machine: String,
    pub knobs: Vec<f64>,
    pub choke: Option<i64>,
    pub overlap: bool,
    tuned_from: f64,
}

impl Drum {
    /// The note a recipe renders for a note played.
    pub fn recipe_pitch(&self, pitch: f64) -> f64 {
        pitch - self.tuned_from + RECIPES_TUNED_AT
    }
}

pub enum Sound {
    Modular(Box<Modular>),
    Drum(Drum),
}

/// A compiled instrument.
pub struct Patch {
    pub sound: Sound,
    pub volume: f64,
    pub voices: usize,
    /// Whether a one-voice instrument slides into a note that overlaps the last, as a glided step does; when off, every
    /// note is struck afresh.
    pub glides: bool,
    glide: f64,
    pub effects: Vec<Effect>,
    pub lfos: LfoBank,
    pub buffer: Vec<f32>,
    pub used: bool,
    /// Each MIDI CC's last value, from 0 to 1, which the Mod Matrix's CC sources read.
    pub controls: [f64; CONTROL_COUNT],
    rate: f64,
}

/// How many MIDI CCs there are, and a CC's highest value.
pub const CONTROL_COUNT: usize = 128;
const CONTROL_TOP: f64 = 127.0;

impl Patch {
    /// The instrument a spec describes, as the tracker writes it (model/objects/built_in_sound.py).
    pub fn compiled(spec: &Value, rate: f64) -> Patch {
        let empty = Value::Nil;
        let oscillators = field(spec, "oscillators").unwrap_or(&empty);
        let sound = if word(oscillators, "type", "basic") == "drum" {
            let choke = field(oscillators, "choke")
                .and_then(crate::protocol::values::as_number)
                .map(|group| group as i64);
            Sound::Drum(Drum {
                machine: word(oscillators, "machine", "kick").to_string(),
                knobs: crate::protocol::values::numbers(oscillators, "knobs"),
                choke,
                overlap: truth(oscillators, "overlap", false),
                tuned_from: number(spec, "tuned_from", MIDDLE_C),
            })
        } else {
            Sound::Modular(Box::new(modular(spec, oscillators, rate)))
        };
        Patch {
            sound,
            volume: number(spec, "volume", 0.8),
            voices: (number(spec, "voices", 1.0) as usize).max(1),
            glides: truth(spec, "glides", true),
            glide: number(spec, "glide", 0.0),
            effects: effects::compiled(list(spec, "effects"), rate),
            lfos: LfoBank::compiled(list(spec, "lfos"), rate),
            buffer: vec![0.0; MOST_FRAMES],
            used: false,
            controls: [0.0; CONTROL_COUNT],
            rate,
        }
    }

    /// Take a MIDI CC's new value, 0 to 127, for the Mod Matrix's CC sources.
    pub fn set_control(&mut self, number: usize, value: f64) {
        if let Some(held) = self.controls.get_mut(number) {
            *held = (value / CONTROL_TOP).clamp(0.0, 1.0);
        }
    }

    /// Back to rest after a runaway: filters and effects cleared, so that its next note plays clean.
    pub fn reset(&mut self) {
        for effect in self.effects.iter_mut() {
            effect.reset();
        }
        if let Sound::Modular(modular) = &mut self.sound {
            modular.shared.reset();
            modular.last_octaves = 0.0;
            modular.last_resonance = 0.0;
        }
    }

    pub fn drum(&self) -> Option<&Drum> {
        match &self.sound {
            Sound::Drum(drum) => Some(drum),
            Sound::Modular(_) => None,
        }
    }

    /// Ready the patch for a chunk: its LFOs moved on and its shared filter's movement held where the newest note left it.
    pub fn ready(&mut self, frames: usize) {
        if self.lfos.is_on() {
            self.lfos.advance(frames);
        }
        if let Sound::Modular(modular) = &mut self.sound {
            let frames = frames.min(MOST_FRAMES);
            modular.shared_octaves[..frames].fill(modular.last_octaves);
            modular.shared_resonance[..frames].fill(modular.last_resonance);
        }
    }

    /// Start a note on a voice made for it.
    pub fn begin(&mut self, voice: &mut Voice) {
        let rate = self.rate;
        self.lfos.note_on();
        let Sound::Modular(modular) = &mut self.sound else { return };
        modular.last_pitch = Some(voice.pitch);
        voice.random = modular.random.between(-1.0, 1.0);
        let seconds = voice.start as f64 / rate;
        // An accent's extra filter sweep and short decay come from whichever slot holds an envelope that accents, such as
        // the acid gate, so that it accents in any slot, not only Env1's.
        voice.accent_depth = 0.0;
        voice.short_decay = None;
        for place in 0..3 {
            let (state, depth, short) = modular.envelopes[place].start(&mut modular.memory[place], voice.level, seconds);
            voice.envelopes[place] = state;
            voice.accent_depth = voice.accent_depth.max(depth);
            voice.short_decay = voice.short_decay.or(short);
        }
        modular.oscillator.begin(&mut voice.oscillator, voice.pitch);
        modular.newest = voice.id;
    }

    /// Slide a held note to a new pitch from a sample, legato, its envelopes going on.
    pub fn slide_to(&mut self, voice: &mut Voice, pitch: f64, sample: i64) {
        let glided = self.glided(voice, sample as f64);
        voice.glide_from = voice.pitch + glided;
        voice.pitch = pitch;
        voice.glide_at = sample;
        if let Sound::Modular(modular) = &mut self.sound {
            modular.last_pitch = Some(pitch);
            modular.newest = voice.id;
        }
    }

    fn glided(&self, voice: &Voice, place: f64) -> f64 {
        if self.glide <= 0.0 {
            return 0.0;
        }
        (voice.glide_from - voice.pitch) * (-(place - voice.glide_at as f64).max(0.0) / (self.glide * self.rate)).exp()
    }

    /// Add a voice's part of the chunk starting at a sample to the patch's buffer, and return whether it still sounds.
    pub fn play(&mut self, voice: &mut Voice, start: i64, frames: usize) -> bool {
        let offset = voice.start - start;
        if offset >= frames as i64 {
            return true;
        }
        let offset = offset.max(0) as usize;
        let count = frames - offset;
        let rate = self.rate;
        if let Some(released) = voice.release_at {
            if !voice.release_told {
                voice.release_told = true;
                if let Sound::Modular(modular) = &mut self.sound {
                    let (began, ended) = (voice.start as f64 / rate, released as f64 / rate);
                    for memory in modular.memory.iter_mut() {
                        memory.note_released(began, ended);
                    }
                }
            }
            if voice.cut_at.is_none() && (start - released) as f64 > LONGEST_RING_SECONDS * rate {
                voice.cut_at = Some(start);
            }
        }
        self.used = true;
        let fade = (CUT_FADE_SECONDS * rate) as i64;
        let mut ended = false;
        let played = if let Some(hit) = &voice.hit {
            let left = hit.len().saturating_sub(voice.age);
            let take = left.min(count);
            for place in 0..take {
                self.buffer[offset + place] += hit[voice.age + place] * voice.level as f32;
            }
            ended = voice.age + take >= hit.len();
            take
        } else {
            self.sound_voice(voice, start + offset as i64, offset, count);
            count
        };
        let mut alive = true;
        if let Some(cut) = voice.cut_at {
            let first = start + offset as i64 - cut;
            for place in 0..played {
                let gain = (1.0 - (first + place as i64) as f64 / fade as f64).clamp(0.0, 1.0);
                self.buffer[offset + place] *= gain as f32;
            }
            alive = first + (played as i64) - 1 < fade;
        }
        voice.age += played;
        alive && !ended && !voice.silent
    }

    fn sound_voice(&mut self, voice: &mut Voice, first: i64, offset: usize, count: usize) {
        let rate = self.rate;
        let glide = self.glide;
        let Sound::Modular(modular) = &mut self.sound else { return };
        let lfos = &self.lfos.now;
        let buffer = &mut self.buffer;
        let is_newest = voice.id == modular.newest;
        let wants_env2 = modular.reads_env2 && (modular.own_filter || is_newest || modular.matrix_reads_env2);
        let takes_velocity = modular.envelopes[0].takes_velocity();
        let key = (voice.pitch - MIDDLE_C) / KEY_SPAN;
        let mut sources = Sources {
            velocity: voice.level,
            key,
            random: voice.random,
            ..Sources::default()
        };
        // The CCs the matrix reads, as their last messages left them, for the chunk ahead.
        for (place, number) in modular.matrix.controls.iter().enumerate() {
            sources.controls[place] = self.controls[*number as usize];
        }
        let gliding = glide > 0.0 && voice.glide_from != voice.pitch;
        modular.oscillator.choose_band(&mut voice.oscillator, voice.pitch);
        for place in 0..count {
            let sample = first + place as i64;
            let note = NoteTime {
                age: (sample - voice.start) as f64 / rate,
                released: voice.release_at.map(|released| (released - voice.start) as f64 / rate),
            };
            let short = voice.short_decay;
            sources.envelopes[0] = modular.envelopes[0].level(&mut voice.envelopes[0], note, None);
            if wants_env2 {
                sources.envelopes[1] = modular.envelopes[1].level(&mut voice.envelopes[1], note, short);
            }
            if modular.reads_env3 {
                sources.envelopes[2] = modular.envelopes[2].level(&mut voice.envelopes[2], note, None);
            }
            for (lfo, values) in sources.lfos.iter_mut().zip(lfos.iter()).take(LFO_COUNT) {
                *lfo = values[offset + place];
            }
            let moved = if modular.matrix.routes.is_empty() {
                Moved::default()
            } else {
                modular.matrix.moved(&sources)
            };
            let mut bend = sources.envelopes[2] * modular.pitch_env + moved.pitch;
            if gliding {
                bend += (voice.glide_from - voice.pitch) * (-((sample - voice.glide_at) as f64).max(0.0) / (glide * rate)).exp();
            }
            let moves = Moves {
                pitch: bend,
                width: moved.pulse_width,
                spread: moved.detune,
            };
            let seconds = note.age;
            let mut wave = 0.0;
            if modular.gate.is_none_or(|gate| gate.feeds_oscillator) {
                let (out, silenced) = modular.oscillator.sample(&mut voice.oscillator, voice.pitch, seconds, moves, rate);
                wave = out;
                if silenced {
                    voice.silent = true;
                }
            }
            let mut light = sources.envelopes[0];
            if !takes_velocity {
                light *= voice.level;
            }
            let out = if let Some(gate) = &modular.gate {
                let note = GateNote {
                    light,
                    place: (sample - voice.start) as f64,
                    pitch: voice.pitch,
                    level: voice.level,
                    octaves: moved.cutoff,
                };
                gate.process(&mut voice.filter, wave, note)
            } else {
                if let Some(filter) = &modular.filter {
                    let mut octaves = sources.envelopes[1] * (filter.amount + voice.accent_depth) * ENVELOPE_OCTAVES + moved.cutoff;
                    if filter.key_track != 0.0 {
                        octaves += filter.key_track * (voice.pitch - MIDDLE_C) / 12.0;
                    }
                    if modular.own_filter {
                        wave = filter.process(&mut voice.filter, wave, octaves, moved.resonance);
                    } else if is_newest {
                        modular.shared_octaves[offset + place] = octaves;
                        modular.shared_resonance[offset + place] = moved.resonance;
                    }
                }
                let mut amp = light;
                if moved.amp != 0.0 {
                    amp *= (1.0 + moved.amp).clamp(0.0, MOST_AMP);
                }
                wave * amp
            };
            buffer[offset + place] += out as f32;
        }
        if voice.envelopes[0].done {
            voice.silent = true;
        }
        if is_newest && !modular.own_filter && count > 0 {
            modular.last_octaves = modular.shared_octaves[offset + count - 1];
            modular.last_resonance = modular.shared_resonance[offset + count - 1];
        }
    }

    /// Finish the chunk's buffer: the shared filter, then the effects in order.
    pub fn finish(&mut self, frames: usize) {
        if let Sound::Modular(modular) = &mut self.sound {
            if let (Some(filter), false) = (&modular.filter, modular.own_filter) {
                for place in 0..frames {
                    let out = filter.process(
                        &mut modular.shared,
                        self.buffer[place] as f64,
                        modular.shared_octaves[place],
                        modular.shared_resonance[place],
                    );
                    self.buffer[place] = out as f32;
                }
            }
        }
        for effect in self.effects.iter_mut() {
            effect.apply(&mut self.buffer[..frames]);
        }
    }
}

fn modular(spec: &Value, oscillators: &Value, rate: f64) -> Modular {
    let empty = Value::Nil;
    let (oscillator, pitch_env) = oscillators::compiled(oscillators, rate);
    let filter_spec = field(spec, "filter").unwrap_or(&empty);
    let resonance = number(filter_spec, "resonance", 0.0);
    let envelope_specs = list(spec, "envelopes");
    let envelope = |place: usize| envelopes::compiled(envelope_specs.get(place).unwrap_or(&empty), resonance);
    let filter = FilterPart::compiled(filter_spec, rate);
    let gate = GatePart::compiled(filter_spec, rate);
    let matrix = ModMatrix::compiled(list(spec, "matrix"));
    let matrix_reads_env2 = matrix.uses(Source::Env2);
    Modular {
        oscillator,
        pitch_env,
        envelopes: [envelope(0), envelope(1), envelope(2)],
        memory: [EnvelopeMemory::default(); 3],
        own_filter: gate.is_some() || truth(spec, "filter_per_note", true),
        reads_env2: filter.is_some() || matrix_reads_env2,
        matrix_reads_env2,
        reads_env3: pitch_env != 0.0 || matrix.uses(Source::Env3),
        filter,
        gate,
        shared: FilterState::default(),
        shared_octaves: vec![0.0; MOST_FRAMES],
        shared_resonance: vec![0.0; MOST_FRAMES],
        last_octaves: 0.0,
        last_resonance: 0.0,
        matrix,
        last_pitch: None,
        newest: u64::MAX,
        random: Random::new(RANDOM_SEED),
    }
}
