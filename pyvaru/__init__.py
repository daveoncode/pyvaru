import pprint
from abc import ABC, abstractmethod
from enum import Enum

from inspect import isfunction

__version__ = '0.3.0'
__all__ = (
    'ValidationRule',
    'ValidationResult',
    'ValidationException',
    'Validator',
    'JoinType',
    'RuleGroup',
    'InvalidRuleGroupException',
)


class JoinType(Enum):
    AND = 1
    OR = 2
    XOR = 3
    NOT = 4


class ValidationRule(ABC):
    """
    Base abstract rule class from which concrete ones must inherit from.

    :param apply_to: Value against which the rule is applied (can be any type).
    :type apply_to: object
    :param label: Short string describing the field that will be validated (e.g. "phone number", "user name"...). \
    This string will be used as the key in the ValidationResult error dictionary.
    :type label: str
    :param error_message: Custom message that will be used instead of the "default_error_message".
    :type error_message: str
    :param stop_if_invalid: True to prevent Validator from processing the rest of the get_rules if the current one \
    is not respected, False (default) to collect all the possible errors.
    :type stop_if_invalid: bool
    """

    #: Default error message for the rule (class attribute).
    default_error_message = 'Data is invalid.'

    def __init__(self,
                 apply_to: object,
                 label: str,
                 error_message: str = None,
                 stop_if_invalid: bool = False):
        self.__apply_to = apply_to
        self.label = label
        self.custom_error_message = error_message
        self.stop_if_invalid = stop_if_invalid

    @property
    def apply_to(self) -> object:
        if isfunction(self.__apply_to):
            # noinspection PyCallingNonCallable
            return self.__apply_to()
        return self.__apply_to

    def get_error_message(self) -> str:
        """
        Returns the message that will be used by the validator if the rule is not respected.
        If a custom error message is provided during rule instantiation that one will be used,
        otherwise the default one.

        :return: Error message
        :rtype: str
        """
        return self.custom_error_message or self.default_error_message

    @abstractmethod
    def apply(self) -> bool:
        """
        Abstract method that must be implemented by concrete get_rules in order to return a boolean
        indicating whether the rule is respected or not.

        :return: True if the rule is respected, False otherwise
        :rtype: bool
        """
        pass  # pragma: no cover

    def __invert__(self):
        def inverted_apply(apply):
            def decorated_function():
                return not apply()

            return decorated_function

        self.apply = inverted_apply(self.apply)
        return self


class InvalidRuleGroupException(Exception):
    """
    Exception raised by RuleGroup if the provided configuration is invalid.
    """
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class RuleGroup(ValidationRule):
    """
    Allows the execution of multiple rules sequentially.
    
    :Example:
        
    >>> rules = [
    >>>    (TypeRule, {'valid_type': list}),
    >>>    (MinLengthRule, {'min_length': 1}),
    >>>    UniqueItemsRule
    >>> ]
    >>> group = RuleGroup(apply_to=countries, label='Countries', rules=rules)

    :param apply_to: Value against which the rule is applied (can be any type).
    :type apply_to: object
    :param label: Short string describing the field that will be validated (e.g. "phone number", "user name"...). \
    This string will be used as the key in the ValidationResult error dictionary.
    :type label: str
    :param rules: List of rules to execute. The list can contain rule type (ie: FullStringRule, MinValueRule...) or \
    tuples in the format: "(RuleClass, options)" (ie: "(MinLengthRule, {'min_length': 1})")
    :type rules: list
    :param error_message: Custom message that will be used instead of the "default_error_message".
    :type error_message: str
    :param stop_if_invalid: True to prevent Validator from processing the rest of the get_rules if the current one \
    is not respected, False (default) to collect all the possible errors.
    :type stop_if_invalid: bool
    """

    def __init__(self,
                 apply_to: object,
                 label: str,
                 rules: list,
                 error_message: str = None,
                 stop_if_invalid: bool = False):
        super().__init__(apply_to, label, error_message, stop_if_invalid)
        self.rules = rules
        self._failed_rule = None

    def _get_configured_rule(self, entry):
        rule_config = {'apply_to': self.apply_to, 'label': self.label}
        rule_class = entry
        if isinstance(entry, (list, tuple)):
            if len(entry) != 2 or not issubclass(entry[0], ValidationRule) or not isinstance(entry[1], dict):
                msg = 'Provided rule configuration does not respect the format: ' \
                      '(rule_class: ValidationRule, rule_config: dict)'
                raise InvalidRuleGroupException(msg)
            rule_class = entry[0]
            rule_config.update(entry[1])
        elif entry is None or not issubclass(entry, ValidationRule):
            msg = 'Expected type "ValidationRule", got "{}" instead.'.format(str(entry))
            raise InvalidRuleGroupException(msg)
        rule = rule_class(**rule_config)  # type: ValidationRule
        return rule

    def get_error_message(self) -> str:
        if isinstance(self._failed_rule, ValidationRule):
            return self._failed_rule.get_error_message()
        return super().get_error_message()

    def apply(self) -> bool:
        for entry in self.rules:
            rule = self._get_configured_rule(entry)
            try:
                if not rule.apply():
                    self._failed_rule = rule
                    return False
            except Exception:
                self._failed_rule = rule
                return False
        return True


