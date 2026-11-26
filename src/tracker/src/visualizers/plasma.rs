// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Plasma, after the demo scene's: smooth fields of sine waves drifting in colour, coloured by the tracks that play.
//!
//! The classic plasma adds four sine waves over the area, one across, one down, one on the diagonal and one in rings about
//! a point that wanders, each moving with time, and turns the sum into a colour through a palette. Here the palette is made
//! from the colours of the tracks playing, blended round the hue wheel, so the plasma takes the song's colours; time runs
//! faster for a faster song and swells a little as the tracks play; each note starting nudges the waves' frequencies, and
//! the brightness rises gently with the playing. It is worked out at SUPERSAMPLE times the big pixels each way, averaged
//! down and held under the limiter. In silence it glows dimly in the colours of the tracks heard last.

use super::colour::{note_colour, Energy, Limiter, TRACK_COLOURS};
use super::picture::{Colour, Painter, Picture};
use super::{Hearing, FULL_VELOCITY};
use std::collections::BTreeMap;
use std::f64::consts::TAU;

pub const OPTION: &str = "plasma";

const SUPERSAMPLE: usize = 2;
const COLOUR_STEP_SHIFT: u32 = 3;
/// The waves: how many fit across the area for each, and how fast each moves, in radians a second at 120 a minute.
const ACROSS_WAVES: f64 = 1.6;
const DOWN_WAVES: f64 = 1.2;
const DIAGONAL_WAVES: f64 = 1.0;
const RING_WAVES: f64 = 2.2;
const ACROSS_SPEED: f64 = 0.9;
const DOWN_SPEED: f64 = 0.7;
const DIAGONAL_SPEED: f64 = 0.5;
const RING_SPEED: f64 = 1.1;
/// How the rings' middle wanders, as a share of the area, and how fast; the rings are stretched across, as a cell is tall.
const WANDER: f64 = 0.3;
const WANDER_SPEED: f64 = 0.23;
const WANDER_ACROSS_SPEED_SHARE: f64 = 1.3;
const RING_STRETCH_ACROSS: f64 = 2.0;
/// How notes stir it: how much a note at full velocity nudges the waves' frequencies, how fast the nudge settles, how much
/// the playing speeds time, and how bright it is at rest and playing.
const NUDGE_PER_NOTE: f64 = 0.08;
const NUDGE_KEPT_PER_SECOND: f64 = 0.4;
const ENERGY_SPEED: f64 = 0.6;
const RESTING_BRIGHTNESS: f64 = 0.55;
const PLAYING_BRIGHTNESS: f64 = 1.0;
const ENERGY_PER_NOTE: f64 = 0.25;
const ENERGY_RISE_PER_SECOND: f64 = 1.5;
const ENERGY_KEPT_PER_SECOND: f64 = 0.35;
/// The palette's size round its cycle, and the full value of a channel.
const PALETTE_SIZE: usize = 256;
const WHOLE: f64 = 255.0;
/// The four waves' sum runs from -4 to 4.
const WAVE_COUNT: f64 = 4.0;
/// The edges are brighter than the middle, by this share at the corners, so that it doesn't look like the lava lamp.
const EDGE_BOOST: f64 = 0.6;
/// The colours it glows in before any track plays.
const QUIET_COLOURS: [Colour; 3] = [TRACK_COLOURS[1], TRACK_COLOURS[4], TRACK_COLOURS[5]];
/// The limiter: bright, and still never flashing.
const MEAN_LEVEL: f64 = 130.0;
const CEILING: i32 = 235;
const MEAN_RISE_PER_SECOND: f64 = 40.0;
const MEAN_FALL_PER_SECOND: f64 = 40.0;
const MOST_GAIN: f64 = 1.2;
const HALF: f64 = 0.5;
/// The sextants of the hue wheel.
const SEXTANTS: f64 = 6.0;

/// A colour's hue, from 0 to 1 round the wheel.
fn hue_of(colour: Colour) -> f64 {
    let [red, green, blue] = colour.map(|channel| channel as f64 / WHOLE);
    let (most, least) = (red.max(green).max(blue), red.min(green).min(blue));
    let range = most - least;
    if range == 0.0 {
        return 0.0;
    }
    let sextant = if most == red {
        ((green - blue) / range).rem_euclid(SEXTANTS)
    } else if most == green {
        (blue - red) / range + 2.0
    } else {
        (red - green) / range + 4.0
    };
    sextant / SEXTANTS
}

/// The colour of a hue at full saturation and brightness, as floats from 0 to 255.
fn colour_of_hue(hue: f64) -> [f64; 3] {
    let place = hue.rem_euclid(1.0) * SEXTANTS;
    let sextant = place.floor() as i64;
    let rising = place - sextant as f64;
    let falling = 1.0 - rising;
    let [red, green, blue] = match sextant {
        0 => [1.0, rising, 0.0],
        1 => [falling, 1.0, 0.0],
        2 => [0.0, 1.0, rising],
        3 => [0.0, falling, 1.0],
        4 => [rising, 0.0, 1.0],
        _ => [1.0, 0.0, falling],
    };
    [red * WHOLE, green * WHOLE, blue * WHOLE]
}

