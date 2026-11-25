// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The transport (the Python interface/tracker/transport.py): the tracker's side of real-time playback, between the pages
//! and the player. It says why nothing can play before anything is rendered, works out each track's route from its
//! instrument, starts the sender on the ports the routes need, launches through the player, ticks it from the app's loop,
//! and answers the lights' questions.

use crate::document::Document;
use crate::realtime::backend::{output_port_names, BackendSender, OpenedPort, BUILT_IN, FLUIDSYNTH, MIDI};
use crate::realtime::player::Player;
use crate::realtime::score::Score;
use crate::realtime::timeline::Route;
use llamatron_math::python_random::PythonRandom;
use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::{Instrument, Item};
use llamatron_model::schema::generated::file_format::{InstrumentSetting, Section, SetlistSetting, TrackSetting, FLUIDSYNTH_DEVICE};
use llamatron_strings::{errors, messages, named};

/// How far ahead of now a launch from silence starts, so that its first window reaches the sender before it is due.
const LAUNCH_LEAD_SECONDS: f64 = 0.003;
/// The port names: FluidSynth's, and the built-in ports', sixteen instruments a port.
const FLUIDSYNTH_PORT_PREFIX: &str = "llamatron FluidSynth";
const BUILT_IN_PORT_PREFIX: &str = "llamatron built-in";
const INSTRUMENTS_PER_PORT: usize = 16;
/// An instrument's kind of built-in sound, a channel counted from 1, latency in milliseconds, and the General MIDI channels
/// FluidSynth's tracks take: the drums' and the melodic ones in turn.
const BUILT_IN_KIND: &str = "built_in";
const CHANNEL_OFFSET: i64 = 1;
const MILLISECONDS: f64 = 1000.0;
const DRUM_CHANNEL: i64 = 9;
const MELODIC_CHANNELS: [i64; 15] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15];
const MIN_GM_SOUND: i64 = 1;
/// The range a play's seed is drawn from.
const SEED_RANGE: i128 = 1 << 31;

/// Why nothing can play: a dialog's title and lines.
pub struct Refusal {
    pub title: String,
    pub lines: Vec<String>,
}

/// The tracker's side of real-time playback: the sender while open, the player while something has played, and the
/// seed the song's random parts are drawn from while it plays.
#[derive(Default)]
pub struct Transport {
    sender: Option<BackendSender>,
    ports: Vec<OpenedPort>,
    player: Option<Player>,
    song_name: String,
    previewing: bool,
    seed: Option<i64>,
}

impl Transport {
    /// Why nothing can play now, or None: the Real Time switch, the instruments, their devices, FluidSynth, the built-in
    /// sound and the scenes that never end. With a track, which a listening page picks an instrument for, no track needs
    /// one yet.
    pub fn refusal(&self, app: &crate::app::App, track: Option<&str>) -> Option<Refusal> {
        let document = &app.document;
        let setlist = document.get_setlist();
        let cannot = |line: String| {
            Some(Refusal {
                title: errors::ERR_CANT_PLAY_TITLE.to_string(),
                lines: vec![line],
            })
        };
        if !matches!(setlist.get_written(SetlistSetting::REAL_TIME), Some(Data::Bool(true))) {
            return cannot(errors::ERR_REAL_TIME_OFF.to_string());
        }
        if setlist.items(Section::INSTRUMENTS).is_empty() {
            return Some(Refusal {
                title: errors::ERR_NO_INSTRUMENTS_TITLE.to_string(),
                lines: vec![errors::ERR_ADD_INSTRUMENT_FIRST.to_string()],
            });
        }
        let song = document.song();
        let tracks = song.get_track_names();
        if track.is_none() && !tracks.iter().any(|name| instrument_name(document, name).is_some()) {
            return cannot(errors::ERR_NO_TRACK_HAS_AN_INSTRUMENT.to_string());
        }
        if track.is_none() && !tracks.iter().any(|name| has_a_device(document, name)) {
            return cannot(errors::ERR_NO_TRACK_HAS_A_DEVICE.to_string());
        }
        let missing = missing_devices(document);
        if !missing.is_empty() {
            return Some(Refusal {
                title: errors::ERR_CANT_PLAY_TITLE.to_string(),
                lines: missing
                    .iter()
                    .map(|(instrument, device)| {
                        named(
                            errors::ERR_DEVICE_NOT_CONNECTED,
                            &[("instrument", instrument.as_str().into()), ("device", device.as_str().into())],
                        )
                    })
                    .collect(),
            });
        }
        let routes = routes(document, &[]);
        if routes.iter().any(|(_, route)| route.port.starts_with(FLUIDSYNTH_PORT_PREFIX)) && !crate::wav::fluidsynth_installed() {
            return cannot(errors::ERR_FLUIDSYNTH_NOT_INSTALLED.to_string());
        }
        if routes.iter().any(|(_, route)| route.sound.is_some()) && crate::wav::backend_path().is_none() {
            return cannot(errors::ERR_SYNTHESIS_OFF.to_string());
        }
        let lines = crate::exporting::loop_error_lines(app);
        if !lines.is_empty() {
            return Some(Refusal {
                title: errors::ERR_LOOP_SCENES_TITLE.to_string(),
                lines,
            });
        }
        None
    }

