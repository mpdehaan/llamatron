// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Exact numbers for lengths and times: a numerator over a denominator, so that three triplets make exactly a quarter (the
//! Python `math/rational.py`). Always in lowest terms with a positive denominator, so that equal values are equal fields.
//!
//! The parts are 128-bit, since a float read exactly, as Python's Fraction reads one, has a denominator of up to 2^1074 in
//! principle and 2^52 or so in practice, and a product of two such needs room; every result is reduced at once.

use std::cmp::Ordering;
use std::fmt;
use std::ops::{Add, Div, Mul, Neg, Sub};

/// Why a text is not a number.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NotANumber(pub String);

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct Rational {
    numerator: i128,
    denominator: i128,
}

fn gcd(first: i128, second: i128) -> i128 {
    let (mut first, mut second) = (first.abs(), second.abs());
    while second != 0 {
        (first, second) = (second, first % second);
    }
    first
}

impl Rational {
    pub const ZERO: Rational = Rational { numerator: 0, denominator: 1 };
    pub const ONE: Rational = Rational { numerator: 1, denominator: 1 };

    /// A numerator over a denominator, which must not be zero.
    pub fn new(numerator: i128, denominator: i128) -> Rational {
        assert!(denominator != 0, "a rational's denominator cannot be zero");
        let sign = if denominator < 0 { -1 } else { 1 };
        let divisor = gcd(numerator, denominator).max(1);
        Rational {
            numerator: sign * numerator / divisor,
            denominator: sign * denominator / divisor,
        }
    }

    pub fn whole(value: i128) -> Rational {
        Rational {
            numerator: value,
            denominator: 1,
        }
    }

    pub fn numerator(&self) -> i128 {
        self.numerator
    }

    pub fn denominator(&self) -> i128 {
        self.denominator
    }

    pub fn is_whole(&self) -> bool {
        self.denominator == 1
    }

    /// A float exactly, as Python's Fraction reads one: its mantissa over a power of two.
    pub fn from_float(value: f64) -> Rational {
        assert!(value.is_finite(), "only a finite float is a rational");
        if value == 0.0 {
            return Rational::ZERO;
        }
        let bits = value.to_bits();
        let negative = bits >> 63 == 1;
        let exponent = ((bits >> 52) & 0x7FF) as i32;
        let fraction = (bits & ((1 << 52) - 1)) as i128;
        let (mantissa, power) = if exponent == 0 {
            (fraction, -1074)
        } else {
            (fraction | (1 << 52), exponent - 1075)
        };
        let signed = if negative { -mantissa } else { mantissa };
        if power >= 0 {
            return Rational::whole(signed << power);
        }
        // Reduce the power of two first, so that the denominator stays within 128 bits for every float llamatron meets.
        let mut numerator = signed;
        let mut shift = -power;
        while shift > 0 && numerator % 2 == 0 {
            numerator /= 2;
            shift -= 1;
        }
        assert!(shift < 127, "a float this small has no 128-bit rational");
        Rational::new(numerator, 1i128 << shift)
    }

    pub fn to_float(&self) -> f64 {
        self.numerator as f64 / self.denominator as f64
    }

    /// The largest whole number not above it.
    pub fn floor(&self) -> i128 {
        self.numerator.div_euclid(self.denominator)
    }

    /// The smallest whole number not below it.
    pub fn ceil(&self) -> i128 {
        -(-self.numerator).div_euclid(self.denominator)
    }

    /// The nearest whole number, a half going to the even neighbour, as Python's round() does.
    pub fn round(&self) -> i128 {
        let whole = self.floor();
        let remainder = self.numerator - whole * self.denominator;
        match (remainder * 2).cmp(&self.denominator) {
            Ordering::Less => whole,
            Ordering::Greater => whole + 1,
            Ordering::Equal if whole % 2 == 0 => whole,
            Ordering::Equal => whole + 1,
        }
    }

    pub fn abs(&self) -> Rational {
        Rational {
            numerator: self.numerator.abs(),
            denominator: self.denominator,
        }
    }

    /// The closest rational whose denominator is at most most, as Python's Fraction.limit_denominator finds it.
    pub fn limit_denominator(&self, most: i128) -> Rational {
        if self.denominator <= most {
            return *self;
        }
        let (mut p0, mut q0, mut p1, mut q1) = (0i128, 1i128, 1i128, 0i128);
        let (mut n, mut d) = (self.numerator, self.denominator);
        loop {
            let a = n.div_euclid(d);
            let q2 = q0 + a * q1;
            if q2 > most {
                break;
            }
            (p0, q0, p1, q1) = (p1, q1, p0 + a * p1, q2);
            (n, d) = (d, n - a * d);
        }
        let k = (most - q0).div_euclid(q1);
        let bound1 = Rational::new(p0 + k * p1, q0 + k * q1);
        let bound2 = Rational::new(p1, q1);
        if (bound2 - *self).abs() <= (bound1 - *self).abs() {
            bound2
        } else {
            bound1
        }
    }

