// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The real-time sender (the Python realtime/sender_process/rust_sender.py): the backend's sending loop, run on a thread of
//! llamatron's own process, which sends the player's events on time through the MIDI ports, the built-in synths and
//! FluidSynth. Its messages are handed across a channel as the backend's values; the events cross as slim records, each
//! port named by its place and each play's tag by a number. Closing ends the loop and waits a little for its thread.

use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{mpsc, Arc, Mutex};
use std::time::{Duration, Instant};

use crate::realtime::player::Sender;
use crate::realtime::timeline::{ClipTag, Playing};
use llamatron_model::file::data::Data;
use llamatron_names::file_format;
use llamatron_names::words;
use llamatron_strings::errors;
use rmpv::Value;

/// The sender's words.
const OPEN: &str = file_format::PartSetting::OPEN;
const START: &str = file_format::RampPart::START;
const ADD: &str = words::ADD;
const FORGET: &str = words::FORGET;
const STOP_TAG: &str = words::STOP_TAG;
const STOP_ALL: &str = words::STOP_ALL;
const SILENCE: &str = words::SILENCE;
const SOUNDS: &str = words::SOUNDS;
const CLOSE: &str = words::CLOSE;
const READY: &str = words::READY;
/// The kinds of port the sender opens, and the drivers.
pub const MIDI: &str = file_format::InstrumentKind::MIDI;
pub const BUILT_IN: &str = file_format::TrackSetting::BUILT_IN;
pub const FLUIDSYNTH: &str = words::FLUIDSYNTH;
const TIMESTAMPED: &str = words::TIMESTAMPED;
/// The records' version; how long the sender has to open its ports and sound card, and to end once closed.
const RECORDS_VERSION: u8 = 1;
const OPEN_TIMEOUT: Duration = Duration::from_secs(20);
const CLOSE_TIMEOUT: Duration = Duration::from_secs(2);
const WAIT_STEP: Duration = Duration::from_millis(10);
/// FluidSynth's library, which the sender loads to play FluidSynth itself, by its names and where it is looked for, and
/// how loud FluidSynth plays.
const LIBRARY_VARIABLE: &str = "LLAMATRON_FLUIDSYNTH_LIBRARY";
const LIBRARY_NAMES: [&str; 4] = ["libfluidsynth.dylib", "libfluidsynth.3.dylib", "libfluidsynth.so.3", "libfluidsynth.so"];
const SYSTEM_LIBRARY_FOLDERS: [&str; 6] = [
    "/opt/homebrew/lib",
    "/usr/local/lib",
    "/usr/lib/x86_64-linux-gnu",
    "/usr/lib/aarch64-linux-gnu",
    "/usr/lib64",
    "/usr/lib",
];
const LIBRARY_FOLDER: &str = words::LIB;
const GAIN: f64 = 0.55;

/// The computer's MIDI output ports by their shown names; none in a screen tour, which lists no ports, as the Python's
/// tests list none.
#[cfg(target_os = "macos")]
pub fn output_port_names() -> Vec<String> {
    if !SENDING_ALLOWED.load(Ordering::SeqCst) {
        return Vec::new();
    }
    llamatron_backend::sender::coremidi::destination_names()
}

/// The MIDI ports an instrument can be sent to: every port the computer lists but FluidSynth's own, which an instrument
/// reaches by choosing FluidSynth.
pub fn device_port_names() -> Vec<String> {
    output_port_names()
        .into_iter()
        .filter(|name| !name.starts_with("llamatron FluidSynth"))
        .collect()
}

/// The computer's MIDI output ports, none listed where CoreMIDI isn't.
#[cfg(not(target_os = "macos"))]
pub fn output_port_names() -> Vec<String> {
    Vec::new()
}

