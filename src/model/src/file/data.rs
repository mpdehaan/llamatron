// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A set file's data as the Python program loads it (model/file/safe_yaml.py, PyYAML's safe loader): nothing, true or
//! false, a whole number, a float, text, a list, or a mapping that keeps its keys in the order the file gives them.
//!
//! The file is read by yaml-rust2 for its structure, and each plain scalar's kind is decided by PyYAML's own rules, YAML
//! 1.1's, so that llamatron reads every set as llamatron reads it: `on`, `yes` and `True` are true, `010` is eight, `1:30`
//! is ninety, `1.5` and `1.0e+3` are floats, `1e3` and `1/4` are text, and `~`, `null` or nothing is nothing.

use llamatron_math::number::python_float_text;
use llamatron_names::file_format;
use llamatron_names::words;
use yaml_rust2::parser::{Event, Parser};
use yaml_rust2::scanner::TScalarStyle;

#[derive(Clone, Debug, PartialEq)]
pub enum Data {
    Null,
    Bool(bool),
    Whole(i128),
    Float(f64),
    Text(String),
    List(Vec<Data>),
    Map(Vec<(Data, Data)>),
}

/// Why a file is not YAML, with where.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NotYaml(pub String);

impl Data {
    pub fn text(value: &str) -> Data {
        Data::Text(value.to_string())
    }

    /// A mapping's value under a text key, or None.
    pub fn get(&self, key: &str) -> Option<&Data> {
        match self {
            Data::Map(pairs) => pairs
                .iter()
                .find(|(found, _)| matches!(found, Data::Text(text) if text == key))
                .map(|(_, value)| value),
            _ => None,
        }
    }

    pub fn as_str(&self) -> Option<&str> {
        match self {
            Data::Text(text) => Some(text),
            _ => None,
        }
    }

    pub fn as_list(&self) -> Option<&[Data]> {
        match self {
            Data::List(items) => Some(items),
            _ => None,
        }
    }

    pub fn as_map(&self) -> Option<&[(Data, Data)]> {
        match self {
            Data::Map(pairs) => Some(pairs),
            _ => None,
        }
    }

    /// A whole number, true and false not counted, as Python's is_whole_number has it.
    pub fn as_whole(&self) -> Option<i128> {
        match self {
            Data::Whole(whole) => Some(*whole),
            _ => None,
        }
    }

    pub fn is_null(&self) -> bool {
        matches!(self, Data::Null)
    }

    /// Set a mapping's value under a text key, in place where the key is there, at the end where it is not.
    pub fn set(&mut self, key: &str, value: Data) {
        if let Data::Map(pairs) = self {
            match pairs.iter_mut().find(|(found, _)| matches!(found, Data::Text(text) if text == key)) {
                Some(pair) => pair.1 = value,
                None => pairs.push((Data::text(key), value)),
            }
        }
    }

    /// Take a mapping's value away under a text key.
    pub fn remove(&mut self, key: &str) -> Option<Data> {
        let Data::Map(pairs) = self else { return None };
        let place = pairs.iter().position(|(found, _)| matches!(found, Data::Text(text) if text == key))?;
        Some(pairs.remove(place).1)
    }
}

impl Data {
    /// The value as Python's str() writes it, for a message: text as it is, the rest as repr() writes it.
    pub fn python_str(&self) -> String {
        match self {
            Data::Text(text) => text.clone(),
            other => other.python_repr(),
        }
    }

    /// The value as Python's repr() writes it: `'abc'`, `5`, `0.25`, `True`, `None`, `[1, 'a']`, `{'a': 1}`.
    pub fn python_repr(&self) -> String {
        match self {
            Data::Null => "None".into(),
            Data::Bool(flag) => if *flag { "True" } else { "False" }.into(),
            Data::Whole(whole) => whole.to_string(),
            Data::Float(float) if float.is_nan() => words::NAN.into(),
            Data::Float(float) if float.is_infinite() => if *float > 0.0 { words::INF } else { "-inf" }.into(),
            Data::Float(float) => python_float_text(*float),
            Data::Text(text) => llamatron_strings::fill::python_repr(text),
            Data::List(items) => format!("[{}]", items.iter().map(Data::python_repr).collect::<Vec<_>>().join(", ")),
            Data::Map(pairs) => format!(
                "{{{}}}",
                pairs
                    .iter()
                    .map(|(key, value)| format!("{}: {}", key.python_repr(), value.python_repr()))
                    .collect::<Vec<_>>()
                    .join(", ")
            ),
        }
    }
}

