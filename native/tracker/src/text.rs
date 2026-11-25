// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A line of the screen as the Rich library's Text holds one: its characters, a style under all of it, and spans of other
//! styles over parts, later spans over earlier; and the segments it is drawn as, one for each run of one style.

use crate::style::Style;
use unicode_width::UnicodeWidthChar;

#[derive(Clone, Debug, Default, PartialEq, Eq, Hash)]
pub struct Text {
    characters: Vec<char>,
    pub style: Style,
    spans: Vec<(usize, usize, Style)>,
}

/// A run of characters drawn in one style.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Segment {
    pub text: String,
    pub style: Style,
}

pub fn cell_width(text: &str) -> usize {
    text.chars().map(|character| character.width().unwrap_or(0)).sum()
}

impl Text {
    pub fn plain(text: &str) -> Text {
        Text {
            characters: text.chars().collect(),
            ..Text::default()
        }
    }

    pub fn styled(text: &str, style: &str) -> Text {
        Text {
            characters: text.chars().collect(),
            style: Style::parse(style),
            spans: Vec::new(),
        }
    }

    pub fn with_style(text: &str, style: Style) -> Text {
        Text {
            characters: text.chars().collect(),
            style,
            spans: Vec::new(),
        }
    }

    /// Add text at the end, in a style of its own over the line's.
    pub fn append(&mut self, text: &str, style: &str) -> &mut Text {
        self.append_style(text, Style::parse(style))
    }

    pub fn append_style(&mut self, text: &str, style: Style) -> &mut Text {
        let start = self.characters.len();
        self.characters.extend(text.chars());
        if !style.is_null() && self.characters.len() > start {
            self.spans.push((start, self.characters.len(), style));
        }
        self
    }

    /// Add another line's text at the end, its own style and spans kept.
    pub fn append_text(&mut self, other: &Text) -> &mut Text {
        let start = self.characters.len();
        self.characters.extend(other.characters.iter());
        if !other.style.is_null() && !other.characters.is_empty() {
            self.spans.push((start, self.characters.len(), other.style.clone()));
        }
        for (from, to, style) in &other.spans {
            self.spans.push((start + from, start + to, style.clone()));
        }
        self
    }

    pub fn text(&self) -> String {
        self.characters.iter().collect()
    }

    pub fn len(&self) -> usize {
        self.characters.len()
    }

    pub fn is_empty(&self) -> bool {
        self.characters.is_empty()
    }

    pub fn cell_len(&self) -> usize {
        self.characters.iter().map(|character| character.width().unwrap_or(0)).sum()
    }

    /// The line cut to a width of cells, its last cell an ellipsis where it was longer, as Rich truncates with overflow
    /// ellipsis.
    pub fn truncate(&mut self, width: usize) {
        if self.cell_len() <= width {
            return;
        }
        let mut cells = 0;
        let mut keep = 0;
        for character in &self.characters {
            let wide = character.width().unwrap_or(0);
            if cells + wide > width.saturating_sub(1) {
                break;
            }
            cells += wide;
            keep += 1;
        }
        self.characters.truncate(keep);
        self.characters.push('…');
        let end = self.characters.len();
        for span in &mut self.spans {
            span.0 = span.0.min(end);
            span.1 = span.1.min(end);
        }
        self.spans.retain(|(start, finish, _)| start < finish);
    }

    /// The line's first cells, up to a width, as Rich slices a line by its characters.
    pub fn slice_cells(&self, width: usize) -> Text {
        self.slice(0, width)
    }

    /// A part of the line, from one character to another, its spans cut to fit.
    pub fn slice(&self, start: usize, end: usize) -> Text {
        let end = end.min(self.characters.len());
        let start = start.min(end);
        let spans = self
            .spans
            .iter()
            .filter(|(from, to, _)| *to > start && *from < end)
            .map(|(from, to, style)| ((*from).max(start) - start, (*to).min(end) - start, style.clone()))
            .collect();
        Text {
            characters: self.characters[start..end].to_vec(),
            style: self.style.clone(),
            spans,
        }
    }

    /// The segments the line is drawn as: each run of characters whose spans are the same, in the line's style with each
    /// span over it in order, as Rich renders a Text.
    pub fn segments(&self) -> Vec<Segment> {
        let mut segments: Vec<Segment> = Vec::new();
        if self.characters.is_empty() {
            return segments;
        }
        let mut edges: Vec<usize> = vec![0, self.characters.len()];
        for (start, end, _) in &self.spans {
            edges.push(*start);
            edges.push(*end);
        }
        edges.sort();
        edges.dedup();
        for pair in edges.windows(2) {
            let (start, end) = (pair[0], pair[1]);
            if start >= end {
                continue;
            }
            let mut style = self.style.clone();
            for (from, to, over) in &self.spans {
                if *from <= start && end <= *to {
                    style = style.and(over);
                }
            }
            segments.push(Segment {
                text: self.characters[start..end].iter().collect(),
                style,
            });
        }
        segments
    }
}
