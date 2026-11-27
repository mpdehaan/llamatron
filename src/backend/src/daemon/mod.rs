// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The daemon's two ways of running, each reading the tracker's messages from standard input (protocol.rs):
//!
//! - Playing: the sound card's stream opens, the daemon answers `ready` with its rate and delay (or `failed` with why),
//!   then compiles instruments, renders drum hits and hands notes to the audio callback as they arrive, reporting its
//!   load every half second, until told to close or its input ends, when it answers with its statistics.
//! - Rendering: no sound card; instruments and notes timed from zero arrive, and `render` plays them through the very
//!   same engine and safety guard into a WAV file, as fast as it can, for the tracker's WAV export.
//!
//! - Sending: the real-time sender (sending.rs), which replaces the Python Realtime Sender Process.
//!
//! Its well-behaved edges: it exits when its input closes or its parent dies, so that it is never left an orphan; it
//! logs start-up, its settings and its problems, never a note, to rotating files in `~/.llamatron/`.

use crate::audio::player::{Command, Player};
use crate::audio::wav;
pub mod sending;

use crate::drums::{self, Hit};
use crate::engine::{Engine, Event, MidiEvent, FORGET, NOTE_ON};
use crate::fluid::{Fluid, FluidProblem};
use crate::instrument::patch::{Drum, Patch, VELOCITY_STEP};
use crate::protocol::values::as_number;
use crate::protocol::{self, mapping, message};
use rmpv::Value;
use std::collections::HashMap;
use std::io::{self, Write};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;

const REPORT_EVERY: Duration = Duration::from_millis(500);
const OFFLINE_CHUNK: usize = 128;
const MILLISECONDS: f64 = 1000.0;
/// FluidSynth's gain where the tracker gives none, the one its own process played at.
const FLUID_GAIN: f64 = 0.55;

/// Where messages to the tracker go, shared by the reader and the reporter: written to the daemon's standard output, or
/// handed to a front end running the backend in its own process.
pub type Output = Arc<dyn Fn(&Value) + Send + Sync>;

/// An output writing each message to the daemon's standard output; a closed output means the tracker has gone, which the
/// reader learns from its input.
pub fn standard_output() -> Output {
    let stdout = Mutex::new(io::stdout());
    Arc::new(move |message: &Value| {
        if let Ok(mut stdout) = stdout.lock() {
            if let Err(problem) = protocol::write_message(&mut *stdout, message) {
                log::warn!("could not write to the tracker: {problem}");
            }
        }
    })
}

/// Hand a message to the tracker.
pub fn tell(output: &Output, message: &Value) {
    output(message);
}

/// The drums' hits, rendered on this thread as notes arrive and kept, by instrument, pitch and velocity step.
#[derive(Default)]
pub struct HitStore {
    drums: HashMap<usize, Drum>,
    hits: HashMap<(usize, i64, i64), Hit>,
}

impl HitStore {
    pub fn set_instrument(&mut self, number: usize, patch: &Patch) {
        self.hits.retain(|key, _| key.0 != number);
        match patch.drum() {
            Some(drum) => {
                self.drums.insert(number, drum.clone());
            }
            None => {
                self.drums.remove(&number);
            }
        }
    }

    /// A drum's hit for a note, its tone rendered at the middle of the velocity's eighth, or None for an instrument that is
    /// not a drum.
    pub fn hit(&mut self, instrument: usize, pitch: f64, velocity: f64, rate: f64) -> Option<Hit> {
        let drum = self.drums.get(&instrument)?;
        let step = velocity as i64 / VELOCITY_STEP;
        let key = (instrument, pitch.round() as i64, step);
        let hit = self.hits.entry(key).or_insert_with(|| {
            drums::render_hit(
                &drum.machine,
                &drum.knobs,
                drum.recipe_pitch(pitch),
                (step * VELOCITY_STEP + VELOCITY_STEP / 2) as f64,
                rate,
            )
        });
        Some(hit.clone())
    }
}

/// A note as the tracker sends it: (seconds, kind, instrument, pitch, velocity).
struct Note {
    when: f64,
    kind: i64,
    instrument: usize,
    pitch: f64,
    velocity: f64,
}

fn notes_of(value: Option<&Value>) -> Vec<Note> {
    let Some(list) = value.and_then(Value::as_array) else { return Vec::new() };
    list.iter()
        .filter_map(|note| {
            let items = note.as_array()?;
            let number = |place: usize| items.get(place).and_then(as_number);
            Some(Note {
                when: number(0)?,
                kind: number(1)? as i64,
                instrument: number(2)? as usize,
                pitch: number(3)?,
                velocity: number(4).unwrap_or(0.0),
            })
        })
        .collect()
}

