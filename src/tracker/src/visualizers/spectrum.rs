// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The spectrum analyser: bars across the clip area rising with the notes heard and falling after, with peak caps that
//! hang and drop.
//!
//! It hears notes rather than sound, so a bar is a band of pitches, low at the left and high at the right, and a note
//! lifts its band by its velocity as it starts, holds it up a little while it is held, and lets it fall at a steady rate
//! when it ends. Each bar is drawn at the characters' own resolution, its top an eighth block, so that it rises smoothly in
//! eight steps a row, coloured up its height from green through yellow to red, held under a ceiling so that it never
//! glares. A cap above each bar marks its highest recent level, hangs a moment and drops slowly.

use super::picture::{colour_style, filled_style, Colour};
use super::{FrameClock, Hearing, Mode, FULL_VELOCITY};
use crate::text::Text;

pub const OPTION: &str = "spectrum";

/// The bars: each this many columns wide with a gap after it, and the pitches they span, low to high.
const BAR_COLUMNS: usize = 2;
const GAP_COLUMNS: usize = 1;
const LOWEST_PITCH: i64 = 28;
const HIGHEST_PITCH: i64 = 100;
/// How a note moves its band: how high a note at full velocity lifts it, as a share of the area's height, how high a held
/// note keeps it, and how fast a band rises toward its level and falls, as shares of the height a second.
const LIFT_AT_FULL_VELOCITY: f64 = 0.9;
const HELD_SHARE: f64 = 0.55;
const RISE_PER_SECOND: f64 = 9.0;
const FALL_PER_SECOND: f64 = 0.9;
/// A note also lifts the bands either side of its own a little, as a sound spreads across a spectrum, by this share for
/// each band away, so many bands either side.
const SPREAD_SHARE: f64 = 0.45;
const SPREAD_BANDS: i64 = 2;
/// The caps: how long one hangs at a band's highest level before it drops, and how fast it drops, as a share of the height
/// a second.
const CAP_HANG_SECONDS: f64 = 0.5;
const CAP_FALL_PER_SECOND: f64 = 0.35;
const CAP_CHARACTER: &str = "▀";
const CAP_COLOUR: Colour = [200, 200, 210];
/// The colours up a bar's height, from the bottom, kept under the ceiling so they never glare.
const GRADIENT: [Colour; 3] = [[40, 190, 80], [230, 205, 50], [225, 70, 45]];
/// A bar's top, by how many eighths of its top row it fills.
const EIGHTHS: [&str; 9] = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"];
const FULL_ROW: i64 = 8;
const SPACE: &str = " ";

/// How many bars fit across a width of columns, each with its gap, at least one.
fn bands_across(width: usize) -> usize {
    (width / (BAR_COLUMNS + GAP_COLUMNS)).max(1)
}

/// The colour at a height up a bar, from 0 at the bottom to 1 at the top, through the gradient's colours.
fn gradient_colour(height: f64) -> Colour {
    let place = height.clamp(0.0, 1.0) * (GRADIENT.len() - 1) as f64;
    let lower = (place as usize).min(GRADIENT.len() - 2);
    let share = place - lower as f64;
    let mut colour = [0; 3];
    for channel in 0..3 {
        let (low, high) = (GRADIENT[lower][channel] as f64, GRADIENT[lower + 1][channel] as f64);
        colour[channel] = (low + (high - low) * share) as i32;
    }
    colour
}

/// Bars of bands of pitches, rising with the notes heard and falling after, with caps that hang and drop.
pub struct Spectrum {
    levels: Vec<f64>,
    targets: Vec<f64>,
    caps: Vec<f64>,
    cap_ages: Vec<f64>,
    clock: FrameClock,
}

impl Spectrum {
    pub fn new() -> Spectrum {
        let mut spectrum = Spectrum {
            levels: Vec::new(),
            targets: Vec::new(),
            caps: Vec::new(),
            cap_ages: Vec::new(),
            clock: FrameClock::default(),
        };
        spectrum.reset(1);
        spectrum
    }

    /// Start every band, and its cap, at nothing, for an area this many bands across.
    fn reset(&mut self, bands: usize) {
        self.levels = vec![0.0; bands];
        self.targets = vec![0.0; bands];
        self.caps = vec![0.0; bands];
        self.cap_ages = vec![0.0; bands];
    }