/// FluidSynth's library: where LLAMATRON_FLUIDSYNTH_LIBRARY says, else beside the fluidsynth program, else in the system's
/// folders, or None.
pub fn fluidsynth_library() -> Option<PathBuf> {
    if let Ok(given) = std::env::var(LIBRARY_VARIABLE) {
        let given = PathBuf::from(given);
        return given.is_file().then_some(given);
    }
    let mut folders: Vec<PathBuf> = Vec::new();
    if let Some(program) = crate::wav::fluidsynth_path() {
        if let Some(prefix) = program.parent().and_then(|folder| folder.parent()) {
            folders.push(prefix.join(LIBRARY_FOLDER));
        }
    }
    folders.extend(SYSTEM_LIBRARY_FOLDERS.iter().map(PathBuf::from));
    folders
        .iter()
        .flat_map(|folder| LIBRARY_NAMES.iter().map(move |name| folder.join(name)))
        .find(|path| path.is_file())
}

/// A port as the daemon opens it: its name, its kind and, for a built-in port, its group of sixteen instruments.
#[derive(Clone, Debug, PartialEq)]
pub struct OpenedPort {
    pub name: String,
    pub kind: &'static str,
    pub group: i64,
}

/// Whether the sender may start: the screen tour switches it off, so that no tour ever opens a MIDI port or the sound
/// card, as the Python's tests refuse a real FluidSynth and list no ports.
pub static SENDING_ALLOWED: AtomicBool = AtomicBool::new(true);

/// The tracker's side of the sender: the backend's sending loop on a thread of this process, handed its messages through
/// a channel.
pub struct BackendSender {
    to_sender: Option<mpsc::Sender<Value>>,
    closed: Arc<AtomicBool>,
    places: HashMap<String, u8>,
    tags: HashMap<ClipTag, u32>,
    sounds: HashMap<(String, i64), Data>,
    started: Instant,
    /// The synths' latest load report, kept by the thread that reads the sender's messages.
    load: Arc<SynthLoad>,
}

/// The built-in synths' and FluidSynth's latest load report: the share of the time the audio callback was busy, as the
/// bits of a float, and how many dropouts the sound card has reported, each kept in an atomic so that no lock is taken.
#[derive(Default)]
pub struct SynthLoad {
    busy_bits: AtomicU64,
    dropouts: AtomicU64,
    reported: AtomicBool,
}

impl SynthLoad {
    /// Keep a load report's figures.
    fn take(&self, report: &Value) {
        let Some(pairs) = report.as_map() else { return };
        let field = |name: &str| pairs.iter().find(|(key, _)| key.as_str() == Some(name)).map(|(_, value)| value);
        if let Some(busy) = field(BUSY).and_then(Value::as_f64) {
            self.busy_bits.store(busy.to_bits(), Ordering::Relaxed);
        }
        if let Some(dropouts) = field(DROPOUTS).and_then(Value::as_u64) {
            self.dropouts.store(dropouts, Ordering::Relaxed);
        }
        self.reported.store(true, Ordering::Relaxed);
    }

    /// The share of the time the callback was busy and the dropouts so far, or None before the first report.
    pub fn latest(&self) -> Option<(f64, u64)> {
        self.reported
            .load(Ordering::Relaxed)
            .then(|| (f64::from_bits(self.busy_bits.load(Ordering::Relaxed)), self.dropouts.load(Ordering::Relaxed)))
    }
}

/// A load report's figures, as the backend names them.
const BUSY: &str = words::LOAD;
const DROPOUTS: &str = words::DROPOUTS;

