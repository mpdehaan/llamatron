// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The daemon as the real-time sender, `llamatron-backend send`: the tracker's player hands it every event of what plays,
//! and it sends each on time through the MIDI ports, the built-in synths and FluidSynth, all in this one process.
//!
//! The first message opens it: `["open", {ports, recording, driver, block, device, fluid}]`, each port `[name, kind,
//! group]` of the kinds `midi`, `built_in` (with its group of sixteen instruments) and `fluidsynth`. The sound card's stream
//! opens only where a built-in or FluidSynth port asks for it, and never when recording, which keeps what would be sent for
//! the tests. It answers `["ready", rate, delay]` or `["failed", problem, detail]`, then takes `start`, `add` (records, as
//! the tracker packs them), `forget`, `stop_tag`, `stop_all`, `silence`, `sounds` and `close`, which it answers with
//! `["closed", started, recordings, statistics]`.

use crate::audio::player::{Command, Player};
use crate::daemon::{item, kind_of, start_reporter, statistics_of, tell, HitStore, Output as Answer};
use crate::fluid::Fluid;
use crate::instrument::patch::Patch;
use crate::protocol::values::{as_number, field, list, truth, word};
use crate::protocol::{self, message};
use crate::sender::engine::{SenderEngine, NOTE_ON};
use crate::sender::outputs::{Output, Shared, INSTRUMENTS_PER_PORT};
use crate::sender::{self, Closed, SenderCommand};
use llamatron_names::wire;
use rmpv::Value;
use std::sync::atomic::AtomicBool;
use std::sync::mpsc;
use std::sync::{Arc, Mutex};

pub const OPEN: &str = wire::OPEN;
pub const START: &str = wire::START;
pub const ADD: &str = wire::ADD;
pub const FORGET: &str = wire::FORGET;
pub const STOP_TAG: &str = wire::STOP_TAG;
pub const STOP_ALL: &str = wire::STOP_ALL;
pub const SILENCE: &str = wire::SILENCE;
pub const SOUNDS: &str = wire::SOUNDS;
pub const CLOSED: &str = wire::CLOSED;
const MIDI: &str = wire::MIDI;
const BUILT_IN: &str = wire::BUILT_IN;
const FLUIDSYNTH: &str = wire::FLUIDSYNTH;
const IMMEDIATE: &str = wire::IMMEDIATE;
const DEFAULT_BLOCK: f64 = 128.0;

/// A port as the tracker names it: its name, its kind, and a built-in port's group.
struct Port {
    name: String,
    kind: String,
    group: usize,
}

fn ports_of(opened: &Value) -> Vec<Port> {
    list(opened, wire::PORTS)
        .iter()
        .filter_map(|port| {
            let items = port.as_array()?;
            let name = items.first()?.as_str()?.to_string();
            let kind = items.get(1).and_then(Value::as_str).unwrap_or(MIDI).to_string();
            let group = items.get(2).and_then(as_number).unwrap_or(0.0) as usize;
            Some(Port { name, kind, group })
        })
        .collect()
}

/// What opening made: the player, where a port needs sound, and the sender's engine.
struct Opened {
    player: Option<Player>,
    hits: Arc<Mutex<HitStore>>,
    engine: SenderEngine,
    rate: f64,
    delay: f64,
}

