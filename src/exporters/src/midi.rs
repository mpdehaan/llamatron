// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The MIDI files llamatron writes (the Python exporters/midi_messages.py, clip_tree.py and midi_arrangement.py), byte for
//! byte as the mido library writes them: events at ticks, 480 to a quarter note, sorted by tick and then kind, each track's
//! messages with the gaps between them as delta times, running status kept between channel messages.
//!
//! The clip tree writes a file per clip; the song is one file of type 1, a tempo track and a track per unmuted track, its
//! scenes laid end to end; the stems are a file per unmuted track, each the song's length; the General MIDI file is the song
//! with each track on a channel of its own and a program change giving it its instrument's sound.

use llamatron_engine::clip::Clip;
use llamatron_engine::error::Rendered;
use llamatron_engine::realizer::{Grid, GridColumn, GridRow};
use llamatron_engine::timing::timed_events;
use llamatron_math::Rational;
use llamatron_model::values::time_signature::TimeSignature;

const TICKS_PER_BEAT: i128 = 480;
const BEATS_PER_WHOLE_NOTE: i128 = 4;
const SINGLE_TRACK_FILE: u16 = 0;
const MULTI_TRACK_FILE: u16 = 1;
/// The kinds of event, in the order those at one tick are written.
const TIME_SIGNATURE: u8 = 0;
const SET_TEMPO: u8 = 1;
const NOTE_OFF: u8 = 2;
const CONTROL_CHANGE: u8 = 3;
const NOTE_ON: u8 = 5;
/// The velocity mido gives a note off that names none.
const NOTE_OFF_VELOCITY: u8 = 64;
const DRUM_CHANNEL: u8 = 9;
const MIDI_CLOCKS_PER_WHOLE_NOTE: i128 = 96;
const THIRTY_SECONDS_PER_QUARTER_NOTE: u8 = 8;
const SLIDE_STEP: (i128, i128) = (1, 64);

/// One MIDI message to write: at a tick, of a kind, with its number (note or CC) and value (velocity, CC value or tempo).
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
struct MidiEvent {
    tick: i128,
    kind: u8,
    number: i64,
    value: i64,
}

/// A fraction of a whole note in ticks, rounding once, so that times never drift.
fn ticks(length: Rational) -> i128 {
    (length * Rational::whole(BEATS_PER_WHOLE_NOTE * TICKS_PER_BEAT)).round()
}

/// A tempo as a MIDI file sets it, microseconds a quarter note, worked out as mido's bpm2tempo works it out.
fn tempo_value(tempo: f64) -> i64 {
    (60.0 * 1e6 / tempo * 4.0 / 4.0).round_ties_even() as i64
}

/// Text as a MIDI file holds it, latin-1, a character it hasn't a question mark.
fn midi_text(text: &str) -> Vec<u8> {
    text.chars()
        .map(|character| if (character as u32) < 256 { character as u32 as u8 } else { b'?' })
        .collect()
}

/// A name with the characters a file name can't safely hold, whitespace and slashes, replaced by underscores.
pub fn safe_file_name(text: &str) -> String {
    text.chars()
        .map(|character| {
            if character.is_whitespace() || character == '/' || character == '\\' {
                '_'
            } else {
                character
            }
        })
        .collect()
}

fn variable_int(mut value: u64) -> Vec<u8> {
    let mut bytes = vec![(value & 0x7f) as u8];
    value >>= 7;
    while value > 0 {
        bytes.push(((value & 0x7f) as u8) | 0x80);
        value >>= 7;
    }
    bytes.reverse();
    bytes
}

/// One track's messages: its name, a program change where it has one, its events in order, and its end.
struct Track {
    bytes: Vec<u8>,
    running_status: Option<u8>,
}

impl Track {
    fn new(name: &str) -> Track {
        let mut track = Track {
            bytes: Vec::new(),
            running_status: None,
        };
        let text = midi_text(name);
        let mut data = vec![0xff, 0x03];
        data.extend(variable_int(text.len() as u64));
        data.extend(text);
        track.meta(0, &data);
        track
    }

    fn meta(&mut self, delay: i128, data: &[u8]) {
        self.bytes.extend(variable_int(delay as u64));
        self.bytes.extend(data);
        self.running_status = None;
    }