    /// Play the current song from a scene, every clip of it; whether it waits for the next bar of what plays.
    pub fn play_scene(&mut self, document: &Document, index: usize) -> Result<bool, String> {
        self.previewing = false;
        let now = self.ready(document, &[])?;
        let (Some(sender), Some(player)) = (self.sender.as_mut(), self.player.as_mut()) else {
            return Err(sender_gone());
        };
        let at = player.play_scene(sender, now, index);
        Ok(at > now + LAUNCH_LEAD_SECONDS)
    }

    /// Play clips of a scene on their own, through their tracks' instruments or those instead names, once as their scene
    /// would or again and again (forever), as a listening page's preview; whether they wait for the next bar.
    pub fn play_clips(&mut self, document: &Document, index: usize, tracks: Vec<String>, instead: &[(String, String)], forever: bool) -> Result<bool, String> {
        if forever && self.is_playing() && !self.previewing {
            self.stop_all();
        }
        self.previewing = forever;
        let now = self.ready(document, instead)?;
        let (Some(sender), Some(player)) = (self.sender.as_mut(), self.player.as_mut()) else {
            return Err(sender_gone());
        };
        let at = player.play_clips(sender, now, index, tracks, forever);
        Ok(at > now + LAUNCH_LEAD_SECONDS)
    }

    /// Cut what a track plays now.
    pub fn stop_clip(&mut self, track: &str) {
        let Some(sender) = self.sender.as_mut() else { return };
        let now = sender.now();
        if let Some(player) = self.player.as_mut() {
            player.stop_clip(sender, now, track);
        }
    }

    /// Stop everything playing, silencing what sounded.
    pub fn stop_all(&mut self) {
        let Some(sender) = self.sender.as_mut() else { return };
        if let Some(player) = self.player.as_mut() {
            player.stop_all(sender);
        }
        self.previewing = false;
    }

    /// The emergency stop: note offs, all notes off and all sound off on every channel the instruments use; what the status
    /// line says.
    pub fn silence_everything(&mut self, document: &Document) -> String {
        let channels = channels_in_use(document);
        if channels.is_empty() {
            return messages::MSG_NOTHING_TO_SILENCE.to_string();
        }
        self.stop_all();
        let mut devices: Vec<&String> = channels.iter().map(|(port, _)| port).collect();
        devices.sort();
        devices.dedup();
        let said = named(
            messages::MSG_SILENCED,
            &[("channels", channels.len().into()), ("devices", devices.len().into())],
        );
        if let Some(sender) = self.sender.as_mut() {
            sender.silence(&channels);
        }
        said
    }

    /// Plan ahead: turn the moments due within the lookahead into queued events.
    pub fn tick(&mut self) {
        let (Some(sender), Some(player)) = (self.sender.as_mut(), self.player.as_mut()) else {
            return;
        };
        let now = sender.now();
        player.tick(sender, now);
    }

    /// Stop everything and end the sender, as the tracker quits.
    pub fn close(&mut self) {
        self.stop_all();
        if let Some(mut sender) = self.sender.take() {
            sender.close();
        }
        self.player = None;
    }

    /// The song playing's name, or none.
    pub fn song_name(&self) -> &str {
        &self.song_name
    }

