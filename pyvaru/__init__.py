from abc import ABC, abstractmethod

from inspect import isfunction

__version__ = '0.2.0'
__all__ = (
    'ValidationRule',
    'ValidationResult',
    'ValidationException',
    'Validator',
)


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

    #: Error message used if the value that is being validated is not the expected type (TypeError exception).
    type_error_message = 'Data type is invalid.'

    def __init__(self,
                 apply_to: object,
                 label: str,
                 error_message: str = None,
                 stop_if_invalid: bool = False):
        self.__apply_to = apply_to
        self.label = label
        self.custom_error_message = error_message
        self.stop_if_invalid = stop_if_invalid
        self._type_error_occurred = False

    @property
    def apply_to(self) -> object:
        if isfunction(self.__apply_to):
            # noinspection PyCallingNonCallable
            return self.__apply_to()
        return self.__apply_to

    @apply_to.setter
    def apply_to(self, what: object):
        self.__apply_to = what

    def get_error_message(self) -> str:
        """
        Returns the message that will be used by the validator if the rule is not respected.
        If a custom error message is provided during rule instantiation that one will be used,
        otherwise the default one.

        :return: Error message
        :rtype: str
        """
        if self._type_error_occurred:
            return self.type_error_message
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

    def annotate_exception(self, exception: Exception) -> None:
        """
        Takes note of an exception occurred during validation.
        (Typically caused by an invalid attribute/key access inside get_rules() method)

        :param exception: Exception catched during validate() phase.
        :param exception: Exception
        :return: None
        """
        if self.errors.get('Exception') is None:
            self.errors['Exception'] = []
        self.errors['Exception'].append(str(exception))

    def is_successful(self) -> bool:
        """
        Checks that the validation result does not contain errors.

        :return: True if the validation is successful, False otherwise.
        :rtype: bool
        """
        return len(self.errors) == 0


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
        self.validation_result = validation_result


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
                if not rule.apply():
                    result.annotate_rule_violation(rule)
                    if rule.stop_if_invalid:
                        break
        except (TypeError, KeyError, NameError, ValueError, AttributeError, IndexError) as e:
            result.annotate_exception(e)
        return result
