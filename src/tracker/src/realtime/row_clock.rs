// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A row's clock (the Python engine/clips/row_clock.py): how many seconds into a row a moment of its music falls, at the
//! row's tempo and every change of tempo inside it. A row with one tempo is one multiplication; a row whose scene ramps
//! its tempo holds a tempo for each beat of the ramp, and a moment is found among them.

use llamatron_math::Rational;

/// What a tempo counts, quarter notes a minute, and the seconds in a minute.
const QUARTERS_PER_WHOLE: f64 = 4.0;
const SECONDS_PER_MINUTE: f64 = 60.0;

/// How long a whole note lasts in seconds at a tempo in quarter notes a minute.
pub fn seconds_per_whole(tempo: f64) -> f64 {
    QUARTERS_PER_WHOLE * SECONDS_PER_MINUTE / tempo
}

/// The tempos of one row in order, each from a time in whole notes counted from the row's start.
#[derive(Clone, Debug)]
pub struct RowClock {
    starts: Vec<f64>,
    seconds: Vec<f64>,
    wholes: Vec<f64>,
}

impl RowClock {
    /// The clock of a row's tempos, each a time in whole notes and a tempo, the first from the row's start.
    pub fn new(tempos: &[(Rational, f64)]) -> RowClock {
        let mut clock = RowClock {
            starts: Vec::new(),
            seconds: Vec::new(),
            wholes: Vec::new(),
        };
        let mut seconds = 0.0;
        for (start, tempo) in tempos {
            let start = start.to_float();
            if let (Some(last_start), Some(last_whole)) = (clock.starts.last(), clock.wholes.last()) {
                seconds += (start - last_start) * last_whole;
            }
            clock.starts.push(start);
            clock.seconds.push(seconds);
            clock.wholes.push(seconds_per_whole(*tempo));
        }
        clock
    }

    /// Whether the row keeps one tempo throughout.
    pub fn has_one_tempo(&self) -> bool {
        self.starts.len() == 1
    }

    /// How many seconds into the row a time in whole notes falls.
    pub fn seconds_at(&self, time: f64) -> f64 {
        if self.starts.len() == 1 {
            return time * self.wholes[0];
        }
        let place = self.starts.iter().rposition(|start| *start <= time).unwrap_or(0);
        self.seconds[place] + (time - self.starts[place]) * self.wholes[place]
    }

    /// How many seconds into the row an exact time falls, divided as Python's float() of a Fraction divides.
    pub fn seconds_at_exact(&self, time: Rational) -> f64 {
        self.seconds_at(time.to_float())
    }

    /// How many whole notes into the row a moment in seconds falls.
    pub fn whole_at(&self, seconds: f64) -> f64 {
        if self.starts.len() == 1 {
            return seconds / self.wholes[0];
        }
        let place = self.seconds.iter().rposition(|start| *start <= seconds).unwrap_or(0);
        self.starts[place] + (seconds - self.seconds[place]) / self.wholes[place]
    }

    /// How long a whole note lasts at a moment of the row, in seconds.
    pub fn seconds_per_whole_at(&self, seconds: f64) -> f64 {
        let place = self.seconds.iter().rposition(|start| *start <= seconds).unwrap_or(0);
        self.wholes[place]
    }
}
