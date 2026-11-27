// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The timeline (the Python realtime/render_process/timeline.py): a rendered grid as one time-ordered list of MIDI events
//! across every track, with absolute times. Real-time playback renders a song as the exports do and then only schedules,
//! so the timeline is read from the same note timing the MIDI export writes. Each event carries the whole-note time it
//! came from, the seconds it plays at, its track's port and channel, and a tag naming its scene and track, so that one
//! clip's events can be dropped or stopped.

use crate::realtime::row_clock::RowClock;
use llamatron_engine::clip::Clip;
use llamatron_engine::error::Rendered;
use llamatron_engine::realizer::{Grid, GridRow};
use llamatron_engine::timing::{keyswitch_events, timed_events};
use llamatron_math::Rational;

/// The kinds of event, as the status byte without its channel.
pub const NOTE_ON: i64 = 0x90;
pub const NOTE_OFF: i64 = 0x80;
pub const CONTROL_CHANGE: i64 = 0xB0;
/// A program change, which only FluidSynth's routes send, at the start of each clip.
pub const PROGRAM_CHANGE: i64 = 0xC0;
/// A controller no MIDI device is sent and the built-in instruments read as their clip starting.
pub const SCENE_STARTED: i64 = 102;
/// The controllers a built-in instrument is told the song's tempo on, for its LFOs that follow it: its tenths of a quarter
/// note a minute in two parts, coarse (the tenths over 128) then fine, as two MIDI values can carry it.
pub const TEMPO_COARSE: i64 = 103;
/// The controllers a built-in instrument is told playback starts from silence and stops on, so that its modulators run
/// only while it plays and On play ones start from zero (the backend's engine/mod.rs, PLAY_STARTED).
pub const PLAY_STARTED: i64 = 105;
pub const PLAY_STOPPED: i64 = 106;
pub const TEMPO_FINE: i64 = 104;
const TEMPO_TENTHS: f64 = 10.0;
const TEMPO_PART: i64 = 128;
const MOST_TEMPO_TENTHS: i64 = TEMPO_PART * TEMPO_PART - 1;

/// A tempo in quarter notes a minute as its two parts, coarse and fine, each a MIDI value.
pub fn tempo_parts(tempo: f64) -> (i64, i64) {
    let tenths = ((tempo * TEMPO_TENTHS).round() as i64).clamp(0, MOST_TEMPO_TENTHS);
    (tenths / TEMPO_PART, tenths % TEMPO_PART)
}
const NO_VELOCITY: i64 = 0;
/// The CC that places a channel in the stereo field.
const PAN_CONTROL: i64 = 10;

/// Where a track's events go: an output port's name, a MIDI channel from 0, the program to choose first, the pan CC's
/// value to send first or None, whether keyswitch notes go this way, the built-in sound that plays the track or None for
/// MIDI, and how many seconds earlier its events are sent, for a device slow to sound.
#[derive(Clone, Debug, PartialEq)]
pub struct Route {
    pub port: String,
    pub channel: i64,
    pub program: Option<i64>,
    pub pan: Option<i64>,
    pub keyswitches: bool,
    pub sound: Option<String>,
    pub early: f64,
}

/// Which clip an event belongs to: the scene's place in the song from 0, the track's name, and which play of the clip.
#[derive(Clone, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ClipTag {
    pub scene: usize,
    pub track: String,
    pub play: i64,
}

/// One event of the timeline: when, in whole notes from the song's start and in seconds, where, what and whose, and
/// whether it is a keyswitch's.
#[derive(Clone, Debug, PartialEq)]
pub struct Playing {
    pub whole: Rational,
    pub seconds: f64,
    pub port: String,
    pub channel: i64,
    pub kind: i64,
    pub number: i64,
    pub value: i64,
    pub tag: ClipTag,
    pub switch: bool,
}

impl Playing {
    /// The event's bytes: two for a program change, three for the rest.
    pub fn data(&self) -> Vec<u8> {
        let status = (self.kind | self.channel) as u8;
        if self.kind == PROGRAM_CHANGE {
            return vec![status, self.number as u8];
        }
        vec![status, self.number as u8, self.value as u8]
    }

    /// What the timeline is ordered by: time, with note offs and program changes first at an instant.
    fn sort_key(&self) -> (Rational, u8) {
        let first = self.kind == NOTE_OFF || self.kind == PROGRAM_CHANGE;
        (self.whole, if first { 0 } else { 1 })
    }
}

