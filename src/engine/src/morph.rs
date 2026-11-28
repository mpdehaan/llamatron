// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A clip morphing into another pattern (the Python engine/parts/blend.py and engine/realizer/morph_controls.py): over its
//! repeats the target comes in from the left, the right or the middle out, the amount setting how much of each pass it
//! covers, its edges moved to the nearest start of a position so that no note is cut; the CC values are the target's inside
//! and the clip's outside, each side's lanes carried across the edges.

use crate::clip::{Clip, Control};
use crate::error::{RenderError, Rendered};
use crate::sound::Sound;
use llamatron_math::Rational;
use llamatron_names::words;

pub const LEFT: &str = words::LEFT;
pub const RIGHT: &str = words::RIGHT;
const AMOUNT_PRECISION: i128 = 1_000_000;
const ALL_OF_THE_TARGET: i128 = 100;

pub struct Blend<'c> {
    pub target: &'c Clip,
    pub amount: Rational,
    pub mode: String,
}

impl Blend<'_> {
    /// Where the target plays in the result, from start to end.
    pub fn region(&self, clip: &Clip) -> Rendered<(Rational, Rational)> {
        let total = clip.total_length()?;
        let share = total * self.amount.limit_denominator(AMOUNT_PRECISION) / Rational::whole(ALL_OF_THE_TARGET);
        let half = Rational::whole(2);
        let (start, end) = match self.mode.as_str() {
            LEFT => (Rational::ZERO, share),
            RIGHT => (total - share, total),
            _ => ((total - share) / half, (total + share) / half),
        };
        let mut edges = vec![Rational::ZERO, total];
        let mut now = Rational::ZERO;
        for position in clip.played_sounds()? {
            edges.push(now);
            now = now + position.place();
        }
        let (start, end) = (closest(&edges, start), closest(&edges, end));
        if end <= start {
            if share < total {
                return Ok((Rational::ZERO, Rational::ZERO));
            }
            return Ok((Rational::ZERO, total));
        }
        Ok((start, end))
    }

    /// The clip's sounds moved towards the target, which lasts as long.
    pub fn sounds(&self, clip: &Clip) -> Rendered<Vec<Sound>> {
        let total = clip.total_length()?;
        if self.target.total_length()? != total {
            return Err(RenderError::Refused(format!(
                "a morph's patterns last {total} and {}",
                self.target.total_length()?
            )));
        }
        let (start, end) = self.region(clip)?;
        if end <= start {
            return Ok(clip.sounds.clone());
        }
        if start == Rational::ZERO && end == total {
            return Ok(self.target.sounds.clone());
        }
        let mut sounds = Vec::new();
        if start > Rational::ZERO {
            sounds.extend(clip.section(Rational::ZERO, start)?.sounds);
        }
        sounds.extend(self.target.section(start, end)?.sounds);
        if end < total {
            sounds.extend(clip.section(end, total)?.sounds);
        }
        Ok(sounds)
    }
}

/// The edge nearest a time, the earlier of two equally near.
fn closest(edges: &[Rational], time: Rational) -> Rational {
    let mut nearest: Option<(Rational, Rational)> = None;
    for edge in edges {
        let apart = (*edge - time).abs();
        if nearest.is_none_or(|(found, least)| apart < least || (apart == least && *edge < found)) {
            nearest = Some((*edge, apart));
        }
    }
    nearest.map(|(edge, _)| edge).unwrap_or(time)
}

/// The CC values of a morph: the target's from start to end and the source's elsewhere, each side's lanes holding across
/// the edges what they would hold there.
pub fn morph_controls(source: &Clip, target: &Clip, start: Rational, end: Rational) -> Rendered<Vec<Control>> {
    if end <= start {
        return Ok(source.controls.clone());
    }
    let mut result: Vec<Control> = source.controls.iter().filter(|control| control.time < start).copied().collect();
    result.extend(carried_to(target, start));
    result.extend(target.controls.iter().filter(|control| start <= control.time && control.time < end));
    if end < source.total_length()? {
        result.extend(carried_to(source, end));
        result.extend(source.controls.iter().filter(|control| control.time >= end));
    }
    Ok(result)
}

/// The values a clip's lanes held just before a time, sent again at that time, each lane in the order it was first sent.
fn carried_to(clip: &Clip, time: Rational) -> Vec<Control> {
    let mut latest: Vec<Control> = Vec::new();
    for control in clip.controls.iter().filter(|control| control.time <= time) {
        match latest.iter_mut().find(|found| found.number == control.number) {
            Some(found) => *found = *control,
            None => latest.push(*control),
        }
    }
    latest
        .into_iter()
        .filter(|control| control.time < time)
        .map(|control| Control { time, ..control })
        .collect()
}
