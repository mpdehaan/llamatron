// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The rotozoom: a picture sampled through a turn and a zoom about its middle, shared by every mode that moves its view.
//! Each output cell takes the nearest cell it lands on, and the averaging down to big pixels after it smooths the steps; a
//! zoom above one keeps the turned picture's corners inside it, so no empty edge shows.

use super::picture::Picture;

/// A picture turned by an angle in radians and zoomed by a factor about its middle, the same size.
pub fn rotozoomed(picture: &Picture, angle: f64, zoom: f64) -> Picture {
    let (rows, columns) = (picture.rows, picture.columns);
    let middle_row = (rows as f64 - 1.0) / 2.0;
    let middle_column = (columns as f64 - 1.0) / 2.0;
    let cosine = angle.cos() / zoom;
    let sine = angle.sin() / zoom;
    let mut cells = Vec::with_capacity(picture.cells.len());
    for row in 0..rows {
        let down = row as f64 - middle_row;
        for column in 0..columns {
            let across = column as f64 - middle_column;
            let source_row = (down * cosine - across * sine + middle_row).round().clamp(0.0, rows as f64 - 1.0) as usize;
            let source_column = (down * sine + across * cosine + middle_column).round().clamp(0.0, columns as f64 - 1.0) as usize;
            cells.push(picture.get(source_row, source_column));
        }
    }
    Picture { rows, columns, cells }
}
