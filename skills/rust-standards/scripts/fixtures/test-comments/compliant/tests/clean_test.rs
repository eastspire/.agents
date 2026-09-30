use std::fmt::Display;
fn assert_display<T: Display>(value: T) -> String {
    format!("{value}")
}

#[test]
fn returns_input_verbatim() {
    let text = String::from("hi");
    assert_eq!(assert_display(text), "hi");
}

#[test]
fn double_slash_inside_a_string_is_not_a_comment() {
    let url = String::from("https://example.com");
    assert!(url.contains("https://"));
}
