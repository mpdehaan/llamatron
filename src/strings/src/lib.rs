// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Every text llamatron shows or raises (the Python `user_strings/`), generated character for character from the Python
//! modules by internal_tools/strings_to_rust.py into `texts/`, and `fill`, which fills a text's template as Python's
//! str.format does.

pub mod fill;
pub mod plugin_texts;
pub mod texts;

pub use fill::{fill, named, Value};
pub use texts::*;
