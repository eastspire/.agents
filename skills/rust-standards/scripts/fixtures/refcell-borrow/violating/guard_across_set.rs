
/// The guard is still in scope when the signal set re-renders.
pub(crate) fn publish_len(cell: &RefCell<Vec<i32>>, signal: Signal<usize>) {
    let guard: Ref<'_, Vec<i32>> = cell.borrow();
    let count: usize = guard.len();
    signal.set(count);
}
