// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Drifts as the song plays (the Python engine/generators/drift/play.py and engine/step_effects.py): one process for each
//! drift for the whole song, which every clip naming it in its chains hears. A drift's clock runs from the top of the song
//! or its run, triggering every so often, a bar unless set; at each trigger it picks new amounts and holds them until the
//! next. Its position between its versions A and B moves a step a trigger in its direction: numbers are blended between A's
//! and B's by the position, and a scale or root is B's with a chance equal to the position. What a trigger picks is worked
//! out once and kept, so every clip hears the same drift.

use llamatron_math::{PythonRandom, Rational, Seed};
use llamatron_model::file::data::Data;
use llamatron_model::schema::checking::{time_length, TimeLength};
use llamatron_names::file_format;
use llamatron_names::words;
use std::collections::HashMap;

const NUMBERS: &[&str] = &["velocity", "probability", "degree", "degree_random", "scale_probability", "root_probability"];

/// What the drifts a clip hears do to one step: added to its velocity, its probability and its degree, and the scale and
/// root that take the clip's place, or None.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct StepEffects {
    pub velocity: i64,
    pub probability: i64,
    pub degree: i64,
    pub scale: Option<String>,
    pub root: Option<String>,
}

/// What one drift picked at one trigger: its blended numbers, its degree's random part, and its scale and root overrides.
#[derive(Clone)]
struct Trigger {
    numbers: HashMap<&'static str, i64>,
    random_degree: i64,
    scale: Option<String>,
    root: Option<String>,
}

/// Every drift of a song as it plays, worked out a trigger at a time and remembered.
pub struct DriftPlay {
    seed: Option<i64>,
    bar: Rational,
    settings: HashMap<String, Data>,
    triggers: HashMap<(String, i128), Trigger>,
    walks: HashMap<String, Vec<i64>>,
    choosers: HashMap<String, PythonRandom>,
}

impl DriftPlay {
    pub fn new(seed: Option<i64>, bar: Rational, settings: HashMap<String, Data>) -> DriftPlay {
        DriftPlay {
            seed,
            bar,
            settings,
            triggers: HashMap::new(),
            walks: HashMap::new(),
            choosers: HashMap::new(),
        }
    }

    fn written(&self, name: &str, setting: &str) -> Option<&Data> {
        self.settings.get(name)?.get(setting).filter(|value| !value.is_null())
    }

    /// How long one of a drift's triggers lasts.
    pub fn every(&self, name: &str) -> Rational {
        match self.written(name, words::EVERY).and_then(|every| time_length(every).ok()) {
            Some(TimeLength::Bars(count)) => self.bar * Rational::whole(count as i128),
            Some(TimeLength::Length(length)) => length,
            None => self.bar,
        }
    }

    /// What the drifts named do to a step at a song time, their numbers added and the last one's overrides winning; origins
    /// gives where each drift's clock starts.
    pub fn effects(&mut self, names: &[String], time: Rational, origins: &[(String, Rational)]) -> StepEffects {
        let mut effects = StepEffects::default();
        for name in names {
            let origin = origins
                .iter()
                .find(|(found, _)| found == name)
                .map(|(_, origin)| *origin)
                .unwrap_or(Rational::ZERO);
            let trigger = ((time - origin) / self.every(name)).floor();
            let picked = self.picked(name, trigger);
            effects.velocity += picked.numbers[file_format::TrackSetting::VELOCITY];
            effects.probability += picked.numbers[file_format::Row::PROBABILITY];
            effects.degree += picked.numbers[file_format::Row::DEGREE] + picked.random_degree;
            effects.scale = picked.scale.or(effects.scale);
            effects.root = picked.root.or(effects.root);
        }
        effects
    }

    fn picked(&mut self, name: &str, trigger: i128) -> Trigger {
        let key = (name.to_string(), trigger);
        if let Some(found) = self.triggers.get(&key) {
            return found.clone();
        }
        let picked = self.pick(name, trigger);
        self.triggers.insert(key, picked.clone());
        picked
    }

