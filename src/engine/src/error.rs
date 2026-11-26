// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What can stop a render: a set the program refuses to play, with the reason, or a part of the render not ported from the
//! Python yet, named, so that the comparison harness counts such a set apart from one that plays differently.

#[derive(Clone, Debug, PartialEq)]
pub enum RenderError {
    Refused(String),
    NotPorted(String),
}

impl RenderError {
    pub fn not_ported(what: &str) -> RenderError {
        RenderError::NotPorted(what.to_string())
    }
}

pub type Rendered<T> = Result<T, RenderError>;
