// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Writing a WAV file: two channels of 32-bit floats, as the tracker's WAV export reads it.

use std::fs::File;
use std::io::{self, BufWriter, Write};

/// The header's bytes after its size field, before the samples; the format chunk's size; a byte's bits; and the
/// samples' chunk's id.
const HEADER_AFTER_SIZE: u32 = 36;
const FORMAT_CHUNK_SIZE: u32 = 16;
const BITS_A_BYTE: u16 = 8;
const DATA_CHUNK: &[u8] = b"data";

const FLOAT_FORMAT: u16 = 3;
const CHANNELS: u16 = 2;
const BYTES: u16 = 4;

pub fn write_stereo(path: &str, rate: u32, left: &[f32], right: &[f32]) -> io::Result<()> {
    let mut file = BufWriter::new(File::create(path)?);
    let data = (left.len() * CHANNELS as usize * BYTES as usize) as u32;
    file.write_all(b"RIFF")?;
    file.write_all(&(HEADER_AFTER_SIZE + data).to_le_bytes())?;
    file.write_all(b"WAVEfmt ")?;
    file.write_all(&FORMAT_CHUNK_SIZE.to_le_bytes())?;
    file.write_all(&FLOAT_FORMAT.to_le_bytes())?;
    file.write_all(&CHANNELS.to_le_bytes())?;
    file.write_all(&rate.to_le_bytes())?;
    file.write_all(&(rate * (CHANNELS * BYTES) as u32).to_le_bytes())?;
    file.write_all(&(CHANNELS * BYTES).to_le_bytes())?;
    file.write_all(&(BYTES * BITS_A_BYTE).to_le_bytes())?;
    file.write_all(DATA_CHUNK)?;
    file.write_all(&data.to_le_bytes())?;
    for (first, second) in left.iter().zip(right) {
        file.write_all(&first.to_le_bytes())?;
        file.write_all(&second.to_le_bytes())?;
    }
    file.flush()
}
