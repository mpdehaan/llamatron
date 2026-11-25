// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The song's draws as a scene plays (the Python engine/realizer/registers.py and draws.py). A draw is one process for the
//! whole song, shared by every track, but each track's clip is played on its own. So every clip is first played to note what
//! its steps draw and reset and when; a timeline then draws them in time order, and at one moment in track order, from where
//! the draws stand as the scene starts; and every clip is played again reading it, each step seeing the values at its own
//! moment, after its own draws.

use crate::order::{chosen_move, walk_order};
use crate::statements::Statement;
use llamatron_math::{PythonRandom, Rational};
use llamatron_model::file::data::Data;
use llamatron_model::schema::generated::file_format::DRAW_NAMES;
use std::cell::RefCell;
use std::rc::Rc;

/// Every draw's value, in the draws' order.
pub type Values = [i64; 8];

/// The place of a draw by its name, AD first.
pub fn draw_place(name: &str) -> Option<usize> {
    DRAW_NAMES.iter().position(|found| *found == name)
}

/// What one step does to the draws: at a time in its scene, from the track at a place in the song, the draws it takes, each
/// once, and the draws it resets before it draws.
#[derive(Clone, Debug, PartialEq)]
pub struct Change {
    pub time: Rational,
    pub place: Rational,
    pub draws: Vec<usize>,
    pub resets: Vec<usize>,
}

/// A draw as the set holds it: its direction and its slots.
#[derive(Clone, Debug, PartialEq)]
pub struct Draw {
    direction: String,
    slots: Vec<Option<i64>>,
    pub redraws_in_conditions: bool,
}

impl Draw {
    pub fn of(data: Option<&Data>) -> Draw {
        let written = |name: &str| data.and_then(|data| data.get(name)).filter(|value| !value.is_null());
        Draw {
            direction: written("direction").map(Data::python_str).unwrap_or("forward".to_string()),
            slots: written("slots")
                .and_then(Data::as_list)
                .map(|slots| slots.iter().map(|slot| slot.as_whole().map(|slot| slot as i64)).collect())
                .unwrap_or_default(),
            redraws_in_conditions: written("conditions_redraw") == Some(&Data::Bool(true)),
        }
    }

    pub fn filled_places(&self) -> Vec<usize> {
        (0..self.slots.len()).filter(|place| self.slots[*place].is_some()).collect()
    }
}

/// Where each of the song's draws stands: how far one that repeats exactly has gone, where one that chooses as it goes is,
/// which slots a serial draw has left this round, and each draw's last slot.
#[derive(Clone, Debug, PartialEq)]
pub struct DrawPlay {
    draws: Rc<Vec<Draw>>,
    taken: [Option<usize>; 8],
    places: [Option<i64>; 8],
    rounds: [Option<Vec<usize>>; 8],
    last: [Option<usize>; 8],
}

impl DrawPlay {
    pub fn new(draws: Rc<Vec<Draw>>) -> DrawPlay {
        DrawPlay {
            draws,
            taken: [None; 8],
            places: [None; 8],
            rounds: Default::default(),
            last: [None; 8],
        }
    }

    /// Send a draw back to its first slot, or a serial draw to a new round.
    pub fn reset(&mut self, name: usize) {
        self.taken[name] = None;
        self.places[name] = None;
        self.rounds[name] = None;
    }

    /// Take a draw's next value, by its direction, from the slots that hold one.
    pub fn draw(&mut self, name: usize, chooser: &mut PythonRandom) -> i64 {
        let draw = self.draws[name].clone();
        let filled = draw.filled_places();
        if filled.is_empty() {
            return 0;
        }
        let place = filled[self.next_of(name, filled.len(), &draw.direction, chooser)];
        self.last[name] = Some(place);
        draw.slots[place].unwrap_or(0)
    }

