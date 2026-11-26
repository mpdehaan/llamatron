// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! llamatron's exact arithmetic and random sources, the bottom layer every other crate stands on (the Python `math/`):
//! rationals for lengths and times, Python's mixed numbers, and CPython's random numbers, drawn exactly as the Python program drew them.

pub mod number;
pub mod python_random;
pub mod rational;
pub mod sha512;

pub use number::Number;
pub use python_random::{PythonRandom, Seed};
pub use rational::Rational;
