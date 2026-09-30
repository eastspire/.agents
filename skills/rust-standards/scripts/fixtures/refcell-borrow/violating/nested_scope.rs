
/// Guard declared inside a nested block, re-entrant call after the block.
pub(crate) fn step_then_publish(
    cell: &RefCell<Vec<i32>>,
    signal: Signal<usize>,
    inner: bool,
) {
    if inner {
        {
            let guard: RefMut<'_, Vec<i32>> = cell.borrow_mut();
            guard.push(1);
        }
        signal.set(1);
    }
}