pub(crate) fn kind_of(message: &Value) -> &str {
    message.as_array().and_then(|items| items.first()).and_then(Value::as_str).unwrap_or("")
}

pub(crate) fn item(message: &Value, place: usize) -> Option<&Value> {
    message.as_array().and_then(|items| items.get(place))
}

/// Play through the sound card until told to close or the input ends.
pub fn play(block: usize, device: Option<&str>, output: Output, input: &mut dyn protocol::Inbox) -> i32 {
    let mut player = match Player::start(block, device) {
        Ok(player) => player,
        Err(problem) => {
            log::error!("could not start: {problem}");
            tell(&output, &message(protocol::FAILED, vec![problem.code().into(), problem.to_string().into()]));
            return 1;
        }
    };
    log::info!(
        "playing at {} Hz, a block of {} frames, notes held back {:.2} ms",
        player.rate,
        player.block,
        player.delay * MILLISECONDS
    );
    tell(&output, &message(protocol::READY, vec![player.rate.into(), player.delay.into()]));
    let reporting = Arc::new(AtomicBool::new(true));
    let reporter = start_reporter(&player, output.clone(), reporting.clone());
    let mut hits = HitStore::default();
    loop {
        let received = match input.next_message() {
            Ok(Some(received)) => received,
            Ok(None) => break,
            Err(problem) => {
                log::error!("could not read the tracker's message: {problem}");
                break;
            }
        };
        if !take_message(&received, &mut player, &mut hits, &output) {
            break;
        }
    }
    reporting.store(false, Ordering::Relaxed);
    let _ = reporter.join();
    let statistics = statistics_of(&player);
    player.stop();
    drop(player);
    tell(&output, &message(protocol::STATISTICS, vec![statistics]));
    log::info!("closed");
    0
}

/// Act on one message while playing, and return whether to go on.
fn take_message(received: &Value, player: &mut Player, hits: &mut HitStore, output: &Output) -> bool {
    match kind_of(received) {
        protocol::CLOSE => return false,
        protocol::INSTRUMENT => {
            let number = item(received, 1).and_then(as_number).unwrap_or(-1.0);
            if number < 0.0 {
                return true;
            }
            let patch = Box::new(Patch::compiled(item(received, 2).unwrap_or(&Value::Nil), player.rate));
            hits.set_instrument(number as usize, &patch);
            player.send(Command::Instrument {
                number: number as usize,
                patch,
            });
        }
        protocol::NOTES => {
            for note in notes_of(item(received, 1)) {
                if note.kind == FORGET {
                    // A forget names the first and last instruments in place of the instrument and pitch.
                    player.send(Command::Forget {
                        when: note.when,
                        first: note.instrument,
                        last: note.pitch as usize,
                    });
                    continue;
                }
                let hit = if note.kind == NOTE_ON {
                    hits.hit(note.instrument, note.pitch, note.velocity, player.rate)
                } else {
                    None
                };
                player.send(Command::Note {
                    when: note.when,
                    kind: note.kind,
                    instrument: note.instrument,
                    pitch: note.pitch,
                    velocity: note.velocity,
                    hit,
                });
            }
        }
        protocol::SILENCE => player.send(Command::Silence),
        protocol::SOUNDFONT => {
            let answer = match fluid_of(received, player.rate) {
                Ok(fluid) => {
                    player.send(Command::Fluid(fluid));
                    message(protocol::SOUNDFONT_READY, vec![])
                }
                Err(problem) => failed_fluid(&problem),
            };
            tell(output, &answer);
        }
        protocol::MIDI => {
            for midi in midi_of(item(received, 1)) {
                player.send(Command::Midi {
                    when: midi.when,
                    status: midi.status,
                    first: midi.first,
                    second: midi.second,
                });
            }
        }
        protocol::FORGET_MIDI => player.send(Command::ForgetMidi {
            when: item(received, 1).and_then(as_number).unwrap_or(0.0),
        }),
        other => log::warn!("a message of a kind the daemon does not know: {other}"),
    }
    true
}

/// A MIDI message for FluidSynth as the tracker sends it: (seconds, status, first, second).
struct Midi {
    when: f64,
    status: u8,
    first: u8,
    second: u8,
}

