// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The check of named values' reader of Rust (.claude/rules/STYLE.md, "Every value with a meaning is named"): each file
//! named on the command line is parsed into its syntax tree, and every literal typed in place is printed, one a line,
//! as `path:line: literal`. A number other than 0 and 1, and a text that is a name (lowercase words joined by
//! underscores, such as `osc2_pitch`), are typed in place unless they stand where a value is given its name: inside a
//! constant or a static, as the whole value of a `let` (a plain value, or a tuple or list of them), or in an attribute.
//! A macro's tokens are read as the expressions they hold, its format text passed over, since a format is shown text.
//!
//! Run with no arguments, it reads the lines of `src/` the working tree adds to the last commit, and every line of a
//! file git does not track yet, so that nothing new breaks the rule while older lines are cleaned; with `--everything`
//! it reads every line of `src/`; with files named, every line of each. It fails where it reports anything. The places
//! where names are defined, and the program's shown texts, are passed over.

use proc_macro2::Span;
use std::collections::{BTreeMap, BTreeSet};
use std::process::{Command, ExitCode};
use syn::punctuated::Punctuated;
use syn::visit::{self, Visit};
use syn::{Expr, ExprLit, Lit, Local, Macro, Token};

/// The numbers that need no name, in their plain sense.
const PLAIN_NUMBERS: [&str; 4] = ["0", "1", "0.0", "1.0"];
/// The separator between words of a name.
const WORD_JOINER: char = '_';
/// The macros whose first argument is a format, shown text the check passes over, and those whose format follows a
/// first argument of their own, such as the condition of `assert!` or the writer of `write!`.
const FORMAT_FIRST: [&str; 9] = [
    "format",
    "print",
    "println",
    "eprint",
    "eprintln",
    "panic",
    "unreachable",
    "todo",
    "unimplemented",
];
const FORMAT_SECOND: [&str; 4] = ["assert", "debug_assert", "write", "writeln"];
const FORMAT_THIRD: [&str; 4] = ["assert_eq", "assert_ne", "debug_assert_eq", "debug_assert_ne"];
/// Where a format stands among a macro's arguments: first, second or third.
const FIRST_PLACE: usize = 0;
const SECOND_PLACE: usize = 1;
const THIRD_PLACE: usize = 2;
/// What the check prints when a file cannot be read or parsed, and when a literal is typed in place; its exits.
const UNREADABLE: &str = "cannot be read";
const UNPARSED: &str = "cannot be parsed";
const TYPED_IN_PLACE: &str = "typed in place: name it (.claude/rules/STYLE.md)";
const COUNTED: &str = "lines type a value in place";
const REPORTED: u8 = 1;
const FAILED: u8 = 2;
/// The flag that reads every line, the folder read, a Rust file's suffix, built output, and the places where names
/// are defined or shown text lives, never read.
const EVERYTHING: &str = "--everything";
const RUST_FOLDER: &str = "src";
const RUST_SUFFIX: &str = ".rs";
const BUILT: &str = "/target/";
const BUILT_FOLDER: &str = "target";
const DEFINING_PLACES: [&str; 5] = [
    "src/names/",
    "src/strings/src/texts/",
    "src/model/src/schema/generated/",
    "src/tracker/src/generated/",
    "src/checks/tests/data/",
];
/// The git commands the check reads a change by: its diff from the last commit with no lines of context, and the files
/// git does not track yet, leaving out what it ignores; and how a diff marks a file, its hunks and its added lines.
const GIT: &str = "git";
const DIFF_ARGUMENTS: [&str; 5] = ["diff", "HEAD", "-U0", "--", RUST_FOLDER];
const UNTRACKED_ARGUMENTS: [&str; 5] = ["ls-files", "--others", "--exclude-standard", "--", RUST_FOLDER];
const ADDED_FILE: &str = "+++ b/";
const OTHER_FILE: &str = "+++ ";
const HUNK: &str = "@@";
const HUNK_START: char = '+';
const ADDED_LINE: &str = "+";

