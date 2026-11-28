// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Filling a text's template as Python's str.format fills it, so that llamatron shows every message character for
//! character as llamatron does: `{name}` and `{}` fields, `!r` for a value's repr, and the format specifications the texts
//! use: a fill character and alignment (`<`, `>`, `^`) with a width that may itself be a field (`{name:<{width}}`), a `+`
//! sign, zero padding (`02`), `d`, and a float's places (`.1f`); `{{` and `}}` for braces.

use llamatron_names::words;
use std::fmt::Write;

/// The sizes Python writes a float plainly between, writing the rest with an exponent.
const SMALLEST_PLAIN: f64 = 1e-4;
const LARGEST_PLAIN: f64 = 1e16;
/// A repr's two quotes; the first printable character, a space, and the delete character, which a repr writes as
/// escapes; and the room a filled template is given beyond its own length.
const QUOTES: usize = 2;
const FIRST_PRINTABLE: u32 = 0x20;
const DELETE: u32 = 0x7F;
const ROOM_FOR_VALUES: usize = 16;
/// A format spec's fill character and alignment, two characters; and the halves a centred value's padding falls into.
const FILL_AND_ALIGN: usize = 2;
const HALVES: usize = 2;

/// A value a template is filled with.
#[derive(Clone, Debug, PartialEq)]
pub enum Value {
    Text(String),
    Whole(i64),
    Float(f64),
    /// A value of another kind, written as str() and repr() write it, such as a list or None.
    Shown {
        shown: String,
        repr: String,
    },
}

impl From<&str> for Value {
    fn from(text: &str) -> Value {
        Value::Text(text.to_string())
    }
}

impl From<String> for Value {
    fn from(text: String) -> Value {
        Value::Text(text)
    }
}

impl From<i64> for Value {
    fn from(whole: i64) -> Value {
        Value::Whole(whole)
    }
}

impl From<usize> for Value {
    fn from(whole: usize) -> Value {
        Value::Whole(whole as i64)
    }
}

impl From<i32> for Value {
    fn from(whole: i32) -> Value {
        Value::Whole(whole as i64)
    }
}

impl From<f64> for Value {
    fn from(float: f64) -> Value {
        Value::Float(float)
    }
}

impl Value {
    /// The value as str() writes it.
    fn shown(&self) -> String {
        match self {
            Value::Text(text) => text.clone(),
            Value::Whole(whole) => whole.to_string(),
            Value::Float(float) => python_float(*float),
            Value::Shown { shown, .. } => shown.clone(),
        }
    }

    /// The value as repr() writes it.
    fn repr(&self) -> String {
        match self {
            Value::Text(text) => python_repr(text),
            Value::Shown { repr, .. } => repr.clone(),
            _ => self.shown(),
        }
    }
}

