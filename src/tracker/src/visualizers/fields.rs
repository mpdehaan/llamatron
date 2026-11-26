// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Fields: grids of whole numbers the visualizer's modes simulate, and the soft shapes they draw into them.
//!
//! The ripple is the classic demo-scene water: two height fields, each step making every cell half the sum of its four
//! neighbours less its value the step before, then damping it, so that waves spread, cross and bounce off the edges. A soft
//! disc is a kernel of weights falling from full at its middle to nothing at its rim, added into a field at a place and
//! clipped at the field's edges. A blur spreads a field into its neighbours, as colour bleeds in water. Whole numbers and
//! shifts keep the water exact and fast.

use super::picture::{Colour, Picture};

/// A disc's weight at its middle, and the shift that divides by it.
const FULL_WEIGHT: f64 = 256.0;
const WEIGHT_SHIFT: i32 = 8;

/// A grid of whole numbers, rows by columns, row by row.
#[derive(Clone, Debug, Default)]
pub struct Field {
    pub rows: usize,
    pub columns: usize,
    pub cells: Vec<i32>,
}

impl Field {
    pub fn zeros(rows: usize, columns: usize) -> Field {
        Field {
            rows,
            columns,
            cells: vec![0; rows * columns],
        }
    }

    /// The value at a place, the nearest edge's where the place is outside.
    pub fn at_edge(&self, row: i64, column: i64) -> i32 {
        let row = row.clamp(0, self.rows as i64 - 1) as usize;
        let column = column.clamp(0, self.columns as i64 - 1) as usize;
        self.cells[row * self.columns + column]
    }

    /// The value at a place, nothing outside the field.
    fn at_or_nothing(&self, row: i64, column: i64) -> i32 {
        if row < 0 || column < 0 || row >= self.rows as i64 || column >= self.columns as i64 {
            return 0;
        }
        self.cells[row as usize * self.columns + column as usize]
    }
}

/// The next height field from the current one and the one before, damped by a shift: each cell loses itself shifted right
/// by the damping shift.
pub fn ripple_step(current: &Field, previous: &Field, damping_shift: i32) -> Field {
    let mut following = Field::zeros(current.rows, current.columns);
    for row in 0..current.rows as i64 {
        for column in 0..current.columns as i64 {
            let neighbours = current.at_or_nothing(row - 1, column)
                + current.at_or_nothing(row + 1, column)
                + current.at_or_nothing(row, column - 1)
                + current.at_or_nothing(row, column + 1);
            let place = row as usize * current.columns + column as usize;
            let mut value = (neighbours >> 1) - previous.cells[place];
            value -= value >> damping_shift;
            following.cells[place] = value;
        }
    }
    following
}

/// The weights of a soft disc of a radius in cells, falling from FULL_WEIGHT at its middle to nothing at its rim, as rows
/// of a square two radii and one across.
fn disc_kernel(radius: usize) -> Vec<Vec<i32>> {
    let span = 2 * radius + 1;
    (0..span)
        .map(|down| {
            (0..span)
                .map(|across| {
                    let distance = ((down as f64 - radius as f64).powi(2) + (across as f64 - radius as f64).powi(2)).sqrt();
                    let falling = (1.0 - distance / (radius as f64 + 1.0)).clamp(0.0, 1.0);
                    (falling * falling * FULL_WEIGHT) as i32
                })
                .collect()
        })
        .collect()
}

/// The places a disc of a radius at a place covers inside a grid, each with its weight.
fn disc_places(rows: usize, columns: usize, row: i64, column: i64, radius: usize) -> Vec<(usize, i32)> {
    let kernel = disc_kernel(radius);
    let mut places = Vec::new();
    for (down, weights) in kernel.iter().enumerate() {
        let at_row = row - radius as i64 + down as i64;
        if at_row < 0 || at_row >= rows as i64 {
            continue;
        }
        for (across, weight) in weights.iter().enumerate() {
            let at_column = column - radius as i64 + across as i64;
            if at_column < 0 || at_column >= columns as i64 {
                continue;
            }
            places.push((at_row as usize * columns + at_column as usize, *weight));
        }
    }
    places
}

/// Add a soft disc into a field at a place, its middle adding amount, clipped at the field's edges.
pub fn add_disc(field: &mut Field, row: i64, column: i64, radius: usize, amount: i32) {
    for (place, weight) in disc_places(field.rows, field.columns, row, column, radius) {
        field.cells[place] += (weight * amount) >> WEIGHT_SHIFT;
    }
}

/// Add a soft disc of a colour into a picture used as a field of colour, its middle adding the colour's amounts.
pub fn add_colour_disc(picture: &mut Picture, row: i64, column: i64, radius: usize, amount: Colour) {
    for (place, weight) in disc_places(picture.rows, picture.columns, row, column, radius) {
        for channel in 0..3 {
            picture.cells[place][channel] += (weight * amount[channel]) >> WEIGHT_SHIFT;
        }
    }
}

/// A picture spread a little into its four neighbours: half of each cell kept and half shared from around it, the edges
/// repeating.
pub fn blurred(picture: &Picture) -> Picture {
    let (rows, columns) = (picture.rows as i64, picture.columns as i64);
    let at = |row: i64, column: i64| picture.get(row.clamp(0, rows - 1) as usize, column.clamp(0, columns - 1) as usize);
    let mut cells = Vec::with_capacity(picture.cells.len());
    for row in 0..rows {
        for column in 0..columns {
            let (here, up, down, left, right) = (
                at(row, column),
                at(row - 1, column),
                at(row + 1, column),
                at(row, column - 1),
                at(row, column + 1),
            );
            let mut colour = [0; 3];
            for channel in 0..3 {
                colour[channel] = (here[channel] * 4 + up[channel] + down[channel] + left[channel] + right[channel]) >> 3;
            }
            cells.push(colour);
        }
    }
    Picture {
        rows: picture.rows,
        columns: picture.columns,
        cells,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A splash in still water spreads out to its neighbours and dies away, never growing without bound.
    #[test]
    fn a_splash_spreads_and_dies_away() {
        let (rows, columns) = (21, 21);
        let mut water = Field::zeros(rows, columns);
        let mut before = Field::zeros(rows, columns);
        let (middle, radius, depth, damping) = (10, 2, 2000, 5);
        add_disc(&mut water, middle, middle, radius, depth);
        let mut largest_late = 0;
        for step in 0..400 {
            let next = ripple_step(&water, &before, damping);
            before = std::mem::replace(&mut water, next);
            if step > 300 {
                largest_late = largest_late.max(water.cells.iter().map(|value| value.abs()).max().unwrap_or(0));
            }
        }
        assert!(largest_late < depth / 10, "{largest_late}");
    }
}
