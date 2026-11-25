// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Reading a MIDI file into what the import works from (the Python importers/midi_reading.py, and the file as the mido
//! library reads it, data bytes past 127 clipped): the notes of each part, one channel of one track, and the tempos, time
//! signatures and keys. Times are exact whole notes from the song's start. A note the file starts and never ends lasts until
//! its track ends, and is counted; a part keeps its channel's CC messages and the General MIDI program its channel is set to.

use llamatron_math::Rational;

const DRUM_CHANNEL: i64 = 9;
const DEFAULT_TEMPO: i64 = 500_000;

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct PartNote {
    pub start: Rational,
    pub end: Rational,
    pub pitch: i64,
    pub velocity: i64,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct HeardControl {
    pub time: Rational,
    pub number: i64,
    pub value: i64,
}

#[derive(Clone, Debug)]
pub struct MidiPart {
    pub name: String,
    pub channel: i64,
    pub notes: Vec<PartNote>,
    pub controls: Vec<HeardControl>,
    pub program: Option<i64>,
}

impl MidiPart {
    pub fn is_drums(&self) -> bool {
        self.channel == DRUM_CHANNEL
    }
}

/// Something the file sets from a time on.
#[derive(Clone, Debug, PartialEq)]
pub struct Change<T> {
    pub time: Rational,
    pub value: T,
}

#[derive(Clone, Debug)]
pub struct MidiContents {
    pub parts: Vec<MidiPart>,
    pub tempos: Vec<Change<i64>>,
    pub time_signatures: Vec<Change<(i64, i64)>>,
    pub keys: Vec<Change<String>>,
    pub unended: i64,
    pub left_out: i64,
    pub controls_without_notes: i64,
}

impl MidiContents {
    pub fn note_count(&self) -> usize {
        self.parts.iter().map(|part| part.notes.len()).sum()
    }
}

/// The notes a channel and pitch has started and not yet ended, each its start and velocity.
type Held = ((i64, i64), Vec<(Rational, i64)>);

/// A message as the reader takes it from a track.
enum Message {
    TrackName(String),
    Tempo(i64),
    TimeSignature(i64, i64),
    Key(String),
    LeftOut,
    Program(i64, i64),
    Control(i64, i64, i64),
    NoteOn(i64, i64, i64),
    NoteOff(i64, i64),
    Other,
}

/// What is wrong with a file that is no MIDI file this reads.
#[derive(Debug)]
pub struct NotMidi(pub String);

struct Bytes<'b> {
    data: &'b [u8],
    place: usize,
}

impl Bytes<'_> {
    fn byte(&mut self) -> Result<u8, NotMidi> {
        let byte = *self.data.get(self.place).ok_or_else(|| NotMidi("the file ends early".to_string()))?;
        self.place += 1;
        Ok(byte)
    }

    fn take(&mut self, count: usize) -> Result<&[u8], NotMidi> {
        let end = self.place + count;
        let taken = self.data.get(self.place..end).ok_or_else(|| NotMidi("the file ends early".to_string()))?;
        self.place = end;
        Ok(taken)
    }

    fn variable(&mut self) -> Result<u64, NotMidi> {
        let mut value = 0u64;
        loop {
            let byte = self.byte()?;
            value = (value << 7) | (byte & 0x7f) as u64;
            if byte & 0x80 == 0 {
                return Ok(value);
            }
        }
    }
}

fn key_name(sharps: i8, minor: u8) -> String {
    let majors = ["Cb", "Gb", "Db", "Ab", "Eb", "Bb", "F", "C", "G", "D", "A", "E", "B", "F#", "C#"];
    let minors = ["Abm", "Ebm", "Bbm", "Fm", "Cm", "Gm", "Dm", "Am", "Em", "Bm", "F#m", "C#m", "G#m", "D#m", "A#m"];
    let place = (sharps.clamp(-7, 7) + 7) as usize;
    if minor == 1 {
        minors[place].to_string()
    } else {
        majors[place].to_string()
    }
}

