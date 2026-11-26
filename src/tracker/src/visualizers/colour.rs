// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Colour for the visualizer's modes: each track's colour, moved by a note's pitch and octave; the energy a mode's notes
//! give it; and the limiter that keeps a picture from ever flashing.
//!
//! The colours are primaries and their neighbours, saturated but never full, so that blobs read apart and mix into clean
//! secondaries rather than mud. A note's pitch leans its track's colour toward the next in the cycle a little, and its
//! octave sets how bright it is. The limiter holds the picture's mean brightness under a level, changing its gain only
//! slowly, and caps every channel below white: the visualizer never strobes or flashes brightly.

use super::picture::{Colour, Picture};

/// Each track's colour, in the song's order, going round.
pub const TRACK_COLOURS: [Colour; 8] = [
    [226, 42, 48],
    [36, 96, 232],
    [246, 196, 36],
    [36, 186, 92],
    [186, 56, 216],
    [36, 196, 206],
    [240, 118, 30],
    [118, 80, 236],
];
/// A drum's notes paint a pale grey whatever the track.
const DRUM_COLOUR: Colour = [200, 200, 210];
/// How far a note's pitch in its octave leans its track's colour toward the next track's.
const PITCH_LEAN: f64 = 0.35;
/// How bright the lowest and highest notes paint, as shares of their colour.
const DIMMEST: f64 = 0.55;
const BRIGHTEST: f64 = 1.15;
const LOWEST_PITCH: f64 = 24.0;
const HIGHEST_PITCH: f64 = 96.0;
const HALF_STEPS_PER_OCTAVE: i64 = 12;

/// A track's colour by its place in the song.
pub fn track_colour(track: usize) -> Colour {
    TRACK_COLOURS[track % TRACK_COLOURS.len()]
}

/// The colour a note paints: its track's, leaning toward the next by its pitch in the octave, brighter for a higher
/// octave; a drum's pale.
pub fn note_colour(track: usize, pitch: i64, drum: bool) -> Colour {
    if drum {
        return DRUM_COLOUR;
    }
    let base = track_colour(track);
    let lean = track_colour(track + 1);
    let in_octave = pitch.rem_euclid(HALF_STEPS_PER_OCTAVE) as f64 / HALF_STEPS_PER_OCTAVE as f64;
    let height = ((pitch as f64 - LOWEST_PITCH) / (HIGHEST_PITCH - LOWEST_PITCH)).clamp(0.0, 1.0);
    let brightness = DIMMEST + (BRIGHTEST - DIMMEST) * height;
    let mut colour = [0; 3];
    for channel in 0..3 {
        let mixed = base[channel] as f64 + (lean[channel] - base[channel]) as f64 * PITCH_LEAN * in_octave;
        colour[channel] = (mixed * brightness) as i32;
    }
    colour
}

/// A level from nothing to full that every note heard pushes up and silence lets fall: a note raises what the level moves
/// toward, by its loudness; the level follows no faster than its rise allows, so that nothing flashes, and what it moves
/// toward dies away each second.
pub struct Energy {
    level: f64,
    target: f64,
    per_note: f64,
    rise_per_second: f64,
    kept_per_second: f64,
}

impl Energy {
    pub fn new(per_note: f64, rise_per_second: f64, kept_per_second: f64) -> Energy {
        Energy {
            level: 0.0,
            target: 0.0,
            per_note,
            rise_per_second,
            kept_per_second,
        }
    }

    pub fn get_level(&self) -> f64 {
        self.level
    }

    /// Take a note heard, as loud as loudness, from nothing to full.
    pub fn strike(&mut self, loudness: f64) {
        self.target = (self.target + self.per_note * loudness).min(1.0);
    }

    /// Move the level toward what the notes struck over some seconds, and let that die away.
    pub fn settle(&mut self, seconds: f64) {
        let rise = self.rise_per_second * seconds;
        self.level += (self.target - self.level).clamp(-rise, rise);
        self.target *= self.kept_per_second.powf(seconds);
    }
}

/// Holds a picture's mean brightness under a level, lets it rise and fall only so fast, and caps every channel under a
/// ceiling, so that nothing ever flashes or strobes: however suddenly the picture underneath brightens, as when every
/// track hits at once, what is shown brightens by at most its rise a second, by a gain of at most its most.
pub struct Limiter {
    shown: Option<f64>,
    mean_level: f64,
    ceiling: i32,
    rise_per_second: f64,
    fall_per_second: f64,
    most_gain: f64,
}

impl Limiter {
    pub fn new(mean_level: f64, ceiling: i32, rise_per_second: f64, fall_per_second: f64, most_gain: f64) -> Limiter {
        Limiter {
            shown: None,
            mean_level,
            ceiling,
            rise_per_second,
            fall_per_second,
            most_gain,
        }
    }

    /// A picture whose mean brightness is held under the level and within the rise and fall allowed over the seconds since
    /// the last, every channel under the ceiling.
    pub fn limited(&mut self, mut picture: Picture, seconds: f64) -> Picture {
        let channels = (picture.cells.len() * 3).max(1) as f64;
        let mean = picture.cells.iter().flatten().map(|channel| *channel as f64).sum::<f64>() / channels;
        let mut wanted = mean.min(self.mean_level);
        if let Some(shown) = self.shown {
            wanted = wanted.clamp(shown - self.fall_per_second * seconds, shown + self.rise_per_second * seconds);
        }
        let gain = if mean > 0.0 { (wanted / mean).min(self.most_gain) } else { 1.0 };
        for cell in &mut picture.cells {
            *cell = cell.map(|channel| ((channel as f64 * gain) as i32).clamp(0, self.ceiling));
        }
        self.shown = Some(mean * gain);
        picture
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// However bright the picture underneath turns at once, the limiter lets its mean rise only by its rise a second.
    #[test]
    fn the_limiter_never_lets_a_picture_flash() {
        let (mean_level, ceiling, rise, fall, most_gain) = (70.0, 225, 50.0, 40.0, 1.5);
        let mut limiter = Limiter::new(mean_level, ceiling, rise, fall, most_gain);
        let frame_seconds = 0.05;
        let dark = Picture::filled(4, 4, [10, 10, 10]);
        limiter.limited(dark, frame_seconds);
        let white = Picture::filled(4, 4, [255, 255, 255]);
        let shown = limiter.limited(white, frame_seconds);
        let brightest = shown.cells.iter().flatten().max().copied().unwrap_or(0);
        assert!(f64::from(brightest) <= 10.0 + rise * frame_seconds + 1.0, "{brightest}");
    }
}
