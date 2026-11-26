// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Every text llamatron shows or raises, in `texts/`, a module for each way a text is used, and `fill`, which fills a
//! text's blanks by name.

pub mod fill;
pub mod plugin_texts;
pub mod texts;

pub use fill::{fill, named, Value};
pub use texts::*;