impl BackendSender {
    /// Start the sender on the ports and take this moment as the timeline's zero; why it could not start where it can't.
    pub fn start(ports: &[OpenedPort]) -> Result<BackendSender, String> {
        if !SENDING_ALLOWED.load(Ordering::SeqCst) {
            return Err(errors::ERR_SENDER_DID_NOT_START.to_string());
        }
        let (to_sender, inbox) = mpsc::channel::<Value>();
        let (answers, answered) = mpsc::channel::<Value>();
        let answers = Mutex::new(answers);
        let output: llamatron_backend::daemon::Output = Arc::new(move |message: &Value| {
            if let Ok(answers) = answers.lock() {
                let _ = answers.send(message.clone());
            }
        });
        let closed = Arc::new(AtomicBool::new(false));
        let ended = closed.clone();
        std::thread::Builder::new()
            .name("llamatron sender".to_string())
            .spawn(move || {
                let mut inbox = inbox;
                // A panic in the sender ends its thread here, never the tracker: the tracker learns it from the closed flag.
                let _ = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| llamatron_backend::daemon::sending::serve(output, &mut inbox)));
                ended.store(true, Ordering::SeqCst);
            })
            .map_err(|problem| problem.to_string())?;
        let _ = to_sender.send(Value::Array(vec![OPEN.into(), Self::opening(ports)]));
        let answer = answered.recv_timeout(OPEN_TIMEOUT).ok();
        let ready = answer
            .as_ref()
            .and_then(|answer| answer.as_array())
            .and_then(|items| items.first())
            .and_then(Value::as_str)
            == Some(READY);
        let mut sender = BackendSender {
            to_sender: Some(to_sender),
            closed,
            places: ports.iter().enumerate().map(|(place, port)| (port.name.clone(), place as u8)).collect(),
            tags: HashMap::new(),
            sounds: HashMap::new(),
            started: Instant::now(),
            load: Arc::new(SynthLoad::default()),
        };
        if !ready {
            sender.close();
            return Err(errors::ERR_SENDER_DID_NOT_START.to_string());
        }
        // The sender's later messages are read here: its load reports are kept, and the rest, its answer as it closes among
        // them, passed over.
        let load = sender.load.clone();
        std::thread::spawn(move || {
            while let Ok(message) = answered.recv() {
                let items = message.as_array();
                if items.and_then(|items| items.first()).and_then(Value::as_str) == Some(llamatron_backend::protocol::LOAD) {
                    if let Some(report) = items.and_then(|items| items.get(1)) {
                        load.take(report);
                    }
                }
            }
        });
        sender.started = Instant::now();
        sender.send(Value::Array(vec![START.into(), Value::Nil]));
        Ok(sender)
    }

    /// The synths' latest load: the share of the time the audio callback was busy and the dropouts so far, or None before
    /// the first report.
    pub fn synth_load(&self) -> Option<(f64, u64)> {
        self.load.latest()
    }

    /// The seconds since the timeline's zero, the clock the events' seconds are on.
    pub fn now(&self) -> f64 {
        self.started.elapsed().as_secs_f64()
    }

    /// Give the built-in ports' channels their sounds, sending only what changed.
    pub fn set_sounds(&mut self, sounds: &[((String, i64), Data)]) {
        let mut changed = Vec::new();
        for ((port, channel), spec) in sounds {
            let Some(place) = self.places.get(port) else { continue };
            if self.sounds.get(&(port.clone(), *channel)) != Some(spec) {
                self.sounds.insert((port.clone(), *channel), spec.clone());
                changed.push(Value::Array(vec![(*place as i64).into(), (*channel).into(), crate::msgpack::value_of(spec)]));
            }
        }
        if !changed.is_empty() {
            self.send(Value::Array(vec![SOUNDS.into(), Value::Array(changed)]));
        }
    }

    /// Note offs, all notes off and all sound off on each port and channel given.
    pub fn silence(&mut self, channels: &[(String, i64)]) {
        let places = channels
            .iter()
            .filter_map(|(port, channel)| self.places.get(port).map(|place| Value::Array(vec![(*place as i64).into(), (*channel).into()])))
            .collect();
        self.send(Value::Array(vec![SILENCE.into(), Value::Array(places)]));
    }

    /// Whether the sender is still running.
    pub fn is_running(&self) -> bool {
        !self.closed.load(Ordering::SeqCst)
    }

    /// Stop everything, close the ports and end the sender's thread, waiting a little for it.
    pub fn close(&mut self) {
        self.send(Value::Array(vec![CLOSE.into()]));
        self.to_sender = None;
        let deadline = Instant::now() + CLOSE_TIMEOUT;
        while self.is_running() && Instant::now() < deadline {
            std::thread::sleep(WAIT_STEP);
        }
    }

    /// What the sender is opened with: the ports with their kinds, the driver, and FluidSynth's library, SoundFont and gain
    /// where its port is among them.
    fn opening(ports: &[OpenedPort]) -> Value {
        let listed = ports
            .iter()
            .map(|port| Value::Array(vec![port.name.as_str().into(), port.kind.into(), port.group.into()]))
            .collect();
        let fluid = match fluidsynth_library().filter(|_| ports.iter().any(|port| port.kind == FLUIDSYNTH)) {
            Some(library) => Value::Array(vec![
                library.display().to_string().into(),
                crate::wav::soundfont_path().display().to_string().into(),
                GAIN.into(),
            ]),
            None => Value::Nil,
        };
        Value::Map(vec![
            (words::PORTS.into(), Value::Array(listed)),
            (words::RECORDING.into(), false.into()),
            (words::DRIVER.into(), TIMESTAMPED.into()),
            (file_format::InstrumentSetting::DEVICE.into(), audio_device()),
            (words::FLUID.into(), fluid),
        ])
    }

    /// The number a play's tag crosses to the sender as.
    fn tag_number(&mut self, tag: &ClipTag) -> u32 {
        let next = self.tags.len() as u32;
        *self.tags.entry(tag.clone()).or_insert(next)
    }

    /// Hand a message to the sender, unless it has gone.
    fn send(&mut self, message: Value) {
        if let Some(to_sender) = &self.to_sender {
            if to_sender.send(message).is_err() {
                self.to_sender = None;
            }
        }
    }
}

