// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The theme colours (the Python interface/tracker/themes.py): each kind of page has a colour of its own, drawn as a stripe
//! under the header in place of its rule.

pub type Colour = (u8, u8, u8);

pub const SONGS: Colour = (0, 90, 255);
pub const PATTERNS: Colour = (0, 200, 0);
pub const GENERATORS: Colour = (220, 0, 220);
pub const SCALES: Colour = (0, 170, 170);
pub const GROOVES: Colour = (255, 128, 0);
pub const INSTRUMENTS: Colour = (230, 200, 0);
pub const DRAWS: Colour = (190, 90, 255);
pub const SET_FILE: Colour = (128, 128, 128);
pub const MAIN_SCREEN: Colour = (255, 255, 255);
pub const FROM_ARRANGE: Colour = (0, 200, 230);
pub const WIZARD: Colour = (0, 255, 255);

/// The luminance every theme's edge is moved to, so that each looks as strong as the others.
const EDGE_LUMINANCE: f64 = 0.22;
const BALANCE_STEPS: usize = 24;
const WHITE: Colour = (255, 255, 255);
const BLACK: Colour = (0, 0, 0);
const CHANNEL_WEIGHTS: [f64; 3] = [0.2126, 0.7152, 0.0722];
/// A stripe's caption is black on a theme brighter than this, and white on a darker one.
const CAPTION_LIGHT_ABOVE: f64 = 0.35;

/// A colour's relative luminance, from 0 for black to 1 for white, as the eye weighs red, green and blue.
pub fn luminance(colour: Colour) -> f64 {
    let mut total = 0.0;
    for (place, channel) in [colour.0, colour.1, colour.2].into_iter().enumerate() {
        let value = channel as f64 / 255.0;
        let linear = if value <= 0.04045 {
            value / 12.92
        } else {
            ((value + 0.055) / 1.055).powf(2.4)
        };
        total += CHANNEL_WEIGHTS[place] * linear;
    }
    total
}

fn mixed(low: Colour, high: Colour, share: f64) -> Colour {
    let part = |a: u8, b: u8| (a as f64 + (b as f64 - a as f64) * share).round_ties_even() as u8;
    (part(low.0, high.0), part(low.1, high.1), part(low.2, high.2))
}

/// A colour of the same hue moved toward black or white until its luminance is the edges', as the Python balances it.
pub fn balanced(colour: Colour) -> Colour {
    balanced_to(colour, EDGE_LUMINANCE)
}

/// How bright text in a theme's colour is, so that every kind reads as strongly as the others.
const TEXT_LUMINANCE: f64 = 0.3;

/// A style naming a theme's colour toned for text, the hue kept.
pub fn text_style(colour: Colour) -> String {
    let (red, green, blue) = balanced_to(colour, TEXT_LUMINANCE);
    format!("rgb({red},{green},{blue})")
}

fn balanced_to(colour: Colour, target: f64) -> Colour {
    let (low, high) = if luminance(colour) >= target { (BLACK, colour) } else { (colour, WHITE) };
    let (mut start, mut end) = (0.0, 1.0);
    for _ in 0..BALANCE_STEPS {
        let middle = (start + end) / 2.0;
        if luminance(mixed(low, high, middle)) < target {
            start = middle;
        } else {
            end = middle;
        }
    }
    mixed(low, high, (start + end) / 2.0)
}

pub fn caption_colour(theme: Colour) -> Colour {
    if luminance(theme) > CAPTION_LIGHT_ABOVE {
        BLACK
    } else {
        WHITE
    }
}