    /// The band a pitch falls in, low pitches at the left.
    fn band_of(&self, pitch: i64) -> usize {
        let share = (pitch.clamp(LOWEST_PITCH, HIGHEST_PITCH) - LOWEST_PITCH) as f64 / (HIGHEST_PITCH - LOWEST_PITCH) as f64;
        ((share * self.levels.len() as f64) as usize).min(self.levels.len() - 1)
    }

    /// Lift each band a note falls in, and those either side a little: by its velocity as it starts, and to the held level
    /// while it sounds.
    fn hear(&mut self, heard: &Hearing) {
        for note in &heard.notes {
            let loudness = note.velocity as f64 / FULL_VELOCITY;
            let lift = if note.started { LIFT_AT_FULL_VELOCITY } else { HELD_SHARE } * loudness;
            let band = self.band_of(note.pitch) as i64;
            for away in -SPREAD_BANDS..=SPREAD_BANDS {
                let Some(target) = usize::try_from(band + away).ok().and_then(|place| self.targets.get_mut(place)) else {
                    continue;
                };
                *target = target.max(lift * SPREAD_SHARE.powi(away.abs() as i32));
            }
        }
    }

    /// Move each band toward its target, rising quickly and falling steadily, and let the caps hang, then drop.
    fn settle(&mut self, seconds: f64) {
        for band in 0..self.levels.len() {
            let (level, target) = (self.levels[band], self.targets[band]);
            self.levels[band] = if target > level {
                target.min(level + RISE_PER_SECOND * seconds)
            } else {
                (level - FALL_PER_SECOND * seconds).max(0.0)
            };
            self.targets[band] = 0.0;
            if self.levels[band] >= self.caps[band] {
                self.caps[band] = self.levels[band];
                self.cap_ages[band] = 0.0;
            } else {
                self.cap_ages[band] += seconds;
            }
            if self.cap_ages[band] > CAP_HANG_SECONDS {
                self.caps[band] = (self.caps[band] - CAP_FALL_PER_SECOND * seconds).max(self.levels[band]);
            }
        }
    }

    /// The bars as lines, top line first, each bar's top an eighth block and its cap above it.
    fn drawn(&self, width: usize, height: usize) -> Vec<Text> {
        let cap_style = colour_style(CAP_COLOUR);
        let mut lines = Vec::with_capacity(height);
        for line in 0..height {
            let row = (height - 1 - line) as i64;
            let colour = gradient_colour(row as f64 / (height.max(2) - 1) as f64);
            let style = colour_style(colour);
            // A full row is a filled cell rather than a full block, which many fonts draw short of the line's height,
            // leaving gaps that show the terminal's background.
            let full = filled_style(colour);
            let mut text = Text::default();
            for band in 0..self.levels.len() {
                let filled = (self.levels[band].min(1.0) * height as f64 * FULL_ROW as f64) as i64;
                let cap = ((self.caps[band] * height as f64) as i64).min(height as i64 - 1);
                let beneath = filled - row * FULL_ROW;
                if beneath >= FULL_ROW {
                    text.append(&SPACE.repeat(BAR_COLUMNS), &full);
                } else if beneath > 0 {
                    text.append(&EIGHTHS[beneath as usize].repeat(BAR_COLUMNS), &style);
                } else if cap == row && self.caps[band] > 0.0 {
                    text.append(&CAP_CHARACTER.repeat(BAR_COLUMNS), &cap_style);
                } else {
                    text.append(&SPACE.repeat(BAR_COLUMNS), "");
                }
                text.append(&SPACE.repeat(GAP_COLUMNS), "");
            }
            text.truncate(width);
            let drawn = text.cell_len();
            if drawn < width {
                text.append(&SPACE.repeat(width - drawn), "");
            }
            lines.push(text);
        }
        lines
    }
}

impl Default for Spectrum {
    fn default() -> Spectrum {
        Spectrum::new()
    }
}

impl Mode for Spectrum {
    fn option(&self) -> &'static str {
        OPTION
    }

    fn frame(&mut self, width: usize, height: usize, now: f64, heard: &Hearing) -> Vec<Text> {
        if width == 0 || height == 0 {
            return Vec::new();
        }
        if bands_across(width) != self.levels.len() {
            self.reset(bands_across(width));
        }
        let seconds = self.clock.seconds_since_last_frame(now);
        self.hear(heard);
        self.settle(seconds);
        self.drawn(width, height)
    }
}
