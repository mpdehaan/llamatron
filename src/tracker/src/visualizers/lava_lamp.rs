// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The lava lamp: colour blobs drifting and rippling over the clip area, one for each track, in the spirit of the early
//! media players' visualizers, never muddy, never overwhelming the music, and never flashing.
//!
//! How it is made, on a simulation SUPERSAMPLE times finer than the big pixels each way:
//! - Each track that has played is a blob drifting on a slow path of its own, faster for a faster song.
//! - A note starting drops a splash into the water at its blob, as strong as its velocity, and a note still held keeps
//!   pushing a little every frame, so a long note sends a thicker train of waves without knowing how long it is. A drum's
//!   splash is smaller.
//! - Each blob glows its colour into a colour field, brighter as its track plays, which fades and bleeds into its
//!   neighbours every frame, so colours meet and mix.
//! - The picture is the colour field seen through the water: each cell takes its colour from a little way along the
//!   water's slope, and a soft highlight follows the slope, so the waves show as ripples in the colour.
//! - The view turns a little back and forth and zooms with a gentle pulse on each beat; then it is averaged down to the big
//!   pixels and held under the limiter.
//!
//! The amounts are named constants here, grouped by what they shape, to tune by eye.

use super::colour::{note_colour, Limiter};
use super::fields::{add_colour_disc, add_disc, blurred, ripple_step, Field};
use super::picture::{Colour, Painter, Picture};
use super::warp::rotozoomed;
use super::{Hearing, FULL_VELOCITY};
use llamatron_names::words;
use std::collections::BTreeMap;
use std::f64::consts::TAU;

pub const OPTION: &str = words::LAVA_LAMP;

/// How much finer the simulation is than the big pixels, each way, and the colour steps the big pixels are rounded to.
const SUPERSAMPLE: usize = 2;
const COLOUR_STEP_SHIFT: u32 = 3;
/// The frame the per-frame amounts are reckoned at.
const REFERENCE_FRAME_SECONDS: f64 = 0.05;
/// The water: how many steps it takes a frame, and how quickly its waves die away (a larger shift, slower).
const WAVE_STEPS: usize = 2;
const DAMPING_SHIFT: i32 = 5;
/// A note's splash: its radius as a share of the field's height, and its depth for each point of velocity; a drum's is
/// smaller and shallower.
const SPLASH_RADIUS_SHARE: f64 = 0.09;
const SPLASH_PER_VELOCITY: i32 = 10;
const DRUM_RADIUS_SHARE: f64 = 0.05;
const DRUM_SPLASH_PER_VELOCITY: i32 = 6;
/// A held note keeps pushing every frame: its radius as a share of the field's height, and how hard for each point of
/// velocity.
const HELD_RADIUS_SHARE: f64 = 0.05;
const HELD_PUSH_PER_VELOCITY: i32 = 1;
/// How notes light their blob: how much a note at full velocity raises its energy, and how quickly the energy may rise and
/// falls, per second.
const ENERGY_PER_NOTE: f64 = 0.45;
const ENERGY_RISE_PER_SECOND: f64 = 3.0;
const ENERGY_KEPT_PER_SECOND: f64 = 0.25;
/// The blobs' glow: its radius as a share of the field's height, how bright while its track rests and how much brighter at
/// full energy, and the colour field's scale.
const GLOW_RADIUS_SHARE: f64 = 0.16;
const GLOW_RESTING: f64 = 0.06;
const GLOW_PLAYING: f64 = 0.32;
const COLOUR_SCALE: i32 = 16;
/// How much of the colour field each frame keeps, out of 256, so that old colour fades.
const COLOUR_KEPT: i32 = 246;
const COLOUR_KEPT_SHIFT: i32 = 8;
/// The drift: how far a blob wanders from the middle as a share of the field, how fast at 120 a minute, and how its path's
/// speeds and phases vary by track.
const DRIFT_REACH: f64 = 0.36;
const DRIFT_SPEED: f64 = 0.18;
const DRIFT_SPEEDS: [f64; 7] = [0.83, 1.0, 1.21, 0.71, 1.37, 0.93, 1.13];
const DRIFT_PHASE: f64 = 2.39996;
/// The second path's speed and phase against the first's, so that a blob's path down differs from its path across.
const DOWN_SPEED_SHARE: f64 = 0.8;
const DOWN_PHASE_SHARE: f64 = 1.7;
const DOWN_SPEEDS_AFTER: usize = 3;
/// Seeing through the water: how far the slope moves the colour (a larger shift, less), at most how many cells, and the
/// highlight along the slope.
const REFRACT_SHIFT: i32 = 6;
const REFRACT_MOST: i32 = 3;
const HIGHLIGHT_SHIFT: i32 = 5;
const HIGHLIGHT_MOST: i32 = 22;
/// The dark ground under everything.
const GROUND: Colour = [6, 5, 14];
/// The rotozoom: how far the view turns either way, in radians, and how long a swing takes in drift time; the zoom at rest,
/// its pulse on each beat and how sharp the pulse is, and how much the playing swells it.
const SWING: f64 = 0.10;
const SWING_PERIOD: f64 = 9.0;
const REST_ZOOM: f64 = 1.16;
const BEAT_PULSE: f64 = 0.025;
const PULSE_SHARPNESS: i32 = 6;
const ENERGY_SWELL: f64 = 0.03;
/// The limiter: the mean brightness held under, the ceiling no channel passes, how fast the mean may rise and fall, out of
/// 255 a second, and the most it may lift a dim picture.
const MEAN_LEVEL: f64 = 70.0;
const CEILING: i32 = 225;
const MEAN_RISE_PER_SECOND: f64 = 50.0;
const MEAN_FALL_PER_SECOND: f64 = 40.0;
const MOST_GAIN: f64 = 1.5;
const HALF: f64 = 0.5;

