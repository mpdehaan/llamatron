// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A compiled instrument and its sounding notes.
//!
//! A voice of parts runs a sample at a time: its envelopes; the matrix, from the envelopes, the LFOs, its velocity, key and a
//! random value; the oscillator, its pitch moved by glide and the matrix; its filter, its cutoff
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
use crate::effects::{self, Effect};
use crate::envelopes::{self, EnvelopeMemory, EnvelopePart, EnvelopeState, NoteTime};
use crate::filters::gate::{GateNote, GatePart, GateState};
use crate::filters::{FilterPart, FilterState, ENVELOPE_OCTAVES};
use crate::instrument::amp::{self, AmpPart};
use crate::modulation::{self, Destination, LfoBank, ModMatrix, Moved, Source, Sources, LFO_COUNT, MOST_FRAMES};
use crate::oscillators::{self, Moves, OscillatorPart, OscillatorState};
use crate::protocol::values::{field, list, number, truth, word};
use rmpv::Value;

const MIDDLE_C: f64 = 60.0;
/// The two places a low-pass gate can stand in a voice: the Filter's, which the Amp follows, and the Amp's own.
const FILTER_GATE: usize = 0;
const AMP_GATE: usize = 1;
/// The rate from which an LFO is heard as a tone, and moves a cutoff at audio rate.
const AUDIO_RATE_HERTZ: f64 = 20.0;
/// The most of a cycle a Key LFO moves a sample: just under half, the highest frequency a sample rate can hold.
const MOST_KEY_STEP: f64 = 0.45;
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
    /// Where each Key LFO is in its cycles on this voice, since each follows the voice's own note.
    lfo_cycles: [f64; LFO_COUNT],
    /// The oscillator's last sample, which the Mod Matrix's Osc source reads a sample later.
    last_wave: f64,
    /// The most the modulation bent the pitch up over the last chunk, in half steps, from which the next chooses its table.
    reach: f64,
    envelopes: [EnvelopeState; 3],
    filter: FilterState,
    /// The voice's low-pass gates, in the Filter's place and the Amp's.
    gates: [GateState; 2],
    glide_from: f64,
    glide_at: i64,
    random: f64,
    accent_depth: f64,
    short_decay: Option<f64>,
    /// Whether the voice's release has been told to its instrument's envelope memories.
    release_told: bool,
}

impl Voice {
    /// Where each of its three envelopes started from: 0 for a fresh note, or where a restruck voice's had reached.
    pub fn envelope_starts(&self) -> [f64; 3] {
        std::array::from_fn(|place| self.envelopes[place].start_level)
    }

    /// Carry on from a voice of the same instrument struck again before it fell silent: its oscillators' phases, its
    /// filter, its Key LFOs and where each envelope had reached, which this voice's envelopes now rise from, so that a
    /// restruck one-voice instrument neither clicks nor restarts its waves.
    pub fn restrike_from(&mut self, old: &Voice) {
        self.oscillator = old.oscillator;
        self.filter = old.filter;
        self.gates = old.gates;
        self.lfo_cycles = old.lfo_cycles;
        self.last_wave = old.last_wave;
        self.reach = old.reach;
        for (envelope, earlier) in self.envelopes.iter_mut().zip(old.envelopes.iter()) {
            envelope.start_level = earlier.last;
        }
    }

    /// What a gate reads of this voice's note at a sample: how far into the note, its pitch and level, and the cutoff
    /// moved in octaves.
    #[inline]
    fn gate_note(&self, sample: i64, octaves: f64) -> GateNote {
        GateNote {
            place: (sample - self.start) as f64,
            pitch: self.pitch,
            level: self.level,
            octaves,
        }
    }

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
            lfo_cycles: [0.0; LFO_COUNT],
            reach: 0.0,
            last_wave: 0.0,
            envelopes: [EnvelopeState::default(); 3],
            filter: FilterState::default(),
            gates: [GateState::default(); 2],
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
    envelopes: [EnvelopePart; 3],
    memory: [EnvelopeMemory; 3],
    filter: Option<FilterPart>,
    /// A low-pass gate in the Filter's place, followed by the Amp, and one in the Amp's place, the voice's last stage.
    gates: [Option<GatePart>; 2],
    /// What each gate's own cell remembers of the notes before, as the envelopes' memories do.
    gate_memory: [EnvelopeMemory; 2],
    /// The Amp the voice ends in, which Env 1 opens (amp.rs), unless a low-pass gate stands in its place.
    amp: AmpPart,
    own_filter: bool,
    shared: FilterState,
    shared_octaves: Vec<f64>,
    shared_resonance: Vec<f64>,
    last_octaves: f64,
    last_resonance: f64,
    matrix: ModMatrix,
    /// Whether Env 2 sweeps the cutoff through the Env amount, as it does unless Disconnect filter unhooks it.
    env2_to_filter: bool,
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
    /// How many more samples the effects keep sounding after the last voice ended, so that a delay's echoes ring out.
    pub tail_left: usize,
    /// Each MIDI CC's last value, from 0 to 1, which the Mod Matrix's CC sources read.
    pub controls: [f64; CONTROL_COUNT],
    /// The coarse part of a tempo being sent, waiting for its fine part (engine/mod.rs, TEMPO_COARSE).
    pub tempo_coarse: f64,
    rate: f64,
}

