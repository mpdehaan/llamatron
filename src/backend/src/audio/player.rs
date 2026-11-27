// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The engine behind the sound card's stream, through cpal (CoreAudio on macOS, ALSA on Linux).
//!
//! The audio callback owns the engine. Each chunk it learns when the chunk's first sample reaches the speakers, on the
//! same clock as the notes' times (clock.rs), and places every note that has arrived at the sample its time falls on, plus
//! the delay every instrument is held back by: the stream's own output latency and one chunk, so that a note sent at its
//! time is never late. Commands arrive from the reader thread through a lock-free queue; what the engine lets go of
//! leaves through another, for the housekeeper to free. The callback never allocates, never waits on a lock, and catches
//! any panic at its edge, playing silence and counting a failure, so that the stream never stops.

use crate::audio::clock;
use crate::drums::Hit;
use crate::engine::{Engine, Event, MidiEvent, Trash};
use crate::fluid::Fluid;
use crate::instrument::patch::Patch;
use crate::modulation::MOST_FRAMES;
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use std::panic::{self, AssertUnwindSafe};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

const COMMANDS: usize = 1 << 16;
const TRASH: usize = 1 << 12;
const FIRST_CALLBACK_SECONDS: f64 = 3.0;
const HOUSEKEEPING: Duration = Duration::from_millis(50);
/// The callback's time is counted in a histogram of these steps, for the 99th percentile.
const HISTOGRAM_STEP_NS: u64 = 10_000;
const HISTOGRAM_BINS: usize = 1000;
const PIECE: usize = 1024;

/// What the reader thread asks of the callback.
pub enum Command {
    Note {
        when: f64,
        kind: i64,
        instrument: usize,
        pitch: f64,
        velocity: f64,
        hit: Option<Hit>,
    },
    Forget {
        when: f64,
        first: usize,
        last: usize,
    },
    Instrument {
        number: usize,
        patch: Box<Patch>,
    },
    Fluid(Box<Fluid>),
    Midi {
        when: f64,
        status: u8,
        first: u8,
        second: u8,
    },
    ForgetMidi {
        when: f64,
    },
    Silence,
}

/// The callback's queue of commands, shared by the threads that send it commands (the reader, and the sender's thread);
/// the lock is only ever held by those threads, never by the callback, which reads the queue's other end without one.
pub type Commands = Arc<Mutex<rtrb::Producer<Command>>>;

/// Hand the callback a command, waiting while its queue is full, which only a flood of notes could cause.
pub fn send(commands: &Commands, mut command: Command) {
    let Ok(mut queue) = commands.lock() else { return };
    loop {
        match queue.push(command) {
            Ok(()) => return,
            Err(rtrb::PushError::Full(back)) => {
                command = back;
                std::thread::sleep(Duration::from_millis(1));
            }
        }
    }
}

/// Why the stream could not start.
#[derive(Debug, thiserror::Error)]
pub enum StartProblem {
    #[error("no sound output device")]
    NoDevice,
    #[error("the sound output device's settings could not be read: {0}")]
    Settings(String),
    #[error("the sound output stream could not be opened: {0}")]
    Stream(String),
    #[error("the sound output stream did not start in time")]
    TooSlow,
}

impl StartProblem {
    /// The word the tracker reads to choose its message (user_strings/errors.py).
    pub fn code(&self) -> &'static str {
        match self {
            StartProblem::NoDevice => "no_device",
            StartProblem::Settings(_) => "settings",
            StartProblem::Stream(_) => "stream",
            StartProblem::TooSlow => "too_slow",
        }
    }
}

/// What the callback counts, read by the reporter and at close.
pub struct Statistics {
    pub chunks: AtomicU64,
    pub stream_errors: AtomicU64,
    pub failures: AtomicU64,
    pub late: AtomicU64,
    pub runaways: AtomicU64,
    pub dropped: AtomicU64,
    pub faults: AtomicU64,
    pub voices: AtomicU64,
    pub busy_ns: AtomicU64,
    pub longest_ns: AtomicU64,
    pub window_longest_ns: AtomicU64,
    pub muted: AtomicBool,
    histogram: Vec<AtomicU64>,
    latency_bits: AtomicU64,
    started: AtomicBool,
}

