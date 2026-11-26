// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A number as the Python program holds one: a whole number, an exact rational, or a float, mixed by Python's rules, so
//! that llamatron rounds exactly where llamatron rounded and its exports come out byte for byte the same.
//!
//! Python's rules, which this keeps: whole numbers stay whole under +, - and *, and give a float under / (true division);
//! a rational with a whole number or a rational stays exact; anything with a float gives a float. Comparison is exact
//! across the kinds, as Python compares an int, a Fraction and a float by their exact values. Text is written as Python's
//! str() writes each kind: `3`, `5/16`, `0.25`.

use crate::rational::Rational;
use std::cmp::Ordering;
use std::fmt;
use std::hash::{Hash, Hasher};
use std::ops::{Add, Div, Mul, Neg, Sub};

#[derive(Clone, Copy, Debug)]
pub enum Number {
    Whole(i128),
    Exact(Rational),
    Float(f64),
}

impl Number {
    /// The number as a float, as Python's float() gives it.
    pub fn to_float(&self) -> f64 {
        match self {
            Number::Whole(whole) => *whole as f64,
            Number::Exact(rational) => rational.to_float(),
            Number::Float(float) => *float,
        }
    }

    /// The number exactly, a float read as Python's Fraction reads one.
    pub fn to_rational(&self) -> Rational {
        match self {
            Number::Whole(whole) => Rational::whole(*whole),
            Number::Exact(rational) => *rational,
            Number::Float(float) => Rational::from_float(*float),
        }
    }

    pub fn is_float(&self) -> bool {
        matches!(self, Number::Float(_))
    }

    pub fn is_finite(&self) -> bool {
        !matches!(self, Number::Float(float) if !float.is_finite())
    }

    /// Floor division, //, as Python divides each kind.
    pub fn floor_div(self, other: Number) -> Number {
        match (self, other) {
            (Number::Whole(first), Number::Whole(second)) => Number::Whole(floor_divided(first, second)),
            (Number::Float(_), _) | (_, Number::Float(_)) => Number::Float((self.to_float() / other.to_float()).floor()),
            _ => Number::Whole((self.to_rational() / other.to_rational()).floor()),
        }
    }

    /// The nearest whole number, a half to the even neighbour, as round() gives it.
    pub fn round(&self) -> i128 {
        match self {
            Number::Whole(whole) => *whole,
            Number::Exact(rational) => rational.round(),
            Number::Float(float) => {
                let rounded = float.round();
                // Rust rounds halves away from zero; Python to the even neighbour.
                if (float - float.trunc()).abs() == 0.5 && rounded % 2.0 != 0.0 {
                    (rounded - float.signum()) as i128
                } else {
                    rounded as i128
                }
            }
        }
    }

    pub fn floor(&self) -> i128 {
        match self {
            Number::Whole(whole) => *whole,
            Number::Exact(rational) => rational.floor(),
            Number::Float(float) => float.floor() as i128,
        }
    }

    pub fn abs(&self) -> Number {
        match self {
            Number::Whole(whole) => Number::Whole(whole.abs()),
            Number::Exact(rational) => Number::Exact(rational.abs()),
            Number::Float(float) => Number::Float(float.abs()),
        }
    }

    /// A rational result kept as a whole number where Python's Fraction arithmetic would have given a Fraction: exact stays
    /// exact, even when whole, so that 1/2 + 1/2 is Rational 1, written `1`, as Python writes Fraction(1).
    fn exact(rational: Rational) -> Number {
        Number::Exact(rational)
    }

    fn mixed(self, other: Number, whole: fn(i128, i128) -> i128, exact: fn(Rational, Rational) -> Rational, float: fn(f64, f64) -> f64) -> Number {
        match (self, other) {
            (Number::Whole(first), Number::Whole(second)) => Number::Whole(whole(first, second)),
            (Number::Float(_), _) | (_, Number::Float(_)) => Number::Float(float(self.to_float(), other.to_float())),
            _ => Number::exact(exact(self.to_rational(), other.to_rational())),
        }
    }
}

impl From<i128> for Number {
    fn from(whole: i128) -> Number {
        Number::Whole(whole)
    }
}

impl From<i64> for Number {
    fn from(whole: i64) -> Number {
        Number::Whole(whole as i128)
    }
}

impl From<f64> for Number {
    fn from(float: f64) -> Number {
        Number::Float(float)
    }
}

impl From<Rational> for Number {
    fn from(rational: Rational) -> Number {
        Number::Exact(rational)
    }
}

impl Add for Number {
    type Output = Number;
    fn add(self, other: Number) -> Number {
        self.mixed(
            other,
            |first, second| first + second,
            |first, second| first + second,
            |first, second| first + second,
        )
    }
}

impl Sub for Number {
    type Output = Number;
    fn sub(self, other: Number) -> Number {
        self.mixed(
            other,
            |first, second| first - second,
            |first, second| first - second,
            |first, second| first - second,
        )
    }
}