/// One track's blob: its energy, rising as its notes play and fading after, what that energy moves toward, and the colour
/// its last note painted.
struct Blob {
    energy: f64,
    target: f64,
    colour: Colour,
}

/// Drifting blobs of colour, one for each track that plays, rippling the water they float in.
pub struct LavaLamp {
    rows: usize,
    columns: usize,
    water: Field,
    water_before: Field,
    colour: Picture,
    blobs: BTreeMap<usize, Blob>,
    motion: f64,
    limiter: Limiter,
}

impl LavaLamp {
    pub fn new() -> LavaLamp {
        LavaLamp {
            rows: 0,
            columns: 0,
            water: Field::default(),
            water_before: Field::default(),
            colour: Picture::filled(0, 0, [0; 3]),
            blobs: BTreeMap::new(),
            motion: 0.0,
            limiter: Limiter::new(MEAN_LEVEL, CEILING, MEAN_RISE_PER_SECOND, MEAN_FALL_PER_SECOND, MOST_GAIN),
        }
    }

    /// A radius in simulation cells, a share of the field's height, at least one.
    fn radius(&self, share: f64) -> usize {
        ((self.rows as f64 * share) as usize).max(1)
    }

    /// Where a track's blob is now, as a row and a column of the simulation, on its slow path.
    fn blob_place(&self, track: usize) -> (i64, i64) {
        let speeds = DRIFT_SPEEDS;
        let phase = track as f64 * DRIFT_PHASE;
        let across = HALF + DRIFT_REACH * (self.motion * speeds[track % speeds.len()] + phase).sin();
        let down_speed = speeds[(track + DOWN_SPEEDS_AFTER) % speeds.len()] * DOWN_SPEED_SHARE;
        let down = HALF + DRIFT_REACH * (self.motion * down_speed + phase * DOWN_PHASE_SHARE).sin();
        ((down * (self.rows as f64 - 1.0)) as i64, (across * (self.columns as f64 - 1.0)) as i64)
    }

    /// Let each note heard splash or push at its track's blob, and raise the blob's energy for a note that started.
    fn hear(&mut self, heard: &Hearing) {
        for note in &heard.notes {
            let colour = note_colour(note.track, note.pitch, note.drum);
            let place = self.blob_place(note.track);
            let blob = self.blobs.entry(note.track).or_insert(Blob {
                energy: 0.0,
                target: 0.0,
                colour,
            });
            blob.colour = colour;
            let velocity = note.velocity as i32;
            if note.started {
                blob.target = (blob.target + ENERGY_PER_NOTE * note.velocity as f64 / FULL_VELOCITY).min(1.0);
                let (share, depth) = if note.drum {
                    (DRUM_RADIUS_SHARE, DRUM_SPLASH_PER_VELOCITY)
                } else {
                    (SPLASH_RADIUS_SHARE, SPLASH_PER_VELOCITY)
                };
                let radius = self.radius(share);
                add_disc(&mut self.water, place.0, place.1, radius, depth * velocity);
            } else {
                let radius = self.radius(HELD_RADIUS_SHARE);
                add_disc(&mut self.water, place.0, place.1, radius, HELD_PUSH_PER_VELOCITY * velocity);
            }
        }
    }

