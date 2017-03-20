import pprint
import re
from datetime import datetime
from unittest import TestCase
from unittest import main as run_tests

from pyvaru import ValidationRule, Validator, ValidationResult, ValidationException, RuleGroup, \
    InvalidRuleGroupException
from pyvaru.rules import TypeRule, FullStringRule, ChoiceRule, MinValueRule, MaxValueRule, MinLengthRule, \
    MaxLengthRule, RangeRule, PatternRule, IntervalRule, PastDateRule, FutureDateRule, UniqueItemsRule

CUSTOM_MESSAGE = 'custom message'


class ValidationRuleTest(TestCase):
    def test_rule_cannot_be_instantiated_because_is_abstract(self):
        with self.assertRaises(TypeError):
            ValidationRule('', 'test')


class ValidationResultTest(TestCase):
    def test_string_conversion_returns_formatted_string_with_errors(self):
        errors = {
            'first_name': FullStringRule.default_error_message,
            'last_name': FullStringRule.default_error_message,
        }
        result = ValidationResult(errors)
        self.assertEqual(str(result), pprint.pformat({'errors': errors}))

    def test_string_conversion_returns_formatted_string_without_errors(self):
        result = ValidationResult()
        self.assertEqual(str(result), pprint.pformat({'errors': {}}))


class ValidationExceptionTest(TestCase):
    def test_string_conversion_returns_formatted_string_with_errors(self):
        errors = {
            'first_name': FullStringRule.default_error_message,
            'last_name': FullStringRule.default_error_message,
        }
        result = ValidationResult(errors)
        exception = ValidationException(result)
        expected_string = pprint.pformat({'message': exception.message, 'errors': result.errors})
        self.assertEqual(str(exception), expected_string)


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
        self.assertTrue(result.is_successful())
        self.assertEqual(result.errors, {})
        self.assertEqual(str(result), "{'errors': {}}")

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
        self.assertEqual(str(result), "{'errors': {}}")

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
        self.assertEqual(str(result), pprint.pformat({'errors': result.errors}))

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
        expected_string_value = pprint.pformat({'message': raise_context.exception.message, 'errors': errors})
        self.assertEqual(str(raise_context.exception), expected_string_value)

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

    def test_validator_handle_possible_exceptions_in_get_rules_as_expected(self):
        class DangerValidator(Validator):
            def get_rules(self) -> list:
                return [
                    FullStringRule(self.data.name, 'name')
                ]

        # normal test
        validator = DangerValidator({'name': 'Dave'})
        result = validator.validate()
        self.assertFalse(result.is_successful())
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(list(result.errors.keys()), ['get_rules'])
        self.assertIsInstance(result.errors.get('get_rules'), list)
        self.assertEqual(len(result.errors.get('get_rules')), 1)
        self.assertIsInstance(result.errors.get('get_rules', [])[0], str)

        # test as context processor
        with self.assertRaises(ValidationException) as exception_context:
            with DangerValidator({'name': 'Dave'}):
                pass

        exception_result = exception_context.exception.validation_result
        self.assertFalse(exception_result.is_successful())
        self.assertEqual(len(exception_result.errors), 1)
        self.assertEqual(list(exception_result.errors.keys()), ['get_rules'])
        self.assertIsInstance(exception_result.errors.get('get_rules'), list)
        self.assertEqual(len(exception_result.errors.get('get_rules')), 1)
        self.assertIsInstance(exception_result.errors.get('get_rules', [])[0], str)

    def test_without_lambdas_stop_if_invalid_does_not_prevent_errors_report(self):
        """
        Exception catched in get_rules() instead of the TypeRule violation we may expect, since the code is
        executed as soon the method is called.
        """

        class MyModel:
            name = 'Foo'

        class DangerValidator(Validator):
            def get_rules(self) -> list:
                return [
                    TypeRule(self.data, 'data', MyModel, stop_if_invalid=True),
                    FullStringRule(self.data.name, 'name'),
                ]

        validator = DangerValidator({'name': 'Foo'})
        result = validator.validate()
        self.assertFalse(result.is_successful())
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(list(result.errors.keys()), ['get_rules'])

    def test_by_using_lambda_and_stop_if_invalid_no_exception_is_reported(self):
        """
        No exception catched, since data access happens after get_rules() invocation, but stop_if_invalid prevents it.
        """

        class MyModel:
            name = 'Foo'

        class DangerValidator(Validator):
            def get_rules(self) -> list:
                return [
                    TypeRule(lambda: self.data, 'data', MyModel, stop_if_invalid=True),
                    FullStringRule(lambda: self.data.name, 'name'),
                ]

        validator = DangerValidator({'name': 'Foo'})
        result = validator.validate()
        self.assertFalse(result.is_successful())
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(list(result.errors.keys()), ['data'])

    def test_validator_catch_and_store_errors_that_may_occour_in_rule_apply(self):
        class RuleA(ValidationRule):
            def apply(self):
                raise NotImplementedError

        class RuleB(ValidationRule):
            def apply(self):
                raise ZeroDivisionError

        class MyValidator(Validator):
            def get_rules(self):
                return [
                    RuleA('', 'field_a'),
                    RuleB('', 'field_b'),
                ]

        validator = MyValidator({})
        result = validator.validate()
        self.assertFalse(result.is_successful())
        self.assertEqual(len(result.errors), 2)
        try:
            raise NotImplementedError
        except NotImplementedError as e:
            expected_a = [str(e)]
        self.assertEqual(result.errors.get('field_a'), expected_a)
        try:
            raise ZeroDivisionError
        except ZeroDivisionError as e:
            expected_b = [str(e)]
        self.assertEqual(result.errors.get('field_b'), expected_b)