/// A row's clock, from its tempo and the changes inside it.
pub fn clock_of(grid: &Grid, row: &GridRow) -> RowClock {
    RowClock::new(&llamatron_exporters::midi::tempos_in(grid, row))
}

/// How long a row lasts in whole notes: as long as its longest clip.
pub fn row_length(row: &GridRow) -> Rendered<Rational> {
    let mut longest = Rational::ZERO;
    for (_, clip) in &row.clips {
        longest = longest.max(clip.total_length()?);
    }
    Ok(longest)
}

/// A rendered grid's events in time order, the scenes laid end to end as the MIDI export lays them; a track with no route
/// or a muted one is left out.
pub fn song_timeline(grid: &Grid, routes: &[(String, Route)]) -> Rendered<Vec<Playing>> {
    let starts = llamatron_exporters::midi::row_starts(grid)?;
    let mut events = Vec::new();
    let mut scene_seconds = 0.0;
    for (place, row) in grid.rows.iter().enumerate() {
        let clock = clock_of(grid, row);
        for column in &grid.columns {
            let Some((_, route)) = routes.iter().find(|(track, _)| *track == column.name) else {
                continue;
            };
            let Some((_, clip)) = row.clips.iter().find(|(track, _)| *track == column.name) else {
                continue;
            };
            if column.mute {
                continue;
            }
            let tag = ClipTag {
                scene: place,
                track: column.name.clone(),
                play: 0,
            };
            events.extend(clip_timeline(clip, route, &tag, starts[place], scene_seconds, &clock)?);
        }
        scene_seconds += clock.seconds_at_exact(row_length(row)?);
    }
    events.sort_by_key(Playing::sort_key);
    Ok(events)
}

/// One clip's notes and CC values as events, placed at its scene's start and timed by its row's clock, after its route's
/// openings: the program change and a built-in instrument's SCENE_STARTED.
pub fn clip_timeline(clip: &Clip, route: &Route, tag: &ClipTag, scene_start: Rational, scene_seconds: f64, clock: &RowClock) -> Rendered<Vec<Playing>> {
    let sent_from = scene_seconds - route.early;
    let at = |time: Rational, kind: i64, number: i64, value: i64| Playing {
        whole: scene_start + time,
        seconds: sent_from + clock.seconds_at_exact(time),
        port: route.port.clone(),
        channel: route.channel,
        kind,
        number,
        value,
        tag: tag.clone(),
        switch: false,
    };
    let mut events = Vec::new();
    if let Some(program) = route.program {
        events.push(at(Rational::ZERO, PROGRAM_CHANGE, program, NO_VELOCITY));
    }
    if let Some(pan) = route.pan {
        events.push(at(Rational::ZERO, CONTROL_CHANGE, PAN_CONTROL, pan));
    }
    let (notes, clip_length) = timed_events(clip, clip.scale.as_ref())?;
    if route.sound.is_some() {
        events.push(at(Rational::ZERO, CONTROL_CHANGE, SCENE_STARTED, NO_VELOCITY));
        // The tempo the clip starts at and each change of it while the clip plays, for LFOs that follow the tempo.
        for (start, tempo) in clock.tempos() {
            let start = if *start < Rational::ZERO { Rational::ZERO } else { *start };
            if start > Rational::ZERO && start >= clip_length {
                continue;
            }
            let (coarse, fine) = tempo_parts(*tempo);
            events.push(at(start, CONTROL_CHANGE, TEMPO_COARSE, coarse));
            events.push(at(start, CONTROL_CHANGE, TEMPO_FINE, fine));
        }
    }
    // Keyswitches go to a plugin through a MIDI port, never to FluidSynth, which would sound each as a note, and come
    // before the notes they change at the same instant.
    if route.keyswitches {
        for switch in keyswitch_events(clip, clip_length) {
            events.push(Playing {
                switch: true,
                ..at(switch.start, NOTE_ON, switch.midi_number, switch.velocity)
            });
            events.push(Playing {
                switch: true,
                ..at(switch.end, NOTE_OFF, switch.midi_number, NO_VELOCITY)
            });
        }
    }
    for note in notes {
        if note.end > note.start {
            events.push(at(note.start, NOTE_ON, note.midi_number, note.velocity));
            events.push(at(note.end, NOTE_OFF, note.midi_number, NO_VELOCITY));
        }
    }
    for (time, number, value) in llamatron_exporters::midi::control_events(clip, clip_length) {
        events.push(at(time, CONTROL_CHANGE, number, value));
    }
    Ok(events)
}
