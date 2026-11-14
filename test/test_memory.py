# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""The memory of answers: an answer is kept until something it was worked out from changes, and a memory can check itself."""

import unittest

from llamatron.support.memory import MAX_ANSWERS, Memory, StaleAnswer
from llamatron.support.revised import ChangeMark

QUESTION = 'question'
OTHER_QUESTION = 'other question'
FIRST_ANSWER = 'first'
SECOND_ANSWER = 'second'


class Counted:
    """Works an answer out and counts how many times it was asked to."""

    __slots__ = ('answer', 'times')

    def __init__(self, answer):
        self.answer = answer
        self.times = 0

    def compute(self):
        self.times += 1
        return self.answer


class TestMemory(unittest.TestCase):

    def setUp(self):
        self.memory = Memory(checks=False)
        self.thing = ChangeMark()
        self.other = ChangeMark()

    def test_an_answer_is_worked_out_once_while_nothing_it_came_from_changes(self):
        counted = Counted(FIRST_ANSWER)
        for _ in range(3):
            self.assertEqual(self.memory.remembered(key=QUESTION, on=(self.thing,), compute=counted.compute), FIRST_ANSWER)
        self.assertEqual(counted.times, 1)

    def test_an_answer_is_worked_out_again_when_a_thing_it_came_from_changes(self):
        counted = Counted(FIRST_ANSWER)
        self.memory.remembered(key=QUESTION, on=(self.thing, self.other), compute=counted.compute)
        self.other.note_change()
        counted.answer = SECOND_ANSWER
        self.assertEqual(self.memory.remembered(key=QUESTION, on=(self.thing, self.other), compute=counted.compute), SECOND_ANSWER)
        self.assertEqual(counted.times, 2)

    def test_a_change_to_something_else_leaves_an_answer_alone(self):
        counted = Counted(FIRST_ANSWER)
        self.memory.remembered(key=QUESTION, on=(self.thing,), compute=counted.compute)
        self.other.note_change()
        self.memory.remembered(key=QUESTION, on=(self.thing,), compute=counted.compute)
        self.assertEqual(counted.times, 1)

    def test_another_thing_under_the_same_key_is_a_change(self):
        # A pattern replaced by another of the same name is another object, whose revision nothing else has had.
        counted = Counted(FIRST_ANSWER)
        self.memory.remembered(key=QUESTION, on=(self.thing,), compute=counted.compute)
        self.memory.remembered(key=QUESTION, on=(ChangeMark(),), compute=counted.compute)
        self.assertEqual(counted.times, 2)

    def test_each_key_has_its_own_answer(self):
        self.memory.remembered(key=QUESTION, on=(self.thing,), compute=Counted(FIRST_ANSWER).compute)
        self.memory.remembered(key=OTHER_QUESTION, on=(self.thing,), compute=Counted(SECOND_ANSWER).compute)
        self.assertEqual(self.memory.remembered(key=QUESTION, on=(self.thing,), compute=Counted(None).compute), FIRST_ANSWER)
        self.assertEqual(self.memory.remembered(key=OTHER_QUESTION, on=(self.thing,), compute=Counted(None).compute), SECOND_ANSWER)
        self.assertEqual(self.memory.count(), 2)

    def test_an_answer_of_none_is_kept_like_any_other(self):
        counted = Counted(None)
        self.memory.remembered(key=QUESTION, on=(self.thing,), compute=counted.compute)
        self.assertIsNone(self.memory.remembered(key=QUESTION, on=(self.thing,), compute=counted.compute))
        self.assertEqual(counted.times, 1)

    def test_forgetting_drops_every_answer(self):
        counted = Counted(FIRST_ANSWER)
        self.memory.remembered(key=QUESTION, on=(self.thing,), compute=counted.compute)
        self.memory.forget()
        self.assertEqual(self.memory.count(), 0)
        self.memory.remembered(key=QUESTION, on=(self.thing,), compute=counted.compute)
        self.assertEqual(counted.times, 2)

    def test_a_full_memory_forgets_everything_and_goes_on(self):
        counted = Counted(FIRST_ANSWER)
        for number in range(MAX_ANSWERS):
            self.memory.remembered(key=number, on=(self.thing,), compute=counted.compute)
        self.assertEqual(self.memory.count(), MAX_ANSWERS)
        # Under the limit every answer was kept: asking for the first again works nothing out.
        self.memory.remembered(key=0, on=(self.thing,), compute=counted.compute)
        self.assertEqual(counted.times, MAX_ANSWERS)
        # The answer that would go past the limit empties the memory first, and is then kept itself.
        self.assertEqual(self.memory.remembered(key=MAX_ANSWERS, on=(self.thing,), compute=counted.compute), FIRST_ANSWER)
        self.assertEqual(self.memory.count(), 1)
        self.memory.remembered(key=0, on=(self.thing,), compute=counted.compute)
        self.assertEqual(counted.times, MAX_ANSWERS + 2)


class TestAMemoryThatChecksItself(unittest.TestCase):

    def setUp(self):
        self.memory = Memory(checks=True)
        self.thing = ChangeMark()
        self.left_out = ChangeMark()

    def test_an_answer_that_left_out_something_it_came_from_is_found_when_that_thing_changes(self):
        counted = Counted(FIRST_ANSWER)
        self.memory.remembered(key=QUESTION, on=(self.thing,), compute=counted.compute)
        # The answer really came from left_out too, which on did not name.
        self.left_out.note_change()
        counted.answer = SECOND_ANSWER
        with self.assertRaises(StaleAnswer) as raised:
            self.memory.remembered(key=QUESTION, on=(self.thing,), compute=counted.compute)
        self.assertIn(QUESTION, str(raised.exception))
        self.assertIn(FIRST_ANSWER, str(raised.exception))
        self.assertIn(SECOND_ANSWER, str(raised.exception))

    def test_a_right_answer_passes_its_check_and_is_checked_once_for_each_change_anywhere(self):
        counted = Counted(FIRST_ANSWER)
        self.memory.remembered(key=QUESTION, on=(self.thing,), compute=counted.compute)
        self.memory.remembered(key=QUESTION, on=(self.thing,), compute=counted.compute)
        self.assertEqual(counted.times, 1)
        self.left_out.note_change()
        self.memory.remembered(key=QUESTION, on=(self.thing,), compute=counted.compute)
        self.memory.remembered(key=QUESTION, on=(self.thing,), compute=counted.compute)
        self.assertEqual(counted.times, 2)

    def test_a_memory_that_does_not_check_goes_on_returning_the_stale_answer(self):
        # The other path: without checking, the mistake above goes unseen, which is why the tests check.
        memory = Memory(checks=False)
        counted = Counted(FIRST_ANSWER)
        memory.remembered(key=QUESTION, on=(self.thing,), compute=counted.compute)
        self.left_out.note_change()
        counted.answer = SECOND_ANSWER
        self.assertEqual(memory.remembered(key=QUESTION, on=(self.thing,), compute=counted.compute), FIRST_ANSWER)


if __name__ == '__main__':
    unittest.main()