    /// Whether a listening page's preview plays.
    pub fn is_previewing(&self) -> bool {
        self.previewing && self.is_playing()
    }

    pub fn is_playing(&self) -> bool {
        self.asking(|player, now| player.is_playing(now)).unwrap_or(false)
    }

    pub fn playing_scenes(&self) -> Vec<usize> {
        self.asking(|player, now| player.playing_scenes(now)).unwrap_or_default()
    }

    pub fn is_clip_playing(&self, index: usize, track: &str) -> bool {
        self.asking(|player, now| player.is_clip_playing(now, index, track)).unwrap_or(false)
    }

    pub fn is_track_sounding(&self, track: &str) -> bool {
        self.asking(|player, now| player.is_track_sounding(now, track)).unwrap_or(false)
    }

    pub fn scene_elapsed(&self, index: usize) -> Option<f64> {
        self.asking(|player, now| player.scene_elapsed(now, index)).flatten()
    }

    pub fn clip_elapsed(&self, index: usize, track: &str) -> Option<f64> {
        self.asking(|player, now| player.clip_elapsed(now, index, track)).flatten()
    }

    pub fn repeats_left(&self, index: usize, track: &str) -> Option<i64> {
        self.asking(|player, now| player.repeats_left(now, index, track)).flatten()
    }

    pub fn song_position(&self) -> Option<f64> {
        self.asking(|player, now| player.song_position(now)).flatten()
    }

    /// Where the song is and how long it is while it plays, such as ▶ 0:22 / 3:00, or None while it doesn't.
    pub fn playing_clock(&self) -> Option<String> {
        let position = self.song_position()?;
        let at = crate::page::clock(Some(position));
        let total = crate::page::clock(self.song_seconds());
        Some(named(
            llamatron_strings::marks::MSG_PLAYING_CLOCK,
            &[("at", at.as_str().into()), ("total", total.as_str().into())],
        ))
    }

    /// How long the song playing lasts, in seconds.
    pub fn song_seconds(&self) -> Option<f64> {
        self.player.as_ref().map(|player| player.get_score().song_seconds())
    }

    /// An answer the player gives on the sender's clock, or None while nothing has played.
    fn asking<T>(&self, question: impl Fn(&Player, f64) -> T) -> Option<T> {
        let (sender, player) = (self.sender.as_ref()?, self.player.as_ref()?);
        Some(question(player, sender.now()))
    }

    /// A score of the current song as it is now, with the sender open on its routes' ports and the player holding it; the
    /// sender's clock now.
    fn ready(&mut self, document: &Document, instead: &[(String, String)]) -> Result<f64, String> {
        let routes = routes(document, instead);
        let playing = self.is_playing();
        if !playing || self.seed.is_none() {
            self.seed = Some(PythonRandom::unseeded().randrange(0, SEED_RANGE, 1) as i64);
        }
        let mut ports: Vec<OpenedPort> = Vec::new();
        for (_, route) in &routes {
            if !ports.iter().any(|port| port.name == route.port) {
                ports.push(opened_port(&route.port));
            }
        }
        ports.sort_by(|a, b| a.name.cmp(&b.name));
        if self.sender.as_ref().is_none_or(|sender| !sender.is_running()) || ports.iter().any(|port| !self.ports.contains(port)) {
            if let Some(mut sender) = self.sender.take() {
                sender.close();
            }
            self.player = None;
            let mut wanted = self.ports.clone();
            for port in ports {
                if !wanted.contains(&port) {
                    wanted.push(port);
                }
            }
            self.sender = Some(BackendSender::start(&wanted)?);
            self.ports = wanted;
        }
        let setlist = document.get_setlist();
        let song = document.song();
        let score = Score::new(setlist, song, &routes, self.seed).map_err(|problem| format!("{problem:?}"))?;
        let sender = self.sender.as_mut().ok_or_else(sender_gone)?;
        sender.set_sounds(&sounds(document, &routes));
        let now = sender.now();
        self.song_name = document.get_current_song_name().to_string();
        match self.player.as_mut() {
            Some(player) if playing => player.set_score(score),
            _ => self.player = Some(Player::new(score, LAUNCH_LEAD_SECONDS)),
        }
        Ok(now)
    }
}

/// Why a launch found no sender.
fn sender_gone() -> String {
    errors::ERR_SENDER_DID_NOT_START.to_string()
}

