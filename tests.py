import re
import unittest
from datetime import datetime

from pyvaru import ValidationRule, Validator, ValidationResult, ValidationException
from pyvaru.rules import TypeRule, FullStringRule, ChoiceRule, MinValueRule, MaxValueRule, MinLengthRule, \
    MaxLengthRule, RangeRule, PatternRule, IntervalRule, PastDateRule, FutureDateRule, UniqueItemsRule

CUSTOM_MESSAGE = 'custom message'


class ValidationRuleTest(unittest.TestCase):
    def test_rule_cannot_be_instantiated_because_is_abstract(self):
        with self.assertRaises(TypeError):
            ValidationRule('', 'test')


class ValidatorTest(unittest.TestCase):
    def test_validator_cannot_be_instantiated_because_is_abstract(self):
        with self.assertRaises(TypeError):
            Validator({})

    def test_validate_returns_expected_result_if_no_rule_is_provided(self):
        class MyValidator(Validator):
            def get_rules(self) -> list:
                return []

        validator = MyValidator({})
        result = validator.validate()
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_successful())
        self.assertEqual(result.errors, {})

    def test_validate_returns_expected_result_if_rules_are_respected(self):
        class GtRule(ValidationRule):
            def apply(self) -> bool:
                return self.apply_to > 5

        class LtRule(ValidationRule):
            def apply(self) -> bool:
                return self.apply_to < 10

        class ContainsRule(ValidationRule):
            def apply(self) -> bool:
                return 'hello' in self.apply_to

        class MyValidator(Validator):
            def get_rules(self) -> list:
                data = self.data  # type: dict
                return [
                    GtRule(data['a'], 'Field A'),
                    LtRule(data['b'], 'Field B'),
                    ContainsRule(data['c'], 'Field C'),
                ]

        validator = MyValidator({'a': 20, 'b': 1, 'c': 'hello world'})
        result = validator.validate()
        self.assertTrue(result.is_successful())
        self.assertEqual(result.errors, {})

    def test_validate_returns_expected_result_if_rules_are_not_respected(self):
        class GtRule(ValidationRule):
            def apply(self) -> bool:
                return self.apply_to > 200

        class LtRule(ValidationRule):
            def apply(self) -> bool:
                return self.apply_to < 0

        class ContainsRule(ValidationRule):
            default_error_message = 'banana not found'

            def apply(self) -> bool:
                return 'banana' in self.apply_to

        class MyValidator(Validator):
            def get_rules(self) -> list:
                data = self.data  # type: dict
                return [
                    GtRule(data['a'], 'Field A', 'GtRule not respected!'),
                    LtRule(data['b'], 'Field B'),
                    ContainsRule(data['c'], 'Field C'),
                ]

        validator = MyValidator({'a': 20, 'b': 1, 'c': 'hello world'})
        result = validator.validate()
        self.assertFalse(result.is_successful())
        self.assertEqual(len(result.errors), 3)
        self.assertEqual(result.errors.get('Field A'), ['GtRule not respected!'])
        self.assertEqual(result.errors.get('Field B'), [ValidationRule.default_error_message])
        self.assertEqual(result.errors.get('Field C'), [ContainsRule.default_error_message])

    def test_validator_as_context_processor_with_failures(self):
        class GtRule(ValidationRule):
            def apply(self) -> bool:
                return self.apply_to > 200

        class LtRule(ValidationRule):
            def apply(self) -> bool:
                return self.apply_to < 0

        class ContainsRule(ValidationRule):
            default_error_message = 'banana not found'

            def apply(self) -> bool:
                return 'banana' in self.apply_to

        class MyValidator(Validator):
            def get_rules(self) -> list:
                data = self.data  # type: dict
                return [
                    GtRule(data['a'], 'Field A', 'GtRule not respected!'),
                    LtRule(data['b'], 'Field B'),
                    ContainsRule(data['c'], 'Field C'),
                ]

        inner_code_calls = 0
        with self.assertRaises(ValidationException) as raise_context:
            with MyValidator({'a': 20, 'b': 1, 'c': 'hello world'}):
                inner_code_calls += 1

        errors = raise_context.exception.validation_result.errors
        self.assertEqual(inner_code_calls, 0)
        self.assertIsInstance(errors, dict)
        self.assertEqual(errors.get('Field A'), ['GtRule not respected!'])
        self.assertEqual(errors.get('Field B'), [ValidationRule.default_error_message])
        self.assertEqual(errors.get('Field C'), [ContainsRule.default_error_message])

    def test_validator_as_context_processor_without_failures(self):
        class GtRule(ValidationRule):
            def apply(self) -> bool:
                return self.apply_to > 5

        class LtRule(ValidationRule):
            def apply(self) -> bool:
                return self.apply_to < 10

        class ContainsRule(ValidationRule):
            def apply(self) -> bool:
                return 'hello' in self.apply_to

        class MyValidator(Validator):
            def get_rules(self) -> list:
                data = self.data  # type: dict
                return [
                    GtRule(data['a'], 'Field A'),
                    LtRule(data['b'], 'Field B'),
                    ContainsRule(data['c'], 'Field C'),
                ]

        with MyValidator({'a': 20, 'b': 1, 'c': 'hello world'}) as validator:
            self.assertIsInstance(validator, MyValidator)

    def test_multiple_rules_applied_to_the_same_field(self):
        class GtRule(ValidationRule):
            def apply(self) -> bool:
                return self.apply_to > 200

        class LtRule(ValidationRule):
            def apply(self) -> bool:
                return self.apply_to < 0

        class MyValidator(Validator):
            def get_rules(self) -> list:
                data = self.data  # type: dict
                return [
                    GtRule(data['a'], 'Field A', 'GtRuleFail'),
                    LtRule(data['a'], 'Field A', 'LtRuleFail'),
                ]

        validator = MyValidator({'a': 100})
        result = validator.validate()
        self.assertFalse(result.is_successful())
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors.get('Field A'), ['GtRuleFail', 'LtRuleFail'])

    def test_rules_processing_is_skipped_if_a_failing_rule_requires_it(self):
        class GtRule(ValidationRule):
            def apply(self) -> bool:
                return self.apply_to > 200

        class LtRule(ValidationRule):
            def apply(self) -> bool:
                return self.apply_to < 0

        class MyValidator(Validator):
            def get_rules(self) -> list:
                data = self.data  # type: dict
                return [
                    GtRule(data['a'], 'Field A', 'GtRuleFail', stop_if_invalid=True),
                    LtRule(data['a'], 'Field A', 'LtRuleFail'),
                ]

        validator = MyValidator({'a': 100})
        result = validator.validate()
        self.assertFalse(result.is_successful())
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors.get('Field A'), ['GtRuleFail'])


