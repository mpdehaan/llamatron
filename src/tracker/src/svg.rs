// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A screen drawn as an SVG picture of a terminal window, as the documents' screenshots show it: the same picture, tag for
//! tag and number for number, that Rich's export_svg drew of the same screen, so that a screenshot changes only where the
//! screen does. A screen is its lines, each a row of pieces of text with the style each is written in.
//!
//! The arithmetic follows Rich's operation for operation, since a float printed differently would change every file.

use llamatron_math::number::python_float_text;
use llamatron_names::file_format;
use llamatron_names::words;

/// A colour as red, green and blue.
type Rgb = (u8, u8, u8);

/// The terminal's colours the picture is drawn in: Rich's SVG export theme, its background, its foreground, and its sixteen
/// numbered colours.
const BACKGROUND: Rgb = (41, 41, 41);
const FOREGROUND: Rgb = (197, 200, 198);
const NUMBERED: [Rgb; 16] = [
    (75, 78, 85),
    (204, 85, 90),
    (152, 168, 75),
    (208, 179, 68),
    (96, 138, 177),
    (152, 114, 159),
    (104, 160, 179),
    (197, 200, 198),
    (154, 155, 153),
    (255, 38, 39),
    (0, 130, 61),
    (208, 132, 66),
    (25, 132, 233),
    (255, 44, 122),
    (57, 130, 128),
    (253, 253, 197),
];
/// The named colours a style may say, by their number among the numbered ones.
const NAMED: [(&str, usize); 8] = [
    (words::BLACK, 0),
    (words::RED, 1),
    (words::GREEN, 2),
    (words::YELLOW, 3),
    (words::BLUE, 4),
    (words::MAGENTA, 5),
    (words::CYAN, 6),
    (words::WHITE, 7),
];
/// How far dim text is blended toward the background.
const DIM_BLEND: f64 = 0.4;
const CHAR_HEIGHT: i64 = 20;
const FONT_ASPECT_RATIO: f64 = 0.61;
const LINE_HEIGHT_RATIO: f64 = 1.22;
const MARGIN: i64 = 1;
const PADDING_TOP: i64 = 40;
const PADDING_SIDE: i64 = 8;
const PADDING_BOTTOM: i64 = 8;
/// A line's clip and background rectangles reach this far past the line, so that neighbouring lines meet.
const LINE_OVERLAP: f64 = 0.25;
const LINE_TOP: f64 = 1.5;

/// A colour a style names: none, the terminal's own, or a colour of its own.
#[derive(Clone, Copy, PartialEq)]
enum Colour {
    Unset,
    Default,
    Exact(Rgb),
}

/// A style as a screen's pieces write it, such as `bold reverse #00ff00 on default`.
struct PieceStyle {
    bold: bool,
    dim: bool,
    italic: bool,
    underline: bool,
    strike: bool,
    reverse: bool,
    colour: Colour,
    background: Colour,
}

impl PieceStyle {
    /// Read a style as Rich writes one: its attributes and its colour, then `on` and its background.
    fn parse(text: &str) -> PieceStyle {
        let mut style = PieceStyle {
            bold: false,
            dim: false,
            italic: false,
            underline: false,
            strike: false,
            reverse: false,
            colour: Colour::Unset,
            background: Colour::Unset,
        };
        let mut after_on = false;
        for word in text.split_whitespace() {
            match word {
                file_format::LfoSetting::ON => after_on = true,
                words::BOLD => style.bold = true,
                file_format::ChordSymbol::DIMINISHED => style.dim = true,
                words::ITALIC => style.italic = true,
                words::UNDERLINE => style.underline = true,
                file_format::VactrolLight::STRIKE => style.strike = true,
                words::REVERSE => style.reverse = true,
                colour if after_on => style.background = colour_named(colour),
                colour => style.colour = colour_named(colour),
            }
        }
        style
    }

    /// The CSS of the text's class: its fill, then bold and the rest, as Rich writes them.
    fn css(&self) -> String {
        let mut colour = exact_or(self.colour, FOREGROUND);
        let mut background = exact_or(self.background, BACKGROUND);
        if self.reverse {
            std::mem::swap(&mut colour, &mut background);
        }
        if self.dim {
            colour = blended(colour, background, DIM_BLEND);
        }
        let mut rules = vec![format!("fill: {}", hex(colour))];
        if self.bold {
            rules.push("font-weight: bold".to_string());
        }
        if self.italic {
            rules.push("font-style: italic;".to_string());
        }
        if self.underline {
            rules.push("text-decoration: underline;".to_string());
        }
        if self.strike {
            rules.push("text-decoration: line-through;".to_string());
        }
        rules.join(";")
    }

    /// The colour of the rectangle behind the text, or None where the text has no background of its own.
    fn background_fill(&self) -> Option<Rgb> {
        if self.reverse {
            return Some(exact_or(self.colour, FOREGROUND));
        }
        match self.background {
            Colour::Exact(rgb) => Some(rgb),
            _ => None,
        }
    }
}