impl Statistics {
    fn new() -> Statistics {
        Statistics {
            chunks: AtomicU64::new(0),
            stream_errors: AtomicU64::new(0),
            failures: AtomicU64::new(0),
            late: AtomicU64::new(0),
            runaways: AtomicU64::new(0),
            dropped: AtomicU64::new(0),
            faults: AtomicU64::new(0),
            voices: AtomicU64::new(0),
            busy_ns: AtomicU64::new(0),
            longest_ns: AtomicU64::new(0),
            window_longest_ns: AtomicU64::new(0),
            muted: AtomicBool::new(false),
            histogram: (0..HISTOGRAM_BINS).map(|_| AtomicU64::new(0)).collect(),
            latency_bits: AtomicU64::new(0),
            started: AtomicBool::new(false),
        }
    }

    fn took(&self, nanoseconds: u64) {
        self.busy_ns.fetch_add(nanoseconds, Ordering::Relaxed);
        self.longest_ns.fetch_max(nanoseconds, Ordering::Relaxed);
        self.window_longest_ns.fetch_max(nanoseconds, Ordering::Relaxed);
        let bin = ((nanoseconds / HISTOGRAM_STEP_NS) as usize).min(HISTOGRAM_BINS - 1);
        self.histogram[bin].fetch_add(1, Ordering::Relaxed);
    }

    /// The callback's time at the 99th percentile, in milliseconds, to the histogram's step.
    pub fn p99_ms(&self) -> f64 {
        let counts: Vec<u64> = self.histogram.iter().map(|bin| bin.load(Ordering::Relaxed)).collect();
        let total: u64 = counts.iter().sum();
        let mut seen = 0;
        for (bin, count) in counts.iter().enumerate() {
            seen += count;
            if total > 0 && seen * 100 >= total * 99 {
                return ((bin as u64 + 1) * HISTOGRAM_STEP_NS) as f64 / 1e6;
            }
        }
        0.0
    }
}

/// The playing stream and the ends of its queues.
pub struct Player {
    _stream: cpal::Stream,
    pub commands: Commands,
    pub statistics: Arc<Statistics>,
    pub rate: f64,
    pub block: usize,
    pub delay: f64,
    running: Arc<AtomicBool>,
    housekeeper: Option<std::thread::JoinHandle<()>>,
}

impl Player {
    /// Open the output stream and wait for its first chunk, which tells the delay.
    pub fn start(block: usize, device_name: Option<&str>) -> Result<Player, StartProblem> {
        let host = cpal::default_host();
        let device = match device_name {
            Some(name) => host
                .output_devices()
                .map_err(|problem| StartProblem::Settings(problem.to_string()))?
                .find(|device| device.name().is_ok_and(|found| found == name)),
            None => host.default_output_device(),
        }
        .ok_or(StartProblem::NoDevice)?;
        let supported = device.default_output_config().map_err(|problem| StartProblem::Settings(problem.to_string()))?;
        let rate = supported.sample_rate().0 as f64;
        let channels = supported.channels() as usize;
        let format = supported.sample_format();
        let mut config: cpal::StreamConfig = supported.into();
        config.buffer_size = cpal::BufferSize::Fixed(block as u32);
        let (commands, inbox) = rtrb::RingBuffer::new(COMMANDS);
        let (bin, trash) = rtrb::RingBuffer::new(TRASH);
        let statistics = Arc::new(Statistics::new());
        let engine = Engine::new(rate, Some(bin));
        let callback = Callback {
            engine,
            inbox,
            statistics: statistics.clone(),
            played: 0,
            delay: block as f64 / rate,
            left: vec![0.0; MOST_FRAMES],
            right: vec![0.0; MOST_FRAMES],
            channels,
        };
        let stream = open_stream(&device, &config, format, callback, statistics.clone())?;
        stream.play().map_err(|problem| StartProblem::Stream(problem.to_string()))?;
        let latency = wait_for_first_chunk(&statistics)?;
        let running = Arc::new(AtomicBool::new(true));
        let housekeeper = Some(start_housekeeper(trash, running.clone()));
        Ok(Player {
            _stream: stream,
            commands: Arc::new(Mutex::new(commands)),
            statistics,
            rate,
            block,
            delay: latency + block as f64 / rate,
            running,
            housekeeper,
        })
    }