class ValidationResult:
    """
    Represents a report of Validator's validate() call.

    :param errors: Map containing errors descriptions (if one ore more get_rules are not respected)
    :type errors: dict
    """

    def __init__(self, errors: dict = None):
        self.errors = errors or {}

    def annotate_rule_violation(self, rule: ValidationRule) -> None:
        """
        Takes note of a rule validation failure by collecting its error message.

        :param rule: Rule that failed validation.
        :type rule: ValidationRule
        :return: None
        """
        if self.errors.get(rule.label) is None:
            self.errors[rule.label] = []
        self.errors[rule.label].append(rule.get_error_message())

    def annotate_exception(self, exception: Exception, rule: ValidationRule = None) -> None:
        """
        Takes note of an exception occurred during validation.
        (Typically caused by an invalid attribute/key access inside get_rules() method)

        :param exception: Exception catched during validate() phase.
        :type exception: Exception
        :param rule: Validation rule that has generated the exception.
        :type rule: ValidationRule
        :return: None
        """
        error_key = rule.label if isinstance(rule, ValidationRule) else 'get_rules'
        if self.errors.get(error_key) is None:
            self.errors[error_key] = []
        self.errors[error_key].append(str(exception))

    def is_successful(self) -> bool:
        """
        Checks that the validation result does not contain errors.

        :return: True if the validation is successful, False otherwise.
        :rtype: bool
        """
        return len(self.errors) == 0

    def __str__(self):
        info = {'errors': self.errors or {}}
        formatted_string = pprint.pformat(info)
        return formatted_string


class ValidationException(Exception):
    """
    Internal exception used by the library to represent a validation failure when using a Validator as a context
    processor.

    :param validation_result: Validation result returned by validator.
    :type validation_result: ValidationResult
    :param message: Error message
    :type message: str
    """

    def __init__(self, validation_result: ValidationResult, message: str = 'Data did not validate.'):
        super().__init__(message)
        self.message = message
        self.validation_result = validation_result

    def __str__(self):
        info = {'message': self.message, 'errors': self.validation_result.errors}
        formatted_string = pprint.pformat(info)
        return formatted_string


class Validator(ABC):
    """
    Validate a data model against a list of ValidationRule(s).
    This class is abstract, concrete validators must inherit from Validator in order to provide a
    an actual implementation of get_rules().

    :param data: Data model to validate (like a dict or a custom Python object instance).
    :type data: object
    """

    def __init__(self, data: object):
        self.data = data

    def __enter__(self):
        validation = self.validate()
        if not validation.is_successful():
            raise ValidationException(validation)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @abstractmethod
    def get_rules(self) -> list:
        """
        Concrete validators must implement this abstract method in order to return a list of ValidationRule(s),
        that will be used to validate the model.

        :return: ValidationRule list
        :rtype: list
        """
        pass  # pragma: no cover

    def validate(self) -> ValidationResult:
        """
        Apply the configured ValidationRule(s) (in the given order) and return a ValidationResult object.

        :return: validation result
        :rtype: ValidationResult
        """
        result = ValidationResult()
        try:
            for rule in self.get_rules():
                try:
                    if not rule.apply():
                        result.annotate_rule_violation(rule)
                        if rule.stop_if_invalid:
                            break
                except Exception as e:
                    result.annotate_exception(e, rule)
        except Exception as e:
            result.annotate_exception(e, None)
        return result
