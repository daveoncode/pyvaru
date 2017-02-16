# Pyvaru Changelog

## v0.2.0

### Improvement:
- ValidationRule's apply_to parameter can now be passed as a lambda expression

### Fixes:
- UniqueItemsRule now works properly with dictionaries by checking values uniqueness

## v0.1.1

### Improvement:
- Attribute/Key/Index errors that may occur in the Validator's get_rules() method are now catched in validate()
implementation and the error properly reported in the ValidationResult

## v0.1.0
### Added:

- Core API (ValidationRule, Validator, ValidationResult, ValidationException)
- Common validation rules