    fn channel(&mut self, delay: i128, data: &[u8]) {
        self.bytes.extend(variable_int(delay as u64));
        if self.running_status == Some(data[0]) {
            self.bytes.extend(&data[1..]);
        } else {
            self.bytes.extend(data);
        }
        self.running_status = Some(data[0]);
    }

    fn event(&mut self, event: &MidiEvent, delay: i128, channel: u8) {
        match event.kind {
            TIME_SIGNATURE => {
                let signature = TimeSignature::new(event.number, event.value).unwrap_or_else(|_| TimeSignature::new(4, 4).expect("4/4 is a time signature"));
                let clocks = (signature.beat_length() * Rational::whole(MIDI_CLOCKS_PER_WHOLE_NOTE)).floor() as u8;
                let denominator = (signature.get_unit() as u32).trailing_zeros() as u8;
                self.meta(
                    delay,
                    &[
                        0xff,
                        0x58,
                        0x04,
                        signature.get_beats() as u8,
                        denominator,
                        clocks,
                        THIRTY_SECONDS_PER_QUARTER_NOTE,
                    ],
                );
            }
            SET_TEMPO => {
                let tempo = event.value as u32;
                self.meta(delay, &[0xff, 0x51, 0x03, (tempo >> 16) as u8, (tempo >> 8) as u8, tempo as u8]);
            }
            NOTE_OFF => self.channel(delay, &[0x80 | channel, event.number as u8, NOTE_OFF_VELOCITY]),
            CONTROL_CHANGE => self.channel(delay, &[0xb0 | channel, event.number as u8, event.value as u8]),
            _ => self.channel(delay, &[0x90 | channel, event.number as u8, event.value as u8]),
        }
    }

    /// A track named name, playing events in order on a channel and ending at a tick, a program sent first where given.
    fn of(name: &str, mut events: Vec<MidiEvent>, end: i128, channel: u8, program: Option<u8>) -> Vec<u8> {
        let mut track = Track::new(name);
        if let Some(program) = program {
            track.channel(0, &[0xc0 | channel, program]);
        }
        events.sort();
        let mut now = 0;
        for event in &events {
            track.event(event, event.tick - now, channel);
            now = event.tick;
        }
        track.meta(end - now, &[0xff, 0x2f, 0x00]);
        track.bytes
    }
}

/// A MIDI file of a type, its tracks' bytes each a chunk.
fn midi_file(format: u16, tracks: Vec<Vec<u8>>) -> Vec<u8> {
    let mut bytes = b"MThd".to_vec();
    bytes.extend(6u32.to_be_bytes());
    bytes.extend(format.to_be_bytes());
    bytes.extend((tracks.len() as u16).to_be_bytes());
    bytes.extend((TICKS_PER_BEAT as u16).to_be_bytes());
    for track in tracks {
        bytes.extend(b"MTrk");
        bytes.extend((track.len() as u32).to_be_bytes());
        bytes.extend(track);
    }
    bytes
}

fn time_signature_event(tick: i128, signature: &TimeSignature) -> MidiEvent {
    MidiEvent {
        tick,
        kind: TIME_SIGNATURE,
        number: signature.get_beats(),
        value: signature.get_unit(),
    }
}

fn tempo_event(tick: i128, tempo: f64) -> MidiEvent {
    MidiEvent {
        tick,
        kind: SET_TEMPO,
        number: 0,
        value: tempo_value(tempo),
    }
}

/// One value a CC lane takes: when, the value, and whether it slides to the next.
pub type ControlPoint = (Rational, i64, bool);

/// A clip's CC values by number, each lane's in time order, a later value at a time replacing an earlier, the groove moving
/// each with its step, those at or after the clip's length left out.
pub fn control_points(clip: &Clip, length: Rational) -> Vec<(i64, Vec<ControlPoint>)> {
    let mut lanes: Vec<(i64, Vec<ControlPoint>)> = Vec::new();
    for control in &clip.controls {
        let time = match &clip.groove {
            Some(groove) => groove.moved(control.time),
            None => control.time,
        };
        if time >= length {
            continue;
        }
        let lane = match lanes.iter().position(|(number, _)| *number == control.number) {
            Some(place) => &mut lanes[place].1,
            None => {
                lanes.push((control.number, Vec::new()));
                &mut lanes.last_mut().expect("a lane was just added").1
            }
        };
        if lane.last().is_some_and(|(last, _, _)| *last == time) {
            lane.pop();
        }
        lane.push((time, control.value, control.slide));
    }
    lanes
}