/// A float as Python's str writes it: the shortest text that reads back exactly, with a point, and Python's exponent form.
pub fn python_float(value: f64) -> String {
    if value.is_nan() {
        return words::NAN.to_string();
    }
    if value.is_infinite() {
        return if value > 0.0 { words::INF } else { "-inf" }.to_string();
    }
    let size = value.abs();
    if size != 0.0 && !(SMALLEST_PLAIN..LARGEST_PLAIN).contains(&size) {
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

/// A text as Python's repr writes it: in single quotes, or double where it holds a single quote and no double.
pub fn python_repr(text: &str) -> String {
    let quote = if text.contains('\'') && !text.contains('"') { '"' } else { '\'' };
    let mut written = String::with_capacity(text.len() + QUOTES);
    written.push(quote);
    for character in text.chars() {
        match character {
            '\\' => written.push_str("\\\\"),
            '\n' => written.push_str("\\n"),
            '\r' => written.push_str("\\r"),
            '\t' => written.push_str("\\t"),
            _ if character == quote => {
                written.push('\\');
                written.push(character);
            }
            _ if (character as u32) < FIRST_PRINTABLE || character as u32 == DELETE => {
                let _ = write!(written, "\\x{:02x}", character as u32);
            }
            _ => written.push(character),
        }
    }
    written.push(quote);
    written
}

/// Fill a template with named values and positional ones, as str.format does; a field with no value is left as written,
/// so that a missing value shows rather than crashes.
pub fn fill(template: &str, named: &[(&str, Value)], positional: &[Value]) -> String {
    let mut out = String::with_capacity(template.len() + ROOM_FOR_VALUES);
    let mut characters = template.chars().peekable();
    let mut next_positional = 0;
    while let Some(character) = characters.next() {
        match character {
            '{' if characters.peek() == Some(&'{') => {
                characters.next();
                out.push('{');
            }
            '}' if characters.peek() == Some(&'}') => {
                characters.next();
                out.push('}');
            }
            '{' => {
                let field = read_field(&mut characters);
                out.push_str(&filled_field(&field, named, positional, &mut next_positional));
            }
            _ => out.push(character),
        }
    }
    out
}

/// Fill a template with named values alone.
pub fn named(template: &str, named: &[(&str, Value)]) -> String {
    fill(template, named, &[])
}

/// The text of one field up to its closing brace, nested braces of a width included.
fn read_field(characters: &mut std::iter::Peekable<std::str::Chars>) -> String {
    let mut field = String::new();
    let mut depth = 0;
    for character in characters.by_ref() {
        match character {
            '{' => depth += 1,
            '}' if depth == 0 => break,
            '}' => depth -= 1,
            _ => {}
        }
        field.push(character);
    }
    field
}

fn lookup(name: &str, named: &[(&str, Value)], positional: &[Value], next_positional: &mut usize) -> Option<Value> {
    if name.is_empty() {
        let value = positional.get(*next_positional).cloned();
        *next_positional += 1;
        return value;
    }
    if let Ok(place) = name.parse::<usize>() {
        return positional.get(place).cloned();
    }
    named.iter().find(|(key, _)| *key == name).map(|(_, value)| value.clone())
}

fn filled_field(field: &str, named: &[(&str, Value)], positional: &[Value], next_positional: &mut usize) -> String {
    let (head, spec) = field.split_once(':').unwrap_or((field, ""));
    let (name, conversion) = head.split_once('!').unwrap_or((head, ""));
    let Some(value) = lookup(name, named, positional, next_positional) else {
        return format!("{{{field}}}");
    };
    let spec = fill(spec, named, positional);
    if conversion == words::R {
        return formatted(&Value::Text(value.repr()), &spec, true);
    }
    formatted(&value, &spec, false)
}

/// A value by a format specification: [[fill]align][sign][0][width][.precision][type].
fn formatted(value: &Value, spec: &str, as_text: bool) -> String {
    if spec.is_empty() {
        return match value {
            Value::Text(text) if as_text => text.clone(),
            _ => value.shown(),
        };
    }
    let characters: Vec<char> = spec.chars().collect();
    let mut place = 0;
    let is_align = |character: char| matches!(character, '<' | '>' | '^' | '=');
    let (mut fill_character, mut align) = (' ', None);
    if characters.len() >= FILL_AND_ALIGN && is_align(characters[1]) {
        fill_character = characters[0];
        align = Some(characters[1]);
        place = FILL_AND_ALIGN;
    } else if !characters.is_empty() && is_align(characters[0]) {
        align = Some(characters[0]);
        place = 1;
    }
    let mut sign = None;
    if place < characters.len() && matches!(characters[place], '+' | '-' | ' ') {
        sign = Some(characters[place]);
        place += 1;
    }
    if place < characters.len() && characters[place] == '0' && align.is_none() {
        fill_character = '0';
        align = Some('=');
        place += 1;
    }
    let digits: String = characters[place..].iter().take_while(|character| character.is_ascii_digit()).collect();
    place += digits.len();
    let width: usize = digits.parse().unwrap_or(0);
    let mut precision = None;
    if place < characters.len() && characters[place] == '.' {
        let places: String = characters[place + 1..].iter().take_while(|character| character.is_ascii_digit()).collect();
        place += 1 + places.len();
        precision = places.parse::<usize>().ok();
    }
    let kind = characters.get(place).copied();
    let body = match (value, kind, precision) {
        (Value::Float(float), _, Some(places)) => format!("{:.*}", places, float.abs()),
        (Value::Whole(whole), Some('f'), Some(places)) => format!("{:.*}", places, (*whole as f64).abs()),
        (Value::Whole(whole), _, _) => whole.unsigned_abs().to_string(),
        (Value::Float(float), _, None) => python_float(float.abs()),
        (Value::Text(text), _, _) => text.clone(),
        (Value::Shown { shown, .. }, _, _) => shown.clone(),
    };
    let negative = match value {
        Value::Whole(whole) => *whole < 0,
        Value::Float(float) => *float < 0.0,
        Value::Text(_) | Value::Shown { .. } => false,
    };
    let sign_text = match (negative, sign) {
        (true, _) => "-",
        (false, Some('+')) => "+",
        (false, Some(' ')) => " ",
        _ => "",
    };
    let numeric = !matches!(value, Value::Text(_));
    let align = align.unwrap_or(if numeric { '>' } else { '<' });
    padded(sign_text, &body, width, fill_character, align)
}

fn padded(sign: &str, body: &str, width: usize, fill_character: char, align: char) -> String {
    let length = sign.chars().count() + body.chars().count();
    if length >= width {
        return format!("{sign}{body}");
    }
    let room = width - length;
    let padding = |count: usize| fill_character.to_string().repeat(count);
    match align {
        '<' => format!("{sign}{body}{}", padding(room)),
        '^' => format!("{}{sign}{body}{}", padding(room / HALVES), padding(room - room / HALVES)),
        '=' => format!("{sign}{}{body}", padding(room)),
        _ => format!("{}{sign}{body}", padding(room)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Every expected text here is what CPython printed for the same template and values.

    /// A named field takes its value, and !r its repr.
    #[test]
    fn a_named_field_takes_its_value_or_its_repr() {
        let (name, value, pattern, note) = ("name", "value", "tune", "C#");
        assert_eq!(named("no pattern called ({name})", &[(name, pattern.into())]), "no pattern called (tune)");
        assert_eq!(named("expected a Note, got {value!r}", &[(value, note.into())]), "expected a Note, got 'C#'");
    }

    /// A spec pads, signs, zero-fills, rounds and aligns as str.format does, a width given by another field included.
    #[test]
    fn a_field_is_padded_signed_and_rounded_by_its_spec() {
        let (name, width, text, narrow) = ("name", "width", "ab", 5);
        assert_eq!(named("{name:<{width}}|", &[(name, text.into()), (width, narrow.into())]), "ab   |");
        let (n, m, f, x) = ("n", "m", "f", "x");
        let (signed, zero_filled, rounded) = (3, 7, 2.25);
        assert_eq!(
            named(
                "{n:+d} {m:02} {f:.1f} {x:>4}",
                &[(n, signed.into()), (m, zero_filled.into()), (f, rounded.into()), (x, text.into())]
            ),
            "+3 07 2.2   ab"
        );
        let (v, w, rounded_away, padded) = ("v", "w", -0.005, -3);
        assert_eq!(named("{v:.2f}|{w:>7}", &[(v, rounded_away.into()), (w, padded.into())]), "-0.01|     -3");
        let (title, heading, wide) = ("title", " Hi ", 10);
        assert_eq!(named("{title:═^{width}}", &[(title, heading.into()), (width, wide.into())]), "═══ Hi ═══");
    }

    /// Positional fields take their values in order, and doubled braces stand for themselves.
    #[test]
    fn positional_fields_fill_in_order_and_doubled_braces_stay() {
        let (first, second) = ("a", "b");
        assert_eq!(fill("{} and {}, {{braces}}", &[], &[first.into(), second.into()]), "a and b, {braces}");
    }

    /// A float and a text are written as Python's str and repr write them.
    #[test]
    fn floats_and_texts_read_as_python_writes_them() {
        let (huge, tiny, tenth, whole) = (1e16, 1.5e-05, 0.1, 3.0);
        assert_eq!(python_float(huge), "1e+16");
        assert_eq!(python_float(tiny), "1.5e-05");
        assert_eq!(python_float(tenth), "0.1");
        assert_eq!(python_float(whole), "3.0");
        assert_eq!(python_repr("it's"), "\"it's\"");
    }
}
