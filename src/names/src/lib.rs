// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Every name llamatron uses as a value, each defined once: the set file's keys and values (`file_format`). It uses
//! no other crate, so that every crate, the strings and the backend included, reads its names here, and a name typed
//! wrong is a name the compiler does not know.

#[rustfmt::skip]
pub mod file_format;
