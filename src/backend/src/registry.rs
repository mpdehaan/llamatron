// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The registries: every component the built-in synths offer is an entry in its kind's registry, the one place it is
//! built from, by the name a spec gives it. A name no registry holds builds nothing rather than falling through to
//! another kind, and the tests walk the registries, so that a component exists for the program only once registered.

/// One registered component: the name a spec gives it, the file in its kind's folder that holds it, and how it is built.
pub struct Entry<Build: 'static> {
    pub name: &'static str,
    pub file: &'static str,
    pub build: Build,
}

/// The entry a registry holds under a name, if any.
pub fn find<Build>(entries: &'static [Entry<Build>], name: &str) -> Option<&'static Entry<Build>> {
    entries.iter().find(|entry| entry.name == name)
}

/// Every registry with its kind's folder, for the tests that hold each folder's files to its registry.
#[cfg(test)]
pub fn folders() -> Vec<(&'static str, Vec<&'static str>, &'static [&'static str])> {
    vec![(
        "effects",
        crate::effects::REGISTRY.iter().map(|entry| entry.file).collect(),
        crate::effects::HELPERS,
    )]
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Every file in a component folder is a registered component's or one of the helpers its kind declares, and every
    /// registered file exists: a component added but never registered, or registered but never written, fails here.
    #[test]
    fn every_component_file_is_registered() {
        let source = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("src");
        let shared = "mod.rs";
        for (folder, registered, helpers) in folders() {
            let mut files: Vec<String> = std::fs::read_dir(source.join(folder))
                .unwrap_or_else(|problem| panic!("the {folder} folder: {problem}"))
                .filter_map(|entry| entry.ok().map(|entry| entry.file_name().to_string_lossy().to_string()))
                .filter(|name| name.ends_with(".rs") && name != shared)
                .collect();
            files.sort();
            for file in &files {
                let known = registered.contains(&file.as_str()) || helpers.contains(&file.as_str());
                assert!(known, "{folder}/{file} is in no registry and is no declared helper");
            }
            for file in &registered {
                assert!(
                    *file == shared || files.iter().any(|found| found == file),
                    "{folder}/{file} is registered but missing"
                );
            }
        }
    }
}