fn midi_of(value: Option<&Value>) -> Vec<Midi> {
    let Some(list) = value.and_then(Value::as_array) else { return Vec::new() };
    list.iter()
        .filter_map(|midi| {
            let items = midi.as_array()?;
            let number = |place: usize| items.get(place).and_then(as_number);
            let byte = |place: usize| number(place).map(|whole| whole.clamp(0.0, 255.0) as u8);
            Some(Midi {
                when: number(0)?,
                status: byte(1)?,
                first: byte(2).unwrap_or(0),
                second: byte(3).unwrap_or(0),
            })
        })
        .collect()
}

/// FluidSynth made ready from a soundfont message: its library, its SoundFont and its gain.
fn fluid_of(received: &Value, rate: f64) -> Result<Box<Fluid>, FluidProblem> {
    let library = item(received, 1).and_then(Value::as_str).unwrap_or("");
    let soundfont = item(received, 2).and_then(Value::as_str).unwrap_or("");
    let gain = item(received, 3).and_then(as_number).unwrap_or(FLUID_GAIN);
    let fluid = Fluid::load(library, soundfont, rate, gain)?;
    log::info!("FluidSynth ready with {soundfont}");
    Ok(Box::new(fluid))
}

fn failed_fluid(problem: &FluidProblem) -> Value {
    log::error!("{problem}");
    message(protocol::FAILED, vec!["fluidsynth".into(), problem.to_string().into()])
}

/// Report the load every half second: the share of the time the callback was busy, its longest chunk against its budget,
/// and what the tracker's screen shows of dropouts.
pub(crate) fn start_reporter(player: &Player, output: Output, reporting: Arc<AtomicBool>) -> std::thread::JoinHandle<()> {
    let statistics = player.statistics.clone();
    let budget = player.block as f64 / player.rate;
    std::thread::spawn(move || {
        let mut last_busy = statistics.busy_ns.load(Ordering::Relaxed);
        let mut last_time = crate::audio::clock::now();
        while reporting.load(Ordering::Relaxed) {
            std::thread::sleep(REPORT_EVERY);
            let now = crate::audio::clock::now();
            let busy = statistics.busy_ns.load(Ordering::Relaxed);
            let load = (busy - last_busy) as f64 / 1e9 / (now - last_time).max(1e-9);
            let peak = statistics.window_longest_ns.swap(0, Ordering::Relaxed) as f64 / 1e9 / budget;
            last_busy = busy;
            last_time = now;
            let report = mapping(vec![
                ("load", load.into()),
                ("peak", peak.into()),
                ("voices", statistics.voices.load(Ordering::Relaxed).into()),
                ("dropouts", statistics.stream_errors.load(Ordering::Relaxed).into()),
                ("late_notes", statistics.late.load(Ordering::Relaxed).into()),
                ("muted", statistics.muted.load(Ordering::Relaxed).into()),
            ]);
            tell(&output, &message(protocol::LOAD, vec![report]));
        }
    })
}

pub(crate) fn statistics_of(player: &Player) -> Value {
    let statistics = &player.statistics;
    let count = |counter: &std::sync::atomic::AtomicU64| Value::from(counter.load(Ordering::Relaxed));
    mapping(vec![
        ("rate", player.rate.into()),
        ("block", (player.block as u64).into()),
        ("delay_ms", (player.delay * MILLISECONDS).into()),
        ("chunks", count(&statistics.chunks)),
        ("underflows", count(&statistics.stream_errors)),
        ("late_notes", count(&statistics.late)),
        ("longest_callback_ms", (statistics.longest_ns.load(Ordering::Relaxed) as f64 / 1e6).into()),
        ("p99_callback_ms", statistics.p99_ms().into()),
        ("budget_ms", (player.block as f64 / player.rate * MILLISECONDS).into()),
        ("failures", count(&statistics.failures)),
        ("runaways", count(&statistics.runaways)),
        ("faults", count(&statistics.faults)),
        ("dropped_notes", count(&statistics.dropped)),
    ])
}

