// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The order a pattern's steps play in, for each of a step sequencer's directions, and the order a clip's patterns play in (the
//! Python engine/realizer/step_order.py and pattern_order.py), and the random streams their choices are drawn from.

use llamatron_math::python_random::{PythonRandom, Seed};
use llamatron_model::schema::generated::file_format::{Direction, PatternOrder};
use std::collections::HashMap;

/// Random numbers drawn from a seed as Python's random.Random(seed) draws them, the generator seeded only at the first draw,
/// since a clip prepares a stream for each of its random choices and almost never draws from them; or from no seed, for a
/// new take each time.
pub struct DrawnWhenAsked {
    seed: Option<String>,
    random: Option<PythonRandom>,
}

impl DrawnWhenAsked {
    pub fn new(seed: Option<String>) -> DrawnWhenAsked {
        DrawnWhenAsked { seed, random: None }
    }

    pub fn source(&mut self) -> &mut PythonRandom {
        let seed = &self.seed;
        self.random.get_or_insert_with(|| match seed {
            Some(text) => PythonRandom::new(Seed::Text(text)),
            None => PythonRandom::unseeded(),
        })
    }

    pub fn random(&mut self) -> f64 {
        self.source().random()
    }
}

/// Where a clip is in each list of steps, carried across its passes.
pub struct StepOrder {
    choices: DrawnWhenAsked,
    places: HashMap<(String, String), i64>,
}

impl StepOrder {
    pub fn new(choices: DrawnWhenAsked) -> StepOrder {
        StepOrder {
            choices,
            places: HashMap::new(),
        }
    }

    /// The next count steps to play from a list of count steps, one pass, for the list a key names.
    pub fn next_steps(&mut self, key: &str, count: usize, direction: &str) -> Vec<usize> {
        let place_key = (key.to_string(), direction.to_string());
        match walk_order(count, direction) {
            Some(order) => {
                let taken = *self.places.get(&place_key).unwrap_or(&0) as usize;
                self.places.insert(place_key, (taken + count) as i64);
                (taken..taken + count).map(|place| order[place % order.len()]).collect()
            }
            None => (0..count).map(|_| self.chosen_step(&place_key, count, direction)).collect(),
        }
    }

    fn chosen_step(&mut self, key: &(String, String), count: usize, direction: &str) -> usize {
        if direction == Direction::RANDOM {
            return self.choices.source().randrange_to(count as i128) as usize;
        }
        let Some(place) = self.places.get(key).copied() else {
            self.places.insert(key.clone(), 0);
            return 0;
        };
        let moved = (place + chosen_move(direction, self.choices.source())).rem_euclid(count as i64);
        self.places.insert(key.clone(), moved);
        moved as usize
    }
}

/// Which way a direction that chooses as it goes moves this time: brownian on half the time, back a quarter and staying put
/// the rest; eitherway on or back, half the time each.
pub fn chosen_move(direction: &str, choices: &mut PythonRandom) -> i64 {
    let chance = choices.random();
    if chance < 0.5 {
        return 1;
    }
    if direction == Direction::BROWNIAN {
        if chance < 0.75 {
            return -1;
        }
        return 0;
    }
    -1
}

/// The steps of a direction that repeats exactly, or None for one chosen as it goes.
pub fn walk_order(count: usize, direction: &str) -> Option<Vec<usize>> {
    let forward: Vec<usize> = (0..count).collect();
    let backward: Vec<usize> = forward.iter().rev().copied().collect();
    Some(match direction {
        Direction::FORWARD => forward,
        Direction::REVERSE_A => [&forward[..1.min(count)], &backward[..count.saturating_sub(1)]].concat(),
        Direction::REVERSE_B => backward,
        Direction::ALTERNATE => [forward, backward].concat(),
        Direction::PENDULUM => {
            let inner = if count > 1 { &backward[1..count - 1] } else { &[][..] };
            [&forward[..], inner].concat()
        }
        _ => return None,
    })
}

/// A clip's patterns in the order one pass plays them: place is the pass, counted from 0.
pub fn ordered_patterns(names: &[String], order: Option<&str>, place: i64, rolls: &mut DrawnWhenAsked) -> Vec<String> {
    let mut names = names.to_vec();
    let backward: Vec<String> = names.iter().rev().cloned().collect();
    let returning = place % 2 == 1;
    match order.unwrap_or(PatternOrder::FORWARD) {
        PatternOrder::REVERSE_A => [&names[..1.min(names.len())], &backward[..names.len().saturating_sub(1)]].concat(),
        PatternOrder::REVERSE_B => backward,
        PatternOrder::ALTERNATE if returning => backward,
        PatternOrder::PENDULUM if returning => [&backward[1.min(backward.len())..], &backward[..1.min(backward.len())]].concat(),
        PatternOrder::RANDOM => {
            rolls.source().shuffle(&mut names);
            names
        }
        PatternOrder::FIRST_THEN_RANDOM => {
            let mut rest = names.split_off(1.min(names.len()));
            rolls.source().shuffle(&mut rest);
            [names, rest].concat()
        }
        _ => names,
    }
}