/// The SVG of a screen of a width, its window titled, its ids prefixed with unique_id.
pub fn screen_svg(lines: &[Vec<(String, String)>], width: usize, title: &str, unique_id: &str) -> String {
    let char_width = CHAR_HEIGHT as f64 * FONT_ASPECT_RATIO;
    let line_height = CHAR_HEIGHT as f64 * LINE_HEIGHT_RATIO;
    let mut backgrounds = String::new();
    let mut matrix = String::new();
    let mut classes: Vec<String> = Vec::new();
    let mut last_line = 0;
    for (y, line) in lines.iter().map(|line| joined(line)).enumerate() {
        last_line = y;
        let mut x = 0usize;
        // Rich records the newline that ends every line but the last as a piece of its own, in no style.
        let newline = [("\n".to_string(), String::new())];
        let ending: &[(String, String)] = if y + 1 < lines.len() { &newline } else { &[] };
        for (text, style_text) in line.iter().chain(ending) {
            let style = PieceStyle::parse(style_text);
            let css = style.css();
            let number = match classes.iter().position(|known| *known == css) {
                Some(place) => place + 1,
                None => {
                    classes.push(css);
                    classes.len()
                }
            };
            let cells = text.chars().count();
            if let Some(fill) = style.background_fill() {
                backgrounds.push_str(&format!(
                    "<rect fill=\"{}\" x=\"{}\" y=\"{}\" width=\"{}\" height=\"{}\" shape-rendering=\"crispEdges\"/>",
                    hex(fill),
                    general(x as f64 * char_width),
                    general(y as f64 * line_height + LINE_TOP),
                    general(char_width * cells as f64),
                    general(line_height + LINE_OVERLAP)
                ));
            }
            if !text.is_empty() && text.chars().any(|character| character != ' ') {
                matrix.push_str(&format!(
                    "<text class=\"{unique_id}-r{number}\" x=\"{}\" y=\"{}\" textLength=\"{}\" clip-path=\"url(#{unique_id}-line-{y})\">{}</text>",
                    general(x as f64 * char_width),
                    general(y as f64 * line_height + CHAR_HEIGHT as f64),
                    general(char_width * cells as f64),
                    escaped(text)
                ));
            }
            x += cells;
        }
    }
    // Rich gives every line but the last a clip of its own.
    let clips: Vec<String> = (0..last_line)
        .map(|line| {
            format!(
                "<clipPath id=\"{unique_id}-line-{line}\">\n    <rect x=\"0\" y=\"{}\" width=\"{}\" height=\"{}\"/>\n            </clipPath>",
                general(line as f64 * line_height + LINE_TOP),
                general(char_width * width as f64),
                general(line_height + LINE_OVERLAP)
            )
        })
        .collect();
    let styles: Vec<String> = classes
        .iter()
        .enumerate()
        .map(|(place, css)| format!(".{unique_id}-r{} {{ {css} }}", place + 1))
        .collect();
    let terminal_width = (width as f64 * char_width + (PADDING_SIDE * 2) as f64).ceil() as i64;
    let terminal_height = (last_line + 1) as f64 * line_height + (PADDING_TOP + PADDING_BOTTOM) as f64;
    let chrome = format!(
        "<rect fill=\"{}\" stroke=\"rgba(255,255,255,0.35)\" stroke-width=\"1\" x=\"{MARGIN}\" y=\"{MARGIN}\" width=\"{terminal_width}\" height=\"{}\" rx=\"8\"/><text class=\"{unique_id}-title\" fill=\"{}\" text-anchor=\"middle\" x=\"{}\" y=\"{}\">{}</text>\n            <g transform=\"translate(26,22)\">\n            <circle cx=\"0\" cy=\"0\" r=\"7\" fill=\"#ff5f57\"/>\n            <circle cx=\"22\" cy=\"0\" r=\"7\" fill=\"#febc2e\"/>\n            <circle cx=\"44\" cy=\"0\" r=\"7\" fill=\"#28c840\"/>\n            </g>\n        ",
        hex(BACKGROUND),
        general(terminal_height),
        hex(FOREGROUND),
        terminal_width / 2,
        MARGIN + CHAR_HEIGHT + 6,
        escaped(title)
    );
    let view_width = terminal_width + MARGIN * 2;
    let view_height = terminal_height + (MARGIN * 2) as f64;
    let clip_width = char_width * width as f64 - 1.0;
    let clip_height = (last_line + 1) as f64 * line_height - 1.0;
    format!(
        "<svg class=\"rich-terminal\" viewBox=\"0 0 {view_width} {}\" xmlns=\"http://www.w3.org/2000/svg\">
    <!-- Generated with Rich https://www.textualize.io -->
    <style>

    @font-face {{
        font-family: \"Fira Code\";
        src: local(\"FiraCode-Regular\"),
                url(\"https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff2/FiraCode-Regular.woff2\") format(\"woff2\"),
                url(\"https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff/FiraCode-Regular.woff\") format(\"woff\");
        font-style: normal;
        font-weight: 400;
    }}
    @font-face {{
        font-family: \"Fira Code\";
        src: local(\"FiraCode-Bold\"),
                url(\"https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff2/FiraCode-Bold.woff2\") format(\"woff2\"),
                url(\"https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff/FiraCode-Bold.woff\") format(\"woff\");
        font-style: bold;
        font-weight: 700;
    }}

    .{unique_id}-matrix {{
        font-family: Fira Code, monospace;
        font-size: {CHAR_HEIGHT}px;
        line-height: {}px;
        font-variant-east-asian: full-width;
    }}

    .{unique_id}-title {{
        font-size: 18px;
        font-weight: bold;
        font-family: arial;
    }}

    {}
    </style>

    <defs>
    <clipPath id=\"{unique_id}-clip-terminal\">
      <rect x=\"0\" y=\"0\" width=\"{}\" height=\"{}\" />
    </clipPath>
    {}
    </defs>

    {chrome}
    <g transform=\"translate({}, {})\" clip-path=\"url(#{unique_id}-clip-terminal)\">
    {backgrounds}
    <g class=\"{unique_id}-matrix\">
    {matrix}
    </g>
    </g>
</svg>
",
        python_float_text(view_height),
        python_float_text(line_height),
        styles.join("\n"),
        python_float_text(clip_width),
        python_float_text(clip_height),
        clips.join("\n"),
        MARGIN + PADDING_SIDE,
        MARGIN + PADDING_TOP
    )
}

/// A colour a style's word names.
fn colour_named(word: &str) -> Colour {
    if word == words::DEFAULT {
        return Colour::Default;
    }
    if let Some(hex) = word.strip_prefix('#') {
        let part = |at: usize| u8::from_str_radix(hex.get(at..at + 2).unwrap_or("00"), 16).unwrap_or(0);
        return Colour::Exact((part(0), part(2), part(4)));
    }
    if let Some(inner) = word.strip_prefix("rgb(").and_then(|rest| rest.strip_suffix(')')) {
        let parts: Vec<u8> = inner.split(',').map(|part| part.trim().parse().unwrap_or(0)).collect();
        return Colour::Exact((
            parts.first().copied().unwrap_or(0),
            parts.get(1).copied().unwrap_or(0),
            parts.get(2).copied().unwrap_or(0),
        ));
    }
    if let Some(number) = word.strip_prefix("color(").and_then(|rest| rest.strip_suffix(')')) {
        let number: usize = number.parse().unwrap_or(0);
        return Colour::Exact(NUMBERED[number.min(NUMBERED.len() - 1)]);
    }
    match NAMED.iter().find(|(name, _)| *name == word) {
        Some((_, number)) => Colour::Exact(NUMBERED[*number]),
        None => Colour::Default,
    }
}

/// A colour of its own, or the one the terminal gives where there is none.
fn exact_or(colour: Colour, terminal: Rgb) -> Rgb {
    match colour {
        Colour::Exact(rgb) => rgb,
        Colour::Unset | Colour::Default => terminal,
    }
}

/// One colour blended part of the way toward another, each channel cut to a whole number as Rich cuts it.
fn blended(from: Rgb, to: Rgb, part: f64) -> Rgb {
    let channel = |a: u8, b: u8| (a as f64 + (b as f64 - a as f64) * part) as u8;
    (channel(from.0, to.0), channel(from.1, to.1), channel(from.2, to.2))
}

/// A colour as `#rrggbb`.
fn hex(rgb: Rgb) -> String {
    format!("#{:02x}{:02x}{:02x}", rgb.0, rgb.1, rgb.2)
}

/// A text made safe in a tag: HTML's five marks escaped as Python's html.escape escapes them, and each space a no-break
/// space, so that runs of spaces keep their width.
fn escaped(text: &str) -> String {
    let mut out = String::new();
    for character in text.chars() {
        match character {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            '\'' => out.push_str("&#x27;"),
            ' ' => out.push_str("&#160;"),
            other => out.push(other),
        }
    }
    out
}

/// A number written as Python's format(number, "g") writes it: six significant digits, trailing zeros dropped.
fn general(number: f64) -> String {
    if number == 0.0 {
        return "0".to_string();
    }
    let exponent = number.abs().log10().floor() as i32;
    let written = if (-4..6).contains(&exponent) {
        let decimals = (5 - exponent).max(0) as usize;
        format!("{number:.decimals$}")
    } else {
        format!("{number:.5e}")
    };
    if written.contains('e') || !written.contains('.') {
        return written;
    }
    written.trim_end_matches('0').trim_end_matches('.').to_string()
}

/// A line's pieces as the terminal holds them: empty pieces left out, since a terminal draws nothing of them.
fn joined(line: &[(String, String)]) -> Vec<(String, String)> {
    line.iter().filter(|(text, _)| !text.is_empty()).cloned().collect()
}
