//! §14.5 fixture: every comment form is banned in a test file.

use std::fmt::Display;

fn assert_display<T: Display>(value: T) -> String {
    format!("{value}")
}

#[test]
fn returns_input_verbatim() {
    // a line comment
    let text = String::from("hi");
    assert_eq!(assert_display(text), "hi");
}

#[test]
fn also_flags_doc_style() {
    /// a doc comment in a test
    let value = 1;
    assert_eq!(value, 1);
}

#[test]
fn also_flags_inner_attribute() {
    //! an inner doc comment in a test
    let value = 2;
    assert_eq!(value, 2);
}

#[test]
fn also_flags_trailing() {
    let value = 3; // trailing comment
    assert_eq!(value, 3);
}
