// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A sample of Rust for the tests of the check of named values: each line the check must report ends with the comment
//! `flagged`, and every other line must pass. It breaks the rule on purpose, so it lives outside `src/`.

/// A constant names its value, and every line of a constant's table does too.
const PREVIEW_CHANNEL: i64 = 15;
const NAMED: [(&str, usize); 2] = [
    (words::BLACK, 0),
    (words::RED, 7),
];

fn sample(amount: f64, values: &[f64]) {
    let second = asheville("osc2_pitch", amount); // flagged
    run(cutoff, 48000); // flagged
    let first = values[0] + 1.0;
    let shown_rows = 7;
    let (resonance, drive) = (0.3, 0.5);
    let abc: &[u8] = b"abc";
    assert!(moved, "the A gauge moves Slow"); // 48 kHz
}
