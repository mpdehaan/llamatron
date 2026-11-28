// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A style a piece of the screen is drawn in, as the Rich library holds one, and written as Rich writes it, so that the
//! screens compare with the Python program's: its attributes, then its colour, then `on` its background.

use llamatron_names::file_format;
/// The attributes a style may set, in the order Rich writes them.
use llamatron_names::words;
const ATTRIBUTES: [&str; 13] = [
    words::BOLD,
    file_format::ChordSymbol::DIMINISHED,
    words::ITALIC,
    words::UNDERLINE,
    words::BLINK,
    words::BLINK2,
    words::REVERSE,
    words::CONCEAL,
    file_format::VactrolLight::STRIKE,
    words::UNDERLINE2,
    words::FRAME,
    words::ENCIRCLE,
    words::OVERLINE,
];

#[derive(Clone, Debug, Default, PartialEq, Eq, Hash)]
pub struct Style {
    /// Each attribute on, off, or left to the style under this one.
    attributes: [Option<bool>; 13],
    pub color: Option<String>,
    pub bgcolor: Option<String>,
}

impl Style {
    /// A style from Rich's words, such as `bold red`, `on default` or `bold reverse #be5aff`.
    pub fn parse(text: &str) -> Style {
        let mut style = Style::default();
        let mut words = text.split_whitespace().peekable();
        while let Some(word) = words.next() {
            if word == file_format::LfoSetting::ON {
                style.bgcolor = words.next().map(str::to_string);
                continue;
            }
            if word == words::NOT {
                if let Some(place) = words.next().and_then(|name| ATTRIBUTES.iter().position(|found| *found == name)) {
                    style.attributes[place] = Some(false);
                }
                continue;
            }
            match ATTRIBUTES.iter().position(|found| *found == word) {
                Some(place) => style.attributes[place] = Some(true),
                None if word != words::NONE => style.color = Some(word.to_string()),
                None => {}
            }
        }
        style
    }

    pub fn is_null(&self) -> bool {
        *self == Style::default()
    }

    pub fn is_on(&self, attribute: &str) -> bool {
        ATTRIBUTES
            .iter()
            .position(|found| *found == attribute)
            .is_some_and(|place| self.attributes[place] == Some(true))
    }

    /// This style with another over it, the other's settings winning, as Rich adds two styles.
    pub fn and(&self, over: &Style) -> Style {
        let mut combined = self.clone();
        for (place, setting) in over.attributes.iter().enumerate() {
            if setting.is_some() {
                combined.attributes[place] = *setting;
            }
        }
        if over.color.is_some() {
            combined.color = over.color.clone();
        }
        if over.bgcolor.is_some() {
            combined.bgcolor = over.bgcolor.clone();
        }
        combined
    }

    /// The style as Rich writes it, an empty string for no style at all.
    pub fn written(&self) -> String {
        let mut words: Vec<String> = Vec::new();
        for (place, setting) in self.attributes.iter().enumerate() {
            match setting {
                Some(true) => words.push(ATTRIBUTES[place].to_string()),
                Some(false) => words.push(format!("not {}", ATTRIBUTES[place])),
                None => {}
            }
        }
        if let Some(color) = &self.color {
            words.push(color.clone());
        }
        if let Some(background) = &self.bgcolor {
            words.push(format!("on {background}"));
        }
        words.join(" ")
    }

    /// A colour written as Rich writes one made from its parts.
    pub fn rgb((red, green, blue): (u8, u8, u8)) -> String {
        format!("#{red:02x}{green:02x}{blue:02x}")
    }
}
