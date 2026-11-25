// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The real-time sender (the Python realtime/sender_process/rust_sender.py): llamatron-backend run as `send`, which sends
//! the player's events on time through the MIDI ports, the built-in synths and FluidSynth, all in one process. It speaks
//! MessagePack framed by length; the events cross as slim records, each port named by its place and each play's tag by a
//! number. The daemon ends when its input closes or its parent dies, and closing waits for it and ends it if it hangs, so
//! that it is never left an orphan or a zombie.

use std::collections::HashMap;
use std::path::PathBuf;
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use crate::msgpack;
use crate::realtime::player::Sender;
use crate::realtime::timeline::{ClipTag, Playing};
use llamatron_model::file::data::Data;
use llamatron_strings::errors;

/// The daemon's words.
const SEND: &str = "send";
const PORTS: &str = "ports";
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
/// The kinds of port the daemon opens, and the drivers.
pub const MIDI: &str = "midi";
pub const BUILT_IN: &str = "built_in";
pub const FLUIDSYNTH: &str = "fluidsynth";
const TIMESTAMPED: &str = "timestamped";
/// The records' version, and how long the daemon has to end once closed before it is ended.
const RECORDS_VERSION: u8 = 1;
const CLOSE_TIMEOUT: Duration = Duration::from_secs(2);
const WAIT_STEP: Duration = Duration::from_millis(10);
/// FluidSynth's library, which the daemon loads to play FluidSynth itself, by its names and where it is looked for, and
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

