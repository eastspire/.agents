
/// The guard is still in scope across a web-sys call.
pub(crate) fn publish_via_window(cell: &RefCell<Vec<i32>>, signal: Signal<usize>) {
    let mut guard: RefMut<'_, Vec<i32>> = cell.borrow_mut();
    guard.clear();
    let target: Option<Window> = window();
    signal.set(target.is_some() as usize);
}
