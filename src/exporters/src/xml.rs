// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! An XML tree as the Live set export reads and writes it, written out exactly as Python's ElementTree writes one: each
//! element's attributes in their order, its text before its children and each child's tail after it, an element with no
//! text and no children closed as ` />`, and the characters escaped as ElementTree escapes them.

#[derive(Clone, Debug, PartialEq)]
pub struct Element {
    pub tag: String,
    pub attributes: Vec<(String, String)>,
    pub text: Option<String>,
    pub tail: Option<String>,
    pub children: Vec<Element>,
}

impl Element {
    pub fn new(tag: &str, attributes: &[(&str, &str)]) -> Element {
        Element {
            tag: tag.to_string(),
            attributes: attributes.iter().map(|(name, value)| (name.to_string(), value.to_string())).collect(),
            text: None,
            tail: None,
            children: Vec::new(),
        }
    }

    pub fn get(&self, name: &str) -> Option<&str> {
        self.attributes.iter().find(|(found, _)| found == name).map(|(_, value)| value.as_str())
    }

    /// Set an attribute, in its place where the element has it, else after the others.
    pub fn set(&mut self, name: &str, value: &str) {
        match self.attributes.iter_mut().find(|(found, _)| found == name) {
            Some(attribute) => attribute.1 = value.to_string(),
            None => self.attributes.push((name.to_string(), value.to_string())),
        }
    }

    /// The first element down a path of tags from this one, such as `DeviceChain/Mixer/Tempo`.
    pub fn find(&self, path: &str) -> Option<&Element> {
        let mut here = self;
        for tag in path.split('/') {
            here = here.children.iter().find(|child| child.tag == tag)?;
        }
        Some(here)
    }

    pub fn find_mut(&mut self, path: &str) -> Option<&mut Element> {
        let mut here = self;
        for tag in path.split('/') {
            here = here.children.iter_mut().find(|child| child.tag == tag)?;
        }
        Some(here)
    }

    /// A new child at the end, with no text, which is returned.
    pub fn add(&mut self, tag: &str, attributes: &[(&str, &str)]) -> &mut Element {
        self.children.push(Element::new(tag, attributes));
        self.children.last_mut().expect("a child was just added")
    }

    /// Every element in this one, this one first, in document order.
    pub fn each<'a>(&'a self, found: &mut Vec<&'a Element>) {
        found.push(self);
        for child in &self.children {
            child.each(found);
        }
    }

    /// Call a function on this element and every one inside it, in document order.
    pub fn each_mut(&mut self, change: &mut dyn FnMut(&mut Element)) {
        change(self);
        for child in &mut self.children {
            child.each_mut(change);
        }
    }

    /// The element as ElementTree writes it, with its tail.
    pub fn write(&self, out: &mut String) {
        out.push('<');
        out.push_str(&self.tag);
        for (name, value) in &self.attributes {
            out.push(' ');
            out.push_str(name);
            out.push_str("=\"");
            escaped_attribute(value, out);
            out.push('"');
        }
        let text = self.text.as_deref().filter(|text| !text.is_empty());
        if text.is_none() && self.children.is_empty() {
            out.push_str(" />");
        } else {
            out.push('>');
            if let Some(text) = text {
                escaped_text(text, out);
            }
            for child in &self.children {
                child.write(out);
            }
            out.push_str("</");
            out.push_str(&self.tag);
            out.push('>');
        }
        if let Some(tail) = self.tail.as_deref() {
            escaped_text(tail, out);
        }
    }
}

fn escaped_text(text: &str, out: &mut String) {
    for character in text.chars() {
        match character {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            other => out.push(other),
        }
    }
}

fn escaped_attribute(text: &str, out: &mut String) {
    for character in text.chars() {
        match character {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            '\r' => out.push_str("&#13;"),
            '\n' => out.push_str("&#10;"),
            '\t' => out.push_str("&#09;"),
            other => out.push(other),
        }
    }
}

/// The text a file's characters stand for, its entities read.
fn unescaped(text: &str) -> String {
    let mut out = String::new();
    let mut rest = text;
    while let Some(start) = rest.find('&') {
        out.push_str(&rest[..start]);
        let Some(length) = rest[start..].find(';') else {
            out.push_str(&rest[start..]);
            return out;
        };
        let entity = &rest[start + 1..start + length];
        let character = match entity {
            "amp" => Some('&'),
            "lt" => Some('<'),
            "gt" => Some('>'),
            "quot" => Some('"'),
            "apos" => Some('\''),
            number if number.starts_with("#x") => u32::from_str_radix(&number[2..], 16).ok().and_then(char::from_u32),
            number if number.starts_with('#') => number[1..].parse().ok().and_then(char::from_u32),
            _ => None,
        };
        match character {
            Some(character) => out.push(character),
            None => out.push_str(&rest[start..=start + length]),
        }
        rest = &rest[start + length + 1..];
    }
    out.push_str(rest);
    out
}