/// The computer's MIDI output ports by the names the daemon shows, none where the daemon isn't built.
pub fn output_port_names() -> Vec<String> {
    let Some(backend) = crate::wav::backend_path() else { return Vec::new() };
    let Ok(listed) = Command::new(backend).arg(PORTS).stderr(Stdio::null()).output() else {
        return Vec::new();
    };
    String::from_utf8_lossy(&listed.stdout)
        .lines()
        .map(str::to_string)
        .filter(|line| !line.is_empty())
        .collect()
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

/// The tracker's side of the daemon run as the sender.
pub struct BackendSender {
    child: Option<Child>,
    input: Arc<Mutex<Option<ChildStdin>>>,
    closed: Arc<AtomicBool>,
    places: HashMap<String, u8>,
    tags: HashMap<ClipTag, u32>,
    sounds: HashMap<(String, i64), Data>,
    started: Instant,
}

impl BackendSender {
    /// Start the daemon on the ports and take this moment as the timeline's zero; why it could not start where it can't.
    pub fn start(ports: &[OpenedPort]) -> Result<BackendSender, String> {
        let program = crate::wav::backend_path().ok_or_else(|| errors::ERR_SYNTH_DAEMON_MISSING.to_string())?;
        let mut child = Command::new(program)
            .arg(SEND)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|problem| problem.to_string())?;
        let mut input = child.stdin.take().ok_or_else(|| errors::ERR_SENDER_DID_NOT_START.to_string())?;
        let mut output = child.stdout.take().ok_or_else(|| errors::ERR_SENDER_DID_NOT_START.to_string())?;
        let opening = Self::opening(ports);
        let opened = msgpack::send(&mut input, &Data::List(vec![Data::text(OPEN), opening]));
        let answer = opened.and_then(|_| msgpack::received(&mut output));
        let ready = answer.as_ref().ok().and_then(|answer| msgpack::first_word(answer)).as_deref() == Some(READY);
        let closed = Arc::new(AtomicBool::new(false));
        let mut sender = BackendSender {
            child: Some(child),
            input: Arc::new(Mutex::new(Some(input))),
            closed: closed.clone(),
            places: ports.iter().enumerate().map(|(place, port)| (port.name.clone(), place as u8)).collect(),
            tags: HashMap::new(),
            sounds: HashMap::new(),
            started: Instant::now(),
        };
        if !ready {
            sender.close();
            return Err(errors::ERR_SENDER_DID_NOT_START.to_string());
        }
        // The daemon's later messages, its load reports and its answer as it closes, are read and passed over, so that its
        // output never fills.
        std::thread::spawn(move || {
            while msgpack::received(&mut output).is_ok() {}
            closed.store(true, Ordering::SeqCst);
        });
        sender.started = Instant::now();
        sender.send(&Data::List(vec![Data::text(START), Data::Null]));
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
                changed.push(Data::List(vec![Data::Whole(*place as i128), Data::Whole(*channel as i128), spec.clone()]));
            }
        }
        if !changed.is_empty() {
            self.send(&Data::List(vec![Data::text(SOUNDS), Data::List(changed)]));
        }
    }

    /// Note offs, all notes off and all sound off on each port and channel given.
    pub fn silence(&mut self, channels: &[(String, i64)]) {
        let places = channels
            .iter()
            .filter_map(|(port, channel)| {
                self.places
                    .get(port)
                    .map(|place| Data::List(vec![Data::Whole(*place as i128), Data::Whole(*channel as i128)]))
            })
            .collect();
        self.send(&Data::List(vec![Data::text(SILENCE), Data::List(places)]));
    }

    /// Whether the daemon is still running.
    pub fn is_running(&self) -> bool {
        !self.closed.load(Ordering::SeqCst)
    }

    /// Stop everything, close the ports and end the daemon, ending it if it hangs.
    pub fn close(&mut self) {
        self.send(&Data::List(vec![Data::text(CLOSE)]));
        if let Ok(mut input) = self.input.lock() {
            input.take();
        }
        let Some(mut child) = self.child.take() else { return };
        let deadline = Instant::now() + CLOSE_TIMEOUT;
        while Instant::now() < deadline {
            if let Ok(Some(_)) = child.try_wait() {
                return;
            }
            std::thread::sleep(WAIT_STEP);
        }
        let _ = child.kill();
        let _ = child.wait();
    }

    /// What the daemon is opened with: the ports with their kinds, the driver, and FluidSynth's library, SoundFont and gain
    /// where its port is among them.
    fn opening(ports: &[OpenedPort]) -> Data {
        let listed = ports
            .iter()
            .map(|port| Data::List(vec![Data::text(&port.name), Data::text(port.kind), Data::Whole(port.group as i128)]))
            .collect();
        let fluid = if ports.iter().any(|port| port.kind == FLUIDSYNTH) {
            match fluidsynth_library() {
                Some(library) => Data::List(vec![
                    Data::text(&library.display().to_string()),
                    Data::text(&crate::wav::soundfont_path().display().to_string()),
                    Data::Float(GAIN),
                ]),
                None => Data::Null,
            }
        } else {
            Data::Null
        };
        Data::Map(vec![
            (Data::text("ports"), Data::List(listed)),
            (Data::text("recording"), Data::Bool(false)),
            (Data::text("driver"), Data::text(TIMESTAMPED)),
            (Data::text("device"), Data::Null),
            (Data::text("fluid"), fluid),
        ])
    }

    /// The number a play's tag crosses to the daemon as.
    fn tag_number(&mut self, tag: &ClipTag) -> u32 {
        let next = self.tags.len() as u32;
        *self.tags.entry(tag.clone()).or_insert(next)
    }

    /// Write a message, unless the daemon has gone.
    fn send(&mut self, message: &Data) {
        let mut body = Vec::new();
        msgpack::packed(message, &mut body);
        self.send_body(&body);
    }

    fn send_body(&mut self, body: &[u8]) {
        if let Ok(mut input) = self.input.lock() {
            if let Some(stream) = input.as_mut() {
                if msgpack::send_packed(stream, body).is_err() {
                    input.take();
                }
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
        // ["add", records]: an array of two, a word and the records as binary.
        let mut body = vec![0x92];
        msgpack::packed(&Data::text(ADD), &mut body);
        msgpack::packed_bytes(&records, &mut body);
        self.send_body(&body);
    }

    fn forget(&mut self, tag: &ClipTag, after: f64) {
        let number = self.tag_number(tag);
        self.send(&Data::List(vec![Data::text(FORGET), Data::Whole(number as i128), Data::Float(after)]));
    }

    fn stop_tag(&mut self, tag: &ClipTag) {
        let number = self.tag_number(tag);
        self.send(&Data::List(vec![Data::text(STOP_TAG), Data::Whole(number as i128)]));
    }

    fn stop_all(&mut self) {
        self.send(&Data::List(vec![Data::text(STOP_ALL)]));
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

    /// The daemon built beside the tests, in the workspace's release folder, which the tests point LLAMATRON_BACKEND at.
    fn built_backend() -> Option<PathBuf> {
        let here = std::env::current_exe().ok()?;
        here.ancestors().map(|folder| folder.join("llamatron-backend")).find(|path| path.is_file())
    }

    #[test]
    fn the_sender_speaks_every_message_to_a_daemon_on_no_ports_and_closes_it() {
        // On no ports the daemon opens no MIDI port and no sound card, so the test makes no sound anywhere.
        let Some(backend) = built_backend() else { return };
        std::env::set_var("LLAMATRON_BACKEND", &backend);
        let mut sender = BackendSender::start(&[]).expect("the daemon starts on no ports");
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