    fn next_of(&mut self, name: usize, count: usize, direction: &str, chooser: &mut PythonRandom) -> usize {
        if direction == "any" || direction == "random" {
            return chooser.randrange_to(count as i128) as usize;
        }
        if direction == "serial" {
            let mut left = self.rounds[name].take().filter(|left| !left.is_empty()).unwrap_or((0..count).collect());
            let taken = left.remove(chooser.randrange_to(left.len() as i128) as usize);
            self.rounds[name] = Some(left);
            return taken;
        }
        if let Some(order) = walk_order(count, direction) {
            let taken = self.taken[name].unwrap_or(0);
            self.taken[name] = Some(taken + 1);
            return order[taken % order.len()];
        }
        let place = match self.places[name] {
            None => 0,
            Some(place) => (place + chosen_move(direction, chooser)).rem_euclid(count as i64),
        };
        self.places[name] = Some(place);
        place as usize
    }

    /// Each draw's last value, 0 for one that has drawn nothing yet.
    pub fn values(&self) -> Values {
        std::array::from_fn(|name| self.last[name].and_then(|place| self.draws[name].slots[place]).unwrap_or(0))
    }

    fn places(&self) -> [Option<usize>; 8] {
        self.last
    }
}

/// The values of every draw through one scene, from what its steps draw.
#[derive(Clone, Debug, PartialEq)]
pub struct Timeline {
    start: Values,
    moments: Vec<(Rational, Rational)>,
    values: Vec<Values>,
    draws: Option<DrawPlay>,
}

impl Timeline {
    /// The timeline the changes make from the values the scene starts with and where its draws stand, None in a song whose
    /// draws hold no value, drawn in time order and at the same time in track order.
    pub fn new(start: Values, changes: &[Change], chooser: &mut PythonRandom, draws: Option<&DrawPlay>) -> Timeline {
        let mut sorted: Vec<&Change> = changes.iter().collect();
        sorted.sort_by_key(|change| (change.time, change.place));
        let mut values = start;
        let mut draws = draws.cloned();
        let mut timeline = Timeline {
            start,
            moments: Vec::new(),
            values: Vec::new(),
            draws: None,
        };
        for change in sorted {
            if let Some(draws) = &mut draws {
                for name in &change.resets {
                    draws.reset(*name);
                }
                for name in &change.draws {
                    values[*name] = draws.draw(*name, chooser);
                }
            }
            timeline.moments.push((change.time, change.place));
            timeline.values.push(values);
        }
        timeline.draws = draws;
        timeline
    }

    /// Every draw's value as a track at a place sees it at a time, after any draw it takes then.
    pub fn values_at(&self, time: Rational, place: Rational) -> Values {
        let found = self.moments.partition_point(|moment| *moment <= (time, place));
        if found == 0 {
            return self.start;
        }
        self.values[found - 1]
    }

    pub fn end_values(&self) -> Values {
        self.values.last().copied().unwrap_or(self.start)
    }

    pub fn end_draws(&self) -> Option<&DrawPlay> {
        self.draws.as_ref()
    }

    /// What a comparison of two settlings of a scene asks: where the draws stand once it is over.
    pub fn end_places(&self) -> Option<[Option<usize>; 8]> {
        self.draws.as_ref().map(DrawPlay::places)
    }
}

/// How far before a track's own change a step takes its draws, and its statements read the values: the first step of a pass
/// after any step before it, and after its own draws.
fn draws_place(first: bool) -> Rational {
    if first {
        Rational::new(2, 5)
    } else {
        Rational::new(3, 4)
    }
}

fn reads_place(first: bool) -> Rational {
    if first {
        Rational::new(3, 10)
    } else {
        Rational::new(1, 2)
    }
}