/// A palette of PALETTE_SIZE colours going round the hues of the colours given and back to the first, each at full
/// saturation and brightness, so that it stays vivid rather than passing through pastels.
fn palette_of(colours: &[Colour]) -> Vec<[f64; 3]> {
    let mut hues: Vec<f64> = colours.iter().map(|colour| hue_of(*colour)).collect();
    hues.push(hues[0] + 1.0);
    for place in 1..hues.len() {
        while hues[place] < hues[place - 1] {
            hues[place] += 1.0;
        }
    }
    (0..PALETTE_SIZE)
        .map(|entry| {
            let place = entry as f64 * colours.len() as f64 / PALETTE_SIZE as f64;
            let lower = place.floor() as usize;
            let share = place - lower as f64;
            colour_of_hue(hues[lower] * (1.0 - share) + hues[lower + 1] * share)
        })
        .collect()
}

/// Sine waves drifting in the playing tracks' colours.
pub struct Plasma {
    rows: usize,
    columns: usize,
    edges: Vec<f64>,
    time: f64,
    nudge: f64,
    energy: Energy,
    colours: BTreeMap<usize, Colour>,
    palette: Vec<[f64; 3]>,
    limiter: Limiter,
}

impl Plasma {
    pub fn new() -> Plasma {
        Plasma {
            rows: 0,
            columns: 0,
            edges: Vec::new(),
            time: 0.0,
            nudge: 0.0,
            energy: Energy::new(ENERGY_PER_NOTE, ENERGY_RISE_PER_SECOND, ENERGY_KEPT_PER_SECOND),
            colours: BTreeMap::new(),
            palette: palette_of(&QUIET_COLOURS),
            limiter: Limiter::new(MEAN_LEVEL, CEILING, MEAN_RISE_PER_SECOND, MEAN_FALL_PER_SECOND, MOST_GAIN),
        }
    }

    /// Let each note heard colour the palette with its track's colour, and each that starts nudge the waves and raise the
    /// energy.
    fn hear(&mut self, heard: &Hearing) {
        let mut changed = false;
        for note in &heard.notes {
            let colour = note_colour(note.track, note.pitch, note.drum);
            if self.colours.get(&note.track) != Some(&colour) {
                self.colours.insert(note.track, colour);
                changed = true;
            }
            if note.started {
                let loudness = note.velocity as f64 / FULL_VELOCITY;
                self.nudge += NUDGE_PER_NOTE * loudness;
                self.energy.strike(loudness);
            }
        }
        if changed {
            let mut colours: Vec<Colour> = self.colours.values().copied().collect();
            if colours.len() < 2 {
                colours.push(QUIET_COLOURS[0]);
            }
            self.palette = palette_of(&colours);
        }
    }
}

impl Default for Plasma {
    fn default() -> Plasma {
        Plasma::new()
    }
}

impl Painter for Plasma {
    const OPTION: &'static str = OPTION;

    fn resized(&mut self, columns: usize, rows: usize) {
        self.rows = rows * SUPERSAMPLE;
        self.columns = columns * SUPERSAMPLE;
        let corner = (HALF * HALF * 2.0).sqrt();
        self.edges = (0..self.rows * self.columns)
            .map(|place| {
                let down = (place / self.columns.max(1)) as f64 / self.rows.max(1) as f64;
                let across = (place % self.columns.max(1)) as f64 / self.columns.max(1) as f64;
                let reach = ((down - HALF).powi(2) + (across - HALF).powi(2)).sqrt() / corner;
                1.0 + EDGE_BOOST * reach
            })
            .collect();
    }

    fn pixels(&mut self, seconds: f64, heard: &Hearing) -> Picture {
        self.hear(heard);
        self.energy.settle(seconds);
        self.nudge *= NUDGE_KEPT_PER_SECOND.powf(seconds);
        self.time += seconds * heard.tempo_factor() * (1.0 + ENERGY_SPEED * self.energy.get_level());
        let stretch = 1.0 + self.nudge;
        let time = self.time;
        let middle_down = HALF + WANDER * (time * WANDER_SPEED).sin();
        let middle_across = HALF + WANDER * (time * WANDER_SPEED * WANDER_ACROSS_SPEED_SHARE).cos();
        let brightness = RESTING_BRIGHTNESS + (PLAYING_BRIGHTNESS - RESTING_BRIGHTNESS) * self.energy.get_level();
        let mut cells = Vec::with_capacity(self.rows * self.columns);
        for row in 0..self.rows {
            let down = row as f64 / self.rows.max(1) as f64;
            for column in 0..self.columns {
                let across = column as f64 / self.columns.max(1) as f64;
                let ring = ((down - middle_down).powi(2) + ((across - middle_across) * RING_STRETCH_ACROSS).powi(2)).sqrt();
                let value = (TAU * ACROSS_WAVES * stretch * across + time * ACROSS_SPEED).sin()
                    + (TAU * DOWN_WAVES * stretch * down + time * DOWN_SPEED).sin()
                    + (TAU * DIAGONAL_WAVES * (across + down) + time * DIAGONAL_SPEED).sin()
                    + (TAU * RING_WAVES * stretch * ring - time * RING_SPEED).sin();
                let place = (((value + WAVE_COUNT) / (2.0 * WAVE_COUNT)) * (PALETTE_SIZE - 1) as f64) as usize;
                let lift = brightness * self.edges[row * self.columns + column];
                cells.push(self.palette[place.min(PALETTE_SIZE - 1)].map(|channel| (channel * lift) as i32));
            }
        }
        let picture = Picture {
            rows: self.rows,
            columns: self.columns,
            cells,
        };
        self.limiter.limited(picture.derezzed(SUPERSAMPLE), seconds).stepped(COLOUR_STEP_SHIFT)
    }
}
