// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The messages the tracker and the daemon speak over the daemon's standard input and output: each a MessagePack array
//! whose first item is the message's kind, framed by its length as four bytes, most significant first, so that a reader
//! always knows where one ends. Any front end that can write MessagePack can drive the daemon.
//!
//! To the daemon: `["instrument", number, spec]`, `["notes", [[seconds, kind, instrument, pitch, velocity], ...]]`,
//! `["silence"]`, `["close"]`, FluidSynth's `["soundfont", library, soundfont, gain]` (answered `soundfont_ready` or
//! `failed`), `["midi", [[seconds, status, first, second], ...]]` and `["forget_midi", seconds]`, and, offline,
//! `["render", path, seconds]`.
//! From the daemon: `["ready", rate, delay]`, `["failed", problem, detail]`, `["load", {...}]` every half second while
//! it plays, `["statistics", {...}]` as it closes, and, offline, `["rendered", {...}]`.

pub mod values;

use rmpv::Value;
use std::io::{self, Read, Write};

pub const READY: &str = "ready";
pub const FAILED: &str = "failed";
pub const LOAD: &str = "load";
pub const STATISTICS: &str = "statistics";
pub const RENDERED: &str = "rendered";
pub const INSTRUMENT: &str = "instrument";
pub const NOTES: &str = "notes";
pub const SILENCE: &str = "silence";
pub const CLOSE: &str = "close";
pub const RENDER: &str = "render";
pub const SOUNDFONT: &str = "soundfont";
pub const SOUNDFONT_READY: &str = "soundfont_ready";
pub const MIDI: &str = "midi";
pub const FORGET_MIDI: &str = "forget_midi";
/// The longest message the daemon reads, past which the stream is taken to be broken.
const LONGEST_MESSAGE: usize = 64 << 20;

/// Read one message, or None at the end of the stream.
pub fn read_message(input: &mut impl Read) -> io::Result<Option<Value>> {
    let mut length = [0u8; 4];
    if let Err(problem) = input.read_exact(&mut length) {
        if problem.kind() == io::ErrorKind::UnexpectedEof {
            return Ok(None);
        }
        return Err(problem);
    }
    let length = u32::from_be_bytes(length) as usize;
    if length > LONGEST_MESSAGE {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            format!("a message of {length} bytes is longer than any the tracker sends"),
        ));
    }
    let mut body = vec![0u8; length];
    input.read_exact(&mut body)?;
    rmpv::decode::read_value(&mut body.as_slice())
        .map(Some)
        .map_err(|problem| io::Error::new(io::ErrorKind::InvalidData, problem.to_string()))
}

/// Write one message and flush it.
pub fn write_message(output: &mut impl Write, message: &Value) -> io::Result<()> {
    let mut body = Vec::new();
    rmpv::encode::write_value(&mut body, message)?;
    output.write_all(&(body.len() as u32).to_be_bytes())?;
    output.write_all(&body)?;
    output.flush()
}

/// A message of a kind and its items.
pub fn message(kind: &str, items: Vec<Value>) -> Value {
    let mut all = vec![Value::from(kind)];
    all.extend(items);
    Value::Array(all)
}

/// A mapping of names to values, for statistics.
pub fn mapping(pairs: Vec<(&str, Value)>) -> Value {
    Value::Map(pairs.into_iter().map(|(name, value)| (Value::from(name), value)).collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_message_reads_back_as_written() {
        let sent = message(
            NOTES,
            vec![Value::Array(vec![Value::Array(vec![1.5.into(), 0.into(), 3.into(), 60.into(), 100.into()])])],
        );
        let mut wire = Vec::new();
        write_message(&mut wire, &sent).unwrap();
        let read = read_message(&mut wire.as_slice()).unwrap().unwrap();
        assert_eq!(read, sent);
        assert!(read_message(&mut [].as_slice()).unwrap().is_none());
    }
}