    fn chooser(&mut self, name: &str) -> &mut PythonRandom {
        let seed = self.seed;
        self.choosers.entry(name.to_string()).or_insert_with(|| match seed {
            Some(seed) => PythonRandom::new(Seed::Text(&format!("{seed}/drift/{name}"))),
            None => PythonRandom::unseeded(),
        })
    }

    /// How far a drift is from A toward B at a trigger, by its direction.
    fn position(&mut self, name: &str, trigger: i128) -> Rational {
        let steps = self
            .written(name, words::STEPS_TO_B)
            .and_then(Data::as_whole)
            .filter(|steps| *steps != 0)
            .unwrap_or(16);
        let direction = self
            .written(name, file_format::ClipSlotSetting::DIRECTION)
            .map(Data::python_str)
            .unwrap_or(file_format::Direction::FORWARD.to_string());
        let place = match direction.as_str() {
            file_format::Direction::FORWARD => trigger.min(steps),
            file_format::ClipSlotSetting::LOOP => trigger.rem_euclid(steps + 1),
            file_format::Direction::PENDULUM => {
                let place = trigger.rem_euclid(2 * steps);
                if place > steps {
                    2 * steps - place
                } else {
                    place
                }
            }
            _ => self.walk(name, trigger, steps),
        };
        Rational::new(place, steps)
    }

    /// A brownian drift's place at a trigger: a step up or down from the one before, held between A and B.
    fn walk(&mut self, name: &str, trigger: i128, steps: i128) -> i128 {
        let mut walk = self.walks.remove(name).unwrap_or(vec![0]);
        while walk.len() as i128 <= trigger {
            let step = *self.chooser(name).choice(&[-1i64, 1]);
            let last = *walk.last().unwrap_or(&0);
            walk.push((last + step).clamp(0, steps as i64));
        }
        let place = walk[trigger.max(0) as usize] as i128;
        self.walks.insert(name.to_string(), walk);
        place
    }

    fn pick(&mut self, name: &str, trigger: i128) -> Trigger {
        let position = self.position(name, trigger);
        let mut numbers = HashMap::new();
        for value in NUMBERS {
            let version = |letter: &str| self.written(name, &format!("{letter}_{value}")).and_then(Data::as_whole).unwrap_or(0);
            let (first, second) = (version("a"), version("b"));
            numbers.insert(*value, (Rational::whole(first) + Rational::whole(second - first) * position).round() as i64);
        }
        let spread = numbers[file_format::DriftValue::DEGREE_RANDOM];
        let random_degree = if spread != 0 {
            self.chooser(name).randint(-spread as i128, spread as i128) as i64
        } else {
            0
        };
        let scale = self.overridden(
            name,
            file_format::SongSetting::SCALE,
            numbers[file_format::DriftValue::SCALE_PROBABILITY],
            position,
        );
        let root = self.overridden(
            name,
            file_format::ScaleSetting::ROOT,
            numbers[file_format::DriftValue::ROOT_PROBABILITY],
            position,
        );
        Trigger {
            numbers,
            random_degree,
            scale,
            root,
        }
    }

    /// The scale or root a trigger overrides with, or None: B's with a chance of the position, else A's, and only with the
    /// override's chance.
    fn overridden(&mut self, name: &str, value: &str, chance: i64, position: Rational) -> Option<String> {
        let first = self.written(name, &format!("a_{value}")).map(Data::python_str);
        let second = self.written(name, &format!("b_{value}")).map(Data::python_str);
        if first.is_none() && second.is_none() {
            return None;
        }
        let mut choice = first;
        if Rational::from_float(self.chooser(name).random()) < position {
            choice = second;
        }
        if choice.is_none() || self.chooser(name).random() * 100.0 >= chance as f64 {
            return None;
        }
        choice
    }
}