/// A port as the daemon opens it, its kind told by its name.
fn opened_port(name: &str) -> OpenedPort {
    if let Some(group) = name.strip_prefix(BUILT_IN_PORT_PREFIX) {
        return OpenedPort {
            name: name.to_string(),
            kind: BUILT_IN,
            group: group.trim().parse().unwrap_or(0),
        };
    }
    if name.starts_with(FLUIDSYNTH_PORT_PREFIX) {
        return OpenedPort {
            name: name.to_string(),
            kind: FLUIDSYNTH,
            group: 0,
        };
    }
    OpenedPort {
        name: name.to_string(),
        kind: MIDI,
        group: 0,
    }
}

/// FluidSynth's port, named after this process.
fn fluidsynth_port() -> String {
    format!("{FLUIDSYNTH_PORT_PREFIX} {}", std::process::id())
}

/// The instrument a track of the current song plays through, by name, where the set has it.
fn instrument_name(document: &Document, track: &str) -> Option<String> {
    let name = document.song().get_track(track)?.get_written(TrackSetting::INSTRUMENT)?.as_str()?.to_string();
    matches!(document.get_setlist().get_item(Section::INSTRUMENTS, &name), Some(Item::Instrument(_))).then_some(name)
}

/// An instrument of the set by name.
fn instrument<'a>(document: &'a Document, name: &str) -> Option<&'a Instrument> {
    match document.get_setlist().get_item(Section::INSTRUMENTS, name) {
        Some(Item::Instrument(instrument)) => Some(instrument),
        _ => None,
    }
}

/// An instrument's device, where it has one.
fn device_of(instrument: &Instrument) -> Option<String> {
    instrument
        .get_written(InstrumentSetting::DEVICE)
        .and_then(Data::as_str)
        .filter(|device| !device.is_empty())
        .map(str::to_string)
}

fn is_built_in(instrument: &Instrument) -> bool {
    instrument.get_written(InstrumentSetting::KIND).and_then(Data::as_str) == Some(BUILT_IN_KIND)
}

/// Whether a track plays through an instrument that has a device or is built in.
fn has_a_device(document: &Document, track: &str) -> bool {
    instrument_name(document, track)
        .and_then(|name| instrument(document, &name))
        .is_some_and(|instrument| device_of(instrument).is_some() || is_built_in(instrument))
}

/// Each instrument whose MIDI port this computer doesn't list now, with its device; FluidSynth is no port.
fn missing_devices(document: &Document) -> Vec<(String, String)> {
    let connected = output_port_names();
    let mut missing = Vec::new();
    for (name, item) in document.get_setlist().items(Section::INSTRUMENTS) {
        let Item::Instrument(instrument) = item else { continue };
        if let Some(device) = device_of(instrument) {
            if device != FLUIDSYNTH_DEVICE && !connected.contains(&device) {
                missing.push((name.clone(), device));
            }
        }
    }
    missing
}

