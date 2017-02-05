from unittest.case import TestCase

import re

from pyvaru import ValidationRule, Validator, ValidationResult
from pyvaru.rules import TypeRule, FullStringRule, ChoiceRule, MinValueRule, MaxValueRule, MinLengthRule, \
    MaxLengthRule, RangeRule, RegexRule


class ValidationRuleTest(TestCase):
    def test_rule_cannot_be_instantiated_because_is_abstract(self):
        with self.assertRaises(TypeError):
            ValidationRule('', 'test')


class ValidatorTest(TestCase):
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
        self.assertTrue(result.valid)
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
        self.assertTrue(result.valid)
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
        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 3)
        self.assertEqual(result.errors.get('Field A'), ['GtRule not respected!'])
        self.assertEqual(result.errors.get('Field B'), [ValidationRule.default_error_message])
        self.assertEqual(result.errors.get('Field C'), [ContainsRule.default_error_message])

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
        self.assertFalse(result.valid)
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
        self.assertFalse(result.valid)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors.get('Field A'), ['GtRuleFail'])


class TypeRuleTest(TestCase):
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
        custom_msg = 'Not a dictionary.'
        rule = TypeRule({}, 'my_object', dict, custom_msg)
        self.assertEqual(rule.get_error_message(), custom_msg)


class FullStringRuleTest(TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(FullStringRule('ciao', 'label').apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(FullStringRule('', 'label').apply())
        self.assertFalse(FullStringRule(' \n\n ', 'label').apply())
        self.assertFalse(FullStringRule(None, 'label').apply())

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = FullStringRule('ciao', 'label')
        self.assertEqual(rule.get_error_message(), FullStringRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        msg = 'not a valid string'
        rule = FullStringRule('ciao', 'label', msg)
        self.assertEqual(rule.get_error_message(), msg)


class ChoiceRuleTest(TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(ChoiceRule('B', 'label', choices=('A', 'B', 'C')).apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(ChoiceRule('D', 'label', choices=('A', 'B', 'C')).apply())

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = ChoiceRule('B', 'label', choices=('A', 'B', 'C'))
        self.assertEqual(rule.get_error_message(), ChoiceRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        msg = 'custom message'
        rule = ChoiceRule('B', 'label', choices=('A', 'B', 'C'), error_message=msg)
        self.assertEqual(rule.get_error_message(), msg)


class MinValueRuleTest(TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(MinValueRule(100, 'label', min_value=50).apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(MinValueRule(1, 'label', min_value=50).apply())

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = MinValueRule(100, 'label', min_value=50)
        self.assertEqual(rule.get_error_message(), MinValueRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        msg = 'custom message'
        rule = MinValueRule(100, 'label', min_value=50, error_message=msg)
        self.assertEqual(rule.get_error_message(), msg)


class MaxValueRuleTest(TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(MaxValueRule(10, 'label', max_value=50).apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(MaxValueRule(1000, 'label', max_value=50).apply())

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = MaxValueRule(10, 'label', max_value=50)
        self.assertEqual(rule.get_error_message(), MaxValueRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        msg = 'custom message'
        rule = MaxValueRule(10, 'label', max_value=50, error_message=msg)
        self.assertEqual(rule.get_error_message(), msg)


class MinLengthRuleTest(TestCase):
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

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = MinLengthRule('hello', 'label', min_length=10)
        self.assertEqual(rule.get_error_message(), MinLengthRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        msg = 'custom message'
        rule = MinLengthRule('hello', 'label', min_length=10, error_message=msg)
        self.assertEqual(rule.get_error_message(), msg)


class MaxLengthRuleTest(TestCase):
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

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = MaxLengthRule('abc', 'label', max_length=3)
        self.assertEqual(rule.get_error_message(), MaxLengthRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        msg = 'custom message'
        rule = MaxLengthRule('abc', 'label', max_length=3, error_message=msg)
        self.assertEqual(rule.get_error_message(), msg)


class RangeRuleTest(TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(RangeRule(20, 'label', valid_range=range(10, 100)).apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(RangeRule(5, 'label', valid_range=range(10, 100)).apply())
        self.assertFalse(RangeRule(200, 'label', valid_range=range(10, 100)).apply())

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = RangeRule(20, 'label', valid_range=range(10, 100))
        self.assertEqual(rule.get_error_message(), RangeRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        msg = 'custom message'
        rule = RangeRule(20, 'label', valid_range=range(10, 100), error_message=msg)
        self.assertEqual(rule.get_error_message(), msg)


class RegexRuleTest(TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(RegexRule('hello', 'label', pattern=r'^[a-z]+$').apply())
        self.assertTrue(RegexRule('HELLO', 'label', pattern=r'^[a-z]+$', flags=re.IGNORECASE).apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(RegexRule('HELLO', 'label', pattern=r'^[a-z]+$').apply())
        self.assertFalse(RegexRule('599.99', 'label', pattern=r'^[a-z]+$').apply())
        self.assertFalse(RegexRule('', 'label', pattern=r'^[a-z]+$').apply())

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = RegexRule('hello', 'label', pattern=r'[a-z]+')
        self.assertEqual(rule.get_error_message(), RegexRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        msg = 'custom message'
        rule = RegexRule('hello', 'label', pattern=r'[a-z]+', error_message=msg)
        self.assertEqual(rule.get_error_message(), msg)
