// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! CPython's `random.Random`, number for number: the Mersenne Twister its C module keeps, its two ways of seeding (a whole
//! number's 32-bit words, or a text's bytes with their SHA-512 digest, read as one big whole number), and the exact
//! algorithm of each call llamatron's generators make (random, getrandbits, randrange, randint, choice, shuffle, uniform,
//! choices, sample, gauss), so that a seeded render here draws the very numbers the Python program drew.

use crate::sha512::sha512;
use std::f64::consts::PI;

const SIZE: usize = 624;
const SHIFT: usize = 397;
const MATRIX: u32 = 0x9908_b0df;
const UPPER: u32 = 0x8000_0000;
const LOWER: u32 = 0x7fff_ffff;
const SEED_START: u32 = 19_650_218;
/// The size of the set sample switches to past, as CPython's sample chooses between its two ways.
const SAMPLE_SET_SIZE: usize = 21;

/// A seed as Python takes one.
pub enum Seed<'a> {
    Whole(i128),
    Text(&'a str),
}

pub struct PythonRandom {
    state: [u32; SIZE],
    place: usize,
    gauss_next: Option<f64>,
}

impl PythonRandom {
    /// A generator seeded as `random.Random(seed)` seeds one.
    pub fn new(seed: Seed) -> PythonRandom {
        let key = match seed {
            Seed::Whole(value) => words_of_whole(value.unsigned_abs()),
            Seed::Text(text) => {
                let mut bytes = text.as_bytes().to_vec();
                bytes.extend_from_slice(&sha512(text.as_bytes()));
                words_of_big_endian(&bytes)
            }
        };
        let mut generator = PythonRandom {
            state: [0; SIZE],
            place: SIZE,
            gauss_next: None,
        };
        generator.seed_by_array(&key);
        generator
    }

