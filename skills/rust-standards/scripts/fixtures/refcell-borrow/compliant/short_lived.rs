
/// One-line borrows: the temporary guard dies at the end of the statement.
pub(crate) fn read_len(cell: &RefCell<Vec<i32>>) -> usize {
    cell.borrow().len()
}

/// Sequential statements: the first guard is dropped before the second.
pub(crate) fn push_and_count(cell: &RefCell<Vec<i32>>, value: i32) -> usize {
    cell.borrow_mut().push(value);
    cell.borrow().len()
}

/// try_borrow with a defined fallback, no unwrap.
pub(crate) fn read_or_default(cell: &RefCell<Vec<i32>>) -> usize {
    match cell.try_borrow() {
        Ok(guard) => guard.len(),
        Err(_) => 0,
    }
}
