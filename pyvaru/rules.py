import re

from pyvaru import ValidationRule


class TypeRule(ValidationRule):
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
    default_error_message = 'Invalid or empty string.'

    def apply(self):
        value = self.apply_to  # type: str
        return isinstance(value, str) and len(value.strip()) > 0


class ChoiceRule(ValidationRule):
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
        return self.apply_to >= self.min_value


class MaxValueRule(ValidationRule):
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
        return self.apply_to <= self.max_value


class MinLengthRule(ValidationRule):
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
        # noinspection PyTypeChecker
        return len(self.apply_to) >= self.min_length


class MaxLengthRule(ValidationRule):
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
        # noinspection PyTypeChecker
        return len(self.apply_to) <= self.max_length


class RangeRule(ValidationRule):
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


class RegexRule(ValidationRule):
    default_error_message = 'Value does not match expected pattern.'

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
        return re.match(self.pattern, string, self.flags) is not None