    /// Hand the callback a command, waiting while its queue is full, which only a flood of notes could cause.
    pub fn send(&mut self, command: Command) {
        send(&self.commands, command);
    }

    /// Stop the housekeeper; the stream closes when the player is dropped.
    pub fn stop(&mut self) {
        self.running.store(false, Ordering::Relaxed);
        if let Some(housekeeper) = self.housekeeper.take() {
            let _ = housekeeper.join();
        }
    }
}

fn wait_for_first_chunk(statistics: &Statistics) -> Result<f64, StartProblem> {
    let began = Instant::now();
    while !statistics.started.load(Ordering::Acquire) {
        if began.elapsed().as_secs_f64() > FIRST_CALLBACK_SECONDS {
            return Err(StartProblem::TooSlow);
        }
        std::thread::sleep(Duration::from_millis(2));
    }
    Ok(f64::from_bits(statistics.latency_bits.load(Ordering::Acquire)))
}

/// The housekeeper frees what the callback lets go of, so that the callback never frees.
fn start_housekeeper(mut trash: rtrb::Consumer<Trash>, running: Arc<AtomicBool>) -> std::thread::JoinHandle<()> {
    std::thread::spawn(move || {
        while running.load(Ordering::Relaxed) {
            while let Ok(thrown) = trash.pop() {
                drop(thrown);
            }
            std::thread::sleep(HOUSEKEEPING);
        }
    })
}

fn open_stream(
    device: &cpal::Device,
    config: &cpal::StreamConfig,
    format: cpal::SampleFormat,
    mut callback: Callback,
    statistics: Arc<Statistics>,
) -> Result<cpal::Stream, StartProblem> {
    let on_error = move |problem: cpal::StreamError| {
        statistics.stream_errors.fetch_add(1, Ordering::Relaxed);
        log::warn!("sound output stream: {problem}");
    };
    let stream = match format {
        cpal::SampleFormat::F32 => device.build_output_stream(
            config,
            move |out: &mut [f32], info: &cpal::OutputCallbackInfo| callback.play(out, info, |sample| sample),
            on_error,
            None,
        ),
        cpal::SampleFormat::I16 => device.build_output_stream(
            config,
            move |out: &mut [i16], info: &cpal::OutputCallbackInfo| callback.play(out, info, |sample| (sample * i16::MAX as f32) as i16),
            on_error,
            None,
        ),
        cpal::SampleFormat::I32 => device.build_output_stream(
            config,
            move |out: &mut [i32], info: &cpal::OutputCallbackInfo| callback.play(out, info, |sample| (sample as f64 * i32::MAX as f64) as i32),
            on_error,
            None,
        ),
        other => {
            return Err(StartProblem::Settings(format!(
                "the device's sample format {other} is not one the daemon plays"
            )))
        }
    };
    stream.map_err(|problem| StartProblem::Stream(problem.to_string()))
}

/// What the audio callback owns.
struct Callback {
    engine: Engine,
    inbox: rtrb::Consumer<Command>,
    statistics: Arc<Statistics>,
    played: i64,
    delay: f64,
    left: Vec<f32>,
    right: Vec<f32>,
    channels: usize,
}