/// The macro that makes a list, whose tokens are an array's or a repeated value's, and the macro that matches a value
/// against a pattern.
const LIST_MACRO: &str = "vec";
const MATCHES_MACRO: &str = "matches";

/// A `matches!`'s tokens: the value, the pattern it is matched against, and the guard after `if`, if any.
fn parse_matches(input: syn::parse::ParseStream) -> syn::Result<(Expr, syn::Pat, Option<Expr>)> {
    let value: Expr = input.parse()?;
    input.parse::<Token![,]>()?;
    let pattern = syn::Pat::parse_multi_with_leading_vert(input)?;
    let guard = if input.peek(Token![if]) {
        input.parse::<Token![if]>()?;
        Some(input.parse::<Expr>()?)
    } else {
        None
    };
    // A trailing comma may close it.
    let _ = input.parse::<Option<Token![,]>>()?;
    Ok((value, pattern, guard))
}

/// A macro's tokens inside square brackets, so that they parse as the array or the repeated value they hold.
fn quote_list(tokens: &proc_macro2::TokenStream) -> proc_macro2::TokenStream {
    let bracketed = proc_macro2::Group::new(proc_macro2::Delimiter::Bracket, tokens.clone());
    proc_macro2::TokenStream::from(proc_macro2::TokenTree::Group(bracketed))
}

/// Whether a text is a name used as a value: lowercase words of letters and digits joined by underscores.
fn is_name(text: &str) -> bool {
    let mut characters = text.chars();
    let starts_with_letter = characters.next().is_some_and(|first| first.is_ascii_lowercase());
    let joined_words = text.split(WORD_JOINER).all(|word| !word.is_empty());
    let lowercase = text
        .chars()
        .all(|character| character.is_ascii_lowercase() || character.is_ascii_digit() || character == WORD_JOINER);
    starts_with_letter && joined_words && lowercase
}

/// A literal as the check reports it, where it is typed in place: a number other than 0 and 1, or a name in quotes.
fn reported(literal: &Lit) -> Option<String> {
    match literal {
        Lit::Int(number) => {
            let digits = number.base10_digits();
            (!PLAIN_NUMBERS.contains(&digits)).then(|| digits.to_string())
        }
        Lit::Float(number) => {
            let digits = number.base10_digits();
            (!PLAIN_NUMBERS.contains(&digits)).then(|| digits.to_string())
        }
        Lit::Str(text) => {
            let value = text.value();
            is_name(&value).then(|| format!("\"{value}\""))
        }
        Lit::ByteStr(bytes) => {
            let value = String::from_utf8_lossy(&bytes.value()).to_string();
            is_name(&value).then(|| format!("b\"{value}\""))
        }
        _ => None,
    }
}

/// Whether an expression is a plain value, which a `let` gives a name: a literal, a negated one, a constant's path,
/// or a tuple or a list of plain values.
fn is_plain(expression: &Expr) -> bool {
    match expression {
        Expr::Lit(_) | Expr::Path(_) => true,
        Expr::Unary(unary) => matches!(*unary.expr, Expr::Lit(_)),
        Expr::Tuple(tuple) => tuple.elems.iter().all(is_plain),
        Expr::Array(array) => array.elems.iter().all(is_plain),
        Expr::Repeat(repeat) => is_plain(&repeat.expr) && is_plain(&repeat.len),
        Expr::Reference(reference) => is_plain(&reference.expr),
        Expr::Paren(inner) => is_plain(&inner.expr),
        _ => false,
    }
}

/// The literals of a file typed in place, each with its line.
struct Finder {
    found: Vec<(usize, String)>,
}

impl Finder {
    /// Note a literal where it is typed in place.
    fn note(&mut self, literal: &Lit, span: Span) {
        if let Some(shown) = reported(literal) {
            self.found.push((span.start().line, shown));
        }
    }

