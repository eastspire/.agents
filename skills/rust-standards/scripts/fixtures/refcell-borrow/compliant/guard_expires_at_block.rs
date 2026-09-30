
/// Guard is used and the block closes before any re-entrant call.
/// Scope tracking MUST consider this guard dead at the next statement.
pub(crate) fn publish_after_block(
    cell: &RefCell<Vec<i32>>,
    signal: Signal<usize>,
) {
    let count: usize = {
        let guard: Ref<'_, Vec<i32>> = cell.borrow();
        guard.len()
    };
    signal.set(count);
}