/// What is wrong with a document that is not XML this reader reads.
#[derive(Debug)]
pub struct NotXml(pub String);

/// The root element of a document, its declaration, comments and processing instructions passed over, as ElementTree reads.
pub fn parse(text: &str) -> Result<Element, NotXml> {
    let mut reader = Reader {
        text: text.replace("\r\n", "\n"),
        place: 0,
    };
    reader.skip_prolog();
    let mut root = reader.element()?;
    root.tail = None;
    tidied(&mut root);
    Ok(root)
}

struct Reader {
    text: String,
    place: usize,
}

impl Reader {
    fn rest(&self) -> &str {
        &self.text[self.place..]
    }

    fn skip_prolog(&mut self) {
        loop {
            let trimmed = self.rest().trim_start();
            let skipped = self.rest().len() - trimmed.len();
            self.place += skipped;
            let end = if self.rest().starts_with("<?") {
                self.rest().find("?>").map(|end| end + 2)
            } else if self.rest().starts_with("<!--") {
                self.rest().find("-->").map(|end| end + 3)
            } else if self.rest().starts_with("<!") {
                self.rest().find('>').map(|end| end + 1)
            } else {
                return;
            };
            match end {
                Some(end) => self.place += end,
                None => return,
            }
        }
    }

    fn until(&mut self, stop: char) -> String {
        let end = self.rest().find(stop).unwrap_or(self.rest().len());
        let found = self.rest()[..end].to_string();
        self.place += end;
        found
    }

    fn element(&mut self) -> Result<Element, NotXml> {
        if !self.rest().starts_with('<') {
            return Err(NotXml(format!("expected an element at {}", self.place)));
        }
        self.place += 1;
        let name_end = self
            .rest()
            .find(|character: char| character.is_whitespace() || character == '>' || character == '/')
            .unwrap_or(0);
        let mut element = Element::new(&self.rest()[..name_end], &[]);
        self.place += name_end;
        loop {
            let trimmed = self.rest().trim_start();
            self.place += self.rest().len() - trimmed.len();
            if self.rest().starts_with("/>") {
                self.place += 2;
                element.tail = Some(self.text_until_tag());
                return Ok(element);
            }
            if self.rest().starts_with('>') {
                self.place += 1;
                break;
            }
            let name = self.until('=').trim().to_string();
            self.place += 1;
            let quote = self.rest().chars().next().ok_or_else(|| NotXml("an attribute has no value".to_string()))?;
            self.place += 1;
            let value = self.until(quote);
            self.place += 1;
            let normalized: String = value
                .chars()
                .map(|character| if matches!(character, '\n' | '\t' | '\r') { ' ' } else { character })
                .collect();
            element.attributes.push((name, unescaped(&normalized)));
        }
        element.text = Some(self.text_until_tag());
        loop {
            if self.rest().starts_with("</") {
                self.until('>');
                self.place += 1;
                element.tail = Some(self.text_until_tag());
                return Ok(element);
            }
            if self.rest().starts_with("<!--") {
                let end = self.rest().find("-->").map(|end| end + 3).unwrap_or(self.rest().len());
                self.place += end;
                let more = self.text_until_tag();
                match element.children.last_mut() {
                    Some(child) => child.tail.get_or_insert_with(String::new).push_str(&more),
                    None => element.text.get_or_insert_with(String::new).push_str(&more),
                }
                continue;
            }
            if self.rest().is_empty() {
                return Err(NotXml(format!("the element {} is not closed", element.tag)));
            }
            element.children.push(self.element()?);
        }
    }

    /// The text before the next tag, or None where there is none, as ElementTree keeps no empty text.
    fn text_until_tag(&mut self) -> String {
        unescaped(&self.until('<'))
    }
}

/// An element's text, or a tail, as ElementTree holds it: None where it is empty.
pub fn tidied(element: &mut Element) {
    element.each_mut(&mut |element| {
        if element.text.as_deref() == Some("") {
            element.text = None;
        }
        if element.tail.as_deref() == Some("") {
            element.tail = None;
        }
    });
}
