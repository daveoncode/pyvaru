import re
from datetime import datetime

from pyvaru import ValidationRule

__all__ = (
    'TypeRule',
    'FullStringRule',
    'ChoiceRule',
    'MinValueRule',
    'MaxValueRule',
    'MinLengthRule',
    'MaxLengthRule',
    'RangeRule',
    'IntervalRule',
    'PatternRule',
    'PastDateRule',
    'FutureDateRule',
    'UniqueItemsRule',
)


class TypeRule(ValidationRule):
    """
    Ensure that the target value is an instance of the given type.

    :param apply_to: Value against which the rule is applied (can be any type).
    :type apply_to: object
    :param label: Short string describing the field that will be validated (e.g. "phone number", "user name"...). \
    This string will be used as the key in the ValidationResult error dictionary.
    :type label: str
    :param valid_type: Valid class
    :type valid_type: type
    :param error_message: Custom message that will be used instead of the "default_error_message".
    :type error_message: str
    :param stop_if_invalid: True to prevent Validator from processing the rest of the get_rules if the current one \
    is not respected, False (default) to collect all the possible errors.
    :type stop_if_invalid: bool
    """

    #: Default error message for the rule.
    default_error_message = 'Object is not an instance of the expected type.'

    def __init__(self,
                 apply_to: object,
                 label: str,
                 valid_type: type,
                 error_message: str = None,
                 stop_if_invalid: bool = False):
        super().__init__(apply_to, label, error_message, stop_if_invalid)
        self.valid_type = valid_type

    def apply(self) -> bool:
        return isinstance(self.apply_to, self.valid_type)