/// A clip's CC values as they are sent, each lane's values in time order, a later one at a time replacing an earlier, the
/// groove moving each with its step, and a slide sending a value every 64th on its way to the next.
pub fn control_events(clip: &Clip, length: Rational) -> Vec<(Rational, i64, i64)> {
    let lanes = control_points(clip, length);
    let step = Rational::new(SLIDE_STEP.0, SLIDE_STEP.1);
    let mut events = Vec::new();
    for (number, lane) in &lanes {
        for (place, (time, value, slide)) in lane.iter().enumerate() {
            events.push((*time, *number, *value));
            let Some((end, target, _)) = lane.get(place + 1).filter(|_| *slide) else {
                continue;
            };
            let mut sent = *value;
            let mut now = *time + step;
            while now < *end {
                let ramped = (Rational::whole(*value as i128) + Rational::whole((*target - *value) as i128) * (now - *time) / (*end - *time)).round() as i64;
                if ramped != sent {
                    events.push((now, *number, ramped));
                    sent = ramped;
                }
                now = now + step;
            }
        }
    }
    events.sort();
    events
}

/// A clip's notes and CC values as events from a start tick.
fn clip_events(clip: &Clip, start: i128) -> Rendered<Vec<MidiEvent>> {
    let (notes, clip_length) = timed_events(clip, clip.scale.as_ref())?;
    let mut events = Vec::new();
    for note in notes {
        let (note_start, note_end) = (start + ticks(note.start), start + ticks(note.end));
        if note_end > note_start {
            events.push(MidiEvent {
                tick: note_start,
                kind: NOTE_ON,
                number: note.midi_number,
                value: note.velocity,
            });
            events.push(MidiEvent {
                tick: note_end,
                kind: NOTE_OFF,
                number: note.midi_number,
                value: 0,
            });
        }
    }
    for (time, number, value) in control_events(clip, clip_length) {
        events.push(MidiEvent {
            tick: start + ticks(time),
            kind: CONTROL_CHANGE,
            number,
            value,
        });
    }
    Ok(events)
}

/// A row's tempos: its own, or the song's, at its start, then its changes.
pub fn tempos_in(grid: &Grid, row: &GridRow) -> Vec<(Rational, f64)> {
    let mut tempos = vec![(Rational::ZERO, row.tempo.unwrap_or(grid.tempo))];
    tempos.extend(row.tempo_changes.iter().copied());
    tempos
}

fn clip_of<'g>(row: &'g GridRow, column: &GridColumn) -> Option<&'g Clip> {
    row.clips.iter().find(|(track, _)| *track == column.name).map(|(_, clip)| clip)
}

/// Where each row starts, the rows laid end to end, each as long as its longest clip.
pub fn row_starts(grid: &Grid) -> Rendered<Vec<Rational>> {
    let mut starts = Vec::new();
    let mut now = Rational::ZERO;
    for row in &grid.rows {
        starts.push(now);
        let mut longest = Rational::ZERO;
        for (_, clip) in &row.clips {
            longest = longest.max(clip.total_length()?);
        }
        now = now + longest;
    }
    starts.push(now);
    Ok(starts)
}

/// A file's name and its bytes.
pub type MidiExport = (String, Vec<u8>);

/// A file per clip, named after the song and the clip's scene and track, numbered from 1.
pub fn clip_tree(grid: &Grid, name: &str) -> Rendered<Vec<MidiExport>> {
    let mut files = Vec::new();
    for (row_number, row) in grid.rows.iter().enumerate() {
        for (track_number, column) in grid.columns.iter().enumerate() {
            let Some(clip) = clip_of(row, column) else { continue };
            let part = |kind: &str, number: usize, named: &str| {
                let numbered = format!("{kind}_{:03}", number + 1);
                if named.is_empty() {
                    numbered
                } else {
                    format!("{numbered}-{}", safe_file_name(named))
                }
            };
            let filename = format!("{name}_clip_{}-{}.mid", part("s", row_number, &row.name), part("t", track_number, &column.name));
            let (_, clip_length) = timed_events(clip, clip.scale.as_ref())?;
            let signature = clip.time_signature.unwrap_or(grid.time_signature);
            let mut events = vec![time_signature_event(0, &signature)];
            for (time, tempo) in tempos_in(grid, row) {
                if time == Rational::ZERO || time < clip_length {
                    events.push(tempo_event(ticks(time), tempo));
                }
            }
            events.extend(clip_events(clip, 0)?);
            let track = Track::of(filename.trim_end_matches(".mid"), events, ticks(clip_length), 0, None);
            files.push((filename, midi_file(SINGLE_TRACK_FILE, vec![track])));
        }
    }
    Ok(files)
}