impl Mul for Number {
    type Output = Number;
    fn mul(self, other: Number) -> Number {
        self.mixed(
            other,
            |first, second| first * second,
            |first, second| first * second,
            |first, second| first * second,
        )
    }
}

impl Div for Number {
    type Output = Number;
    /// True division: two whole numbers give a float, as in Python.
    fn div(self, other: Number) -> Number {
        match (self, other) {
            (Number::Whole(first), Number::Whole(second)) => Number::Float(true_divided(first, second)),
            (Number::Float(_), _) | (_, Number::Float(_)) => Number::Float(self.to_float() / other.to_float()),
            _ => Number::exact(self.to_rational() / other.to_rational()),
        }
    }
}

/// Two whole numbers divided as Python divides them, correctly rounded where both are within a float's exact range.
fn true_divided(first: i128, second: i128) -> f64 {
    first as f64 / second as f64
}

impl Neg for Number {
    type Output = Number;
    fn neg(self) -> Number {
        match self {
            Number::Whole(whole) => Number::Whole(-whole),
            Number::Exact(rational) => Number::Exact(-rational),
            Number::Float(float) => Number::Float(-float),
        }
    }
}

impl PartialEq for Number {
    fn eq(&self, other: &Number) -> bool {
        self.partial_cmp(other) == Some(Ordering::Equal)
    }
}

impl PartialOrd for Number {
    /// Exact across the kinds, as Python compares them; a float that is not a number compares with nothing.
    fn partial_cmp(&self, other: &Number) -> Option<Ordering> {
        if !self.is_finite() || !other.is_finite() {
            return self.to_float().partial_cmp(&other.to_float());
        }
        match (self, other) {
            (Number::Whole(first), Number::Whole(second)) => Some(first.cmp(second)),
            (Number::Float(first), Number::Float(second)) => first.partial_cmp(second),
            _ => Some(self.to_rational().cmp(&other.to_rational())),
        }
    }
}

impl Hash for Number {
    /// Equal numbers hash alike whatever their kinds, as in Python.
    fn hash<H: Hasher>(&self, state: &mut H) {
        if self.is_finite() {
            self.to_rational().hash(state);
        } else {
            self.to_float().to_bits().hash(state);
        }
    }
}

impl fmt::Display for Number {
    /// As Python's str() writes it: `3`, `5/16`, `0.25`.
    fn fmt(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Number::Whole(whole) => write!(formatter, "{whole}"),
            Number::Exact(rational) => write!(formatter, "{rational}"),
            Number::Float(float) => write!(formatter, "{}", python_float_text(*float)),
        }
    }
}

/// A division rounded toward minus infinity, as Python's // rounds, whatever the signs.
pub fn floor_divided(numerator: i128, denominator: i128) -> i128 {
    let quotient = numerator / denominator;
    if numerator % denominator != 0 && (numerator < 0) != (denominator < 0) {
        quotient - 1
    } else {
        quotient
    }
}

/// A float as Python's str() writes it.
pub fn python_float_text(value: f64) -> String {
    if value.is_nan() {
        return "nan".to_string();
    }
    if value.is_infinite() {
        return if value > 0.0 { "inf" } else { "-inf" }.to_string();
    }
    let size = value.abs();
    if size != 0.0 && !(1e-4..1e16).contains(&size) {
        let text = format!("{value:e}");
        let (mantissa, exponent) = text.split_once('e').unwrap_or((&text, "0"));
        let exponent: i32 = exponent.parse().unwrap_or(0);
        let sign = if exponent < 0 { '-' } else { '+' };
        return format!("{mantissa}e{sign}{:02}", exponent.abs());
    }
    let text = format!("{value:?}");
    if text.contains('.') {
        text
    } else {
        format!("{text}.0")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn numbers_mix_as_python_mixes_them() {
        let three = Number::Whole(3);
        let quarter = Number::Exact(Rational::new(1, 4));
        assert!(matches!(three / Number::Whole(2), Number::Float(value) if value == 1.5));
        assert!(matches!(three * quarter, Number::Exact(value) if value == Rational::new(3, 4)));
        assert!(matches!(quarter + Number::Float(0.5), Number::Float(value) if value == 0.75));
        assert_eq!(Number::Float(0.25), quarter);
        assert_eq!((Number::Whole(-7)).floor_div(Number::Whole(2)), Number::Whole(-4));
        assert_eq!(floor_divided(-32, -3), 10);
        assert_eq!(floor_divided(7, -2), -4);
        assert_eq!(Number::Float(2.5).round(), 2);
        assert_eq!(Number::Float(-3.5).round(), -4);
        assert_eq!(quarter.to_string(), "1/4");
        assert_eq!(Number::Float(0.25).to_string(), "0.25");
    }
}
