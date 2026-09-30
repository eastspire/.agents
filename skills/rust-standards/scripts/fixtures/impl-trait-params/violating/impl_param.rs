//! Fixture: impl Trait used as a parameter type.
/// Every one of these is a §9.2 violation.

use std::fmt::Display;

/// §9.2 forbids this: the caller can never name the bound.
pub fn render(value: impl Display) -> String {
    format!("{value}")
}

/// Multi-parameter form, also forbidden.
pub fn compare(left: impl AsRef<str>, right: impl AsRef<str>) -> bool {
    left.as_ref() == right.as_ref()
}

/// A reference to an opaque type is the same violation.
pub fn borrow_it(value: &impl AsRef<str>) -> usize {
    value.as_ref().len()
}
