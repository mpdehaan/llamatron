// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! llamatron reads every plain scalar as PyYAML reads it: tests/data/yaml_scalar_cases.txt, written by
//! internal_tools/yaml_scalar_cases.py from PyYAML itself.

use llamatron_model::file::data::{resolved, Data};

const CASES: &str = include_str!("data/yaml_scalar_cases.txt");

fn kind_and_repr(data: &Data) -> (String, String) {
    match data {
        Data::Null => ("null".into(), "None".into()),
        Data::Bool(flag) => ("bool".into(), if *flag { "True" } else { "False" }.into()),
        Data::Whole(whole) => ("int".into(), whole.to_string()),
        Data::Float(float) if float.is_nan() => ("float".into(), "nan".into()),
        Data::Float(float) if float.is_infinite() => ("float".into(), if *float > 0.0 { "inf" } else { "-inf" }.into()),
        Data::Float(float) => ("float".into(), llamatron_math::number::python_float_text(*float)),
        Data::Text(text) => ("str".into(), format!("'{text}'")),
        _ => ("other".into(), String::new()),
    }
}

#[test]
fn every_plain_scalar_reads_as_pyyaml_reads_it() {
    let mut wrong = Vec::new();
    for line in CASES.lines() {
        let fields: Vec<&str> = line.split('\t').collect();
        let [text, kind, repr] = fields[..] else {
            panic!("a case of the wrong shape: {line:?}")
        };
        let (found_kind, found_repr) = kind_and_repr(&resolved(text));
        if (found_kind.as_str(), found_repr.as_str()) != (kind, repr) {
            wrong.push(format!("{text:?}: PyYAML {kind} {repr}, here {found_kind} {found_repr}"));
        }
    }
    assert!(wrong.is_empty(), "{}", wrong.join("\n"));
}
