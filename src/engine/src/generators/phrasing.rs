// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Phrasing generator (the Python engine/generators/phrasing/): a tune delivered as a singer or a horn player delivers it,
//! in lines, each growing toward its main note and falling away, a breath after it, its notes run together or apart. No note
//! is left out, no pitch changes and nothing is drawn by chance.

use crate::clip::Clip;
use crate::error::{RenderError, Rendered};
use crate::generators::parts::{parts_of, Part};
use llamatron_math::Rational;
use llamatron_model::file::data::Data;
use llamatron_names::file_format;
use llamatron_names::words;

/// How many bars a line lasts where the settings name none, and a deep breath's length, a quarter of a whole note.
const DEFAULT_LINE_BARS: i128 = 2;
const DEEP_BREATH_DIVISOR: i128 = 4;

const CHOPPY: &str = words::CHOPPY;
const FLOWING: &str = words::FLOWING;

pub struct Phrasing {
    line: Rational,
    bar: Rational,
    breath: Rational,
    depth: i128,
    join: String,
}

impl Phrasing {
    pub fn of(settings: &Data, bar: Rational) -> Rendered<Phrasing> {
        let written = |name: &str, default: &str| {
            settings
                .get(name)
                .filter(|value| !value.is_null())
                .map(Data::python_str)
                .unwrap_or(default.to_string())
        };
        let line_bars = settings.get(words::LINE_BARS).and_then(Data::as_whole).unwrap_or(DEFAULT_LINE_BARS);
        let breath = match written(words::BREATH, words::QUICK).as_str() {
            words::NONE => Rational::ZERO,
            words::DEEP => Rational::new(1, DEEP_BREATH_DIVISOR),
            _ => Rational::new(1, 8),
        };
        let depth = match written(words::RISE_AND_FALL, "a little").as_str() {
            words::NONE => 0,
            "a lot" => 22,
            _ => 10,
        };
        if line_bars <= 0 {
            return Err(RenderError::Refused("a Phrasing's lines must last a bar or more".to_string()));
        }
        Ok(Phrasing {
            line: bar * Rational::whole(line_bars),
            bar,
            breath,
            depth,
            join: written(file_format::SetlistSetting::NOTES, "as written"),
        })
    }

    pub fn generate(&self, clip: &Clip) -> Rendered<Clip> {
        let mut parts = parts_of(&clip.resolved_sounds()?);
        let mut lines: Vec<(i128, Vec<usize>)> = Vec::new();
        for (place, part) in parts.iter().enumerate() {
            if part.is_note() {
                let number = (part.start / self.line).floor();
                match lines.iter_mut().find(|(found, _)| *found == number) {
                    Some((_, line)) => line.push(place),
                    None => lines.push((number, vec![place])),
                }
            }
        }
        lines.sort_by_key(|(number, _)| *number);
        for (_, line) in &lines {
            self.join_notes(&mut parts, line);
            self.take_breath(&mut parts[line[line.len() - 1]]);
            self.shape_loudness(&mut parts, line);
        }
        let sounds = parts.iter().flat_map(Part::sounds).collect();
        Ok(Clip {
            sounds,
            time_signature: None,
            looping: true,
            groove: None,
            ..clip.clone()
        })
    }

    /// A line's notes choppy or flowing: all but its last when flowing, which the breath follows.
    fn join_notes(&self, parts: &mut [Part], line: &[usize]) {
        if self.join == CHOPPY {
            for place in line {
                let heard = parts[*place].heard;
                parts[*place].heard = if heard <= Rational::new(1, 4) {
                    heard / Rational::whole(2)
                } else {
                    heard - Rational::new(1, 8)
                };
            }
        } else if self.join == FLOWING {
            for pair in line.windows(2) {
                let (part, after) = (&parts[pair[0]], &parts[pair[1]]);
                let reach = after.start - part.start;
                let heard = if reach <= part.heard {
                    part.heard
                } else if after.pitch() == part.pitch() {
                    reach - Rational::new(1, 32)
                } else {
                    reach
                };
                parts[pair[0]].heard = heard;
            }
        }
    }

    /// A line's last note shortened for the breath after it, by no more than half the note, and by nothing where the tune
    /// already rests or the note sounds on into the next line.
    fn take_breath(&self, last: &mut Part) {
        let line_end = Rational::whole((last.start / self.line).floor() + 1) * self.line;
        let silence = line_end - (last.start + last.heard);
        let wanted = self.breath - silence;
        if silence >= Rational::ZERO && wanted > Rational::ZERO {
            last.heard = last.heard - wanted.min(last.heard * Rational::new(1, 2));
        }
    }

    /// A line risen to its main note and fallen away, a note on a bar's start a little louder.
    fn shape_loudness(&self, parts: &mut [Part], line: &[usize]) {
        if self.depth == 0 {
            return;
        }
        let main = parts[self.main_note(parts, line)].start;
        let first = parts[line[0]].start;
        let last = parts[line[line.len() - 1]].start;
        let share = |start: Rational, first: Rational, last: Rational| {
            if last == first {
                Rational::whole(1)
            } else {
                (start - first) / (last - first)
            }
        };
        let one = Rational::whole(1);
        for place in line {
            let start = parts[*place].start;
            let mut height = if start <= main {
                Rational::new(-2, 5) + (one - Rational::new(-2, 5)) * share(start, first, main)
            } else {
                one + (Rational::new(-4, 5) - one) * share(start, main, last)
            };
            if (start / self.bar).is_whole() {
                height = height + Rational::new(1, 5);
            }
            parts[*place].louder_by(((height - one) * Rational::whole(self.depth)).round() as i64);
        }
    }

    /// The note a line grows toward: its longest note starting on a bar's start or middle in the line's second half, the
    /// higher and then the later of two as long; or the longest in the second half; or the longest of all.
    fn main_note(&self, parts: &[Part], line: &[usize]) -> usize {
        let middle = Rational::whole((parts[line[0]].start / self.line).floor()) * self.line + self.line / Rational::whole(2);
        let late: Vec<usize> = line.iter().copied().filter(|place| parts[*place].start >= middle).collect();
        let half_bar = self.bar / Rational::whole(2);
        let strong: Vec<usize> = late.iter().copied().filter(|place| (parts[*place].start / half_bar).is_whole()).collect();
        let chosen = if !strong.is_empty() {
            strong
        } else if !late.is_empty() {
            late
        } else {
            line.to_vec()
        };
        let weight = |place: &usize| (parts[*place].heard, parts[*place].pitch(), parts[*place].start);
        // The first of the heaviest, as Python's max takes it.
        let mut best = chosen[0];
        for place in &chosen[1..] {
            if weight(place) > weight(&best) {
                best = *place;
            }
        }
        best
    }
}