impl Sender for BackendSender {
    fn add(&mut self, events: Vec<Playing>) {
        let mut records = vec![RECORDS_VERSION];
        for event in &events {
            let Some(place) = self.places.get(&event.port).copied() else { continue };
            let tag = self.tag_number(&event.tag);
            records.extend(event.seconds.to_le_bytes());
            records.extend(tag.to_le_bytes());
            records.extend([place, event.channel as u8, event.kind as u8, event.number as u8, event.value as u8]);
        }
        self.send(Value::Array(vec![ADD.into(), Value::Binary(records)]));
    }

    fn forget(&mut self, tag: &ClipTag, after: f64) {
        let number = self.tag_number(tag);
        self.send(Value::Array(vec![FORGET.into(), number.into(), after.into()]));
    }

    fn stop_tag(&mut self, tag: &ClipTag) {
        let number = self.tag_number(tag);
        self.send(Value::Array(vec![STOP_TAG.into(), number.into()]));
    }

    fn stop_all(&mut self) {
        self.send(Value::Array(vec![STOP_ALL.into()]));
    }
}

impl Drop for BackendSender {
    fn drop(&mut self) {
        self.close();
    }
}

/// Where a development check sends the sound card's stream, a loopback device it records, named by AUDIO_DEVICE_VARIABLE;
/// the computer's default output otherwise.
fn audio_device() -> Value {
    match std::env::var(AUDIO_DEVICE_VARIABLE) {
        Ok(device) if !device.is_empty() => device.into(),
        _ => Value::Nil,
    }
}

/// The environment variable a development check names its audio device by.
const AUDIO_DEVICE_VARIABLE: &str = "LLAMATRON_AUDIO_DEVICE";

#[cfg(test)]
mod tests {
    use super::*;
    use llamatron_math::Rational;

    #[test]
    fn the_sender_takes_every_message_on_no_ports_and_closes() {
        // On no ports the sender opens no MIDI port and no sound card, so the test makes no sound anywhere.
        let mut sender = BackendSender::start(&[]).expect("the sender starts on no ports");
        assert!(sender.is_running());
        let tag = ClipTag {
            scene: 0,
            track: words::LEAD.to_string(),
            play: 1,
        };
        let event = Playing {
            whole: Rational::ZERO,
            seconds: 0.5,
            port: words::NOWHERE.to_string(),
            channel: 0,
            kind: crate::realtime::timeline::NOTE_ON,
            number: 60,
            value: 100,
            tag: tag.clone(),
            switch: false,
        };
        sender.add(vec![event]);
        sender.forget(&tag, crate::realtime::player::BEFORE_EVERYTHING);
        sender.stop_tag(&tag);
        sender.silence(&[]);
        sender.stop_all();
        assert!(sender.now() >= 0.0);
        sender.close();
        std::thread::sleep(Duration::from_millis(200));
        assert!(!sender.is_running());
    }
}