/// A track's messages, each with the ticks since the one before.
fn track_messages(data: &[u8]) -> Result<Vec<(u64, Message)>, NotMidi> {
    let mut bytes = Bytes { data, place: 0 };
    let mut messages = Vec::new();
    let mut running: Option<u8> = None;
    while bytes.place < data.len() {
        let delta = bytes.variable()?;
        let mut status = bytes.byte()?;
        if status < 0x80 {
            status = running.ok_or_else(|| NotMidi("running status with no status before".to_string()))?;
            bytes.place -= 1;
        }
        let clip = |byte: u8| (byte.min(127)) as i64;
        let message = match status {
            0xff => {
                let kind = bytes.byte()?;
                let length = bytes.variable()? as usize;
                let payload = bytes.take(length)?.to_vec();
                running = None;
                match kind {
                    0x03 => Message::TrackName(payload.iter().map(|byte| *byte as char).collect()),
                    0x51 if payload.len() >= 3 => Message::Tempo(((payload[0] as i64) << 16) | ((payload[1] as i64) << 8) | payload[2] as i64),
                    0x58 if payload.len() >= 2 => Message::TimeSignature(payload[0] as i64, 1i64 << payload[1]),
                    0x59 if payload.len() >= 2 => Message::Key(key_name(payload[0] as i8, payload[1])),
                    _ => Message::Other,
                }
            }
            0xf0 | 0xf7 => {
                let length = bytes.variable()? as usize;
                bytes.take(length)?;
                running = None;
                Message::Other
            }
            _ => {
                running = Some(status);
                let channel = (status & 0x0f) as i64;
                match status & 0xf0 {
                    0x80 => {
                        let note = clip(bytes.byte()?);
                        bytes.byte()?;
                        Message::NoteOff(channel, note)
                    }
                    0x90 => {
                        let note = clip(bytes.byte()?);
                        let velocity = clip(bytes.byte()?);
                        Message::NoteOn(channel, note, velocity)
                    }
                    0xa0 => {
                        bytes.take(2)?;
                        Message::LeftOut
                    }
                    0xb0 => {
                        let number = clip(bytes.byte()?);
                        let value = clip(bytes.byte()?);
                        Message::Control(channel, number, value)
                    }
                    0xc0 => Message::Program(channel, clip(bytes.byte()?)),
                    0xd0 => {
                        bytes.take(1)?;
                        Message::LeftOut
                    }
                    0xe0 => {
                        bytes.take(2)?;
                        Message::LeftOut
                    }
                    _ => {
                        running = None;
                        Message::Other
                    }
                }
            }
        };
        messages.push((delta, message));
    }
    Ok(messages)
}

/// Changes in time order, none repeating the one before, starting at the song's start with the default where the file set
/// nothing there.
fn from_the_start<T: Clone + PartialEq>(mut changes: Vec<Change<T>>, default: T) -> Vec<Change<T>> {
    changes.sort_by_key(|change| change.time);
    if changes.first().is_none_or(|change| change.time != Rational::ZERO) {
        changes.insert(
            0,
            Change {
                time: Rational::ZERO,
                value: default,
            },
        );
    }
    let mut kept: Vec<Change<T>> = Vec::new();
    for change in changes {
        match kept.last_mut() {
            Some(last) if last.time == change.time => *last = change,
            Some(last) if last.value == change.value => {}
            _ => kept.push(change),
        }
    }
    kept
}

