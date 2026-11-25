// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The real-time sender (the Python realtime/sender_process/rust_sender.py): the backend's sending loop, run on a thread of
//! llamatron2's own process, which sends the player's events on time through the MIDI ports, the built-in synths and
//! FluidSynth. Its messages are handed across a channel as the backend's values; the events cross as slim records, each
//! port named by its place and each play's tag by a number. Closing ends the loop and waits a little for its thread.

use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{mpsc, Arc, Mutex};
use std::time::{Duration, Instant};

use crate::realtime::player::Sender;
use crate::realtime::timeline::{ClipTag, Playing};
use llamatron_model::file::data::Data;
use llamatron_strings::errors;
use rmpv::Value;

/// The sender's words.
const OPEN: &str = "open";
const START: &str = "start";
const ADD: &str = "add";
const FORGET: &str = "forget";
const STOP_TAG: &str = "stop_tag";
const STOP_ALL: &str = "stop_all";
const SILENCE: &str = "silence";
const SOUNDS: &str = "sounds";
const CLOSE: &str = "close";
const READY: &str = "ready";
/// The kinds of port the sender opens, and the drivers.
pub const MIDI: &str = "midi";
pub const BUILT_IN: &str = "built_in";
pub const FLUIDSYNTH: &str = "fluidsynth";
const TIMESTAMPED: &str = "timestamped";
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
const LIBRARY_FOLDER: &str = "lib";
const GAIN: f64 = 0.55;

/// The computer's MIDI output ports by their shown names.
#[cfg(target_os = "macos")]
pub fn output_port_names() -> Vec<String> {
    llamatron_backend::sender::coremidi::destination_names()
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

/// The tracker's side of the sender: the backend's sending loop on a thread of this process, handed its messages through
/// a channel.
pub struct BackendSender {
    to_sender: Option<mpsc::Sender<Value>>,
    closed: Arc<AtomicBool>,
    places: HashMap<String, u8>,
    tags: HashMap<ClipTag, u32>,
    sounds: HashMap<(String, i64), Data>,
    started: Instant,
}

impl BackendSender {
    /// Start the sender on the ports and take this moment as the timeline's zero; why it could not start where it can't.
    pub fn start(ports: &[OpenedPort]) -> Result<BackendSender, String> {
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
        };
        if !ready {
            sender.close();
            return Err(errors::ERR_SENDER_DID_NOT_START.to_string());
        }
        // The sender's later messages, its load reports and its answer as it closes, are taken and passed over.
        std::thread::spawn(move || while answered.recv().is_ok() {});
        sender.started = Instant::now();
        sender.send(Value::Array(vec![START.into(), Value::Nil]));
        Ok(sender)
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
            ("ports".into(), Value::Array(listed)),
            ("recording".into(), false.into()),
            ("driver".into(), TIMESTAMPED.into()),
            ("device".into(), Value::Nil),
            ("fluid".into(), fluid),
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
            track: "lead".to_string(),
            play: 1,
        };
        let event = Playing {
            whole: Rational::ZERO,
            seconds: 0.5,
            port: "nowhere".to_string(),
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
