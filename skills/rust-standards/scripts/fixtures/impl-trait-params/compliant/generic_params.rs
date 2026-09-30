//! Fixture: §9.2-compliant spellings. Must produce zero findings.

use std::fmt::Display;

/// Return-position `impl Trait` is idiomatic and explicitly ALLOWED.
pub fn numbers() -> impl Iterator<Item = u32> {
    (0..10).map(|value| value * 2)
}

/// A `where` clause is the required spelling.
pub fn render<T>(value: T) -> String
where
    T: Display,
{
    format!("{value}")
}

/// Explicit generic bound on the parameter type.
pub fn compare<T, U>(left: T, right: U) -> bool
where
    T: AsRef<str>,
    U: AsRef<str>,
{
    left.as_ref() == right.as_ref()
}

/// A type implementing the trait in a bound position is fine.
pub struct Wrapper<T: Display>(T);

/// The word "impl" in a doc comment must not be reported.
/// Docs mention impl Iterator above; a string mentioning "impl Foo" too.
pub const NOTE: &str = "impl Trait";