/// Each track's route, for the tracks whose instrument has a device or is built in; instead maps a track to an instrument
/// to play through for one preview. A track through FluidSynth takes the channel the General MIDI export gives it and its
/// instrument's sound as the program; each built-in instrument is a channel of the built-in ports, in the order the tracks
/// first name them.
pub fn routes(document: &Document, instead: &[(String, String)]) -> Vec<(String, Route)> {
    let song = document.song();
    let mut midi: Vec<(String, &Instrument)> = Vec::new();
    let mut built_in: Vec<(String, String)> = Vec::new();
    for track in song.get_track_names() {
        let chosen = instead.iter().find(|(name, _)| name == track).map(|(_, instrument)| instrument.clone());
        let Some(name) = chosen.or_else(|| instrument_name(document, track)) else {
            continue;
        };
        let Some(held) = instrument(document, &name) else { continue };
        if is_built_in(held) {
            built_in.push((track.to_string(), name));
        } else if device_of(held).is_some() {
            midi.push((track.to_string(), held));
        }
    }
    let is_drum = |track: &str| song.get_track(track).is_some_and(|held| held.is_drum());
    let is_muted = |track: &str| {
        song.get_track(track)
            .is_some_and(|held| matches!(held.get_written(TrackSetting::MUTE), Some(Data::Bool(true))))
    };
    let mut melodic = 0;
    let mut channels: Vec<(String, i64)> = Vec::new();
    for (track, held) in &midi {
        if device_of(held).as_deref() == Some(FLUIDSYNTH_DEVICE) && (is_drum(track) || !is_muted(track)) {
            let channel = if is_drum(track) {
                DRUM_CHANNEL
            } else {
                melodic += 1;
                MELODIC_CHANNELS[(melodic - 1) % MELODIC_CHANNELS.len()]
            };
            channels.push((track.clone(), channel));
        }
    }
    let mut routes = Vec::new();
    for (track, held) in &midi {
        let early = held
            .get_written(InstrumentSetting::LATENCY)
            .and_then(Data::as_whole)
            .map_or(0.0, |latency| latency as f64 / MILLISECONDS);
        let device = device_of(held).unwrap_or_default();
        if device != FLUIDSYNTH_DEVICE {
            let channel = held
                .get_written(InstrumentSetting::CHANNEL)
                .and_then(Data::as_whole)
                .map_or(1, |channel| channel as i64)
                - CHANNEL_OFFSET;
            routes.push((
                track.clone(),
                Route {
                    port: device,
                    channel,
                    program: None,
                    keyswitches: true,
                    sound: None,
                    early,
                },
            ));
        } else if let Some((_, channel)) = channels.iter().find(|(name, _)| name == track) {
            let sound = held.get_written(InstrumentSetting::GM_SOUND).and_then(Data::as_whole).map(|sound| sound as i64);
            let program = if is_drum(track) { None } else { sound.map(|sound| sound - MIN_GM_SOUND) };
            routes.push((
                track.clone(),
                Route {
                    port: fluidsynth_port(),
                    channel: *channel,
                    program,
                    keyswitches: false,
                    sound: None,
                    early,
                },
            ));
        }
    }
    let mut numbers: Vec<String> = Vec::new();
    for (track, name) in built_in {
        let number = numbers.iter().position(|held| *held == name).unwrap_or_else(|| {
            numbers.push(name.clone());
            numbers.len() - 1
        });
        let port = format!("{BUILT_IN_PORT_PREFIX} {}", number / INSTRUMENTS_PER_PORT);
        let channel = (number % INSTRUMENTS_PER_PORT) as i64;
        routes.push((
            track,
            Route {
                port,
                channel,
                program: None,
                keyswitches: false,
                sound: Some(name),
                early: 0.0,
            },
        ));
    }
    routes
}

/// The sound each built-in route's port and channel plays, as the backend compiles it.
fn sounds(document: &Document, routes: &[(String, Route)]) -> Vec<((String, i64), Data)> {
    let drums_from = document
        .get_setlist()
        .get_written(SetlistSetting::DEFAULT_DRUM_OCTAVE)
        .and_then(Data::as_whole)
        .map_or(3, |octave| octave as i64)
        * 12;
    let mut found = Vec::new();
    for (_, route) in routes {
        let Some(name) = &route.sound else { continue };
        let Some(held) = instrument(document, name) else { continue };
        let key = (route.port.clone(), route.channel);
        if !found.iter().any(|(held_key, _): &((String, i64), Data)| *held_key == key) {
            found.push((key, crate::sound_spec::synth_spec(&crate::instrument_sound::Sound::of(held), drums_from)));
        }
    }
    found
}

/// The port and channel pairs the set's instruments use on the devices connected now, each once.
fn channels_in_use(document: &Document) -> Vec<(String, i64)> {
    let connected = output_port_names();
    let mut pairs: Vec<(String, i64)> = Vec::new();
    for (_, item) in document.get_setlist().items(Section::INSTRUMENTS) {
        let Item::Instrument(instrument) = item else { continue };
        let Some(device) = device_of(instrument) else { continue };
        if device == FLUIDSYNTH_DEVICE || !connected.contains(&device) {
            continue;
        }
        let channel = instrument
            .get_written(InstrumentSetting::CHANNEL)
            .and_then(Data::as_whole)
            .map_or(1, |channel| channel as i64)
            - CHANNEL_OFFSET;
        if !pairs.contains(&(device.clone(), channel)) {
            pairs.push((device, channel));
        }
    }
    pairs.sort();
    pairs
}
