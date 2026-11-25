// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Writing a WAV file: two channels of 32-bit floats, the mono mix in both, as the tracker's WAV export reads it.

use std::fs::File;
use std::io::{self, BufWriter, Write};

const FLOAT_FORMAT: u16 = 3;
const CHANNELS: u16 = 2;
const BYTES: u16 = 4;

pub fn write_stereo(path: &str, rate: u32, samples: &[f32]) -> io::Result<()> {
    let mut file = BufWriter::new(File::create(path)?);
    let data = (samples.len() * CHANNELS as usize * BYTES as usize) as u32;
    file.write_all(b"RIFF")?;
    file.write_all(&(36 + data).to_le_bytes())?;
    file.write_all(b"WAVEfmt ")?;
    file.write_all(&16u32.to_le_bytes())?;
    file.write_all(&FLOAT_FORMAT.to_le_bytes())?;
    file.write_all(&CHANNELS.to_le_bytes())?;
    file.write_all(&rate.to_le_bytes())?;
    file.write_all(&(rate * (CHANNELS * BYTES) as u32).to_le_bytes())?;
    file.write_all(&(CHANNELS * BYTES).to_le_bytes())?;
    file.write_all(&(BYTES * 8).to_le_bytes())?;
    file.write_all(b"data")?;
    file.write_all(&data.to_le_bytes())?;
    for sample in samples {
        let bytes = sample.to_le_bytes();
        file.write_all(&bytes)?;
        file.write_all(&bytes)?;
    }
    file.flush()
}