class TypeRuleTest(TestCase):
    def test_rule_returns_true_if_respected(self):
        rule = TypeRule({'a': 1, 'b': 2}, 'my_object', dict)
        self.assertTrue(rule.apply())

    def test_rule_supports_lambda_expressions(self):
        rule = TypeRule(lambda: {'a': 1, 'b': 2}, 'my_object', dict)
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

    # bitwise operators

    def test_rule_can_be_negated_with_bitwise_inversion(self):
        # since negated, fails because type is right:
        negated_rule = ~ TypeRule({'a': 1, 'b': 2}, 'my_object', dict)
        self.assertFalse(negated_rule.apply())

        # since negated, pass because type is wrong:
        negated_rule_2 = ~ TypeRule('banana', 'my_object', dict)
        self.assertTrue(negated_rule_2.apply())


class RuleGroupTest(TestCase):
    def test_bad_configuration_of_rules_raise_exception(self):
        group = RuleGroup(apply_to=['Italy', 'France', 'Germany'], label='Countries', rules=[None, None])
        with self.assertRaises(InvalidRuleGroupException):
            group.apply()

        group = RuleGroup(apply_to=['Italy', 'France', 'Germany'], label='Countries', rules=[(TypeRule, 1)])
        with self.assertRaises(InvalidRuleGroupException):
            group.apply()

        group = RuleGroup(apply_to=['Italy', 'France', 'Germany'], label='Countries', rules=[[TypeRule]])
        with self.assertRaises(InvalidRuleGroupException):
            group.apply()

    def test_group_returns_true_if_respected(self):
        rules = [
            (TypeRule, {'valid_type': list}),
            (MinLengthRule, {'min_length': 1}),
            UniqueItemsRule
        ]
        group = RuleGroup(apply_to=['Italy', 'France', 'Germany'], label='Countries', rules=rules)
        self.assertTrue(group.apply())

    def test_group_supports_lambda_expressions(self):
        rules = [
            (TypeRule, {'valid_type': list}),
            (MinLengthRule, {'min_length': 1}),
            UniqueItemsRule
        ]
        group = RuleGroup(lambda: ['Italy', 'France', 'Germany'], label='Countries', rules=rules)
        self.assertTrue(group.apply())

    def test_group_returns_false_if_not_respected(self):
        rules = [
            (TypeRule, {'valid_type': list}),
            (MinLengthRule, {'min_length': 2}),
            UniqueItemsRule
        ]

        # TypeRule test
        group_1 = RuleGroup(apply_to='foo', label='Countries', rules=rules)
        self.assertFalse(group_1.apply())

        # MinLengthRule test
        group_2 = RuleGroup(apply_to=['USA'], label='Countries', rules=rules)
        self.assertFalse(group_2.apply())

        # UniqueItemsRule test
        group_3 = RuleGroup(apply_to=['USA', 'Italy', 'USA'], label='Countries', rules=rules)
        self.assertFalse(group_3.apply())

    def test_group_returns_false_if_given_type_is_wrong(self):
        class MyObject:
            pass

        rules = [
            (MinLengthRule, {'min_length': 2}),
            UniqueItemsRule
        ]
        group = RuleGroup(lambda: MyObject(), label='Countries', rules=rules)
        self.assertFalse(group.apply())

    def test_default_message_is_used_if_no_custom_provided(self):
        rules = [
            (TypeRule, {'valid_type': list}),
            (MinLengthRule, {'min_length': 2}),
            UniqueItemsRule
        ]

        # TypeRule test
        group_1 = RuleGroup(apply_to='foo', label='Countries', rules=rules)
        group_1.apply()
        self.assertEqual(group_1.get_error_message(), TypeRule.default_error_message)

        # MinLengthRule test
        group_2 = RuleGroup(apply_to=['USA'], label='Countries', rules=rules)
        group_2.apply()
        self.assertEqual(group_2.get_error_message(), MinLengthRule.default_error_message)

        # UniqueItemsRule test
        group_3 = RuleGroup(apply_to=['USA', 'Italy', 'USA'], label='Countries', rules=rules)
        group_3.apply()
        self.assertEqual(group_3.get_error_message(), UniqueItemsRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        rules = [
            (TypeRule, {'valid_type': list, 'error_message': 'Custom TypeRule message'}),
            (MinLengthRule, {'min_length': 2, 'error_message': 'Custom MinLengthRule message'}),
            (UniqueItemsRule, {'error_message': 'Custom UniqueItemsRule message'})
        ]

        # TypeRule test
        group_1 = RuleGroup(apply_to='foo', label='Countries', rules=rules)
        group_1.apply()
        self.assertEqual(group_1.get_error_message(), 'Custom TypeRule message')

        # MinLengthRule test
        group_2 = RuleGroup(apply_to=['USA'], label='Countries', rules=rules)
        group_2.apply()
        self.assertEqual(group_2.get_error_message(), 'Custom MinLengthRule message')

        # UniqueItemsRule test
        group_3 = RuleGroup(apply_to=['USA', 'Italy', 'USA'], label='Countries', rules=rules)
        group_3.apply()
        self.assertEqual(group_3.get_error_message(), 'Custom UniqueItemsRule message')

    # bitwise operators

    def test_group_can_be_negated_with_bitwise_inversion(self):
        rules = [
            (TypeRule, {'valid_type': list}),
            (MinLengthRule, {'min_length': 2}),
            UniqueItemsRule
        ]

        # TypeRule test
        group_1 = ~ RuleGroup(apply_to='foo', label='Countries', rules=rules)
        self.assertTrue(group_1.apply())

        # MinLengthRule test
        group_2 = ~ RuleGroup(apply_to=['USA'], label='Countries', rules=rules)
        self.assertTrue(group_2.apply())

        # UniqueItemsRule test
        group_3 = ~ RuleGroup(apply_to=['USA', 'Italy', 'USA'], label='Countries', rules=rules)
        self.assertTrue(group_3.apply())

        group_4 = ~ RuleGroup(apply_to=['USA', 'Italy', 'Germany'], label='Countries', rules=rules)
        self.assertFalse(group_4.apply())


class FullStringRuleTest(TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(FullStringRule('ciao', 'label').apply())

    def test_rule_supports_lambda_expressions(self):
        self.assertTrue(FullStringRule(lambda: 'ciao', 'label').apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(FullStringRule('', 'label').apply())
        self.assertFalse(FullStringRule(' \n\n ', 'label').apply())

    def test_rule_returns_false_if_given_type_is_wrong(self):
        self.assertFalse(FullStringRule(None, 'label').apply())
        self.assertFalse(FullStringRule([1, 2, 3], 'label').apply())
        self.assertFalse(FullStringRule(datetime.now(), 'label').apply())

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = FullStringRule('ciao', 'label')
        self.assertEqual(rule.get_error_message(), FullStringRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        rule = FullStringRule('ciao', 'label', CUSTOM_MESSAGE)
        self.assertEqual(rule.get_error_message(), CUSTOM_MESSAGE)

    # bitwise operators

    def test_rule_can_be_negated_with_bitwise_inversion(self):
        # since negated, fails because the string has content
        negated_rule = ~ FullStringRule('ciao', 'label')
        self.assertFalse(negated_rule.apply())

        # since negated, pass because the string is empty
        negated_rule = ~ FullStringRule('', 'label')
        self.assertTrue(negated_rule.apply())


class ChoiceRuleTest(TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(ChoiceRule('B', 'label', choices=('A', 'B', 'C')).apply())

    def test_rule_supports_lambda_expressions(self):
        self.assertTrue(ChoiceRule(lambda: 'B', 'label', choices=('A', 'B', 'C')).apply())

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

    # bitwise operators

    def test_rule_can_be_negated_with_bitwise_inversion(self):
        # since negated, fails because "B" is in available options:
        negated_rule = ~ ChoiceRule('B', 'label', choices=('A', 'B', 'C'))
        self.assertFalse(negated_rule.apply())

        # since negated, pass because type "Z" is not in available options:
        negated_rule_2 = ~ ChoiceRule('Z', 'label', choices=('A', 'B', 'C'))
        self.assertTrue(negated_rule_2.apply())


class MinValueRuleTest(TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(MinValueRule(100, 'label', min_value=50).apply())

    def test_rule_supports_lambda_expressions(self):
        self.assertTrue(MinValueRule(lambda: 100, 'label', min_value=50).apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(MinValueRule(1, 'label', min_value=50).apply())

    def test_rules_returns_false_if_the_given_type_is_wrong(self):
        self.assertFalse(MinValueRule('ciao', 'label', min_value=50).apply())
        self.assertFalse(MinValueRule({'a': 0}, 'label', min_value=50).apply())
        self.assertFalse(MinValueRule([1, 2, 3], 'label', min_value=50).apply())

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = MinValueRule(100, 'label', min_value=50)
        self.assertEqual(rule.get_error_message(), MinValueRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        rule = MinValueRule(100, 'label', min_value=50, error_message=CUSTOM_MESSAGE)
        self.assertEqual(rule.get_error_message(), CUSTOM_MESSAGE)

    # bitwise operators

    def test_rule_can_be_negated_with_bitwise_inversion(self):
        # since negated, fails because 100 is > 50
        negated_rule = ~ MinValueRule(100, 'label', min_value=50)
        self.assertFalse(negated_rule.apply())

        # since negated, pass because 10 is < 50
        negated_rule_2 = ~ MinValueRule(10, 'label', min_value=50)
        self.assertTrue(negated_rule_2.apply())

        # since negated, pass because 50 == 50
        negated_rule_3 = ~ MinValueRule(50, 'label', min_value=50)
        self.assertFalse(negated_rule_3.apply())


class MaxValueRuleTest(TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(MaxValueRule(10, 'label', max_value=50).apply())

    def test_rule_supports_lambda_expressions(self):
        self.assertTrue(MaxValueRule(lambda: 10, 'label', max_value=50).apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(MaxValueRule(1000, 'label', max_value=50).apply())

    def test_rules_returns_false_if_the_given_type_is_wrong(self):
        self.assertFalse(MaxValueRule('hello', 'label', max_value=50).apply())
        self.assertFalse(MaxValueRule([1, 2, 3], 'label', max_value=50).apply())
        self.assertFalse(MaxValueRule({'a': 'b'}, 'label', max_value=50).apply())

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = MaxValueRule(10, 'label', max_value=50)
        self.assertEqual(rule.get_error_message(), MaxValueRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        rule = MaxValueRule(10, 'label', max_value=50, error_message=CUSTOM_MESSAGE)
        self.assertEqual(rule.get_error_message(), CUSTOM_MESSAGE)

    # bitwise operators

    def test_rule_can_be_negated_with_bitwise_inversion(self):
        # since negated, fails because 10 is < 50
        negated_rule = ~ MaxValueRule(10, 'label', max_value=50)
        self.assertFalse(negated_rule.apply())

        # since negated, pass because 100 is > 50
        negated_rule_2 = ~ MaxValueRule(100, 'label', max_value=50)
        self.assertTrue(negated_rule_2.apply())

        # since negated, pass because 50 == 50
        negated_rule_3 = ~ MaxValueRule(50, 'label', max_value=50)
        self.assertFalse(negated_rule_3.apply())


class MinLengthRuleTest(TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(MinLengthRule('hello', 'label', min_length=3).apply())
        self.assertTrue(MinLengthRule(['foo', 'bar', 'baz'], 'label', min_length=3).apply())
        self.assertTrue(MinLengthRule(('foo', 'bar', 'baz'), 'label', min_length=3).apply())
        self.assertTrue(MinLengthRule({'a': 1, 'b': 2, 'c': 3}, 'label', min_length=3).apply())
        self.assertTrue(MinLengthRule({'foo', 'bar', 'baz'}, 'label', min_length=3).apply())

    def test_rule_supports_lambda_expressions(self):
        self.assertTrue(MinLengthRule(lambda: 'hello', 'label', min_length=3).apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(MinLengthRule('hello', 'label', min_length=10).apply())
        self.assertFalse(MinLengthRule(['foo', 'bar', 'baz'], 'label', min_length=10).apply())
        self.assertFalse(MinLengthRule(('foo', 'bar', 'baz'), 'label', min_length=10).apply())
        self.assertFalse(MinLengthRule({'a': 1, 'b': 2, 'c': 3}, 'label', min_length=10).apply())
        self.assertFalse(MinLengthRule({'foo', 'bar', 'baz'}, 'label', min_length=10).apply())

    def test_rules_returns_false_if_the_given_type_is_wrong(self):
        self.assertFalse(MinLengthRule(5, 'label', min_length=10).apply())
        self.assertFalse(MinLengthRule(datetime.now(), 'label', min_length=10).apply())

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = MinLengthRule('hello', 'label', min_length=10)
        self.assertEqual(rule.get_error_message(), MinLengthRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        rule = MinLengthRule('hello', 'label', min_length=10, error_message=CUSTOM_MESSAGE)
        self.assertEqual(rule.get_error_message(), CUSTOM_MESSAGE)

    # bitwise operators

    def test_rule_can_be_negated_with_bitwise_inversion(self):
        # since negated, fails because len('abcde') > 3
        negated_rule = ~ MinLengthRule('abcde', 'label', min_length=3)
        self.assertFalse(negated_rule.apply())

        # since negated, pass because len('a') is < 3
        negated_rule_2 = ~ MinLengthRule('a', 'label', min_length=3)
        self.assertTrue(negated_rule_2.apply())

        # since negated, pass because same length
        negated_rule_3 = ~ MinLengthRule('abc', 'label', min_length=3)
        self.assertFalse(negated_rule_3.apply())


class MaxLengthRuleTest(TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(MaxLengthRule('abc', 'label', max_length=3).apply())
        self.assertTrue(MaxLengthRule(['foo', 'bar', 'baz'], 'label', max_length=3).apply())
        self.assertTrue(MaxLengthRule(('foo', 'bar', 'baz'), 'label', max_length=3).apply())
        self.assertTrue(MaxLengthRule({'a': 1, 'b': 2, 'c': 3}, 'label', max_length=3).apply())
        self.assertTrue(MaxLengthRule({'foo', 'bar', 'baz'}, 'label', max_length=3).apply())

    def test_rule_supports_lambda_expressions(self):
        self.assertTrue(MaxLengthRule(lambda: 'abc', 'label', max_length=3).apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(MaxLengthRule('abc', 'label', max_length=2).apply())
        self.assertFalse(MaxLengthRule(['foo', 'bar', 'baz'], 'label', max_length=2).apply())
        self.assertFalse(MaxLengthRule(('foo', 'bar', 'baz'), 'label', max_length=2).apply())
        self.assertFalse(MaxLengthRule({'a': 1, 'b': 2, 'c': 3}, 'label', max_length=2).apply())
        self.assertFalse(MaxLengthRule({'foo', 'bar', 'baz'}, 'label', max_length=2).apply())

    def test_rules_returns_false_if_the_given_type_is_wrong(self):
        self.assertFalse(MaxLengthRule(8, 'label', max_length=2).apply())
        self.assertFalse(MaxLengthRule(datetime.now(), 'label', max_length=2).apply())

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = MaxLengthRule('abc', 'label', max_length=3)
        self.assertEqual(rule.get_error_message(), MaxLengthRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        rule = MaxLengthRule('abc', 'label', max_length=3, error_message=CUSTOM_MESSAGE)
        self.assertEqual(rule.get_error_message(), CUSTOM_MESSAGE)

    # bitwise operators

    def test_rule_can_be_negated_with_bitwise_inversion(self):
        # since negated, fails because len('abcde') < 3
        negated_rule = ~ MaxLengthRule('a', 'label', max_length=3)
        self.assertFalse(negated_rule.apply())

        # since negated, pass because len('abcde') is > 3
        negated_rule_2 = ~ MaxLengthRule('abcde', 'label', max_length=3)
        self.assertTrue(negated_rule_2.apply())

        # since negated, pass because same length
        negated_rule_3 = ~ MaxLengthRule('abc', 'label', max_length=3)
        self.assertFalse(negated_rule_3.apply())


class RangeRuleTest(TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(RangeRule(20, 'label', valid_range=range(10, 100)).apply())
        self.assertTrue(RangeRule(20, 'label', valid_range=range(100, 1, -1)).apply())

    def test_rule_supports_lambda_expressions(self):
        self.assertTrue(RangeRule(lambda: 20, 'label', valid_range=range(10, 100)).apply())

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

    # bitwise operators

    def test_rule_can_be_negated_with_bitwise_inversion(self):
        # since negated, fails because 22 is in range
        negated_rule = ~ RangeRule(22, 'label', valid_range=range(10, 100))
        self.assertFalse(negated_rule.apply())

        # since negated, pass because 500 is not in range
        negated_rule_2 = ~ RangeRule(500, 'label', valid_range=range(10, 100))
        self.assertTrue(negated_rule_2.apply())


class IntervalRuleTest(TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(IntervalRule(25, interval_from=10, interval_to=50, label='label').apply())

    def test_rule_supports_lambda_expressions(self):
        self.assertTrue(IntervalRule(lambda: 25, interval_from=10, interval_to=50, label='label').apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(IntervalRule(9, interval_from=10, interval_to=50, label='label').apply())
        self.assertFalse(IntervalRule(51, interval_from=10, interval_to=50, label='label').apply())
        self.assertFalse(IntervalRule('hello', interval_from=10, interval_to=50, label='label').apply())
        self.assertFalse(IntervalRule([1, 2, 3], interval_from=10, interval_to=50, label='label').apply())

    def test_rules_returns_false_if_the_given_type_is_wrong(self):
        self.assertFalse(IntervalRule(datetime.now(), interval_from=10, interval_to=50, label='label').apply())
        self.assertFalse(IntervalRule({'a': 123}, interval_from=10, interval_to=50, label='label').apply())

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = IntervalRule(9, interval_from=10, interval_to=50, label='label')
        self.assertEqual(rule.get_error_message(), IntervalRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        rule = IntervalRule(9, interval_from=10, interval_to=50, label='label', error_message=CUSTOM_MESSAGE)
        self.assertEqual(rule.get_error_message(), CUSTOM_MESSAGE)

    # bitwise operators

    def test_rule_can_be_negated_with_bitwise_inversion(self):
        # since negated, fails because 25 is in the interval
        negated_rule = ~ IntervalRule(25, interval_from=10, interval_to=50, label='label')
        self.assertFalse(negated_rule.apply())

        # since negated, pass because 200 is not in the interval
        negated_rule = ~ IntervalRule(200, interval_from=10, interval_to=50, label='label')
        self.assertTrue(negated_rule.apply())


class PatternRuleTest(TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(PatternRule('hello', 'label', pattern=r'^[a-z]+$').apply())
        self.assertTrue(PatternRule('HELLO', 'label', pattern=r'^[a-z]+$', flags=re.IGNORECASE).apply())

    def test_rule_supports_lambda_expressions(self):
        self.assertTrue(PatternRule(lambda: 'hello', 'label', pattern=r'^[a-z]+$').apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(PatternRule('HELLO', 'label', pattern=r'^[a-z]+$').apply())
        self.assertFalse(PatternRule('599.99', 'label', pattern=r'^[a-z]+$').apply())
        self.assertFalse(PatternRule('', 'label', pattern=r'^[a-z]+$').apply())

    def test_rule_returns_false_if_given_type_is_wrong(self):
        self.assertFalse(PatternRule(42, 'label', pattern=r'^[a-z]+$').apply())
        self.assertFalse(PatternRule([1, 2, 3], 'label', pattern=r'^[a-z]+$').apply())

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = PatternRule('hello', 'label', pattern=r'[a-z]+')
        self.assertEqual(rule.get_error_message(), PatternRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        msg = 'custom message'
        rule = PatternRule('hello', 'label', pattern=r'[a-z]+', error_message=msg)
        self.assertEqual(rule.get_error_message(), msg)

    # bitwise operators

    def test_rule_can_be_negated_with_bitwise_inversion(self):
        # since negated, fails because pattern is matched
        negated_rule = ~ PatternRule('hello', 'label', pattern=r'^[a-z]+$')
        self.assertFalse(negated_rule.apply())

        # since negated, pass because pattern is not matched
        negated_rule_2 = ~ PatternRule('213', 'label', pattern=r'^[a-z]+$')
        self.assertTrue(negated_rule_2.apply())


class PastDateRuleTest(TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(PastDateRule(datetime(2015, 1, 1), 'date', reference_date=datetime(2020, 1, 1)).apply())

    def test_rule_supports_lambda_expressions(self):
        rule = PastDateRule(lambda: datetime(2015, 1, 1), 'date', reference_date=datetime(2020, 1, 1))
        self.assertTrue(rule.apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(PastDateRule(datetime(2022, 1, 1), 'date', reference_date=datetime(2020, 1, 1)).apply())

    def test_rule_returns_false_if_given_type_is_wrong(self):
        self.assertFalse(PastDateRule('nope!', 'date', reference_date=datetime(2020, 1, 1)).apply())

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = PastDateRule(datetime(2015, 1, 1), 'date', reference_date=datetime(2020, 1, 1))
        self.assertEqual(rule.get_error_message(), PastDateRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        rule = PastDateRule(datetime(2015, 1, 1),
                            'date',
                            reference_date=datetime(2020, 1, 1),
                            error_message=CUSTOM_MESSAGE)
        self.assertEqual(rule.get_error_message(), CUSTOM_MESSAGE)

    # bitwise operators

    def test_rule_can_be_negated_with_bitwise_inversion(self):
        # since negated, fail because date is in the past
        negated_rule = ~ PastDateRule(datetime(2015, 1, 1), 'date', reference_date=datetime(2020, 1, 1))
        self.assertFalse(negated_rule.apply())

        # since negated, pass because date is not in the past
        negated_rule_2 = ~ PastDateRule(datetime(2030, 1, 1), 'date', reference_date=datetime(2020, 1, 1))
        self.assertTrue(negated_rule_2.apply())


class FutureDateRuleTest(TestCase):
    def test_rule_returns_true_if_respected(self):
        self.assertTrue(FutureDateRule(datetime(2015, 1, 1), 'date', reference_date=datetime(2010, 1, 1)).apply())

    def test_rule_supports_lambda_expressions(self):
        rule = FutureDateRule(lambda: datetime(2015, 1, 1), 'date', reference_date=datetime(2010, 1, 1))
        self.assertTrue(rule.apply())

    def test_rule_returns_false_if_not_respected(self):
        self.assertFalse(FutureDateRule(datetime(2000, 1, 1), 'date', reference_date=datetime(2020, 1, 1)).apply())

    def test_rule_returns_false_if_given_type_is_wrong(self):
        self.assertFalse(FutureDateRule('nope!', 'date', reference_date=datetime(2020, 1, 1)).apply())

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = FutureDateRule(datetime(2015, 1, 1), 'date', reference_date=datetime(2020, 1, 1))
        self.assertEqual(rule.get_error_message(), FutureDateRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        rule = FutureDateRule(datetime(2015, 1, 1),
                              'date',
                              reference_date=datetime(2020, 1, 1),
                              error_message=CUSTOM_MESSAGE)
        self.assertEqual(rule.get_error_message(), CUSTOM_MESSAGE)

    # bitwise operators

    def test_rule_can_be_negated_with_bitwise_inversion(self):
        # since negated, fail because date is in the future
        negated_rule = ~ FutureDateRule(datetime(2055, 1, 1), 'date', reference_date=datetime(2020, 1, 1))
        self.assertFalse(negated_rule.apply())

        # since negated, pass because date is not in the future
        negated_rule_2 = ~ FutureDateRule(datetime(1999, 1, 1), 'date', reference_date=datetime(2020, 1, 1))
        self.assertTrue(negated_rule_2.apply())


class UniqueItemsRuleTest(TestCase):
    def test_rule_returns_always_true_for_sets(self):
        self.assertTrue(UniqueItemsRule({'one', 'two', 'three'}, 'set_test').apply())
        self.assertTrue(UniqueItemsRule({1, 1, 1, 1}, 'set_test').apply())
        self.assertTrue(UniqueItemsRule(set(), 'list').apply())

    def test_rule_returns_true_if_respected_with_lists(self):
        self.assertTrue(UniqueItemsRule(['one', 'two', 'three'], 'list_test').apply())

    def test_rule_returns_false_if_not_respected_with_lists(self):
        self.assertFalse(UniqueItemsRule(['one', 'two', 'three', 'one'], 'list_test').apply())

    def test_rule_returns_true_if_respected_with_tuples(self):
        self.assertTrue(UniqueItemsRule(('one', 'two', 'three'), 'tuple_test').apply())

    def test_rule_returns_false_if_not_respected_with_tuples(self):
        self.assertFalse(UniqueItemsRule(('one', 'one', 'two', 'three'), 'tuple_test').apply())

    def test_rule_returns_true_if_respected_with_strings(self):
        self.assertTrue(UniqueItemsRule('ABCDE', 'string_test').apply())

    def test_rule_returns_false_if_not_respected_with_strings(self):
        self.assertFalse(UniqueItemsRule('ABCDEA', 'string_test').apply())

    def test_rule_returns_true_if_respected_with_dictionaries(self):
        self.assertTrue(UniqueItemsRule({'a': 1}, 'dict_test').apply())
        self.assertTrue(UniqueItemsRule({'a': 1, 'b': 2}, 'dict_test').apply())
        complex_data = {
            'a': {
                'x': 1,
                'y': [1, 2, 3]
            },
            'b': {
                'x': 1,
                'y': [1, 2, 3, 4]
            }
        }
        self.assertTrue(UniqueItemsRule(complex_data, 'dict_test').apply())

    def test_rule_returns_false_if_not_respected_with_dictionaries(self):
        self.assertFalse(UniqueItemsRule({'a': 1, 'b': 1}, 'dict_test').apply())
        complex_data = {
            'a': {
                'x': 1,
                'y': [1, 2, 3]
            },
            'b': {
                'x': 1,
                'y': [1, 2, 3]
            }
        }
        self.assertFalse(UniqueItemsRule(complex_data, 'dict_test').apply())

    def test_rule_supports_lambda_expressions(self):
        self.assertTrue(UniqueItemsRule(lambda: ['one', 'two', 'three'], 'list').apply())

    def test_rule_returns_false_if_given_type_is_wrong(self):
        self.assertFalse(UniqueItemsRule(42, 'list').apply())
        self.assertFalse(UniqueItemsRule(True, 'list').apply())
        self.assertFalse(UniqueItemsRule(datetime.now(), 'list').apply())

    def test_default_message_is_used_if_no_custom_provided(self):
        rule = UniqueItemsRule(['one', 'two', 'three'], 'list')
        self.assertEqual(rule.get_error_message(), UniqueItemsRule.default_error_message)

    def test_custom_message_used_if_provided(self):
        rule = UniqueItemsRule(['one', 'two', 'three'], 'list', error_message=CUSTOM_MESSAGE)
        self.assertEqual(rule.get_error_message(), CUSTOM_MESSAGE)

    # bitwise operators

    def test_rule_can_be_negated_with_bitwise_inversion(self):
        # since negated, fails because the list does not contain duplicated items
        negated_rule = ~ UniqueItemsRule(['one', 'two', 'three'], 'list_test')
        self.assertFalse(negated_rule.apply())

        # since negated, pass because the list contains duplicated items
        negated_rule = ~ UniqueItemsRule(['one', 'two', 'three', 'one'], 'list_test')
        self.assertTrue(negated_rule.apply())


if __name__ == '__main__':
    run_tests(verbosity=2)