/// What every arrangement file starts with: the song's time signature, then a tempo wherever it changes, always at the start.
fn conductor_events(grid: &Grid, starts: &[Rational]) -> Vec<MidiEvent> {
    let mut events = vec![time_signature_event(0, &grid.time_signature)];
    let mut tempo = None;
    for (row, start) in grid.rows.iter().zip(starts) {
        for (time, changed) in tempos_in(grid, row) {
            if Some(changed) != tempo {
                tempo = Some(changed);
                events.push(tempo_event(ticks(*start + time), changed));
            }
        }
    }
    events
}

/// A track's notes and CC values across the whole song, each clip at its scene's start.
fn track_events(grid: &Grid, column: &GridColumn, starts: &[Rational]) -> Rendered<Vec<MidiEvent>> {
    let mut events = Vec::new();
    for (row, start) in grid.rows.iter().zip(starts) {
        if let Some(clip) = clip_of(row, column) {
            events.extend(clip_events(clip, ticks(*start))?);
        }
    }
    Ok(events)
}

fn sounding(grid: &Grid) -> Vec<&GridColumn> {
    grid.columns.iter().filter(|column| !column.mute).collect()
}

/// The whole song as one file of type 1: the tempo track named after the song, then a track per unmuted track; with
/// general_midi, each track on a channel of its own, drums on channel 10, and a program change giving it its sound.
pub fn song_file(grid: &Grid, name: &str, general_midi: bool) -> Rendered<MidiExport> {
    song_file_of(grid, name, general_midi, &|_| true)
}

/// The whole song as song_file writes it, with only the unmuted tracks kept, as the WAV export keeps those that play
/// through FluidSynth, the channels given among them alone.
pub fn song_file_of(grid: &Grid, name: &str, general_midi: bool, kept: &dyn Fn(&GridColumn) -> bool) -> Rendered<MidiExport> {
    let starts = row_starts(grid)?;
    let end = ticks(starts[starts.len() - 1]);
    let mut tracks = vec![Track::of(name, conductor_events(grid, &starts), end, 0, None)];
    let mut melodic = 0;
    for column in sounding(grid).into_iter().filter(|column| kept(column)) {
        let (channel, program) = if !general_midi {
            (0, None)
        } else if column.drum {
            (DRUM_CHANNEL, None)
        } else {
            let channel = [0u8, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15][melodic % 15];
            melodic += 1;
            (channel, column.gm_sound.map(|sound| (sound - 1) as u8))
        };
        tracks.push(Track::of(&column.name, track_events(grid, column, &starts)?, end, channel, program));
    }
    let filename = if general_midi { format!("{name}_gm.mid") } else { format!("{name}.mid") };
    Ok((filename, midi_file(MULTI_TRACK_FILE, tracks)))
}

/// A file per unmuted track, each the song's length and carrying its tempo changes.
pub fn stems(grid: &Grid, name: &str) -> Rendered<Vec<MidiExport>> {
    let starts = row_starts(grid)?;
    let end = ticks(starts[starts.len() - 1]);
    let mut files = Vec::new();
    for (number, column) in sounding(grid).into_iter().enumerate() {
        let filename = if column.name.is_empty() {
            format!("{name}_stem_{:03}.mid", number + 1)
        } else {
            format!("{name}_stem_{:03}-{}.mid", number + 1, safe_file_name(&column.name))
        };
        let mut events = conductor_events(grid, &starts);
        events.extend(track_events(grid, column, &starts)?);
        files.push((filename, midi_file(SINGLE_TRACK_FILE, vec![Track::of(&column.name, events, end, 0, None)])));
    }
    Ok(files)
}

/// What a track plays, read back in seconds from the song's start through the song's tempo map, as the WAV export renders
/// a built-in instrument: each note's start, with its pitch and velocity, and its end, with a velocity of 0; the moments
/// its clips start; and the moments every note of it is ended.
pub struct TimedTrack {
    pub notes: Vec<(f64, i64, i64)>,
    pub scene_starts: Vec<f64>,
    pub endings: Vec<f64>,
    /// The track's CCs, the endings and the clip starts' mark aside: seconds, number and value.
    pub controls: Vec<(f64, i64, i64)>,
    /// The song's tempo from its start and at each change: seconds, and quarter notes a minute.
    pub tempos: Vec<(f64, f64)>,
}

