// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The messages llamatron-backend speaks, MessagePack framed by their length: writing set data and bytes, reading the
//! word an answer starts with, as the WAV export and the real-time sender use them.

use llamatron_model::file::data::Data;
use std::io::{Read, Write};

/// Bytes as MessagePack's binary, which the real-time sender's records cross as.
pub fn packed_bytes(bytes: &[u8], out: &mut Vec<u8>) {
    out.push(0xc6);
    out.extend((bytes.len() as u32).to_be_bytes());
    out.extend(bytes);
}

/// Write one already packed message, framed by its length in four bytes, most significant first.
pub fn send_packed(input: &mut impl Write, body: &[u8]) -> std::io::Result<()> {
    input.write_all(&(body.len() as u32).to_be_bytes())?;
    input.write_all(body)?;
    input.flush()
}

/// Write one message to the backend, MessagePack framed by its length in four bytes, most significant first.
pub fn send(input: &mut impl Write, message: &Data) -> std::io::Result<()> {
    let mut body = Vec::new();
    packed(message, &mut body);
    input.write_all(&(body.len() as u32).to_be_bytes())?;
    input.write_all(&body)?;
    input.flush()
}

/// Read one framed message from the backend, as its bytes.
pub fn received(output: &mut impl Read) -> std::io::Result<Vec<u8>> {
    let mut length = [0u8; 4];
    output.read_exact(&mut length)?;
    let mut body = vec![0u8; u32::from_be_bytes(length) as usize];
    output.read_exact(&mut body)?;
    Ok(body)
}

/// A message's first item where it is an array starting with a string, as every answer of the backend is.
pub fn first_word(message: &[u8]) -> Option<String> {
    let rest = match *message.first()? {
        byte if byte & 0xf0 == 0x90 => &message[1..],
        0xdc => message.get(3..)?,
        0xdd => message.get(5..)?,
        _ => return None,
    };
    let (length, start) = match *rest.first()? {
        byte if byte & 0xe0 == 0xa0 => ((byte & 0x1f) as usize, 1),
        0xd9 => (*rest.get(1)? as usize, 2),
        0xda => (u16::from_be_bytes([*rest.get(1)?, *rest.get(2)?]) as usize, 3),
        _ => return None,
    };
    rest.get(start..start + length).map(|text| String::from_utf8_lossy(text).to_string())
}

/// Data as MessagePack.
pub fn packed(data: &Data, out: &mut Vec<u8>) {
    match data {
        Data::Null => out.push(0xc0),
        Data::Bool(value) => out.push(if *value { 0xc3 } else { 0xc2 }),
        Data::Whole(value) => {
            out.push(0xd3);
            out.extend((*value as i64).to_be_bytes());
        }
        Data::Float(value) => {
            out.push(0xcb);
            out.extend(value.to_be_bytes());
        }
        Data::Text(text) => {
            out.push(0xdb);
            out.extend((text.len() as u32).to_be_bytes());
            out.extend(text.as_bytes());
        }
        Data::List(items) => {
            out.push(0xdd);
            out.extend((items.len() as u32).to_be_bytes());
            for item in items {
                packed(item, out);
            }
        }
        Data::Map(pairs) => {
            out.push(0xdf);
            out.extend((pairs.len() as u32).to_be_bytes());
            for (key, value) in pairs {
                packed(key, out);
                packed(value, out);
            }
        }
    }
}