/// Render notes timed from zero into WAV files as the tracker asks, with no sound card.
pub fn render(rate: f64, output: Output, input: &mut dyn protocol::Inbox) -> i32 {
    log::info!("rendering at {rate} Hz");
    let mut engine = Engine::new(rate, None);
    let mut hits = HitStore::default();
    loop {
        let received = match input.next_message() {
            Ok(Some(received)) => received,
            Ok(None) => return 0,
            Err(problem) => {
                log::error!("could not read the tracker's message: {problem}");
                return 1;
            }
        };
        match kind_of(&received) {
            protocol::CLOSE => return 0,
            protocol::INSTRUMENT => {
                let number = item(&received, 1).and_then(as_number).unwrap_or(-1.0);
                if number >= 0.0 {
                    let patch = Box::new(Patch::compiled(item(&received, 2).unwrap_or(&Value::Nil), rate));
                    hits.set_instrument(number as usize, &patch);
                    engine.set_instrument(number as usize, patch);
                }
            }
            protocol::NOTES => {
                for note in notes_of(item(&received, 1)) {
                    let hit = if note.kind == NOTE_ON {
                        hits.hit(note.instrument, note.pitch, note.velocity, rate)
                    } else {
                        None
                    };
                    let sample = (note.when * rate).round() as i64;
                    engine.schedule(Event {
                        sample,
                        order: 0,
                        kind: note.kind,
                        instrument: note.instrument,
                        pitch: note.pitch,
                        velocity: note.velocity,
                        hit,
                    });
                }
            }
            protocol::SOUNDFONT => {
                let answer = match fluid_of(&received, rate) {
                    Ok(fluid) => {
                        engine.set_fluid(fluid);
                        message(protocol::SOUNDFONT_READY, vec![])
                    }
                    Err(problem) => failed_fluid(&problem),
                };
                tell(&output, &answer);
            }
            protocol::MIDI => {
                for midi in midi_of(item(&received, 1)) {
                    let sample = (midi.when * rate).round() as i64;
                    engine.schedule_midi(MidiEvent {
                        sample,
                        order: 0,
                        status: midi.status,
                        first: midi.first,
                        second: midi.second,
                    });
                }
            }
            protocol::RENDER => {
                let path = item(&received, 1).and_then(Value::as_str).unwrap_or("").to_string();
                let seconds = item(&received, 2).and_then(as_number).unwrap_or(0.0);
                let answer = render_file(&mut engine, &path, seconds);
                tell(&output, &answer);
                engine = Engine::new(rate, None);
            }
            other => log::warn!("a message of a kind the daemon does not know: {other}"),
        }
    }
}

fn render_file(engine: &mut Engine, path: &str, seconds: f64) -> Value {
    let frames = (seconds * engine.rate).ceil() as usize;
    let (mut left, mut right) = (Vec::with_capacity(frames), Vec::with_capacity(frames));
    let (mut chunk_left, mut chunk_right) = (vec![0.0; OFFLINE_CHUNK], vec![0.0; OFFLINE_CHUNK]);
    let mut start = 0;
    while start < frames {
        engine.render(start as i64, &mut chunk_left, &mut chunk_right);
        let take = OFFLINE_CHUNK.min(frames - start);
        left.extend_from_slice(&chunk_left[..take]);
        right.extend_from_slice(&chunk_right[..take]);
        start += OFFLINE_CHUNK;
    }
    let peak = left.iter().chain(right.iter()).fold(0.0_f32, |most, sample| most.max(sample.abs()));
    if let Err(problem) = wav::write_stereo(path, engine.rate as u32, &left, &right) {
        log::error!("could not write the rendered file: {problem}");
        return message(protocol::FAILED, vec!["write".into(), problem.to_string().into()]);
    }
    let counts = engine.counts;
    message(
        protocol::RENDERED,
        vec![mapping(vec![
            ("frames", (frames as u64).into()),
            ("peak", (peak as f64).into()),
            ("runaways", counts.runaways.into()),
            ("faults", engine.guard.faults.into()),
        ])],
    )
}

/// Exit when the parent dies, so that the daemon is never left an orphan: on Linux the kernel signals it at once, and on
/// every system a watcher sees the parent's id change as the orphan is taken in by the system's first process.
pub fn watch_parent() {
    #[cfg(target_os = "linux")]
    // SAFETY: prctl with PR_SET_PDEATHSIG takes a signal number and touches no memory of ours.
    unsafe {
        libc::prctl(libc::PR_SET_PDEATHSIG, libc::SIGTERM);
    }
    // SAFETY: getppid has no preconditions.
    let parent = unsafe { libc::getppid() };
    std::thread::spawn(move || loop {
        std::thread::sleep(Duration::from_millis(250));
        // SAFETY: as above.
        if unsafe { libc::getppid() } != parent {
            log::info!("the tracker has gone; exiting");
            let _ = io::stderr().flush();
            std::process::exit(0);
        }
    });
}