impl Callback {
    fn play<T: Copy>(&mut self, out: &mut [T], info: &cpal::OutputCallbackInfo, convert: impl Fn(f32) -> T) {
        let began = clock::now();
        let stamps = info.timestamp();
        let latency = stamps.playback.duration_since(&stamps.callback).map(|span| span.as_secs_f64()).unwrap_or(0.0);
        if !self.statistics.started.load(Ordering::Relaxed) {
            self.statistics.latency_bits.store(latency.to_bits(), Ordering::Release);
            self.statistics.started.store(true, Ordering::Release);
            // The delay every note is held back by is fixed now, the stream's latency and one chunk.
            self.delay += latency;
        }
        let dac = began + latency;
        let frames = out.len() / self.channels.max(1);
        let outcome = panic::catch_unwind(AssertUnwindSafe(|| {
            self.take_commands(dac);
            let mut done = 0;
            while done < frames {
                let piece = PIECE.min(frames - done);
                self.engine.render(self.played + done as i64, &mut self.left[..piece], &mut self.right[..piece]);
                for place in 0..piece {
                    let frame = (done + place) * self.channels;
                    // Left and right go to the first two channels; a mono device takes the left, and any further channel
                    // stays silent.
                    for channel in 0..self.channels {
                        let sample = match channel {
                            0 => self.left[place],
                            1 => self.right[place],
                            _ => 0.0,
                        };
                        out[frame + channel] = convert(sample);
                    }
                }
                done += piece;
            }
        }));
        if outcome.is_err() {
            // The audio callback's edge: a panic plays silence, the engine starts clean, the stream goes on.
            self.statistics.failures.fetch_add(1, Ordering::Relaxed);
            self.engine.silence();
            for sample in out.iter_mut() {
                *sample = convert(0.0);
            }
        }
        self.played += frames as i64;
        self.publish();
        let took = ((clock::now() - began) * 1e9) as u64;
        self.statistics.took(took);
    }

    fn take_commands(&mut self, dac: f64) {
        let rate = self.engine.rate;
        let sample_of = |when: f64, played: i64, delay: f64| played + ((when + delay - dac) * rate).round() as i64;
        while let Ok(command) = self.inbox.pop() {
            match command {
                Command::Note {
                    when,
                    kind,
                    instrument,
                    pitch,
                    velocity,
                    hit,
                } => {
                    let sample = sample_of(when, self.played, self.delay);
                    self.engine.schedule(Event {
                        sample,
                        order: 0,
                        kind,
                        instrument,
                        pitch,
                        velocity,
                        hit,
                    });
                }
                Command::Forget { when, first, last } => {
                    let sample = sample_of(when, self.played, self.delay);
                    self.engine.forget(first, last, sample);
                }
                Command::Instrument { number, patch } => self.engine.set_instrument(number, patch),
                Command::Fluid(fluid) => self.engine.set_fluid(fluid),
                Command::Midi { when, status, first, second } => {
                    let sample = sample_of(when, self.played, self.delay);
                    self.engine.schedule_midi(MidiEvent {
                        sample,
                        order: 0,
                        status,
                        first,
                        second,
                    });
                }
                Command::ForgetMidi { when } => {
                    let sample = sample_of(when, self.played, self.delay);
                    self.engine.forget_midi(sample);
                }
                Command::Silence => self.engine.silence(),
            }
        }
    }

    fn publish(&self) {
        let counts = self.engine.counts;
        let statistics = &self.statistics;
        statistics.chunks.fetch_add(1, Ordering::Relaxed);
        statistics.late.store(counts.late, Ordering::Relaxed);
        statistics.runaways.store(counts.runaways, Ordering::Relaxed);
        statistics.dropped.store(counts.dropped_notes, Ordering::Relaxed);
        statistics.voices.store(counts.voices, Ordering::Relaxed);
        statistics.faults.store(self.engine.guard.faults, Ordering::Relaxed);
        statistics
            .muted
            .store(self.engine.guard.is_muted() || self.engine.right_guard.is_muted(), Ordering::Relaxed);
    }
}