    /// A generator seeded from the clock, as Python's own module is when the program starts, for a render with no seed.
    pub fn unseeded() -> PythonRandom {
        let nanoseconds = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|since| since.as_nanos())
            .unwrap_or(0);
        PythonRandom::new(Seed::Whole((nanoseconds ^ (std::process::id() as u128) << 64) as i128))
    }

    fn seed_whole(&mut self, value: u32) {
        self.state[0] = value;
        for place in 1..SIZE {
            let previous = self.state[place - 1];
            self.state[place] = 1_812_433_253u32.wrapping_mul(previous ^ (previous >> 30)).wrapping_add(place as u32);
        }
        self.place = SIZE;
    }

    fn seed_by_array(&mut self, key: &[u32]) {
        self.seed_whole(SEED_START);
        let (mut i, mut j) = (1usize, 0usize);
        for _ in 0..SIZE.max(key.len()) {
            let previous = self.state[i - 1];
            self.state[i] = (self.state[i] ^ (previous ^ (previous >> 30)).wrapping_mul(1_664_525))
                .wrapping_add(key[j])
                .wrapping_add(j as u32);
            i += 1;
            j += 1;
            if i >= SIZE {
                self.state[0] = self.state[SIZE - 1];
                i = 1;
            }
            if j >= key.len() {
                j = 0;
            }
        }
        for _ in 0..SIZE - 1 {
            let previous = self.state[i - 1];
            self.state[i] = (self.state[i] ^ (previous ^ (previous >> 30)).wrapping_mul(1_566_083_941)).wrapping_sub(i as u32);
            i += 1;
            if i >= SIZE {
                self.state[0] = self.state[SIZE - 1];
                i = 1;
            }
        }
        self.state[0] = UPPER;
    }

    fn twist(&mut self) {
        for place in 0..SIZE {
            let mixed = (self.state[place] & UPPER) | (self.state[(place + 1) % SIZE] & LOWER);
            let mut next = self.state[(place + SHIFT) % SIZE] ^ (mixed >> 1);
            if mixed & 1 == 1 {
                next ^= MATRIX;
            }
            self.state[place] = next;
        }
        self.place = 0;
    }

    /// The next 32 bits, tempered.
    fn next_word(&mut self) -> u32 {
        if self.place >= SIZE {
            self.twist();
        }
        let mut value = self.state[self.place];
        self.place += 1;
        value ^= value >> 11;
        value ^= (value << 7) & 0x9d2c_5680;
        value ^= (value << 15) & 0xefc6_0000;
        value ^ (value >> 18)
    }

    /// A float from 0 up to 1, of 53 random bits.
    pub fn random(&mut self) -> f64 {
        let high = (self.next_word() >> 5) as f64;
        let low = (self.next_word() >> 6) as f64;
        (high * 67_108_864.0 + low) * (1.0 / 9_007_199_254_740_992.0)
    }

    /// A whole number of some random bits, at most 128.
    pub fn getrandbits(&mut self, bits: u32) -> u128 {
        if bits == 0 {
            return 0;
        }
        if bits <= 32 {
            return (self.next_word() >> (32 - bits)) as u128;
        }
        let mut value = 0u128;
        let mut left = bits;
        let mut shift = 0;
        while left > 0 {
            let mut word = self.next_word();
            if left < 32 {
                word >>= 32 - left;
            }
            value |= (word as u128) << shift;
            shift += 32;
            left = left.saturating_sub(32);
        }
        value
    }

    /// A whole number from 0 up to below a bound, by drawing just enough bits and drawing again past the bound.
    pub fn randbelow(&mut self, bound: u128) -> u128 {
        let bits = 128 - bound.leading_zeros();
        let mut drawn = self.getrandbits(bits);
        while drawn >= bound {
            drawn = self.getrandbits(bits);
        }
        drawn
    }

    /// `randrange(start, stop, step)`, which must have something in its range.
    pub fn randrange(&mut self, start: i128, stop: i128, step: i128) -> i128 {
        assert!(step != 0, "randrange's step cannot be zero");
        let width = stop - start;
        if step == 1 {
            assert!(width > 0, "randrange's range is empty");
            return start + self.randbelow(width as u128) as i128;
        }
        let count = if step > 0 {
            floor_divided(width + step - 1, step)
        } else {
            floor_divided(width + step + 1, step)
        };
        assert!(count > 0, "randrange's range is empty");
        start + step * self.randbelow(count as u128) as i128
    }

    /// `randrange(stop)`.
    pub fn randrange_to(&mut self, stop: i128) -> i128 {
        assert!(stop > 0, "randrange's range is empty");
        self.randbelow(stop as u128) as i128
    }

    /// A whole number from low to high, both included.
    pub fn randint(&mut self, low: i128, high: i128) -> i128 {
        self.randrange(low, high + 1, 1)
    }

    /// The place of one item chosen from a sequence of a length, as `choice` picks it.
    pub fn choice_place(&mut self, length: usize) -> usize {
        assert!(length > 0, "cannot choose from an empty sequence");
        self.randbelow(length as u128) as usize
    }

    /// One item chosen from a slice.
    pub fn choice<'a, T>(&mut self, items: &'a [T]) -> &'a T {
        &items[self.choice_place(items.len())]
    }

    /// Shuffle a slice in place, from its end, as Python does.
    pub fn shuffle<T>(&mut self, items: &mut [T]) {
        for place in (1..items.len()).rev() {
            let other = self.randbelow(place as u128 + 1) as usize;
            items.swap(place, other);
        }
    }

    /// A float between two bounds.
    pub fn uniform(&mut self, low: f64, high: f64) -> f64 {
        low + (high - low) * self.random()
    }

    /// The places of k items chosen with replacement, by weight where weights are given, as `choices` picks them.
    pub fn choices_places(&mut self, length: usize, weights: Option<&[f64]>, k: usize) -> Vec<usize> {
        match weights {
            None => (0..k).map(|_| (self.random() * length as f64).floor() as usize).collect(),
            Some(weights) => {
                let mut cumulative = Vec::with_capacity(weights.len());
                let mut total = 0.0;
                for weight in weights {
                    total += weight;
                    cumulative.push(total);
                }
                let total = total + 0.0;
                assert!(total > 0.0, "the weights must add up to more than zero");
                let highest = length.saturating_sub(1);
                (0..k)
                    .map(|_| {
                        let drawn = self.random() * total;
                        // bisect_right over cumulative[..highest]
                        cumulative[..highest].partition_point(|sum| *sum <= drawn)
                    })
                    .collect()
            }
        }
    }

    /// The places of k items chosen without replacement from a population, as `sample` picks them.
    pub fn sample_places(&mut self, length: usize, k: usize) -> Vec<usize> {
        assert!(k <= length, "a sample cannot be larger than its population");
        let mut set_size = SAMPLE_SET_SIZE;
        if k > 5 {
            let exponent = ((3.0 * k as f64).ln() / 4f64.ln()).ceil() as u32;
            set_size += 4usize.pow(exponent);
        }
        let mut chosen = Vec::with_capacity(k);
        if length <= set_size {
            let mut pool: Vec<usize> = (0..length).collect();
            for place in 0..k {
                let picked = self.randbelow((length - place) as u128) as usize;
                chosen.push(pool[picked]);
                pool[picked] = pool[length - place - 1];
            }
        } else {
            let mut taken = std::collections::HashSet::new();
            for _ in 0..k {
                let mut picked = self.randbelow(length as u128) as usize;
                while taken.contains(&picked) {
                    picked = self.randbelow(length as u128) as usize;
                }
                taken.insert(picked);
                chosen.push(picked);
            }
        }
        chosen
    }

    /// A normal draw of a mean and spread, two at a time, as `gauss` makes them.
    pub fn gauss(&mut self, mean: f64, spread: f64) -> f64 {
        let drawn = match self.gauss_next.take() {
            Some(kept) => kept,
            None => {
                let angle = self.random() * 2.0 * PI;
                let radius = (-2.0 * (1.0 - self.random()).ln()).sqrt();
                self.gauss_next = Some(angle.sin() * radius);
                angle.cos() * radius
            }
        };
        mean + drawn * spread
    }
}