    /// Read a macro's tokens as the expressions they hold, passing over its format text; a macro whose tokens are no
    /// list of expressions, such as one of statements, is read for nothing.
    fn read_macro(&mut self, called: &Macro) {
        let name = called.path.segments.last().map(|segment| segment.ident.to_string()).unwrap_or_default();
        let format_place = if FORMAT_FIRST.contains(&name.as_str()) {
            Some(FIRST_PLACE)
        } else if FORMAT_SECOND.contains(&name.as_str()) {
            Some(SECOND_PLACE)
        } else if FORMAT_THIRD.contains(&name.as_str()) {
            Some(THIRD_PLACE)
        } else {
            None
        };
        // A `matches!` holds a value, a pattern and perhaps a guard, each read.
        if name == MATCHES_MACRO {
            if let Ok((value, pattern, guard)) = called.parse_body_with(parse_matches) {
                self.visit_expr(&value);
                self.visit_pat(&pattern);
                if let Some(guard) = guard {
                    self.visit_expr(&guard);
                }
            }
            return;
        }
        // A list made by `vec!` is read as the array or the repeated value it holds, such as `vec![0.0; 128]`.
        if name == LIST_MACRO {
            let tokens = &called.tokens;
            if let Ok(list) = syn::parse2::<Expr>(quote_list(tokens)) {
                self.visit_expr(&list);
            }
            return;
        }
        let Ok(arguments) = called.parse_body_with(Punctuated::<Expr, Token![,]>::parse_terminated) else {
            return;
        };
        for (place, argument) in arguments.iter().enumerate() {
            let is_format = Some(place) == format_place && matches!(argument, Expr::Lit(ExprLit { lit: Lit::Str(_), .. }));
            if !is_format {
                self.visit_expr(argument);
            }
        }
    }
}

impl<'tree> Visit<'tree> for Finder {
    /// A literal in an expression.
    fn visit_expr_lit(&mut self, literal: &'tree ExprLit) {
        self.note(&literal.lit, literal.lit.span());
    }

