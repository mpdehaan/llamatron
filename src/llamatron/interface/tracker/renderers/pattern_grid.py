# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How the tracker draws the pattern editor's grid (interface/forms/pattern_grid.py): rules in box characters, with a double
joint where a step starts a beat and the cursor's cell boxed in bold double rules, the line of step numbers, and the rows
view's rows, a label column and a cell per step, the cursor's cell reversed and a blocked cell's mark dim.

A joint where the beat edge crosses a dim rule is plain, between the two, so that neither line reads as broken: a bold cross
showed as a break in the rule at every beat, and a dim one as a break in the beat edge at every rule and section heading, both
of which were seen once. Every crossing is read after a change to a drawing (.claude/UX.md).
"""

from rich.text import Text

from llamatron.interface.forms import pattern_grid
from llamatron.interface.tracker import drawing
from llamatron.interface.tracker.drawing import Align, Box, fit, Style
from llamatron.user_strings import labels

# Each kind of rule's pieces: its left end, its joint, its joint at a beat, its right end, its line, and where it edges the
# cursor's box, the joint at the box's ends and the right end where the box's right bar is the grid's border.
RULE_PIECES = {
    pattern_grid.TOP: (Box.TOP_LEFT, Box.TOP_TEE, Box.DOUBLE_TOP_TEE, Box.TOP_RIGHT, Box.RULE, None, None),
    pattern_grid.INNER: (Box.LEFT_TEE, Box.CROSS, Box.DOUBLE_CROSS, Box.RIGHT_TEE, Box.RULE, Box.DOUBLE_RULE_DOUBLE_CROSS, Box.DOUBLE_RULE_DOUBLE_RIGHT_TEE),
    pattern_grid.BOTTOM: (Box.BOTTOM_LEFT, Box.BOTTOM_TEE, Box.DOUBLE_BOTTOM_TEE, Box.BOTTOM_RIGHT, Box.RULE, Box.DOUBLE_RULE_DOUBLE_BOTTOM_TEE, Box.DOUBLE_BOTTOM_RIGHT),
    pattern_grid.CLOSING: (Box.LEFT_TEE, Box.BOTTOM_TEE, Box.DOUBLE_BOTTOM_TEE, Box.RIGHT_TEE, Box.RULE, None, None),
    pattern_grid.OPENING: (Box.LEFT_TEE, Box.TOP_TEE, Box.DOUBLE_TOP_TEE, Box.RIGHT_TEE, Box.RULE, None, None),
    pattern_grid.PLAIN: (Box.LEFT_TEE, Box.CROSS, Box.DOUBLE_CROSS, Box.RIGHT_TEE, Box.RULE, None, None),
    pattern_grid.HEADING: (
        Box.DOUBLE_RULE_LEFT_TEE, Box.DOUBLE_RULE_CROSS, Box.DOUBLE_RULE_DOUBLE_CROSS, Box.DOUBLE_RULE_RIGHT_TEE, Box.DOUBLE_RULE,
        Box.DOUBLE_RULE_DOUBLE_CROSS, Box.DOUBLE_RULE_DOUBLE_RIGHT_TEE,
    ),
}
LABEL_STYLES = {pattern_grid.PLAIN_LABEL: Style.PLAIN, pattern_grid.BOLD_LABEL: Style.BOLD, pattern_grid.REVERSED_LABEL: Style.REVERSE}


def rule_line(*, rule, label_width):
    """Return a rule across the grid. When the rule edges the cursor's cell, the piece over or under the cell is a bold double
    rule, joined to the cell's double bars at both ends, or at the grid's border, so that the cursor's cell is boxed on that
    side too, since the single rule between the double joints read as the wrong corners."""
    left, tee, beat_tee, right, line_character, boxed_tee, boxed_right = RULE_PIECES[rule.kind]
    boxed = rule.boxed
    # The line has no style of its own, so that a plain joint stays plain among the dim pieces.
    line = Text(no_wrap=True)
    line.append(left + line_character * label_width, style=Style.DIM)
    for step in range(rule.first, rule.last):
        if boxed is not None and step in (boxed, boxed + 1):
            line.append(boxed_tee, style=Style.PLAIN)
        elif not rule.joints:
            line.append(line_character, style=Style.DIM)
        elif step in rule.beats:
            line.append(beat_tee, style=Style.PLAIN)
        else:
            line.append(tee, style=Style.DIM)
        if step == boxed:
            line.append(Box.DOUBLE_RULE * pattern_grid.CELL_WIDTH, style=Style.SELECTED_EDGE)
        else:
            line.append(line_character * pattern_grid.CELL_WIDTH, style=Style.DIM)
    if boxed is not None and boxed + 1 == rule.last:
        line.append(boxed_right, style=Style.PLAIN)
    else:
        line.append(right, style=Style.DIM)
    return line


def append_edge(*, line, step, beats, replaced=None):
    """Add a step's left edge to a line: a plain double line where the step starts a beat, beside the dim single lines, so the
    beats stand out as columns, unless a bar runs through it. Never bold, since many fonts draw bold double lines short of the
    next line."""
    if isinstance(replaced, Text):
        line.append_text(replaced)
    elif replaced is not None:
        line.append(replaced)
    elif step in beats:
        line.append(Box.DOUBLE_BAR, style=Style.PLAIN)
    else:
        line.append(Box.BAR, style=Style.DIM)


def step_numbers_line(*, numbers, label_width):
    """Return the line of step numbers, the number of the step that sounds in the read head's light yellow, a beat's bold."""
    head = Text(no_wrap=True)
    head.append(Box.BAR, style=Style.DIM)
    head.append(fit(text=labels.MSG_STEP_HEADING, width=label_width), style=Style.BOLD)
    for step in range(numbers.first, numbers.last):
        append_edge(line=head, step=step, beats=numbers.beats)
        style = Style.READ_HEAD if step == numbers.sounding else (Style.BOLD if step in numbers.beats else Style.PLAIN)
        head.append(fit(text=str(step + 1), width=pattern_grid.CELL_WIDTH, align=Align.CENTER), style=style)
    head.append(Box.BAR, style=Style.DIM)
    return head


def row_lines(*, row, label_width):
    """Return a row's lines: its labels, and each step's cells, the cursor's reversed on the line that holds the value; a
    section's heading has no cells, so no divider crosses it."""
    lines = []
    for number, label in enumerate(row.labels):
        line = Text(no_wrap=True)
        line.append(Box.BAR, style=Style.DIM)
        line.append(fit(text=drawing.SPACE + label, width=label_width), style=LABEL_STYLES[row.label_kinds[number]])
        if row.heading:
            # The dividers above end in the rule over the heading and the ones below start in the rule under it.
            line.append(drawing.SPACE * ((row.last - row.first) * (pattern_grid.CELL_WIDTH + 1)))
            line.append(Box.BAR, style=Style.DIM)
            lines.append(line)
            continue
        for step in range(row.first, row.last):
            append_edge(line=line, step=step, beats=row.beats)
            text = fit(text=row.cells[step - row.first][number], width=pattern_grid.CELL_WIDTH, align=Align.CENTER)
            selected = row.selected == (step, number)
            # A blocked cell's mark is dim, so that the values stand out from the places that can't hold one.
            line.append(text, style=Style.REVERSE if selected else (Style.DIM if step in row.blocked else Style.PLAIN))
        line.append(Box.BAR, style=Style.DIM)
        lines.append(line)
    return lines
