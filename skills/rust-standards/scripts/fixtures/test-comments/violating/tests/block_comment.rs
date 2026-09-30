//! §14.5 fixture: block comments are banned too.

#[test]
fn block_form() {
    /* multi
       line
       block */
    let value = 4;
    assert_eq!(value, 4);
}