impl From<&Data> for llamatron_strings::Value {
    /// A value for a message, which a template writes as str() or, with !r, as repr() writes it.
    fn from(data: &Data) -> llamatron_strings::Value {
        match data {
            Data::Whole(whole) => llamatron_strings::Value::Whole(*whole as i64),
            Data::Float(float) => llamatron_strings::Value::Float(*float),
            Data::Text(text) => llamatron_strings::Value::Text(text.clone()),
            other => llamatron_strings::Value::Shown {
                shown: other.python_str(),
                repr: other.python_repr(),
            },
        }
    }
}

/// A value as a YAML document, through yaml-rust2's emitter, for a file other than a set file, whose own layout
/// `writing::dump_file_layout` keeps.
pub fn dump(data: &Data) -> Result<String, NotYaml> {
    let mut written = String::new();
    yaml_rust2::YamlEmitter::new(&mut written)
        .dump(&yaml_of(data))
        .map_err(|problem| NotYaml(problem.to_string()))?;
    // The emitter starts the document with its marker; the file holds the document alone.
    let body = written.strip_prefix("---\n").unwrap_or(&written);
    Ok(format!("{body}\n"))
}

/// A value as yaml-rust2's own.
fn yaml_of(data: &Data) -> yaml_rust2::Yaml {
    use yaml_rust2::Yaml;
    match data {
        Data::Null => Yaml::Null,
        Data::Bool(flag) => Yaml::Boolean(*flag),
        Data::Whole(whole) => Yaml::Integer(*whole as i64),
        Data::Float(float) => Yaml::Real(yaml_float(*float)),
        Data::Text(text) => Yaml::String(text.clone()),
        Data::List(items) => Yaml::Array(items.iter().map(yaml_of).collect()),
        Data::Map(pairs) => Yaml::Hash(pairs.iter().map(|(key, value)| (yaml_of(key), yaml_of(value))).collect()),
    }
}

/// Read a YAML text as the Python program reads it: one document, or nothing where the text is empty.
pub fn load(text: &str) -> Result<Data, NotYaml> {
    let mut parser = Parser::new_from_str(text);
    let mut builder = Builder::default();
    loop {
        let (event, mark) = parser.next_token().map_err(|problem| NotYaml(problem.to_string()))?;
        match event {
            Event::StreamEnd => break,
            Event::Nothing | Event::StreamStart | Event::DocumentStart | Event::DocumentEnd => {}
            other => builder.take(other).map_err(|problem| NotYaml(format!("{problem} at line {}", mark.line())))?,
        }
    }
    Ok(builder.finished.unwrap_or(Data::Null))
}

/// What is being built: the open lists and mappings, each with its anchor, and the anchored values seen.
#[derive(Default)]
struct Builder {
    open: Vec<(Data, usize, Option<Data>)>,
    anchors: Vec<(usize, Data)>,
    finished: Option<Data>,
}

impl Builder {
    fn take(&mut self, event: Event) -> Result<(), String> {
        match event {
            Event::SequenceStart(anchor, _) => self.open.push((Data::List(Vec::new()), anchor, None)),
            Event::MappingStart(anchor, _) => self.open.push((Data::Map(Vec::new()), anchor, None)),
            Event::SequenceEnd | Event::MappingEnd => {
                let (done, anchor, _) = self.open.pop().ok_or("an end with nothing open")?;
                self.add(done, anchor);
            }
            Event::Scalar(value, style, anchor, tag) => {
                let tagged_text = tag.as_ref().is_some_and(|tag| tag.suffix == words::STR);
                let data = if style == TScalarStyle::Plain && !tagged_text {
                    resolved(&value)
                } else {
                    Data::Text(value)
                };
                self.add(data, anchor);
            }
            Event::Alias(anchor) => {
                let found = self
                    .anchors
                    .iter()
                    .rev()
                    .find(|(id, _)| *id == anchor)
                    .map(|(_, value)| value.clone())
                    .ok_or("an alias to no anchor")?;
                self.add(found, 0);
            }
            _ => {}
        }
        Ok(())
    }