class TypeRuleTest(unittest.TestCase):
    def test_rule_returns_true_if_respected(self):
        rule = TypeRule({'a': 1, 'b': 2}, 'my_object', dict)
        self.assertTrue(rule.apply())

    def test_rule_returns_true_if_type_is_a_subtype(self):
        class BaseClass:
            pass

        class SubClass(BaseClass):
            def __init__(self):
                super().__init__()

            pass

        rule = TypeRule(SubClass(), 'my_object', BaseClass)
        self.assertTrue(rule.apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(TypeRule([1, 2, 3], 'my_object', dict).apply())
        self.assertFalse(TypeRule(123, 'my_object', dict).apply())
        self.assertFalse(TypeRule('123', 'my_object', dict).apply())
        self.assertFalse(TypeRule(True, 'my_object', dict).apply())

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = TypeRule({}, 'my_object', dict)
        self.assertEqual(rule.get_error_message(), TypeRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        rule = TypeRule({}, 'my_object', dict, CUSTOM_MESSAGE)
        self.assertEqual(rule.get_error_message(), CUSTOM_MESSAGE)


class FullStringRuleTest(unittest.TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(FullStringRule('ciao', 'label').apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(FullStringRule('', 'label').apply())
        self.assertFalse(FullStringRule(' \n\n ', 'label').apply())

    def test_rule_returns_false_if_given_type_is_wrong(self):
        self.assertFalse(FullStringRule(None, 'label').apply())
        self.assertFalse(FullStringRule([1, 2, 3], 'label').apply())
        self.assertFalse(FullStringRule(datetime.now(), 'label').apply())

    def test_rule_changes_error_message_if_given_type_is_wrong(self):
        rule = FullStringRule([1, 2, 3], 'label')
        rule.apply()
        self.assertEqual(rule.get_error_message(), FullStringRule.type_error_message)

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = FullStringRule('ciao', 'label')
        self.assertEqual(rule.get_error_message(), FullStringRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        rule = FullStringRule('ciao', 'label', CUSTOM_MESSAGE)
        self.assertEqual(rule.get_error_message(), CUSTOM_MESSAGE)


class ChoiceRuleTest(unittest.TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(ChoiceRule('B', 'label', choices=('A', 'B', 'C')).apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(ChoiceRule('D', 'label', choices=('A', 'B', 'C')).apply())

    def test_rule_returns_false_if_given_type_is_wrong(self):
        self.assertFalse(ChoiceRule({'a': 1}, 'label', choices=('A', 'B', 'C')).apply())
        self.assertFalse(ChoiceRule(42, 'label', choices=('A', 'B', 'C')).apply())
        self.assertFalse(ChoiceRule(True, 'label', choices=('A', 'B', 'C')).apply())

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = ChoiceRule('B', 'label', choices=('A', 'B', 'C'))
        self.assertEqual(rule.get_error_message(), ChoiceRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        rule = ChoiceRule('B', 'label', choices=('A', 'B', 'C'), error_message=CUSTOM_MESSAGE)
        self.assertEqual(rule.get_error_message(), CUSTOM_MESSAGE)


class MinValueRuleTest(unittest.TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(MinValueRule(100, 'label', min_value=50).apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(MinValueRule(1, 'label', min_value=50).apply())

    def test_rules_returns_false_if_the_given_type_is_wrong(self):
        self.assertFalse(MinValueRule('ciao', 'label', min_value=50).apply())
        self.assertFalse(MinValueRule({'a': 0}, 'label', min_value=50).apply())
        self.assertFalse(MinValueRule([1, 2, 3], 'label', min_value=50).apply())

    def test_rule_changes_error_message_if_the_given_type_is_wrong(self):
        rule = MinValueRule([1, 2, 3], 'label', min_value=50)
        rule.apply()
        self.assertEqual(rule.get_error_message(), MinValueRule.type_error_message)

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = MinValueRule(100, 'label', min_value=50)
        self.assertEqual(rule.get_error_message(), MinValueRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        rule = MinValueRule(100, 'label', min_value=50, error_message=CUSTOM_MESSAGE)
        self.assertEqual(rule.get_error_message(), CUSTOM_MESSAGE)


class MaxValueRuleTest(unittest.TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(MaxValueRule(10, 'label', max_value=50).apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(MaxValueRule(1000, 'label', max_value=50).apply())

    def test_rules_returns_false_if_the_given_type_is_wrong(self):
        self.assertFalse(MaxValueRule('hello', 'label', max_value=50).apply())
        self.assertFalse(MaxValueRule([1, 2, 3], 'label', max_value=50).apply())
        self.assertFalse(MaxValueRule({'a': 'b'}, 'label', max_value=50).apply())

    def test_rule_changes_error_message_if_the_given_type_is_wrong(self):
        rule = MaxValueRule({'a': 'b'}, 'label', max_value=50)
        rule.apply()
        self.assertEqual(rule.get_error_message(), MaxValueRule.type_error_message)

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = MaxValueRule(10, 'label', max_value=50)
        self.assertEqual(rule.get_error_message(), MaxValueRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        rule = MaxValueRule(10, 'label', max_value=50, error_message=CUSTOM_MESSAGE)
        self.assertEqual(rule.get_error_message(), CUSTOM_MESSAGE)


class MinLengthRuleTest(unittest.TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(MinLengthRule('hello', 'label', min_length=3).apply())
        self.assertTrue(MinLengthRule(['foo', 'bar', 'baz'], 'label', min_length=3).apply())
        self.assertTrue(MinLengthRule(('foo', 'bar', 'baz'), 'label', min_length=3).apply())
        self.assertTrue(MinLengthRule({'a': 1, 'b': 2, 'c': 3}, 'label', min_length=3).apply())
        self.assertTrue(MinLengthRule({'foo', 'bar', 'baz'}, 'label', min_length=3).apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(MinLengthRule('hello', 'label', min_length=10).apply())
        self.assertFalse(MinLengthRule(['foo', 'bar', 'baz'], 'label', min_length=10).apply())
        self.assertFalse(MinLengthRule(('foo', 'bar', 'baz'), 'label', min_length=10).apply())
        self.assertFalse(MinLengthRule({'a': 1, 'b': 2, 'c': 3}, 'label', min_length=10).apply())
        self.assertFalse(MinLengthRule({'foo', 'bar', 'baz'}, 'label', min_length=10).apply())

    def test_rules_returns_false_if_the_given_type_is_wrong(self):
        self.assertFalse(MinLengthRule(5, 'label', min_length=10).apply())
        self.assertFalse(MinLengthRule(datetime.now(), 'label', min_length=10).apply())

    def test_rule_changes_error_message_if_the_given_type_is_wrong(self):
        rule = MinLengthRule(5, 'label', min_length=10)
        rule.apply()
        self.assertEqual(rule.get_error_message(), MinLengthRule.type_error_message)

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = MinLengthRule('hello', 'label', min_length=10)
        self.assertEqual(rule.get_error_message(), MinLengthRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        rule = MinLengthRule('hello', 'label', min_length=10, error_message=CUSTOM_MESSAGE)
        self.assertEqual(rule.get_error_message(), CUSTOM_MESSAGE)


class MaxLengthRuleTest(unittest.TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(MaxLengthRule('abc', 'label', max_length=3).apply())
        self.assertTrue(MaxLengthRule(['foo', 'bar', 'baz'], 'label', max_length=3).apply())
        self.assertTrue(MaxLengthRule(('foo', 'bar', 'baz'), 'label', max_length=3).apply())
        self.assertTrue(MaxLengthRule({'a': 1, 'b': 2, 'c': 3}, 'label', max_length=3).apply())
        self.assertTrue(MaxLengthRule({'foo', 'bar', 'baz'}, 'label', max_length=3).apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(MaxLengthRule('abc', 'label', max_length=2).apply())
        self.assertFalse(MaxLengthRule(['foo', 'bar', 'baz'], 'label', max_length=2).apply())
        self.assertFalse(MaxLengthRule(('foo', 'bar', 'baz'), 'label', max_length=2).apply())
        self.assertFalse(MaxLengthRule({'a': 1, 'b': 2, 'c': 3}, 'label', max_length=2).apply())
        self.assertFalse(MaxLengthRule({'foo', 'bar', 'baz'}, 'label', max_length=2).apply())

    def test_rules_returns_false_if_the_given_type_is_wrong(self):
        self.assertFalse(MaxLengthRule(8, 'label', max_length=2).apply())
        self.assertFalse(MaxLengthRule(datetime.now(), 'label', max_length=2).apply())

    def test_rule_changes_error_message_if_the_given_type_is_wrong(self):
        rule = MaxLengthRule(8, 'label', max_length=2)
        rule.apply()
        self.assertEqual(rule.get_error_message(), MaxLengthRule.type_error_message)

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = MaxLengthRule('abc', 'label', max_length=3)
        self.assertEqual(rule.get_error_message(), MaxLengthRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        rule = MaxLengthRule('abc', 'label', max_length=3, error_message=CUSTOM_MESSAGE)
        self.assertEqual(rule.get_error_message(), CUSTOM_MESSAGE)


class RangeRuleTest(unittest.TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(RangeRule(20, 'label', valid_range=range(10, 100)).apply())
        self.assertTrue(RangeRule(20, 'label', valid_range=range(100, 1, -1)).apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(RangeRule(5, 'label', valid_range=range(10, 100)).apply())
        self.assertFalse(RangeRule(200, 'label', valid_range=range(10, 100)).apply())

    def test_floats_are_never_in_range(self):
        self.assertFalse(RangeRule(11.5, 'label', valid_range=range(10, 100)).apply())

    def test_non_numeric_values_are_never_in_range(self):
        self.assertFalse(RangeRule('hello', 'label', valid_range=range(10, 100)).apply())
        self.assertFalse(RangeRule([1, 2, 3], 'label', valid_range=range(10, 100)).apply())
        self.assertFalse(RangeRule(datetime.now(), 'label', valid_range=range(10, 100)).apply())

    def test_range_step_is_respected(self):
        # with default step of 1, value 22 is in range
        self.assertTrue(RangeRule(22, 'label', valid_range=range(10, 100)).apply())
        # with step of 5, value 22 should not be considered in range
        self.assertFalse(RangeRule(22, 'label', valid_range=range(10, 100, 5)).apply())

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = RangeRule(20, 'label', valid_range=range(10, 100))
        self.assertEqual(rule.get_error_message(), RangeRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        msg = 'custom message'
        rule = RangeRule(20, 'label', valid_range=range(10, 100), error_message=msg)
        self.assertEqual(rule.get_error_message(), msg)


class IntervalRuleTest(unittest.TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(IntervalRule(25, interval_from=10, interval_to=50, label='label').apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(IntervalRule(9, interval_from=10, interval_to=50, label='label').apply())
        self.assertFalse(IntervalRule(51, interval_from=10, interval_to=50, label='label').apply())
        self.assertFalse(IntervalRule('hello', interval_from=10, interval_to=50, label='label').apply())
        self.assertFalse(IntervalRule([1, 2, 3], interval_from=10, interval_to=50, label='label').apply())

    def test_rules_returns_false_if_the_given_type_is_wrong(self):
        self.assertFalse(IntervalRule(datetime.now(), interval_from=10, interval_to=50, label='label').apply())
        self.assertFalse(IntervalRule({'a': 123}, interval_from=10, interval_to=50, label='label').apply())

    def test_rule_changes_error_message_if_the_given_type_is_wrong(self):
        rule = IntervalRule({'a': 123}, interval_from=10, interval_to=50, label='label')
        rule.apply()
        self.assertEqual(rule.get_error_message(), IntervalRule.type_error_message)

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = IntervalRule(9, interval_from=10, interval_to=50, label='label')
        self.assertEqual(rule.get_error_message(), IntervalRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        rule = IntervalRule(9, interval_from=10, interval_to=50, label='label', error_message=CUSTOM_MESSAGE)
        self.assertEqual(rule.get_error_message(), CUSTOM_MESSAGE)


class PatternRuleTest(unittest.TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(PatternRule('hello', 'label', pattern=r'^[a-z]+$').apply())
        self.assertTrue(PatternRule('HELLO', 'label', pattern=r'^[a-z]+$', flags=re.IGNORECASE).apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(PatternRule('HELLO', 'label', pattern=r'^[a-z]+$').apply())
        self.assertFalse(PatternRule('599.99', 'label', pattern=r'^[a-z]+$').apply())
        self.assertFalse(PatternRule('', 'label', pattern=r'^[a-z]+$').apply())

    def test_rule_returns_false_if_given_type_is_wrong(self):
        self.assertFalse(PatternRule(42, 'label', pattern=r'^[a-z]+$').apply())
        self.assertFalse(PatternRule([1, 2, 3], 'label', pattern=r'^[a-z]+$').apply())
        self.assertFalse(PatternRule(datetime.now(), 'label', pattern=r'^[a-z]+$').apply())

    def test_rule_changes_error_message_if_given_type_is_wrong(self):
        rule = PatternRule([1, 2, 3], 'label', pattern=r'^[a-z]+$')
        rule.apply()
        self.assertEqual(rule.get_error_message(), PatternRule.type_error_message)

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = PatternRule('hello', 'label', pattern=r'[a-z]+')
        self.assertEqual(rule.get_error_message(), PatternRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        msg = 'custom message'
        rule = PatternRule('hello', 'label', pattern=r'[a-z]+', error_message=msg)
        self.assertEqual(rule.get_error_message(), msg)


class PastDateRuleTest(unittest.TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(PastDateRule(datetime(2015, 1, 1), 'date', reference_date=datetime(2020, 1, 1)).apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(PastDateRule(datetime(2022, 1, 1), 'date', reference_date=datetime(2020, 1, 1)).apply())

    def test_rule_returns_false_if_given_type_is_wrong(self):
        self.assertFalse(PastDateRule('nope!', 'date', reference_date=datetime(2020, 1, 1)).apply())

    def test_rule_changes_error_message_if_given_type_is_wrong(self):
        rule = PastDateRule('nope!', 'date', reference_date=datetime(2020, 1, 1))
        rule.apply()
        self.assertEqual(rule.get_error_message(), PastDateRule.type_error_message)

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = PastDateRule(datetime(2015, 1, 1), 'date', reference_date=datetime(2020, 1, 1))
        self.assertEqual(rule.get_error_message(), PastDateRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        rule = PastDateRule(datetime(2015, 1, 1),
                            'date',
                            reference_date=datetime(2020, 1, 1),
                            error_message=CUSTOM_MESSAGE)
        self.assertEqual(rule.get_error_message(), CUSTOM_MESSAGE)


class FutureDateRuleTest(unittest.TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(FutureDateRule(datetime(2015, 1, 1), 'date', reference_date=datetime(2010, 1, 1)).apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(FutureDateRule(datetime(2000, 1, 1), 'date', reference_date=datetime(2020, 1, 1)).apply())

    def test_rule_returns_false_if_given_type_is_wrong(self):
        self.assertFalse(FutureDateRule('nope!', 'date', reference_date=datetime(2020, 1, 1)).apply())

    def test_rule_changes_error_message_if_given_type_is_wrong(self):
        rule = FutureDateRule('nope!', 'date', reference_date=datetime(2020, 1, 1))
        rule.apply()
        self.assertEqual(rule.get_error_message(), FutureDateRule.type_error_message)

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = FutureDateRule(datetime(2015, 1, 1), 'date', reference_date=datetime(2020, 1, 1))
        self.assertEqual(rule.get_error_message(), FutureDateRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        rule = FutureDateRule(datetime(2015, 1, 1),
                              'date',
                              reference_date=datetime(2020, 1, 1),
                              error_message=CUSTOM_MESSAGE)
        self.assertEqual(rule.get_error_message(), CUSTOM_MESSAGE)


class UniqueItemsRuleTest(unittest.TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(UniqueItemsRule(['one', 'two', 'three'], 'list').apply())
        self.assertTrue(UniqueItemsRule(('one', 'two', 'three'), 'list').apply())
        self.assertTrue(UniqueItemsRule('ABCDE', 'list').apply())
        self.assertTrue(UniqueItemsRule({'a': 1}, 'list').apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(UniqueItemsRule(['one', 'two', 'three', 'one'], 'list').apply())
        self.assertFalse(UniqueItemsRule(('one', 'one', 'two', 'three'), 'list').apply())
        self.assertFalse(UniqueItemsRule('ABCDEA', 'list').apply())

    def test_rule_returns_false_if_given_type_is_wrong(self):
        self.assertFalse(UniqueItemsRule(42, 'list').apply())
        self.assertFalse(UniqueItemsRule(True, 'list').apply())
        self.assertFalse(UniqueItemsRule(datetime.now(), 'list').apply())

    def test_rule_changes_error_message_if_given_type_is_wrong(self):
        rule = UniqueItemsRule(42, 'list')
        rule.apply()
        self.assertEqual(rule.get_error_message(), UniqueItemsRule.type_error_message)

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = UniqueItemsRule(['one', 'two', 'three'], 'list')
        self.assertEqual(rule.get_error_message(), UniqueItemsRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        rule = UniqueItemsRule(['one', 'two', 'three'], 'list', error_message=CUSTOM_MESSAGE)
        self.assertEqual(rule.get_error_message(), CUSTOM_MESSAGE)


if __name__ == '__main__':
    unittest.main(verbosity=2)