    /// A constant gives its values their names: nothing inside it is read.
    fn visit_item_const(&mut self, _constant: &'tree syn::ItemConst) {}

    /// A static gives its values their names, as a constant does.
    fn visit_item_static(&mut self, _static_item: &'tree syn::ItemStatic) {}

    /// An associated constant, inside an `impl`, gives its value its name too.
    fn visit_impl_item_const(&mut self, _constant: &'tree syn::ImplItemConst) {}

    /// An attribute's literals configure the compiler, and are passed over.
    fn visit_attribute(&mut self, _attribute: &'tree syn::Attribute) {}

    /// A `let` whose whole value is plain gives it a name; any other's value is read.
    fn visit_local(&mut self, local: &'tree Local) {
        if let Some(init) = &local.init {
            if is_plain(&init.expr) && init.diverge.is_none() {
                // The value is named, but a type the name is given, such as a list's length, is still read.
                self.visit_pat(&local.pat);
                return;
            }
        }
        visit::visit_local(self, local);
    }

    /// A macro's arguments, in an expression or a statement.
    fn visit_macro(&mut self, called: &'tree Macro) {
        self.read_macro(called);
    }
}

/// Every literal a file types in place, each with its line and its literals joined, or why the file cannot be read.
fn typed_in_place(path: &str) -> Result<BTreeMap<usize, Vec<String>>, String> {
    let text = std::fs::read_to_string(path).map_err(|_| format!("{path}: {UNREADABLE}"))?;
    let tree = syn::parse_file(&text).map_err(|problem| format!("{path}: {UNPARSED}: {problem}"))?;
    let mut finder = Finder { found: Vec::new() };
    finder.visit_file(&tree);
    let mut by_line: BTreeMap<usize, Vec<String>> = BTreeMap::new();
    for (line, literal) in finder.found {
        by_line.entry(line).or_default().push(literal);
    }
    Ok(by_line)
}

/// Whether a file is one the check reads: Rust, not built output, and no place where names are defined.
fn is_read(path: &str) -> bool {
    path.ends_with(RUST_SUFFIX) && !path.contains(BUILT) && !DEFINING_PLACES.iter().any(|place| path.starts_with(place))
}

/// What a git command prints.
fn git(arguments: &[&str]) -> String {
    Command::new(GIT)
        .args(arguments)
        .output()
        .map(|output| String::from_utf8_lossy(&output.stdout).to_string())
        .unwrap_or_default()
}

/// The lines the working tree adds to the last commit, by file, and every file git does not track yet, whose every
/// line counts, as None.
fn added_lines() -> BTreeMap<String, Option<BTreeSet<usize>>> {
    let mut lines: BTreeMap<String, Option<BTreeSet<usize>>> = BTreeMap::new();
    let (mut path, mut number) = (None::<String>, 0);
    for line in git(&DIFF_ARGUMENTS).lines() {
        if let Some(file) = line.strip_prefix(ADDED_FILE) {
            path = Some(file.to_string());
        } else if line.starts_with(OTHER_FILE) {
            path = None;
        } else if line.starts_with(HUNK) {
            let start = line.split(' ').find_map(|part| part.strip_prefix(HUNK_START));
            number = start
                .and_then(|start| start.split(',').next())
                .and_then(|first| first.parse().ok())
                .unwrap_or(0);
        } else if line.starts_with(ADDED_LINE) {
            if let Some(file) = &path {
                lines
                    .entry(file.clone())
                    .or_insert_with(|| Some(BTreeSet::new()))
                    .get_or_insert_with(BTreeSet::new)
                    .insert(number);
            }
            number += 1;
        }
    }
    for file in git(&UNTRACKED_ARGUMENTS).lines() {
        lines.insert(file.to_string(), None);
    }
    lines
}

/// Every Rust file under the folder read.
fn every_file(folder: &std::path::Path, files: &mut Vec<String>) {
    let Ok(entries) = std::fs::read_dir(folder) else { return };
    for entry in entries.flatten() {
        let path = entry.path();
        let is_built = path.file_name().is_some_and(|name| name == BUILT_FOLDER);
        if path.is_dir() && !is_built {
            every_file(&path, files);
        } else if let Some(text) = path.to_str() {
            files.push(text.to_string());
        }
    }
}

/// Report the literals typed in place in the lines chosen, by file, and how many lines report one where every line
/// is read; fail where any does or a file cannot be read.
fn main() -> ExitCode {
    let arguments: Vec<String> = std::env::args().skip(1).collect();
    let everything = arguments.iter().any(|argument| argument == EVERYTHING);
    let named: Vec<&String> = arguments.iter().filter(|argument| *argument != EVERYTHING).collect();
    let chosen: BTreeMap<String, Option<BTreeSet<usize>>> = if everything {
        let mut files = Vec::new();
        every_file(std::path::Path::new(RUST_FOLDER), &mut files);
        files.into_iter().map(|file| (file, None)).collect()
    } else if !named.is_empty() {
        named.into_iter().map(|file| (file.clone(), None)).collect()
    } else {
        added_lines()
    };
    let (mut reported, mut unreadable) = (0, false);
    for (path, lines) in &chosen {
        if !is_read(path) {
            continue;
        }
        match typed_in_place(path) {
            Ok(by_line) => {
                for (line, literals) in by_line {
                    if lines.as_ref().is_none_or(|lines| lines.contains(&line)) {
                        println!("{path}:{line}: {} {TYPED_IN_PLACE}", literals.join(", "));
                        reported += 1;
                    }
                }
            }
            Err(problem) => {
                eprintln!("{problem}");
                unreadable = true;
            }
        }
    }
    if everything {
        println!("{reported} {COUNTED}");
    }
    if unreadable {
        ExitCode::from(FAILED)
    } else if reported > 0 {
        ExitCode::from(REPORTED)
    } else {
        ExitCode::SUCCESS
    }
}