    /// Move each blob's energy toward its target no faster than it may rise, and let the target fall away.
    fn settle(&mut self, seconds: f64) {
        let kept = ENERGY_KEPT_PER_SECOND.powf(seconds);
        let rise = ENERGY_RISE_PER_SECOND * seconds;
        for blob in self.blobs.values_mut() {
            blob.energy += (blob.target - blob.energy).clamp(-rise, rise);
            blob.target *= kept;
        }
    }

    /// Fade the colour field and bleed it into its neighbours, then let each blob glow its colour into it, brighter as its
    /// track plays.
    fn glow(&mut self, seconds: f64) {
        for cell in &mut self.colour.cells {
            *cell = cell.map(|channel| (channel * COLOUR_KEPT) >> COLOUR_KEPT_SHIFT);
        }
        self.colour = blurred(&self.colour);
        let share = seconds / REFERENCE_FRAME_SECONDS;
        let radius = self.radius(GLOW_RADIUS_SHARE);
        let glows: Vec<((i64, i64), Colour)> = self
            .blobs
            .iter()
            .map(|(track, blob)| {
                let strength = (GLOW_RESTING + GLOW_PLAYING * blob.energy) * share;
                let amount = blob.colour.map(|channel| (channel as f64 * COLOUR_SCALE as f64 * strength) as i32);
                (self.blob_place(*track), amount)
            })
            .collect();
        for ((row, column), amount) in glows {
            add_colour_disc(&mut self.colour, row, column, radius, amount);
        }
    }

    /// The colour field as seen through the water: each cell's colour taken a little way along the water's slope, with a
    /// soft highlight on the slope, over the dark ground.
    fn seen_through_water(&self) -> Picture {
        let mut cells = Vec::with_capacity(self.rows * self.columns);
        for row in 0..self.rows as i64 {
            for column in 0..self.columns as i64 {
                let across = self.water.at_edge(row, column + 1) - self.water.at_edge(row, column - 1);
                let down = self.water.at_edge(row + 1, column) - self.water.at_edge(row - 1, column);
                let source_row = (row + (down >> REFRACT_SHIFT).clamp(-REFRACT_MOST, REFRACT_MOST) as i64).clamp(0, self.rows as i64 - 1);
                let source_column = (column + (across >> REFRACT_SHIFT).clamp(-REFRACT_MOST, REFRACT_MOST) as i64).clamp(0, self.columns as i64 - 1);
                let seen = self.colour.get(source_row as usize, source_column as usize);
                let highlight = (-down >> HIGHLIGHT_SHIFT).clamp(-HIGHLIGHT_MOST, HIGHLIGHT_MOST);
                let mut colour = [0; 3];
                for channel in 0..3 {
                    colour[channel] = seen[channel] / COLOUR_SCALE + highlight + GROUND[channel];
                }
                cells.push(colour);
            }
        }
        Picture {
            rows: self.rows,
            columns: self.columns,
            cells,
        }
    }
}

impl Default for LavaLamp {
    fn default() -> LavaLamp {
        LavaLamp::new()
    }
}

impl Painter for LavaLamp {
    const OPTION: &'static str = OPTION;

    /// Start the water and the colour afresh for an area of this many big pixels.
    fn resized(&mut self, columns: usize, rows: usize) {
        self.rows = rows * SUPERSAMPLE;
        self.columns = columns * SUPERSAMPLE;
        self.water = Field::zeros(self.rows, self.columns);
        self.water_before = Field::zeros(self.rows, self.columns);
        self.colour = Picture::filled(self.rows, self.columns, [0; 3]);
    }

    fn pixels(&mut self, seconds: f64, heard: &Hearing) -> Picture {
        self.motion += seconds * heard.tempo_factor() * DRIFT_SPEED;
        self.hear(heard);
        self.settle(seconds);
        for _ in 0..WAVE_STEPS {
            let next = ripple_step(&self.water, &self.water_before, DAMPING_SHIFT);
            self.water_before = std::mem::replace(&mut self.water, next);
        }
        self.glow(seconds);
        let picture = self.seen_through_water();
        let energy = self.blobs.values().map(|blob| blob.energy).fold(0.0, f64::max);
        let pulse = (HALF + HALF * (TAU * heard.beats.rem_euclid(1.0)).cos()).powi(PULSE_SHARPNESS);
        let angle = SWING * (TAU * self.motion / SWING_PERIOD).sin();
        let zoom = REST_ZOOM + BEAT_PULSE * pulse + ENERGY_SWELL * energy;
        let turned = rotozoomed(&picture, angle, zoom);
        let small = turned.derezzed(SUPERSAMPLE);
        self.limiter.limited(small, seconds).stepped(COLOUR_STEP_SHIFT)
    }
}