/// How many MIDI CCs there are, and a CC's highest value.
pub const CONTROL_COUNT: usize = 128;
const CONTROL_TOP: f64 = 127.0;

impl Patch {
    /// Seed what makes the instrument's filter a unit of its own, its parts' spread, by its number.
    pub fn seed_unit(&mut self, number: usize) {
        if let Sound::Modular(modular) = &mut self.sound {
            if let Some(filter) = modular.filter.as_mut() {
                filter.ladder.unit = crate::filters::ladder::LadderUnit::seeded(number as u64 + 1);
            }
            if let crate::oscillators::OscillatorPart::Asheville(asheville) = &mut modular.oscillator {
                asheville.seed(number as u64 + 1);
            }
        }
    }

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
            volume: number(spec, "volume", 0.9),
            voices: (number(spec, "voices", 1.0) as usize).max(1),
            glides: truth(spec, "glides", true),
            glide: number(spec, "glide", 0.0),
            effects: effects::compiled(list(spec, "effects"), rate),
            lfos: LfoBank::compiled(list(spec, "lfos"), rate).with_rate_routes(modulation::rate_routes(list(spec, "matrix"))),
            buffer: vec![0.0; MOST_FRAMES],
            used: false,
            tail_left: 0,
            controls: [0.0; CONTROL_COUNT],
            tempo_coarse: 0.0,
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
        voice.filter.seed(voice.random);
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
        for (place, gate) in modular.gates.iter().enumerate() {
            if let Some(gate) = gate {
                gate.start(&mut voice.gates[place], &mut modular.gate_memory[place], voice.level, seconds);
            }
        }
        modular.oscillator.begin(&mut voice.oscillator, voice.pitch);
        modular.oscillator.free_run(&mut voice.oscillator, voice.random, voice.start as f64 / rate);
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
                    for memory in modular.memory.iter_mut().chain(modular.gate_memory.iter_mut()) {
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
        let bank = &self.lfos;
        // A Key LFO's step a sample, its ratio times the note's frequency over the rate, the same through the chunk.
        // Held under half the sample rate, MOST_KEY_STEP of a cycle a sample, so that no ratio runs a modulator past hearing.
        let frequency = oscillators::frequency_of(voice.pitch);
        let key_steps: [Option<f64>; LFO_COUNT] = std::array::from_fn(|place| bank.ratio(place).map(|ratio| (ratio * frequency / rate).min(MOST_KEY_STEP)));
        // An LFO+ fading in rises by the voice's own age, so that each note's vibrato eases in from its start.
        let fades = bank.fades();
        let fading = fades.iter().any(|fade| *fade > 0.0);
        let buffer = &mut self.buffer;
        let is_newest = voice.id == modular.newest;
        let wants_env2 = modular.reads_env2 && (modular.own_filter || is_newest || modular.matrix_reads_env2);
        // What each envelope's level is scaled by to light an amp or a gate: the note's velocity, unless the envelope
        // takes velocity itself.
        let velocity_of: [f64; 3] = std::array::from_fn(|place| if modular.envelopes[place].takes_velocity() { 1.0 } else { voice.level });
        // The oscillator is needed unless the first gate the sound meets is fed a ping alone.
        let first_gate = modular.gates[FILTER_GATE].as_ref().or(modular.gates[AMP_GATE].as_ref());
        let wants_oscillator = first_gate.is_none_or(|gate| gate.feeds_oscillator);
        // The envelopes' levels with velocity, which light a gate, worked out only where a gate stands, so that the
        // many voices with none pay nothing for it.
        let lit_of = |levels: &[f64; 3]| -> [f64; 3] { std::array::from_fn(|place| levels[place] * velocity_of[place]) };
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
        modular.oscillator.choose_band(&mut voice.oscillator, voice.pitch, voice.reach);
        let mut reach: f64 = 0.0;
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
            sources.oscillator = voice.last_wave;
            sources.oscs = voice.oscillator.sides;
            for (number, (lfo, values)) in sources.lfos.iter_mut().zip(lfos.iter()).take(LFO_COUNT).enumerate() {
                *lfo = match key_steps[number] {
                    Some(step) => bank.key_lfo_value(number, &mut voice.lfo_cycles[number], step),
                    None => values[offset + place],
                };
            }
            if fading {
                for (lfo, fade) in sources.lfos.iter_mut().zip(fades.iter()) {
                    *lfo *= modulation::faded_in(note.age, *fade);
                }
            }
            let moved = if modular.matrix.routes.is_empty() {
                Moved::default()
            } else {
                modular.matrix.moved(&sources)
            };
            let mut bend = moved.pitch;
            if gliding {
                bend += (voice.glide_from - voice.pitch) * (-((sample - voice.glide_at) as f64).max(0.0) / (glide * rate)).exp();
            }
            reach = reach.max(bend);
            let moves = Moves {
                pitch: bend,
                width: moved.pulse_width,
                spread: moved.detune,
            };
            let seconds = note.age;
            let mut wave = 0.0;
            if wants_oscillator {
                let (out, silenced) = modular.oscillator.sample(&mut voice.oscillator, voice.pitch, seconds, moves, rate);
                wave = out;
                voice.last_wave = out.clamp(-1.0, 1.0);
                if silenced {
                    voice.silent = true;
                }
            }
            if let Some(gate) = &modular.gates[FILTER_GATE] {
                let gate_note = voice.gate_note(sample, moved.cutoff);
                let light = gate.light(&mut voice.gates[FILTER_GATE], note, &lit_of(&sources.envelopes));
                wave = gate.process(&mut voice.gates[FILTER_GATE], wave, light, gate_note);
            } else if let Some(filter) = &modular.filter {
                let mut octaves = moved.cutoff;
                if modular.env2_to_filter {
                    octaves += sources.envelopes[1] * (filter.amount + voice.accent_depth) * ENVELOPE_OCTAVES;
                }
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
            let moved_amp = if moved.amp != 0.0 { (1.0 + moved.amp).clamp(0.0, MOST_AMP) } else { 1.0 };
            let out = match &modular.gates[AMP_GATE] {
                Some(gate) => {
                    let gate_note = voice.gate_note(sample, moved.cutoff);
                    let light = gate.light(&mut voice.gates[AMP_GATE], note, &lit_of(&sources.envelopes));
                    gate.process(&mut voice.gates[AMP_GATE], wave, light, gate_note) * moved_amp
                }
                None => modular.amp.process(wave, sources.envelopes[0] * velocity_of[0], moved_amp),
            };
            buffer[offset + place] += out as f32;
        }
        voice.reach = reach;
        // A gate in the Amp's place ends the note when it has closed; otherwise Env 1, which opens the Amp, does.
        let env1_done = voice.envelopes[0].done;
        let closed = match &modular.gates[AMP_GATE] {
            Some(gate) => gate.is_done(&voice.gates[AMP_GATE], env1_done),
            None => env1_done,
        };
        if closed {
            voice.silent = true;
        }
        if is_newest && !modular.own_filter && count > 0 {
            modular.last_octaves = modular.shared_octaves[offset + count - 1];
            modular.last_resonance = modular.shared_resonance[offset + count - 1];
        }
    }