    fn add(&mut self, value: Data, anchor: usize) {
        if anchor != 0 {
            self.anchors.push((anchor, value.clone()));
        }
        let Some((holder, _, key)) = self.open.last_mut() else {
            self.finished = Some(value);
            return;
        };
        match holder {
            Data::List(items) => items.push(value),
            Data::Map(pairs) => match key.take() {
                None => *key = Some(value),
                Some(found) => {
                    // A key given twice keeps its first place and its last value, as a Python dict does.
                    match pairs.iter_mut().find(|(existing, _)| *existing == found) {
                        Some(pair) => pair.1 = value,
                        None => pairs.push((found, value)),
                    }
                }
            },
            _ => {}
        }
    }
}

/// A plain scalar's value by PyYAML's implicit resolvers, YAML 1.1's: null, a flag, a whole number, a float, or text.
pub fn resolved(text: &str) -> Data {
    if matches!(text, "" | "~" | words::NULL | "Null" | "NULL") {
        return Data::Null;
    }
    if let Some(flag) = flag_of(text) {
        return Data::Bool(flag);
    }
    if let Some(whole) = whole_of(text) {
        return Data::Whole(whole);
    }
    if let Some(float) = float_of(text) {
        return Data::Float(float);
    }
    Data::Text(text.to_string())
}

fn flag_of(text: &str) -> Option<bool> {
    match text {
        words::YES | "Yes" | "YES" | words::TRUE | "True" | "TRUE" | file_format::LfoSetting::ON | "On" | "ON" => Some(true),
        words::NO | "No" | "NO" | words::FALSE | "False" | "FALSE" | file_format::InstrumentKind::OFF | "Off" | "OFF" => Some(false),
        _ => None,
    }
}

fn sign_of(text: &str) -> (i128, &str) {
    match text.as_bytes().first() {
        Some(b'-') => (-1, &text[1..]),
        Some(b'+') => (1, &text[1..]),
        _ => (1, text),
    }
}

fn all(text: &str, allowed: impl Fn(char) -> bool) -> bool {
    !text.is_empty() && text.chars().all(allowed)
}

/// A whole number by PyYAML's int resolver: binary, octal after a leading 0, decimal, hexadecimal, or base 60 (`1:30`).
fn whole_of(text: &str) -> Option<i128> {
    let (sign, body) = sign_of(text);
    let digits = |part: &str, base: u32| i128::from_str_radix(&part.replace('_', ""), base).ok();
    if let Some(binary) = body.strip_prefix("0b") {
        return all(binary, |digit| matches!(digit, '0' | '1' | '_'))
            .then(|| digits(binary, 2))
            .flatten()
            .map(|value| sign * value);
    }
    if let Some(hexadecimal) = body.strip_prefix("0x") {
        return all(hexadecimal, |digit| digit.is_ascii_hexdigit() || digit == '_')
            .then(|| digits(hexadecimal, 16))
            .flatten()
            .map(|value| sign * value);
    }
    if body == "0" {
        return Some(0);
    }
    if let Some(octal) = body.strip_prefix('0') {
        return all(octal, |digit| matches!(digit, '0'..='7' | '_'))
            .then(|| digits(octal, 8))
            .flatten()
            .map(|value| sign * value);
    }
    if body.contains(':') {
        return base_sixty(body).map(|value| sign * value);
    }
    let first = body.chars().next()?;
    (('1'..='9').contains(&first) && all(body, |digit| digit.is_ascii_digit() || digit == '_'))
        .then(|| digits(body, 10))
        .flatten()
        .map(|value| sign * value)
}

/// `[1-9][0-9_]*(:[0-5]?[0-9])+`, each part after the first below sixty.
fn base_sixty(body: &str) -> Option<i128> {
    let mut parts = body.split(':');
    let first = parts.next()?;
    if !first.starts_with(|digit: char| ('1'..='9').contains(&digit)) || !all(first, |digit| digit.is_ascii_digit() || digit == '_') {
        return None;
    }
    let mut value: i128 = first.replace('_', "").parse().ok()?;
    for part in parts {
        if part.is_empty() || part.len() > 2 || !all(part, |digit| digit.is_ascii_digit()) || (part.len() == 2 && part.as_bytes()[0] > b'5') {
            return None;
        }
        value = value * 60 + part.parse::<i128>().ok()?;
    }
    Some(value)
}