/// The controls that end every note, and the one the real-time player marks a clip's start with.
const ENDING_CONTROLS: [i64; 2] = [120, 123];
const CLIP_START_CONTROL: i64 = 102;

/// A track's notes, clip starts and endings in seconds, or None where the song has no track of the name.
pub fn timed_track(grid: &Grid, track: &str) -> Rendered<Option<TimedTrack>> {
    let Some(column) = grid.columns.iter().find(|column| column.name == track) else {
        return Ok(None);
    };
    let starts = row_starts(grid)?;
    let tempo_map = TempoMap::of(&conductor_events(grid, &starts));
    let mut events = track_events(grid, column, &starts)?;
    events.sort();
    let mut timed = TimedTrack {
        notes: Vec::new(),
        scene_starts: Vec::new(),
        endings: Vec::new(),
        controls: Vec::new(),
        tempos: tempo_map.tempos(),
    };
    for (row, start) in grid.rows.iter().zip(&starts) {
        if clip_of(row, column).is_some() {
            timed.scene_starts.push(tempo_map.seconds(ticks(*start)));
        }
    }
    for event in &events {
        let now = tempo_map.seconds(event.tick);
        match event.kind {
            NOTE_ON if event.value > 0 => timed.notes.push((now, event.number, event.value)),
            NOTE_ON | NOTE_OFF => timed.notes.push((now, event.number, 0)),
            CONTROL_CHANGE if ENDING_CONTROLS.contains(&event.number) => timed.endings.push(now),
            CONTROL_CHANGE if event.number != CLIP_START_CONTROL => timed.controls.push((now, event.number, event.value)),
            _ => {}
        }
    }
    Ok(Some(timed))
}

/// How long the song lasts in seconds, through its tempo map.
pub fn song_seconds(grid: &Grid) -> Rendered<f64> {
    let starts = row_starts(grid)?;
    let end = ticks(starts[starts.len() - 1]);
    Ok(TempoMap::of(&conductor_events(grid, &starts)).seconds(end))
}

/// A song's tempos by the tick each starts at, microseconds a quarter note, which turn a tick into seconds as a MIDI file
/// is read back, the tempo before the first change a MIDI file's own.
struct TempoMap {
    changes: Vec<(i128, i64)>,
}

/// The tempo a MIDI file plays at before it sets one, 120 quarter notes a minute.
const FIRST_TEMPO: i64 = 500_000;
const MICROSECONDS_PER_MINUTE: f64 = 60_000_000.0;

impl TempoMap {
    /// The map of a conductor track's tempo events.
    fn of(events: &[MidiEvent]) -> TempoMap {
        let mut changes: Vec<(i128, i64)> = events
            .iter()
            .filter(|event| event.kind == SET_TEMPO)
            .map(|event| (event.tick, event.value))
            .collect();
        changes.sort();
        TempoMap { changes }
    }

    /// The tempo from the start and at each change, in seconds and quarter notes a minute.
    fn tempos(&self) -> Vec<(f64, f64)> {
        let quarters_a_minute = |microseconds: i64| MICROSECONDS_PER_MINUTE / microseconds.max(1) as f64;
        let mut tempos = vec![(0.0, quarters_a_minute(FIRST_TEMPO))];
        for (change, changed) in &self.changes {
            let at = self.seconds(*change);
            if at <= 0.0 {
                tempos[0] = (0.0, quarters_a_minute(*changed));
            } else {
                tempos.push((at, quarters_a_minute(*changed)));
            }
        }
        tempos
    }

    /// The seconds from the start to a tick.
    fn seconds(&self, tick: i128) -> f64 {
        let mut seconds = 0.0;
        let mut at = 0;
        let mut tempo = FIRST_TEMPO;
        for (change, changed) in &self.changes {
            if *change >= tick {
                break;
            }
            seconds += (change - at) as f64 * tempo as f64 / 1e6 / TICKS_PER_BEAT as f64;
            at = *change;
            tempo = *changed;
        }
        seconds + (tick - at) as f64 * tempo as f64 / 1e6 / TICKS_PER_BEAT as f64
    }
}
