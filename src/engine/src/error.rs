// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What can stop a render: a set the program refuses to play, with the reason.

#[derive(Clone, Debug, PartialEq)]
pub enum RenderError {
    Refused(String),
}

pub type Rendered<T> = Result<T, RenderError>;