/// A float by PyYAML's float resolver: digits with a point, an exponent only with its sign (`1.0e+3`), base 60 with a point,
/// and `.inf`, `.nan`.
fn float_of(text: &str) -> Option<f64> {
    let (sign, body) = sign_of(text);
    if matches!(body, ".inf" | ".Inf" | ".INF") {
        return Some(sign as f64 * f64::INFINITY);
    }
    if matches!(text, ".nan" | ".NaN" | ".NAN") {
        return Some(f64::NAN);
    }
    let (mantissa, exponent) = match body.find(['e', 'E']) {
        Some(place) => (&body[..place], Some(&body[place + 1..])),
        None => (body, None),
    };
    if let Some(exponent) = exponent {
        let (_, power) = sign_of(exponent);
        if !matches!(exponent.as_bytes().first(), Some(b'+' | b'-')) || !all(power, |digit| digit.is_ascii_digit()) {
            return None;
        }
    }
    if mantissa.contains(':') {
        let (whole, fraction) = mantissa.split_once('.')?;
        if exponent.is_some() || !all(fraction, |digit| digit.is_ascii_digit() || digit == '_') && !fraction.is_empty() {
            return None;
        }
        let value = base_sixty(whole)? as f64 + format!("0.{}", fraction.replace('_', "")).parse::<f64>().ok()?;
        return Some(sign as f64 * value);
    }
    let (whole, fraction) = mantissa.split_once('.')?;
    let whole_ok = whole.is_empty() && !fraction.is_empty()
        || all(whole, |digit| digit.is_ascii_digit() || digit == '_') && whole.starts_with(|digit: char| digit.is_ascii_digit());
    if !whole_ok || !fraction.chars().all(|digit| digit.is_ascii_digit() || digit == '_') {
        return None;
    }
    // A float that starts with its point takes no sign in PyYAML's pattern, so -.5 is text.
    if whole.is_empty() && (!fraction.starts_with(|digit: char| digit.is_ascii_digit()) || body.len() != text.len()) {
        return None;
    }
    let cleaned = format!("{}{}", if sign < 0 { "-" } else { "" }, body.replace('_', ""));
    cleaned.parse().ok()
}

/// A text as Python's json.dumps writes it: in double quotes, every character beyond ASCII as \u escapes.
pub fn json_text(text: &str) -> String {
    let mut written = String::with_capacity(text.len() + 2);
    written.push('"');
    for character in text.chars() {
        match character {
            '"' => written.push_str("\\\""),
            '\\' => written.push_str("\\\\"),
            '\n' => written.push_str("\\n"),
            '\r' => written.push_str("\\r"),
            '\t' => written.push_str("\\t"),
            '\u{8}' => written.push_str("\\b"),
            '\u{c}' => written.push_str("\\f"),
            _ if (character as u32) < 0x20 || (character as u32) > 0x7e => {
                let mut units = [0u16; 2];
                for unit in character.encode_utf16(&mut units) {
                    written.push_str(&format!("\\u{unit:04x}"));
                }
            }
            _ => written.push(character),
        }
    }
    written.push('"');
    written
}

/// A float as PyYAML's safe_dump writes it: Python's repr in lower case, `.0` put before an exponent with no point, and
/// `.inf`, `-.inf`, `.nan`.
pub fn yaml_float(value: f64) -> String {
    if value.is_nan() {
        return ".nan".to_string();
    }
    if value.is_infinite() {
        return if value > 0.0 { ".inf" } else { "-.inf" }.to_string();
    }
    let text = python_float_text(value).to_lowercase();
    if !text.contains('.') && text.contains('e') {
        return text.replacen('e', ".0e", 1);
    }
    text
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_file_loads_with_its_order_and_quoting() {
        let data = load("b: [1, '2', x]\na: {c: on}\n").unwrap();
        let Data::Map(pairs) = &data else { panic!("a mapping") };
        assert_eq!(pairs[0].0, Data::text(file_format::Accidental::FLAT));
        assert_eq!(
            data.get(file_format::Accidental::FLAT).unwrap(),
            &Data::List(vec![Data::Whole(1), Data::text("2"), Data::text(words::X)])
        );
        assert_eq!(data.get(file_format::DriftVersion::A).unwrap().get(words::C), Some(&Data::Bool(true)));
    }

    #[test]
    fn texts_and_floats_are_written_in_the_files_form() {
        assert_eq!(json_text("é \"x\""), "\"\\u00e9 \\\"x\\\"\"");
        assert_eq!(yaml_float(1e16), "1.0e+16");
        assert_eq!(yaml_float(0.25), "0.25");
    }
}