/// Why opening failed: the problem's word for the tracker and what it was.
struct Failed(&'static str, String);

fn open(opened: &Value) -> Result<Opened, Failed> {
    let ports = ports_of(opened);
    let recording = truth(opened, wire::RECORDING, false);
    // The tracker chooses the driver, as before: timestamped where CoreMIDI is, immediate elsewhere.
    let scheduled = word(opened, wire::DRIVER, wire::TIMESTAMPED) != IMMEDIATE;
    let wants_sound = !recording && ports.iter().any(|port| port.kind == BUILT_IN || port.kind == FLUIDSYNTH);
    let hits = Arc::new(Mutex::new(HitStore::default()));
    let mut player = None;
    let (mut rate, mut delay) = (0.0, 0.0);
    if wants_sound {
        let block = crate::protocol::values::number(opened, wire::BLOCK, DEFAULT_BLOCK) as usize;
        let device = field(opened, wire::DEVICE).and_then(Value::as_str);
        let started = Player::start(block, device).map_err(|problem| Failed(problem.code(), problem.to_string()))?;
        rate = started.rate;
        delay = started.delay;
        player = Some(started);
    }
    if let (Some(player), true) = (&mut player, ports.iter().any(|port| port.kind == FLUIDSYNTH)) {
        load_fluid(opened, player, rate)?;
    }
    let shared = player.as_ref().map(|player| Shared {
        commands: player.commands.clone(),
        hits: hits.clone(),
        delay,
        rate,
    });
    let mut outputs = Vec::with_capacity(ports.len());
    #[cfg(target_os = "macos")]
    let mut client = None;
    for port in &ports {
        let output = match (recording, port.kind.as_str(), &shared) {
            (true, _, _) => Output::Recording { sent: Vec::new(), scheduled },
            (false, BUILT_IN, Some(shared)) => Output::BuiltIn {
                first: port.group * INSTRUMENTS_PER_PORT,
                shared: shared.clone(),
            },
            (false, FLUIDSYNTH, Some(shared)) => Output::Fluid { shared: shared.clone() },
            #[cfg(target_os = "macos")]
            _ => {
                if client.is_none() {
                    client = Some(crate::sender::coremidi::client().map_err(|problem| Failed(wire::PORT, problem.to_string()))?);
                }
                let opened = crate::sender::coremidi::CoreMidiOutput::open(client.clone().expect("made just above"), &port.name);
                Output::CoreMidi(opened.map_err(|problem| Failed(wire::PORT, problem.to_string()))?)
            }
            #[cfg(not(target_os = "macos"))]
            _ => Output::Midir(midir_port(&port.name)?),
        };
        outputs.push(output);
    }
    Ok(Opened {
        player,
        hits,
        engine: SenderEngine::new(outputs, scheduled),
        rate,
        delay,
    })
}

#[cfg(not(target_os = "macos"))]
fn midir_port(name: &str) -> Result<midir::MidiOutputConnection, Failed> {
    let output = midir::MidiOutput::new(wire::LLAMATRON).map_err(|problem| Failed(wire::PORT, problem.to_string()))?;
    let found = output
        .ports()
        .into_iter()
        .find(|port| output.port_name(port).is_ok_and(|found| found == name || found.starts_with(name)))
        .ok_or_else(|| Failed(wire::PORT, format!("no MIDI destination is called {name}")))?;
    output
        .connect(&found, wire::LLAMATRON)
        .map_err(|problem| Failed(wire::PORT, problem.to_string()))
}

fn load_fluid(opened: &Value, player: &mut Player, rate: f64) -> Result<(), Failed> {
    let Some(given) = field(opened, wire::FLUID).and_then(Value::as_array) else {
        return Ok(());
    };
    let text = |place: usize| given.get(place).and_then(Value::as_str).unwrap_or("");
    let gain = given.get(2).and_then(as_number).unwrap_or(0.55);
    let fluid = Fluid::load(text(0), text(1), rate, gain).map_err(|problem| Failed(wire::FLUIDSYNTH, problem.to_string()))?;
    log::info!("FluidSynth ready with {}", text(1));
    player.send(Command::Fluid(Box::new(fluid)));
    Ok(())
}

/// Serve as the sender until told to close or the input ends.
pub fn serve(answer: Answer, input: &mut dyn protocol::Inbox) -> i32 {
    let first = match input.next_message() {
        Ok(Some(first)) if kind_of(&first) == OPEN => first,
        _ => {
            log::error!("the sender was not opened");
            return 1;
        }
    };
    let ports: Vec<Port> = ports_of(item(&first, 1).unwrap_or(&Value::Nil));
    let opened = match open(item(&first, 1).unwrap_or(&Value::Nil)) {
        Ok(opened) => opened,
        Err(Failed(problem, detail)) => {
            log::error!("the sender could not open: {detail}");
            tell(&answer, &message(protocol::FAILED, vec![problem.into(), detail.into()]));
            return 1;
        }
    };
    log::info!("sending to {} ports, notes held back {:.2} ms", ports.len(), opened.delay * 1000.0);
    tell(&answer, &message(protocol::READY, vec![opened.rate.into(), opened.delay.into()]));
    let Opened {
        mut player,
        hits,
        engine,
        rate,
        delay,
    } = opened;
    let reporting = Arc::new(AtomicBool::new(true));
    let reporter = player.as_ref().map(|player| start_reporter(player, answer.clone(), reporting.clone()));
    let (commands, inbox) = mpsc::channel();
    let thread = std::thread::spawn(move || sender::run(engine, inbox, delay));
    let mut closed = None;
    loop {
        let received = match input.next_message() {
            Ok(Some(received)) => received,
            Ok(None) => break,
            Err(problem) => {
                log::error!("could not read the tracker's message: {problem}");
                break;
            }
        };
        if kind_of(&received) == protocol::CLOSE {
            let (answered, answer_inbox) = mpsc::channel();
            let _ = commands.send(SenderCommand::Close(answered));
            closed = answer_inbox.recv().ok();
            break;
        }
        take(&received, &commands, &ports, &mut player, &hits, rate);
    }
    drop(commands);
    let _ = thread.join();
    reporting.store(false, std::sync::atomic::Ordering::Relaxed);
    if let Some(reporter) = reporter {
        let _ = reporter.join();
    }
    let statistics = player.as_ref().map(statistics_of).unwrap_or(Value::Nil);
    if let Some(player) = player.as_mut() {
        player.stop();
    }
    drop(player);
    if let Some(closed) = closed {
        tell(&answer, &closed_message(&closed, &ports, statistics));
    }
    log::info!("the sender closed");
    0
}

fn take(received: &Value, commands: &mpsc::Sender<SenderCommand>, ports: &[Port], player: &mut Option<Player>, hits: &Arc<Mutex<HitStore>>, rate: f64) {
    let number = |place: usize| item(received, place).and_then(as_number);
    let command = match kind_of(received) {
        START => SenderCommand::Start(number(1)),
        ADD => {
            let events = sender::events_of(item(received, 1).and_then(Value::as_slice).unwrap_or(&[]));
            warm_hits(&events, ports, hits, rate);
            SenderCommand::Add(events)
        }
        FORGET => SenderCommand::Forget {
            tag: number(1).unwrap_or(0.0) as u32,
            after: number(2).unwrap_or(0.0),
        },
        STOP_TAG => SenderCommand::StopTag(number(1).unwrap_or(0.0) as u32),
        STOP_ALL => SenderCommand::StopAll,
        SILENCE => SenderCommand::Silence(pairs_of(item(received, 1))),
        SOUNDS => {
            set_sounds(item(received, 1), ports, player, hits, rate);
            return;
        }
        other => {
            log::warn!("a sender message of a kind the daemon does not know: {other}");
            return;
        }
    };
    let _ = commands.send(command);
}

/// Render now, on the reader, the drum hits a batch's notes on built-in ports will need, so that the sender's thread finds
/// each kept and never waits for one.
fn warm_hits(events: &[sender::engine::Sent], ports: &[Port], hits: &Arc<Mutex<HitStore>>, rate: f64) {
    let Ok(mut hits) = hits.lock() else { return };
    for event in events {
        let Some(port) = ports.get(event.port) else { continue };
        if port.kind == BUILT_IN && event.kind == NOTE_ON && event.value > 0 {
            let instrument = port.group * INSTRUMENTS_PER_PORT + event.channel as usize;
            hits.hit(instrument, event.number as f64, event.value as f64, rate);
        }
    }
}

/// Give built-in ports' channels their sounds, each (port's place, channel, spec), compiled here and handed to the player.
fn set_sounds(given: Option<&Value>, ports: &[Port], player: &mut Option<Player>, hits: &Arc<Mutex<HitStore>>, rate: f64) {
    let Some(player) = player else { return };
    for sound in given.and_then(Value::as_array).map(Vec::as_slice).unwrap_or(&[]) {
        let Some(items) = sound.as_array() else { continue };
        let place = items.first().and_then(as_number).unwrap_or(-1.0);
        let channel = items.get(1).and_then(as_number).unwrap_or(0.0) as usize;
        let Some(port) = ports.get(place as usize).filter(|port| port.kind == BUILT_IN && place >= 0.0) else {
            continue;
        };
        let number = port.group * INSTRUMENTS_PER_PORT + channel;
        let patch = Box::new(Patch::compiled(items.get(2).unwrap_or(&Value::Nil), rate));
        if let Ok(mut hits) = hits.lock() {
            hits.set_instrument(number, &patch);
        }
        player.send(Command::Instrument { number, patch });
    }
}

fn pairs_of(value: Option<&Value>) -> Vec<(usize, u8)> {
    value
        .and_then(Value::as_array)
        .map(Vec::as_slice)
        .unwrap_or(&[])
        .iter()
        .filter_map(|pair| {
            let items = pair.as_array()?;
            Some((as_number(items.first()?)? as usize, as_number(items.get(1)?)? as u8))
        })
        .collect()
}

fn closed_message(closed: &Closed, ports: &[Port], statistics: Value) -> Value {
    let started = closed.started.map(Value::from).unwrap_or(Value::Nil);
    let recordings: Vec<(Value, Value)> = ports
        .iter()
        .zip(closed.recordings.iter())
        .map(|(port, sent)| {
            let items = sent
                .iter()
                .map(|(moment, data)| Value::Array(vec![Value::from(*moment), Value::Array(data.iter().map(|byte| Value::from(*byte)).collect())]))
                .collect();
            (Value::from(port.name.as_str()), Value::Array(items))
        })
        .collect();
    message(CLOSED, vec![started, Value::Map(recordings), statistics])
}