    /// The song's tempo now, in quarter notes a minute, which its LFOs and its effects that follow the tempo take.
    pub fn set_tempo(&mut self, tempo: f64) {
        self.lfos.set_tempo(tempo);
        for effect in self.effects.iter_mut() {
            effect.set_tempo(tempo);
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
        // A chunk a voice played starts the effects' tail afresh; a chunk of their tail alone counts it down.
        if self.used {
            self.tail_left = self.effects.iter().map(Effect::tail_samples).max().unwrap_or(0);
        } else {
            self.tail_left = self.tail_left.saturating_sub(frames);
        }
    }

    /// Whether the effects are still sounding after the last voice ended, and so must still run.
    pub fn rings(&self) -> bool {
        self.tail_left > 0
    }
}

/// The envelope whose accent adds a sweep of its own to the filter through Env2.
const ACCENTING_ENVELOPE: &str = "acid_gate";

fn modular(spec: &Value, oscillators: &Value, rate: f64) -> Modular {
    let empty = Value::Nil;
    let oscillator = oscillators::compiled(oscillators, rate);
    let filter_spec = field(spec, "filter").unwrap_or(&empty);
    let resonance = number(filter_spec, "resonance", 0.0);
    let envelope_specs = list(spec, "envelopes");
    let envelope = |place: usize| envelopes::compiled(envelope_specs.get(place).unwrap_or(&empty), resonance);
    let mut filter = FilterPart::compiled(filter_spec, rate);
    let amp_spec = field(spec, "amp").unwrap_or(&empty);
    let gates = [GatePart::compiled(filter_spec, rate), GatePart::compiled(amp_spec, rate)];
    let gates_read = |place: usize| gates.iter().flatten().any(|gate| gate.reads_envelope(place));
    let matrix = ModMatrix::compiled(list(spec, "matrix"));
    // A cutoff moved at audio rate, by an oscillator or an LFO past hearing's bottom, is worked out every sample, so that
    // filter FM is smooth rather than stepped.
    let lfo_rates: Vec<f64> = list(spec, "lfos").iter().map(|lfo| number(lfo, "rate", 0.0)).collect();
    let audio_rate = |source: Source| match source {
        Source::Oscillator | Source::Osc(_) => true,
        Source::Lfo(place) => lfo_rates.get(place).is_some_and(|hertz| *hertz >= AUDIO_RATE_HERTZ),
        _ => false,
    };
    if let Some(filter) = filter.as_mut() {
        filter.every_sample = matrix
            .routes
            .iter()
            .any(|route| route.destination == Destination::Cutoff && (audio_rate(route.source) || route.via.is_some_and(audio_rate)));
    }
    let matrix_reads_env2 = matrix.uses(Source::Env2);
    let env2_to_filter = !truth(spec, "disconnect_filter", false);
    // Env2 sweeps the cutoff only through an Env amount or an accent's extra sweep; with neither, nothing hears it, and
    // its level is never worked out.
    let can_accent = envelope_specs.iter().any(|envelope| word(envelope, "type", "") == ACCENTING_ENVELOPE);
    let env2_sweeps = env2_to_filter && filter.as_ref().is_some_and(|filter| filter.amount != 0.0 || can_accent);
    Modular {
        oscillator,
        envelopes: [envelope(0), envelope(1), envelope(2)],
        memory: [EnvelopeMemory::default(); 3],
        own_filter: gates[FILTER_GATE].is_some() || truth(spec, "filter_per_note", true),
        reads_env2: env2_sweeps || matrix_reads_env2 || gates_read(1),
        env2_to_filter,
        matrix_reads_env2,
        reads_env3: matrix.uses(Source::Env3) || gates_read(2),
        filter,
        gates,
        gate_memory: [EnvelopeMemory::default(); 2],
        amp: amp::compiled(amp_spec),
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

#[cfg(test)]
mod tests {
    use super::*;

    /// The filter's coefficients are worked out every sample where the Mod Matrix moves its cutoff at audio rate, by the
    /// oscillator or an LFO past hearing's bottom, and every few samples where only a slow source moves it.
    #[test]
    fn an_audio_rate_route_to_the_cutoff_works_the_filter_out_every_sample() {
        let every_sample = |source: &str, lfo_hertz: f64| {
            let route = Value::Map(vec![
                ("source".into(), source.into()),
                ("destination".into(), "cutoff".into()),
                ("amount".into(), 0.5.into()),
            ]);
            let lfo = Value::Map(vec![("rate".into(), lfo_hertz.into())]);
            let spec = Value::Map(vec![
                ("filter".into(), Value::Map(vec![("type".into(), "ladder".into())])),
                ("matrix".into(), Value::Array(vec![route])),
                ("lfos".into(), Value::Array(vec![lfo])),
            ]);
            let Sound::Modular(modular) = Patch::compiled(&spec, 48000.0).sound else {
                panic!("a modular sound")
            };
            modular.filter.expect("a filter").every_sample
        };
        let (slow, audio) = (5.0, 440.0);
        assert!(every_sample("osc", slow));
        assert!(every_sample("lfo1", audio));
        assert!(!every_sample("lfo1", slow));
        assert!(!every_sample("velocity", slow));
    }
}
