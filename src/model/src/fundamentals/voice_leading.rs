// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Voice leading (the Python music_theory/fundamentals/voice_leading.py): moving from one chord to the next with as little
//! movement as the notes allow. Pitches are MIDI numbers.

use crate::fundamentals::generated::intervals::HALF_STEPS_PER_OCTAVE;

/// How far a voicing's notes move from the chord before: lowest to lowest where both have as many notes, else each note to
/// the nearest of the chord before.
pub fn movement(pitches: &[i64], before: &[i64]) -> i64 {
    let mut now = pitches.to_vec();
    now.sort();
    if now.len() == before.len() {
        return now.iter().zip(before).map(|(pitch, other)| (pitch - other).abs()).sum();
    }
    now.iter().map(|pitch| distance_to_nearest(*pitch, before)).sum()
}

/// How far a pitch is from the nearest of others.
pub fn distance_to_nearest(pitch: i64, others: &[i64]) -> i64 {
    others.iter().map(|other| (pitch - other).abs()).min().unwrap_or(0)
}

/// A chord's pitches, lowest first, in an inversion: so many of its lowest notes an octave up, never all of them.
pub fn inverted(pitches: &[i64], inversion: usize) -> Vec<i64> {
    lowest_moved_up(pitches, inversion.min(pitches.len().saturating_sub(1)))
}

/// Every inversion of a chord's pitches given lowest first.
pub fn inversions(pitches: &[i64]) -> Vec<Vec<i64>> {
    (0..pitches.len()).map(|moved| lowest_moved_up(pitches, moved)).collect()
}

/// A chord's pitches in an inversion, moved so many octaves.
pub fn voiced(pitches: &[i64], inversion: usize, shift: i64) -> Vec<i64> {
    inverted(pitches, inversion)
        .into_iter()
        .map(|pitch| pitch + shift * HALF_STEPS_PER_OCTAVE)
        .collect()
}

fn lowest_moved_up(pitches: &[i64], moved: usize) -> Vec<i64> {
    pitches
        .iter()
        .enumerate()
        .map(|(place, pitch)| if place < moved { pitch + HALF_STEPS_PER_OCTAVE } else { *pitch })
        .collect()
}
