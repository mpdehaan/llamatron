// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Cycle, a mode of modes: each of the other modes in turn, moving on every CYCLE_SECONDS.
//!
//! It shows each mode from the start, fresh, and says which is showing, so that the page shows the name for a while each
//! time it moves on, as it does when the key changes the mode. The order is shuffled once when the program starts, so that
//! every run, and so every recording, goes through the modes in an order of its own, and keeps it for the whole run.

use super::{made, Hearing, Mode};
use crate::text::Text;
use llamatron_math::python_random::{PythonRandom, Seed};
use llamatron_names::words;
use std::sync::OnceLock;

pub const OPTION: &str = words::CYCLE;

/// How long each mode shows before the next.
const CYCLE_SECONDS: f64 = 15.0;

/// The order Cycle shows the modes in, shuffled once as the program starts from the clock, so that each run has its own.
fn cycle_order() -> &'static [&'static str] {
    static ORDER: OnceLock<Vec<&'static str>> = OnceLock::new();
    ORDER.get_or_init(|| {
        let mut order: Vec<&'static str> = super::ported_modes().into_iter().filter(|name| *name != OPTION).collect();
        let seed = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_or(0, |since| since.as_nanos() as i128);
        PythonRandom::new(Seed::Whole(seed)).shuffle(&mut order);
        order
    })
}

/// Each of the other modes in turn, in the run's order, every CYCLE_SECONDS.
pub struct Cycle {
    order: Vec<&'static str>,
    place: usize,
    showing: Option<Box<dyn Mode>>,
    since: Option<f64>,
}

impl Cycle {
    /// Go through the run's order, leaving out the modes named in hidden, the ones the set hides, unless that leaves none.
    pub fn new(hidden: &[String]) -> Cycle {
        let every = cycle_order();
        let mut order: Vec<&'static str> = every.iter().copied().filter(|name| !hidden.iter().any(|each| each == name)).collect();
        if order.is_empty() {
            order = every.to_vec();
        }
        let showing = order.first().and_then(|name| made(name, &[]));
        Cycle {
            order,
            place: 0,
            showing,
            since: None,
        }
    }
}

impl Mode for Cycle {
    fn option(&self) -> &'static str {
        OPTION
    }

    fn shown_name(&self) -> String {
        self.showing
            .as_ref()
            .map_or_else(|| crate::settings::mode_name(OPTION), |mode| mode.shown_name())
    }

    fn frame(&mut self, width: usize, height: usize, now: f64, heard: &Hearing) -> Vec<Text> {
        let since = *self.since.get_or_insert(now);
        if now - since >= CYCLE_SECONDS && !self.order.is_empty() {
            self.place = (self.place + 1) % self.order.len();
            self.showing = made(self.order[self.place], &[]);
            self.since = Some(now);
        }
        match &mut self.showing {
            Some(mode) => mode.frame(width, height, now, heard),
            None => Vec::new(),
        }
    }
}
