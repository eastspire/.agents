
/// Guard lives in its own block and is dropped before the signal set.
pub(crate) fn count_and_publish(cell: &RefCell<Vec<i32>>, signal: Signal<usize>) {
    let count: usize = {
        let guard: Ref<'_, Vec<i32>> = cell.borrow();
        guard.len()
    };
    signal.set(count);
}
