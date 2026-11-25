// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Reading the tracker's MessagePack values: a patch spec is a mapping of names, as the tracker's `built_in_sound.py`
//! writes it, read here with a default for anything left out, so that an older or newer tracker never crashes the daemon.

use rmpv::Value;

/// A setting of a mapping by name, or None.
pub fn field<'a>(value: &'a Value, name: &str) -> Option<&'a Value> {
    value.as_map()?.iter().find(|(key, _)| key.as_str() == Some(name)).map(|(_, found)| found)
}

/// A number of a mapping by name, or the default where it is missing or not a number.
pub fn number(value: &Value, name: &str, default: f64) -> f64 {
    field(value, name).and_then(as_number).unwrap_or(default)
}

/// A value as a number, an integer or a float.
pub fn as_number(value: &Value) -> Option<f64> {
    value
        .as_f64()
        .or_else(|| value.as_i64().map(|whole| whole as f64))
        .or_else(|| value.as_u64().map(|whole| whole as f64))
}

/// A word of a mapping by name, or the default.
pub fn word<'a>(value: &'a Value, name: &str, default: &'a str) -> &'a str {
    field(value, name).and_then(Value::as_str).unwrap_or(default)
}

/// A truth of a mapping by name, or the default.
pub fn truth(value: &Value, name: &str, default: bool) -> bool {
    field(value, name).and_then(Value::as_bool).unwrap_or(default)
}

/// A list of a mapping by name, or an empty one.
pub fn list<'a>(value: &'a Value, name: &str) -> &'a [Value] {
    field(value, name).and_then(Value::as_array).map(Vec::as_slice).unwrap_or(&[])
}

/// A list of numbers of a mapping by name.
pub fn numbers(value: &Value, name: &str) -> Vec<f64> {
    list(value, name).iter().filter_map(as_number).collect()
}
