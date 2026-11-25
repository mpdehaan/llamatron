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
//! Its well-behaved edges: it exits when its input closes or its parent dies, so that it is never left an orphan; it
//! logs start-up, its settings and its problems, never a note, to rotating files in `~/.llamatron/`.

use crate::drums::{self, Hit};
use crate::engine::{Engine, Event, FORGET, NOTE_ON};
use crate::patch::{Drum, Patch, VELOCITY_STEP};
use crate::player::{Command, Player};
use crate::protocol::{self, mapping, message};
use crate::value::as_number;
use crate::wav;
use rmpv::Value;
use std::collections::HashMap;
use std::io::{self, Write};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;

const REPORT_EVERY: Duration = Duration::from_millis(500);
const OFFLINE_CHUNK: usize = 128;
const MILLISECONDS: f64 = 1000.0;

/// Where messages to the tracker are written, shared by the reader and the reporter.
pub type Output = Arc<Mutex<io::Stdout>>;

/// Write a message to the tracker; a closed output means the tracker has gone, which the reader learns from its input.
pub fn tell(output: &Output, message: &Value) {
    if let Ok(mut stdout) = output.lock() {
        if let Err(problem) = protocol::write_message(&mut *stdout, message) {
            log::warn!("could not write to the tracker: {problem}");
        }
    }
}

/// The drums' hits, rendered on this thread as notes arrive and kept, by instrument, pitch and velocity step.
#[derive(Default)]
struct HitStore {
    drums: HashMap<usize, Drum>,
    hits: HashMap<(usize, i64, i64), Hit>,
}

impl HitStore {
    fn set_instrument(&mut self, number: usize, patch: &Patch) {
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
    fn hit(&mut self, instrument: usize, pitch: f64, velocity: f64, rate: f64) -> Option<Hit> {
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

fn kind_of(message: &Value) -> &str {
    message.as_array().and_then(|items| items.first()).and_then(Value::as_str).unwrap_or("")
}

fn item(message: &Value, place: usize) -> Option<&Value> {
    message.as_array().and_then(|items| items.get(place))
}

/// Play through the sound card until told to close or the input ends.
pub fn play(block: usize, device: Option<&str>, output: Output) -> i32 {
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
    let mut input = io::stdin().lock();
    loop {
        let received = match protocol::read_message(&mut input) {
            Ok(Some(received)) => received,
            Ok(None) => break,
            Err(problem) => {
                log::error!("could not read the tracker's message: {problem}");
                break;
            }
        };
        if !take_message(&received, &mut player, &mut hits) {
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
fn take_message(received: &Value, player: &mut Player, hits: &mut HitStore) -> bool {
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
        other => log::warn!("a message of a kind the daemon does not know: {other}"),
    }
    true
}

/// Report the load every half second: the share of the time the callback was busy, its longest chunk against its budget,
/// and what the tracker's screen shows of dropouts.
fn start_reporter(player: &Player, output: Output, reporting: Arc<AtomicBool>) -> std::thread::JoinHandle<()> {
    let statistics = player.statistics.clone();
    let budget = player.block as f64 / player.rate;
    std::thread::spawn(move || {
        let mut last_busy = statistics.busy_ns.load(Ordering::Relaxed);
        let mut last_time = crate::clock::now();
        while reporting.load(Ordering::Relaxed) {
            std::thread::sleep(REPORT_EVERY);
            let now = crate::clock::now();
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

fn statistics_of(player: &Player) -> Value {
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
pub fn render(rate: f64, output: Output) -> i32 {
    log::info!("rendering at {rate} Hz");
    let mut engine = Engine::new(rate, None);
    let mut hits = HitStore::default();
    let mut input = io::stdin().lock();
    loop {
        let received = match protocol::read_message(&mut input) {
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
    let mut samples = Vec::with_capacity(frames);
    let mut chunk = vec![0.0; OFFLINE_CHUNK];
    let mut start = 0;
    while start < frames {
        engine.render(start as i64, &mut chunk);
        let take = OFFLINE_CHUNK.min(frames - start);
        samples.extend_from_slice(&chunk[..take]);
        start += OFFLINE_CHUNK;
    }
    let peak = samples.iter().fold(0.0_f32, |most, sample| most.max(sample.abs()));
    if let Err(problem) = wav::write_stereo(path, engine.rate as u32, &samples) {
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