/// A division rounded toward minus infinity, as Python's // rounds, whatever the signs.
fn floor_divided(numerator: i128, denominator: i128) -> i128 {
    let quotient = numerator / denominator;
    if (numerator % denominator != 0) && ((numerator < 0) != (denominator < 0)) {
        quotient - 1
    } else {
        quotient
    }
}

/// A whole number's 32-bit words, least significant first, as CPython hands a seed to the twister; zero is one word.
fn words_of_whole(value: u128) -> Vec<u32> {
    let mut words = Vec::new();
    let mut left = value;
    while left > 0 {
        words.push(left as u32);
        left >>= 32;
    }
    if words.is_empty() {
        words.push(0);
    }
    words
}

/// The 32-bit words, least significant first, of a whole number written as big-endian bytes, the top word dropped where it
/// is zero, as CPython reads an integer made from bytes.
fn words_of_big_endian(bytes: &[u8]) -> Vec<u32> {
    let mut words: Vec<u32> = bytes
        .rchunks(4)
        .map(|chunk| {
            let mut word = [0u8; 4];
            word[4 - chunk.len()..].copy_from_slice(chunk);
            u32::from_be_bytes(word)
        })
        .collect();
    while words.len() > 1 && words.last() == Some(&0) {
        words.pop();
    }
    words
}

#[cfg(test)]
mod tests {
    use super::*;

    // Every expected value here was printed by CPython: random.Random(seed) and its calls.
    #[test]
    fn a_whole_seed_draws_pythons_numbers() {
        let mut generator = PythonRandom::new(Seed::Whole(42));
        assert_eq!(generator.random(), 0.6394267984578837);
        assert_eq!(generator.random(), 0.025010755222666936);
    }
}