    /// Read a written number as Python's Fraction reads text: a whole number, `5/16`, or a decimal such as `0.25` or `1e-3`.
    pub fn parse(text: &str) -> Result<Rational, NotANumber> {
        let trimmed = text.trim();
        let refused = || NotANumber(text.to_string());
        if let Some((top, bottom)) = trimmed.split_once('/') {
            let numerator: i128 = top.trim().parse().map_err(|_| refused())?;
            let denominator: i128 = bottom.trim().parse().map_err(|_| refused())?;
            if denominator == 0 {
                return Err(refused());
            }
            return Ok(Rational::new(numerator, denominator));
        }
        let (mantissa, exponent) = match trimmed.find(['e', 'E']) {
            Some(place) => (&trimmed[..place], trimmed[place + 1..].parse::<i32>().map_err(|_| refused())?),
            None => (trimmed, 0),
        };
        let (sign, digits) = match mantissa.strip_prefix('-') {
            Some(rest) => (-1, rest),
            None => (1, mantissa.strip_prefix('+').unwrap_or(mantissa)),
        };
        let (whole, fraction) = digits.split_once('.').unwrap_or((digits, ""));
        let joined = format!("{whole}{fraction}");
        if joined.is_empty() || !joined.chars().all(|digit| digit.is_ascii_digit() || digit == '_') {
            return Err(refused());
        }
        let numerator: i128 = joined.replace('_', "").parse().map_err(|_| refused())?;
        let power = exponent - fraction.len() as i32;
        let value = if power >= 0 {
            Rational::whole(numerator * 10i128.pow(power as u32))
        } else {
            Rational::new(numerator, 10i128.pow((-power) as u32))
        };
        Ok(Rational::whole(sign) * value)
    }
}

impl Default for Rational {
    fn default() -> Rational {
        Rational::ZERO
    }
}

impl fmt::Display for Rational {
    /// The way a song file writes a length: a whole number, or 5/16.
    fn fmt(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        if self.denominator == 1 {
            write!(formatter, "{}", self.numerator)
        } else {
            write!(formatter, "{}/{}", self.numerator, self.denominator)
        }
    }
}

impl Add for Rational {
    type Output = Rational;
    fn add(self, other: Rational) -> Rational {
        if self.denominator == other.denominator {
            return Rational::new(self.numerator + other.numerator, self.denominator);
        }
        Rational::new(
            self.numerator * other.denominator + other.numerator * self.denominator,
            self.denominator * other.denominator,
        )
    }
}

impl Sub for Rational {
    type Output = Rational;
    fn sub(self, other: Rational) -> Rational {
        self + -other
    }
}

impl Mul for Rational {
    type Output = Rational;
    fn mul(self, other: Rational) -> Rational {
        // Cross-reducing first keeps the parts small, as two lengths multiplied often share a factor.
        let first = gcd(self.numerator, other.denominator).max(1);
        let second = gcd(other.numerator, self.denominator).max(1);
        Rational::new(
            (self.numerator / first) * (other.numerator / second),
            (self.denominator / second) * (other.denominator / first),
        )
    }
}

impl Div for Rational {
    type Output = Rational;
    fn div(self, other: Rational) -> Rational {
        assert!(other.numerator != 0, "division by zero");
        self * Rational::new(other.denominator, other.numerator)
    }
}

impl Neg for Rational {
    type Output = Rational;
    fn neg(self) -> Rational {
        Rational {
            numerator: -self.numerator,
            denominator: self.denominator,
        }
    }
}

impl PartialOrd for Rational {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for Rational {
    fn cmp(&self, other: &Self) -> Ordering {
        (self.numerator * other.denominator).cmp(&(other.numerator * self.denominator))
    }
}

impl From<i128> for Rational {
    fn from(value: i128) -> Rational {
        Rational::whole(value)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn three_triplets_make_a_quarter_and_halves_round_to_even() {
        let triplet = Rational::new(1, 12);
        assert_eq!(triplet + triplet + triplet, Rational::new(1, 4));
        assert_eq!(Rational::new(5, 2).round(), 2);
        assert_eq!(Rational::new(7, 2).round(), 4);
        assert_eq!(Rational::new(-5, 2).round(), -2);
        assert_eq!(Rational::new(-7, 3).floor(), -3);
    }

    #[test]
    fn text_and_floats_read_as_pythons_fraction_reads_them() {
        assert_eq!(Rational::parse("5/16"), Ok(Rational::new(5, 16)));
        assert_eq!(Rational::parse("-0.25"), Ok(Rational::new(-1, 4)));
        assert_eq!(Rational::parse("1e-3"), Ok(Rational::new(1, 1000)));
        assert_eq!(Rational::from_float(0.1), Rational::new(3602879701896397, 36028797018963968));
        assert_eq!(Rational::from_float(0.1).limit_denominator(1000), Rational::new(1, 10));
        assert_eq!(Rational::new(5, 16).to_string(), "5/16");
    }
}
