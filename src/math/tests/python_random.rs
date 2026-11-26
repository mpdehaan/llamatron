// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Rust port of CPython's random numbers, held to CPython case for case: tests/data/python_random_cases.txt, written by
//! internal_tools/python_random_cases.py from CPython itself.

use llamatron_math::{PythonRandom, Seed};

const CASES: &str = include_str!("data/python_random_cases.txt");
const WEIGHTS: [f64; 4] = [1.0, 2.0, 3.0, 0.5];

fn joined<T: ToString>(items: impl IntoIterator<Item = T>) -> String {
    items.into_iter().map(|item| item.to_string()).collect::<Vec<_>>().join(",")
}

/// A float as Python's repr writes it: the shortest text that reads back exactly, with a point.
fn python_float(value: f64) -> String {
    let text = format!("{value:?}");
    if text.contains(['.', 'e', 'n', 'i']) {
        text
    } else {
        format!("{text}.0")
    }
}

fn drawn(generator: &mut PythonRandom, call: &str, arguments: &[f64]) -> String {
    let whole = |place: usize| arguments[place] as i128;
    match call {
        "random" => python_float(generator.random()),
        "getrandbits" => generator.getrandbits(whole(0) as u32).to_string(),
        "randrange" if arguments.len() == 1 => generator.randrange_to(whole(0)).to_string(),
        "randrange" => generator.randrange(whole(0), whole(1), whole(2)).to_string(),
        "randint" => generator.randint(whole(0), whole(1)).to_string(),
        "choice" => generator.choice_place(whole(0) as usize).to_string(),
        "shuffle" => {
            let mut items: Vec<usize> = (0..whole(0) as usize).collect();
            generator.shuffle(&mut items);
            joined(items)
        }
        "uniform" => python_float(generator.uniform(arguments[0], arguments[1])),
        "choices" => joined(generator.choices_places(whole(0) as usize, None, whole(1) as usize)),
        "weighted" => joined(generator.choices_places(WEIGHTS.len(), Some(&WEIGHTS), whole(0) as usize)),
        "sample" => joined(generator.sample_places(whole(0) as usize, whole(1) as usize)),
        "gauss" => python_float(generator.gauss(arguments[0], arguments[1])),
        other => panic!("a call the cases name that the test does not know: {other}"),
    }
}

#[test]
fn every_call_draws_what_cpython_drew() {
    let mut checked = 0;
    for line in CASES.lines() {
        let fields: Vec<&str> = line.split('\t').collect();
        let [kind, seed, call, arguments, expected] = fields[..] else {
            panic!("a case of the wrong shape: {line}")
        };
        let arguments: Vec<f64> = arguments
            .split(',')
            .filter(|part| !part.is_empty())
            .map(|part| part.parse().expect("a number"))
            .collect();
        let mut generator = match kind {
            "whole" => PythonRandom::new(Seed::Whole(seed.parse().expect("a whole seed"))),
            _ => PythonRandom::new(Seed::Text(seed)),
        };
        let results: Vec<String> = (0..3).map(|_| drawn(&mut generator, call, &arguments)).collect();
        assert_eq!(results.join(";"), expected, "{kind} seed {seed:?}, {call}({arguments:?})");
        checked += 1;
    }
    assert!(checked > 100);
}
