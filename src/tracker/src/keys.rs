// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A binding tied to where it is bound (the Python interface/tracker/key_table.py): its keys, what they're called on screen
//! and what they do there. The page names its action by the binding itself, matched as the very static it is, since two
//! bindings may hold the same keys and words.

use crate::keybindings::{Binding, KeyClass, Keys};
use llamatron_names::keys;
use llamatron_strings::legends;

pub const STEP_BACK: i64 = -1;
pub const STEP_FORWARD: i64 = 1;

#[derive(Clone, Debug)]
pub struct KeyItem {
    pub binding: &'static Binding,
    pub owner: &'static KeyClass,
    pub keys: Vec<&'static str>,
    pub label: String,
    pub what: String,
    /// Whether the action is passed the key's name: a key that types its own character, or an arrow that moves a cursor.
    pub wants_key: bool,
    /// Whether the legend shows it, as its class's IN_LEGEND says.
    pub shown: bool,
}

impl KeyItem {
    /// A binding of a class, as bound.
    pub fn of(owner: &'static KeyClass, binding: &'static Binding) -> KeyItem {
        KeyItem {
            binding,
            owner,
            keys: keys_of(&binding.keys),
            label: binding.name.to_string(),
            what: binding.what.to_string(),
            wants_key: false,
            shown: owner.in_legend.iter().any(|listed| std::ptr::eq(*listed, binding)),
        }
    }

    pub fn wanting_key(mut self) -> KeyItem {
        self.wants_key = true;
        self
    }

    pub fn saying(mut self, what: &str) -> KeyItem {
        self.what = what.to_string();
        self
    }

    pub fn named(mut self, label: &str) -> KeyItem {
        self.label = label.to_string();
        self
    }

    pub fn with_keys(mut self, keys: Vec<&'static str>) -> KeyItem {
        self.keys = keys;
        self
    }

    pub fn is(&self, binding: &'static Binding) -> bool {
        std::ptr::eq(self.binding, binding)
    }

    /// The direction a stepping key steps in, back or forward, or None for a key that doesn't step.
    pub fn step_of(&self, key: &str) -> Option<i64> {
        match &self.binding.keys {
            Keys::Steps { back, .. } if back.contains(&key) => Some(STEP_BACK),
            Keys::Steps { .. } => Some(STEP_FORWARD),
            _ => None,
        }
    }

    fn place_in_help(&self) -> usize {
        self.owner
            .in_help
            .iter()
            .position(|listed| std::ptr::eq(*listed, self.binding))
            .unwrap_or(usize::MAX)
    }
}

/// Every key of a binding's keys: both ways of keys that step, back first.
pub fn keys_of(keys: &Keys) -> Vec<&'static str> {
    match keys {
        Keys::One(key) => vec![*key],
        Keys::Many(keys) => keys.to_vec(),
        Keys::Steps { back, forward } => back.iter().chain(forward.iter()).copied().collect(),
    }
}

pub fn first_key(binding: &Binding) -> &'static str {
    keys_of(&binding.keys)[0]
}

/// Bindings with a class's own in the order its IN_HELP lists them, each run of its own between a part's bindings put in
/// order, as the Python's in_order does.
pub fn in_order(owner: &'static KeyClass, items: Vec<KeyItem>) -> Vec<KeyItem> {
    let mut result = Vec::new();
    let mut run: Vec<KeyItem> = Vec::new();
    for item in items {
        if std::ptr::eq(item.owner, owner) {
            run.push(item);
        } else {
            run.sort_by_key(KeyItem::place_in_help);
            result.append(&mut run);
            result.push(item);
        }
    }
    run.sort_by_key(KeyItem::place_in_help);
    result.append(&mut run);
    result
}

/// A legend's keys with Up and Down and Left and Right shown as one entry of all four arrows where both do the same.
pub fn arrows_joined(items: Vec<KeyItem>) -> Vec<KeyItem> {
    let up_down = items.iter().position(|item| item.label == legends::KeyName::UP_DOWN);
    let left_right = items.iter().position(|item| item.label == legends::KeyName::LEFT_RIGHT);
    let (Some(up_down), Some(left_right)) = (up_down, left_right) else {
        return items;
    };
    if items[up_down].what != items[left_right].what {
        return items;
    }
    let mut joined = Vec::new();
    for (place, mut item) in items.into_iter().enumerate() {
        if place == left_right {
            continue;
        }
        if place == up_down {
            item.label = legends::KeyName::ARROWS.to_string();
        }
        joined.push(item);
    }
    joined
}

/// A key the tour recorded, as Textual names it, as the tracker names it: plus, minus and slash by their marks, a letter in
/// lower case, and delete as backspace.
pub fn pressed_key(name: &str) -> String {
    match name {
        keys::PLUS => "+".to_string(),
        keys::MINUS => "-".to_string(),
        keys::SLASH => "/".to_string(),
        keys::DELETE => keys::BACKSPACE.to_string(),
        _ if name.chars().count() == 1 => name.to_lowercase(),
        _ => name.to_string(),
    }
}