/// How a clip's steps meet the draws.
pub enum Registers {
    /// Played to note what its steps draw: every step sees no value, which doesn't matter, since what a step draws never
    /// depends on a value.
    Recorder { place: Rational, changes: RefCell<Vec<Change>> },
    /// A finished clip, reading its scene's timeline.
    Reader { place: Rational, timeline: Rc<Timeline> },
    /// The first guess for a clip a statement can end: played as if no other track drew, keeping the values itself.
    Solo {
        place: Rational,
        changes: RefCell<Vec<Change>>,
        values: RefCell<Values>,
        draws: RefCell<Option<Box<DrawPlay>>>,
        chooser: Rc<RefCell<PythonRandom>>,
    },
    /// A later guess, deciding whether it goes on from a guess at the scene's timeline.
    Trial {
        place: Rational,
        changes: RefCell<Vec<Change>>,
        timeline: Rc<Timeline>,
    },
}

impl Registers {
    pub fn recorder(place: usize) -> Registers {
        Registers::Recorder {
            place: Rational::whole(place as i128),
            changes: RefCell::new(Vec::new()),
        }
    }

    pub fn is_counting(&self) -> bool {
        !matches!(self, Registers::Reader { .. })
    }

    fn place(&self) -> Rational {
        match self {
            Registers::Recorder { place, .. } | Registers::Reader { place, .. } | Registers::Solo { place, .. } | Registers::Trial { place, .. } => *place,
        }
    }

    fn changes(&self) -> Option<&RefCell<Vec<Change>>> {
        match self {
            Registers::Recorder { changes, .. } | Registers::Solo { changes, .. } | Registers::Trial { changes, .. } => Some(changes),
            Registers::Reader { .. } => None,
        }
    }

    /// Every change noted, for a clip played to count them.
    pub fn get_changes(&self) -> Vec<Change> {
        self.changes().map(|changes| changes.borrow().clone()).unwrap_or_default()
    }

    /// The values a step sees at a time in the scene.
    pub fn at_step(&self, time: Rational) -> Values {
        match self {
            Registers::Reader { timeline, place } => timeline.values_at(time, *place),
            _ => [0; 8],
        }
    }

    /// The values as a step's statements read them, after its own draws and every earlier track's then; None while nothing
    /// is known of them.
    pub fn before_step(&self, time: Rational, first: bool) -> Option<Values> {
        match self {
            Registers::Recorder { .. } => None,
            Registers::Reader { timeline, place } | Registers::Trial { timeline, place, .. } => Some(timeline.values_at(time, *place - reads_place(first))),
            Registers::Solo { values, .. } => Some(*values.borrow()),
        }
    }

    /// Note the draws a clip resets as it starts.
    pub fn as_clip_starts(&self, resets: &[usize]) {
        let Some(changes) = self.changes() else { return };
        changes.borrow_mut().push(Change {
            time: Rational::ZERO,
            place: self.place() - Rational::new(9, 10),
            draws: Vec::new(),
            resets: resets.to_vec(),
        });
        if let Registers::Solo { draws, .. } = self {
            if let Some(draws) = draws.borrow_mut().as_mut() {
                for name in resets {
                    draws.reset(*name);
                }
            }
        }
    }

    /// Note the draws a step resets and then takes at a time in the scene, just before its statements read the values.
    pub fn before_statements(&self, time: Rational, drawn: &[usize], resets: &[usize], first: bool) {
        let Some(changes) = self.changes() else { return };
        changes.borrow_mut().push(Change {
            time,
            place: self.place() - draws_place(first),
            draws: drawn.to_vec(),
            resets: resets.to_vec(),
        });
        if let Registers::Solo { draws, values, chooser, .. } = self {
            if let Some(draws) = draws.borrow_mut().as_mut() {
                for name in resets {
                    draws.reset(*name);
                }
                for name in drawn {
                    values.borrow_mut()[*name] = draws.draw(*name, &mut chooser.borrow_mut());
                }
            }
        }
    }
}

/// Whether a step's statement holds for the values as the step is reached, which is never while they are not known.
pub fn holds(statement: &Statement, values: Option<Values>) -> bool {
    values.is_some_and(|values| statement.is_true(&values))
}