/// What a MIDI file's bytes hold: a part for each channel of each track that plays notes.
pub fn read_midi(data: &[u8]) -> Result<MidiContents, NotMidi> {
    let mut bytes = Bytes { data, place: 0 };
    if bytes.take(4)? != b"MThd" {
        return Err(NotMidi("MThd not found".to_string()));
    }
    let length = u32::from_be_bytes(bytes.take(4)?.try_into().unwrap_or([0; 4])) as usize;
    let header = bytes.take(length)?.to_vec();
    let ticks_per_beat = if header.len() >= 6 {
        u16::from_be_bytes([header[4], header[5]]) as i128
    } else {
        480
    };
    let whole_notes = |tick: u64| Rational::new(tick as i128, ticks_per_beat * 4);
    let mut parts = Vec::new();
    let (mut tempos, mut time_signatures, mut keys) = (Vec::new(), Vec::new(), Vec::new());
    let (mut unended, mut left_out, mut controls_without_notes) = (0, 0, 0);
    let mut numbered = 1;
    let mut programs_in_file: Vec<(i64, i64)> = Vec::new();
    while bytes.place + 8 <= data.len() {
        let name = bytes.take(4)?.to_vec();
        let size = u32::from_be_bytes(bytes.take(4)?.try_into().unwrap_or([0; 4])) as usize;
        let chunk = bytes.take(size.min(data.len() - bytes.place))?.to_vec();
        if name != b"MTrk" {
            continue;
        }
        let mut tick = 0u64;
        let mut track_name: Option<String> = None;
        let mut held: Vec<Held> = Vec::new();
        let mut notes_by_channel: Vec<(i64, Vec<PartNote>)> = Vec::new();
        let mut controls_by_channel: Vec<(i64, Vec<HeardControl>)> = Vec::new();
        let mut programs: Vec<(i64, i64)> = Vec::new();
        for (delta, message) in track_messages(&chunk)? {
            tick += delta;
            let time = whole_notes(tick);
            match message {
                Message::TrackName(text) if track_name.is_none() => track_name = Some(text.trim_matches(|character| " \t:".contains(character)).to_string()),
                Message::Tempo(tempo) => tempos.push(Change { time, value: tempo }),
                Message::TimeSignature(beats, unit) => time_signatures.push(Change { time, value: (beats, unit) }),
                Message::Key(key) => keys.push(Change { time, value: key }),
                Message::LeftOut => left_out += 1,
                Message::Program(channel, program) => {
                    if !programs.iter().any(|(found, _)| *found == channel) {
                        programs.push((channel, program));
                    }
                    if !programs_in_file.iter().any(|(found, _)| *found == channel) {
                        programs_in_file.push((channel, program));
                    }
                }
                Message::Control(channel, number, value) => match controls_by_channel.iter_mut().find(|(found, _)| *found == channel) {
                    Some((_, controls)) => controls.push(HeardControl { time, number, value }),
                    None => controls_by_channel.push((channel, vec![HeardControl { time, number, value }])),
                },
                Message::NoteOn(channel, note, velocity) if velocity > 0 => match held.iter_mut().find(|(key, _)| *key == (channel, note)) {
                    Some((_, starts)) => starts.push((time, velocity)),
                    None => held.push(((channel, note), vec![(time, velocity)])),
                },
                Message::NoteOn(channel, note, _) | Message::NoteOff(channel, note) => {
                    let Some((_, starts)) = held.iter_mut().find(|(key, starts)| *key == (channel, note) && !starts.is_empty()) else {
                        continue;
                    };
                    let (start, velocity) = starts.remove(0);
                    if time > start {
                        let note = PartNote {
                            start,
                            end: time,
                            pitch: note,
                            velocity,
                        };
                        match notes_by_channel.iter_mut().find(|(found, _)| *found == channel) {
                            Some((_, notes)) => notes.push(note),
                            None => notes_by_channel.push((channel, vec![note])),
                        }
                    }
                }
                _ => {}
            }
        }
        let end = whole_notes(tick);
        for ((channel, pitch), starts) in &held {
            for (start, velocity) in starts {
                unended += 1;
                if end > *start {
                    let note = PartNote {
                        start: *start,
                        end,
                        pitch: *pitch,
                        velocity: *velocity,
                    };
                    match notes_by_channel.iter_mut().find(|(found, _)| found == channel) {
                        Some((_, notes)) => notes.push(note),
                        None => notes_by_channel.push((*channel, vec![note])),
                    }
                }
            }
        }
        controls_without_notes += controls_by_channel
            .iter()
            .filter(|(channel, _)| !notes_by_channel.iter().any(|(found, _)| found == channel))
            .map(|(_, controls)| controls.len() as i64)
            .sum::<i64>();
        if notes_by_channel.is_empty() {
            continue;
        }
        let name = track_name.filter(|name| !name.is_empty()).unwrap_or_else(|| format!("track {numbered}"));
        numbered += 1;
        notes_by_channel.sort_by_key(|(channel, _)| *channel);
        for (channel, mut notes) in notes_by_channel {
            notes.sort();
            let controls = controls_by_channel
                .iter()
                .find(|(found, _)| *found == channel)
                .map(|(_, controls)| controls.clone())
                .unwrap_or_default();
            let program = programs.iter().find(|(found, _)| *found == channel).map(|(_, program)| *program);
            parts.push(MidiPart {
                name: name.clone(),
                channel,
                notes,
                controls,
                program,
            });
        }
    }
    for part in &mut parts {
        if part.program.is_none() {
            part.program = programs_in_file.iter().find(|(found, _)| *found == part.channel).map(|(_, program)| *program);
        }
    }
    keys.sort_by_key(|change: &Change<String>| change.time);
    Ok(MidiContents {
        parts,
        tempos: from_the_start(tempos, DEFAULT_TEMPO),
        time_signatures: from_the_start(time_signatures, (4, 4)),
        keys,
        unended,
        left_out,
        controls_without_notes,
    })
}

/// What a list of changes in time order sets at a time: the last change at or before it.
pub fn value_at<T: Clone>(changes: &[Change<T>], time: Rational) -> T {
    let mut value = changes[0].value.clone();
    for change in changes {
        if change.time > time {
            break;
        }
        value = change.value.clone();
    }
    value
}