class FullStringRule(ValidationRule):
    """
    Ensure that the target value is a non empty string object.

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

    #: Default error message for the rule.
    default_error_message = 'String is empty.'

    #: Error message used if the value that is being validated is not a string.
    type_error_message = 'Not a string.'

    def __init__(self, apply_to: object, label: str, error_message: str = None, stop_if_invalid: bool = False):
        super().__init__(apply_to, label, error_message, stop_if_invalid)

    def apply(self):
        value = self.apply_to  # type: str
        if isinstance(value, str):
            return len(value.strip()) > 0
        else:
            self._type_error_occurred = True
            return False


class ChoiceRule(ValidationRule):
    """
    Ensure that the target value is contained in a provided list of possible options.

    :param apply_to: Value against which the rule is applied (can be any type).
    :type apply_to: object
    :param label: Short string describing the field that will be validated (e.g. "phone number", "user name"...). \
    This string will be used as the key in the ValidationResult error dictionary.
    :type label: str
    :param choices: Available options.
    :type choices: tuple
    :param error_message: Custom message that will be used instead of the "default_error_message".
    :type error_message: str
    :param stop_if_invalid: True to prevent Validator from processing the rest of the get_rules if the current one \
    is not respected, False (default) to collect all the possible errors.
    :type stop_if_invalid: bool
    """

    #: Default error message for the rule.
    default_error_message = 'Value not found in available choices.'

    def __init__(self,
                 apply_to: object,
                 label: str,
                 choices: tuple,
                 error_message: str = None,
                 stop_if_invalid: bool = False):
        super().__init__(apply_to, label, error_message, stop_if_invalid)
        self.choices = choices

    def apply(self) -> bool:
        return self.apply_to in self.choices


class MinValueRule(ValidationRule):
    """
    Ensure that the target value is >= than the provided reference value.

    :param apply_to: Value against which the rule is applied (can be any type).
    :type apply_to: object
    :param label: Short string describing the field that will be validated (e.g. "phone number", "user name"...). \
    This string will be used as the key in the ValidationResult error dictionary.
    :type label: str
    :param min_value: Minimum value allowed.
    :type min_value: float
    :param error_message: Custom message that will be used instead of the "default_error_message".
    :type error_message: str
    :param stop_if_invalid: True to prevent Validator from processing the rest of the get_rules if the current one \
    is not respected, False (default) to collect all the possible errors.
    :type stop_if_invalid: bool
    """

    #: Default error message for the rule.
    default_error_message = 'Value is smaller than expected one.'

    def __init__(self,
                 apply_to: object,
                 label: str,
                 min_value: float,
                 error_message: str = None,
                 stop_if_invalid: bool = False):
        super().__init__(apply_to, label, error_message, stop_if_invalid)
        self.min_value = min_value

    def apply(self) -> bool:
        try:
            return self.apply_to >= self.min_value
        except TypeError:
            self._type_error_occurred = True
            return False


class MaxValueRule(ValidationRule):
    """
    Ensure that the target value is <= than the provided reference value.

    :param apply_to: Value against which the rule is applied (can be any type).
    :type apply_to: object
    :param label: Short string describing the field that will be validated (e.g. "phone number", "user name"...). \
    This string will be used as the key in the ValidationResult error dictionary.
    :type label: str
    :param max_value: Maximum value allowed.
    :type max_value: float
    :param error_message: Custom message that will be used instead of the "default_error_message".
    :type error_message: str
    :param stop_if_invalid: True to prevent Validator from processing the rest of the get_rules if the current one \
    is not respected, False (default) to collect all the possible errors.
    :type stop_if_invalid: bool
    """

    #: Default error message for the rule.
    default_error_message = 'Value is greater than expected one.'

    def __init__(self,
                 apply_to: object,
                 label: str,
                 max_value: float,
                 error_message: str = None,
                 stop_if_invalid: bool = False):
        super().__init__(apply_to, label, error_message, stop_if_invalid)
        self.max_value = max_value

    def apply(self) -> bool:
        try:
            return self.apply_to <= self.max_value
        except TypeError:
            self._type_error_occurred = True
            return False


class MinLengthRule(ValidationRule):
    """
    Ensure that the target value has a length >= than the provided reference value.
    This rule can be applied to all python objects supporting len() (strings, lists, tuples, sets, dicts... and even
    custom types).

    :param apply_to: Value against which the rule is applied (can be any type).
    :type apply_to: object
    :param label: Short string describing the field that will be validated (e.g. "phone number", "user name"...). \
    This string will be used as the key in the ValidationResult error dictionary.
    :type label: str
    :param min_length: Minimum length allowed.
    :type min_length: int
    :param error_message: Custom message that will be used instead of the "default_error_message".
    :type error_message: str
    :param stop_if_invalid: True to prevent Validator from processing the rest of the get_rules if the current one \
    is not respected, False (default) to collect all the possible errors.
    :type stop_if_invalid: bool
    """

    #: Default error message for the rule.
    default_error_message = 'Length is smaller than expected one.'

    def __init__(self,
                 apply_to: object,
                 label: str,
                 min_length: int,
                 error_message: str = None,
                 stop_if_invalid: bool = False):
        super().__init__(apply_to, label, error_message, stop_if_invalid)
        self.min_length = min_length

    def apply(self) -> bool:
        try:
            # noinspection PyTypeChecker
            return len(self.apply_to) >= self.min_length
        except TypeError:
            self._type_error_occurred = True
            return False


class MaxLengthRule(ValidationRule):
    """
    Ensure that the target value has a length <= than the provided reference value.
    This rule can be applied to all python objects supporting len() (strings, lists, tuples, sets, dicts... and even
    custom types).

    :param apply_to: Value against which the rule is applied (can be any type).
    :type apply_to: object
    :param label: Short string describing the field that will be validated (e.g. "phone number", "user name"...). \
    This string will be used as the key in the ValidationResult error dictionary.
    :type label: str
    :param max_length: Maximum length allowed.
    :type max_length: int
    :param error_message: Custom message that will be used instead of the "default_error_message".
    :type error_message: str
    :param stop_if_invalid: True to prevent Validator from processing the rest of the get_rules if the current one \
    is not respected, False (default) to collect all the possible errors.
    :type stop_if_invalid: bool
    """

    #: Default error message for the rule.
    default_error_message = 'Length is greater than expected one.'

    def __init__(self,
                 apply_to: object,
                 label: str,
                 max_length: int,
                 error_message: str = None,
                 stop_if_invalid: bool = False):
        super().__init__(apply_to, label, error_message, stop_if_invalid)
        self.max_length = max_length

    def apply(self) -> bool:
        try:
            # noinspection PyTypeChecker
            return len(self.apply_to) <= self.max_length
        except TypeError:
            self._type_error_occurred = True
            return False


class RangeRule(ValidationRule):
    """
    Ensure that the target value is contained in the provided range.

    **IMPORTANT**: this rule handles python range() objects (and its "step" configuration),
    so does not support floats as test value
    (testing for a float will always fail and even for an integer if it doesn't match the step increment).

    For a validation like "value *BETWEEN* x *AND* y" use **IntervalRule** instead!

    :param apply_to: Value against which the rule is applied (can be any type).
    :type apply_to: object
    :param label: Short string describing the field that will be validated (e.g. "phone number", "user name"...). \
    This string will be used as the key in the ValidationResult error dictionary.
    :type label: str
    :param valid_range: Allowed range.
    :type valid_range: range
    :param error_message: Custom message that will be used instead of the "default_error_message".
    :type error_message: str
    :param stop_if_invalid: True to prevent Validator from processing the rest of the get_rules if the current one \
    is not respected, False (default) to collect all the possible errors.
    :type stop_if_invalid: bool
    """

    #: Default error message for the rule.
    default_error_message = 'Value is out of range.'

    def __init__(self,
                 apply_to: object,
                 label: str,
                 valid_range: range,
                 error_message: str = None,
                 stop_if_invalid: bool = False):
        super().__init__(apply_to, label, error_message, stop_if_invalid)
        self.valid_range = valid_range

    def apply(self) -> bool:
        return self.apply_to in self.valid_range


class IntervalRule(ValidationRule):
    """
    Ensure that the target value is contained in the provided interval.

    :param apply_to: Value against which the rule is applied (can be any type).
    :type apply_to: object
    :param label: Short string describing the field that will be validated (e.g. "phone number", "user name"...). \
    This string will be used as the key in the ValidationResult error dictionary.
    :type label: str
    :param interval_from: Minimum allowed value.
    :type interval_from: float
    :param interval_to: Maximum allowed value.
    :type interval_to: float
    :param error_message: Custom message that will be used instead of the "default_error_message".
    :type error_message: str
    :param stop_if_invalid: True to prevent Validator from processing the rest of the get_rules if the current one \
    is not respected, False (default) to collect all the possible errors.
    :type stop_if_invalid: bool
    """

    #: Default error message for the rule.
    default_error_message = 'Value is not in interval.'

    def __init__(self,
                 apply_to: object,
                 label: str,
                 interval_from: float,
                 interval_to: float,
                 error_message: str = None,
                 stop_if_invalid: bool = False):
        super().__init__(apply_to, label, error_message, stop_if_invalid)
        self.interval_from = interval_from
        self.interval_to = interval_to

    def apply(self) -> bool:
        try:
            return self.interval_from <= self.apply_to <= self.interval_to
        except TypeError:
            self._type_error_occurred = True
            return False


class PatternRule(ValidationRule):
    """
    Ensure that the target string respects the given pattern.

    :param apply_to: Value against which the rule is applied (can be any type).
    :type apply_to: object
    :param pattern: Regex used for pattern matching.
    :type pattern: str
    :param flags: Regex flags.
    :type flags: int
    :param label: Short string describing the field that will be validated (e.g. "phone number", "user name"...). \
    This string will be used as the key in the ValidationResult error dictionary.
    :type label: str
    :param error_message: Custom message that will be used instead of the "default_error_message".
    :type error_message: str
    :param stop_if_invalid: True to prevent Validator from processing the rest of the get_rules if the current one \
    is not respected, False (default) to collect all the possible errors.
    :type stop_if_invalid: bool
    """

    #: Default error message for the rule.
    default_error_message = 'Value does not match expected pattern.'

    #: Error message used if the value that is being validated is not a string.
    type_error_message = 'Not a string.'

    def __init__(self,
                 apply_to: object,
                 label: str,
                 pattern: str,
                 flags: int = 0,
                 error_message: str = None,
                 stop_if_invalid: bool = False):
        super().__init__(apply_to, label, error_message, stop_if_invalid)
        self.pattern = pattern
        self.flags = flags

    def apply(self) -> bool:
        string = self.apply_to  # type: str
        try:
            return re.match(self.pattern, string, self.flags) is not None
        except TypeError:
            self._type_error_occurred = True
            return False


class PastDateRule(ValidationRule):
    """
    Ensure that the target value is a past date.

    :param apply_to: Value against which the rule is applied.
    :type apply_to: object
    :param label: Short string describing the field that will be validated (e.g. "phone number", "user name"...). \
    This string will be used as the key in the ValidationResult error dictionary.
    :type label: str
    :param reference_date: Date used for time checking (default to datetime.now()).
    :type reference_date: datetime
    :param error_message: Custom message that will be used instead of the "default_error_message".
    :type error_message: str
    :param stop_if_invalid: True to prevent Validator from processing the rest of the get_rules if the current one \
    is not respected, False (default) to collect all the possible errors.
    :type stop_if_invalid: bool
    """

    #: Default error message for the rule.
    default_error_message = 'Not a past date.'

    #: Error message used if the value that is being validated is not a date.
    type_error_message = 'Not a date object.'

    def __init__(self,
                 apply_to: object,
                 label: str,
                 reference_date: datetime = None,
                 error_message: str = None,
                 stop_if_invalid: bool = False):
        super().__init__(apply_to, label, error_message, stop_if_invalid)
        self.reference_date = reference_date or datetime.now()

    def apply(self) -> bool:
        try:
            return self.apply_to < self.reference_date
        except TypeError:
            self._type_error_occurred = True
            return False


class FutureDateRule(ValidationRule):
    """
    Ensure that the target value is a future date.

    :param apply_to: Value against which the rule is applied.
    :type apply_to: object
    :param label: Short string describing the field that will be validated (e.g. "phone number", "user name"...). \
    This string will be used as the key in the ValidationResult error dictionary.
    :type label: str
    :param reference_date: Date used for time checking (default to datetime.now()).
    :type reference_date: datetime
    :param error_message: Custom message that will be used instead of the "default_error_message".
    :type error_message: str
    :param stop_if_invalid: True to prevent Validator from processing the rest of the get_rules if the current one \
    is not respected, False (default) to collect all the possible errors.
    :type stop_if_invalid: bool
    """

    #: Default error message for the rule.
    default_error_message = 'Not a future date.'

    #: Error message used if the value that is being validated is not a date.
    type_error_message = 'Not a date object.'

    def __init__(self,
                 apply_to: object,
                 label: str,
                 reference_date: datetime = None,
                 error_message: str = None,
                 stop_if_invalid: bool = False):
        super().__init__(apply_to, label, error_message, stop_if_invalid)
        self.reference_date = reference_date or datetime.now()

    def apply(self) -> bool:
        try:
            return self.apply_to > self.reference_date
        except TypeError:
            self._type_error_occurred = True
            return False


class UniqueItemsRule(ValidationRule):
    """
    Ensure that the target list (or iterable) does not contain duplicated items.

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

    #: Default error message for the rule.
    default_error_message = 'List contains duplicated items.'

    #: Error message used if the value that is being validated is not an iterable one.
    type_error_message = 'Not an iterable object.'

    def __init__(self, apply_to: object, label: str, error_message: str = None, stop_if_invalid: bool = False):
        super().__init__(apply_to, label, error_message, stop_if_invalid)

    def _dictionary_items_are_unique(self):
        data = self.apply_to  # type: dict
        values = list(data.values())
        if len(values) > 1:
            index = 1
            while index < len(values):
                if values[index - 1] == values[index]:
                    return False
                index += 1
        return True

    def _collection_items_are_unique(self):
        try:
            # noinspection PyTypeChecker
            return len(set(self.apply_to)) == len(self.apply_to)
        except TypeError:
            self._type_error_occurred = True
            return False

    def apply(self) -> bool:
        if isinstance(self.apply_to, dict):
            return self._dictionary_items_are_unique()
        if isinstance(self.apply_to, set):
            return True
        return self._collection_items_are_unique()
