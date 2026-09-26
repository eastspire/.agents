# euv-ui 完整 pub API(组件 + hooks + style)

Source: `ui/src/` — auto-extracted from `pub` declarations.

Re-exported at crate root as `euv::euv_button`, `euv::use_async` 等 via `ui/src/lib.rs` `pub use {component::*, hook::*, style::*}`.

### `component::router::fn`

- `fn` **`normalize_path`** — `pub fn normalize_path(path: &str) -> String {...}`
- `fn` **`route_matches`** — `pub fn route_matches(route_path: &str, request_path: &str) -> bool {...}`
- `fn` **`find_active_route`** — `pub fn find_active_route<'a>( path: &str, routes: &'a [NestedRouteConfig], ) -> Option<&'a NestedRouteConfig> {...}`
- `fn` **`route_chain`** — `pub fn route_chain<'a>(path: &str, routes: &'a [NestedRouteConfig]) -> Vec<&'a NestedRouteConfig> {...}`
- `fn` **`build_chain`** — `pub(crate) fn build_chain<'a>( path: &str, routes: &'a [NestedRouteConfig], chain: &mut Vec<&'a NestedRouteConfig>, ) -> bool {...}`

### `component::router::impl`

- `fn` **`new`** — `pub fn new<P, F>(path: P, component: F, children: Vec<NestedRouteConfig>) -> Self where P: Into<String>, F: Fn() -> VirtualNode + 'static, {...}`
- `fn` **`component`** — `pub fn component(&self) -> Rc<dyn Fn() -> VirtualNode> {...}`
- `fn` **`children`** — `pub fn children(&self) -> &[NestedRouteConfig] {...}`

### `component::router::struct`

- `struct` **`NestedRouteConfig`** — `pub struct NestedRouteConfig {`

### `hook::counter::impl`

- `fn` **`increment`** — `pub fn increment(&self) {...}`
- `fn` **`decrement`** — `pub fn decrement(&self) {...}`
- `fn` **`set`** — `pub fn set(&self, next: i32) {...}`
- `fn` **`set_unchecked`** — `pub fn set_unchecked(&self, next: i32) {...}`
- `fn` **`is_at_max`** — `pub fn is_at_max(&self) -> bool {...}`
- `fn` **`is_at_min`** — `pub fn is_at_min(&self) -> bool {...}`
- `fn` **`get`** — `pub fn get(&self) -> i32 {...}`

### `hook::counter::struct`

- `struct` **`Counter`** — `pub struct Counter {`

### `hook::debounced_value::enum`

- `enum` **`DebounceState`** — `pub(crate) enum DebounceState<T> {`

### `hook::debounced_value::fn`

- `fn` **`use_debounced_value`** — `pub fn use_debounced_value<T>(delay_ms: u32) -> DebouncedValue<T> where T: Clone + PartialEq + Debug + Default + 'static, {...}`

### `hook::debounced_value::impl`

- `fn` **`set`** — `pub fn set(&self, next: T, now_ms: u64) {...}`
- `fn` **`tick`** — `pub fn tick(&self, now_ms: u64) -> bool {...}`
- `fn` **`cancel`** — `pub fn cancel(&self) {...}`
- `fn` **`get`** — `pub fn get(&self) -> T {...}`
- `fn` **`is_pending`** — `pub fn is_pending(&self) -> bool {...}`

### `hook::debounced_value::struct`

- `struct` **`DebouncedValue`** — `pub struct DebouncedValue<T: Clone + PartialEq + Default + 'static> {`

### `hook::error_boundary::enum`

- `enum` **`ErrorBoundaryPhase`** — `pub enum ErrorBoundaryPhase {`

### `hook::error_boundary::fn`

- `fn` **`extract_message`** — `pub(crate) fn extract_message(payload: &Box<dyn Any + Send>) -> String {...}`
- `fn` **`use_error_boundary`** — `pub fn use_error_boundary() -> ErrorBoundary {...}`

### `hook::error_boundary::impl`

- `fn` **`new`** — `pub fn new() -> Self {...}`
- `fn` **`try_with`** — `pub fn try_with<F, R>(&self, closure: F) -> Result<R, String> where F: FnOnce() -> R + UnwindSafe, {...}`
- `fn` **`report_error`** — `pub fn report_error(&self, message: &str) -> String {...}`
- `fn` **`reset`** — `pub fn reset(&self) {...}`

### `hook::error_boundary::struct`

- `struct` **`ErrorBoundary`** — `pub struct ErrorBoundary {`

### `hook::form::impl`

- `fn` **`field`** — `pub fn field(&self, name: &'static str) -> String {...}`
- `fn` **`error`** — `pub fn error(&self, name: &'static str) -> String {...}`
- `fn` **`is_touched`** — `pub fn is_touched(&self, name: &'static str) -> bool {...}`
- `fn` **`set_field`** — `pub fn set_field(&self, name: &'static str, value: &str) {...}`
- `fn` **`touch`** — `pub fn touch(&self, name: &'static str) {...}`
- `fn` **`validate`** — `pub fn validate(&self, validators: &HashMap<&'static str, Validator>) -> bool {...}`
- `fn` **`submit`** — `pub fn submit<F>(&self, validators: &HashMap<&'static str, Validator>, on_submit: F) -> bool where F: FnOnce(&HashMap<&'static str, String>), {...}`
- `fn` **`reset`** — `pub fn reset(&self) {...}`
- `fn` **`error_count`** — `pub fn error_count(&self) -> usize {...}`

### `hook::form::struct`

- `struct` **`FormState`** — `pub struct FormState {`

### `hook::form::trait`

- `trait` **`HookContextFormExt`** — `pub trait HookContextFormExt {`

### `hook::form::type`

- `type` **`Validator`** — `pub type Validator = Box<dyn Fn(&str) -> Option<String>>;`

### `hook::i18n::fn`

- `fn` **`interpolate`** — `pub(crate) fn interpolate(template: &str, vars: &HashMap<&'static str, &'static str>) -> String {...}`
- `fn` **`use_i18n`** — `pub fn use_i18n(init_locale: &str) -> I18n {...}`
- `fn` **`i18n_register`** — `pub fn i18n_register(handle: I18n, locale: &str, entries: &[(&'static str, &'static str)]) {...}`
- `fn` **`i18n_reset_for_tests`** — `pub fn i18n_reset_for_tests() {...}`
- `fn` **`messages_lock`** — `pub(crate) fn messages_lock() -> &'static RwLock<HashMap<String, HashMap<String, String>>> {...}`

### `hook::i18n::impl`

- `fn` **`change_locale`** — `pub fn change_locale(&self, locale: &str) {...}`
- `fn` **`change_fallback_locale`** — `pub fn change_fallback_locale(&self, locale: &str) {...}`
- `fn` **`add_messages`** — `pub fn add_messages(&self, locale: &str, entries: &[MessageEntry]) {...}`
- `fn` **`remove_locale`** — `pub fn remove_locale(&self, locale: &str) {...}`
- `fn` **`remove_message`** — `pub fn remove_message(&self, locale: &str, key: &str) {...}`
- `fn` **`t`** — `pub fn t(&self, key: &str) -> String {...}`
- `fn` **`t_with`** — `pub fn t_with(&self, key: &str, vars: &HashMap<&'static str, &'static str>) -> String {...}`
- `fn` **`locale_count`** — `pub fn locale_count(&self) -> usize {...}`
- `fn` **`active_message_count`** — `pub fn active_message_count(&self) -> usize {...}`

### `hook::i18n::struct`

- `static` **`I18N_MESSAGES`** — `pub(crate) static I18N_MESSAGES: OnceLock<RwLock<HashMap<String, HashMap<String, String>>>> = OnceLock::new();`
- `struct` **`I18n`** — `pub struct I18n {`

### `hook::i18n::trait`

- `trait` **`HookContextI18nExt`** — `pub trait HookContextI18nExt {`

### `hook::i18n::type`

- `type` **`MessageEntry`** — `pub type MessageEntry = (&'static str, &'static str);`

### `hook::lazy::enum`

- `enum` **`LoadState`** — `pub enum LoadState<T> {`

### `hook::lazy::fn`

- `fn` **`use_lazy_component`** — `pub fn use_lazy_component<T, F>(factory: F) -> LazyComponent<T> where T: Clone + PartialEq + Debug + 'static, F: Fn() -> T + 'static, {...}`

### `hook::lazy::impl`

- `fn` **`new`** — `pub fn new<F>(factory: F) -> Self where F: Fn() -> T + 'static, {...}`
- `fn` **`prefetch`** — `pub fn prefetch(&self) {...}`
- `fn` **`get`** — `pub fn get(&self) -> Option<T> {...}`
- `fn` **`loaded`** — `pub fn loaded(&self) -> Option<T> {...}`
- `fn` **`reset`** — `pub fn reset(&self) {...}`
- `fn` **`change_factory`** — `pub fn change_factory<F>(&self, factory: F) where F: Fn() -> T + 'static, {...}`

### `hook::lazy::struct`

- `struct` **`LazyComponent`** — `pub struct LazyComponent<T: Clone + PartialEq + 'static> {`

### `hook::previous::fn`

- `fn` **`use_previous`** — `pub fn use_previous<T>() -> Previous<T> where T: Clone + PartialEq + Debug + 'static, {...}`
- `fn` **`previous_step`** — `pub fn previous_step<T>(previous: Previous<T>, current: T) -> Option<T> where T: Clone + PartialEq + Debug + 'static, {...}`

### `hook::previous::impl`

- `fn` **`new`** — `pub fn new() -> Self {...}`
- `fn` **`record`** — `pub fn record(&self, current: T) {...}`
- `fn` **`get_previous_snapshot`** — `pub fn get_previous_snapshot(&self) -> Option<T> {...}`
- `fn` **`clear`** — `pub fn clear(&self) {...}`

### `hook::previous::struct`

- `struct` **`Previous`** — `pub struct Previous<T: Clone + PartialEq + 'static> {`

### `hook::profiler::fn`

- `fn` **`now_ms`** — `pub fn now_ms() -> f64 {...}`
- `fn` **`use_profiler`** — `pub fn use_profiler() -> ProfilerHandle {...}`
- `fn` **`profiler_measure`** — `pub fn profiler_measure<F, R>(label: &str, body: F) -> R where F: FnOnce() -> R, {...}`

### `hook::profiler::impl`

- `fn` **`new_with_empty_entries`** — `pub fn new_with_empty_entries() -> Self {...}`
- `fn` **`measure`** — `pub fn measure<F, R>(&self, label: &str, f: F) -> R where F: FnOnce() -> R, {...}`
- `fn` **`begin`** — `pub fn begin(&self, label: &str) -> ProfilerMark {...}`
- `fn` **`clear`** — `pub fn clear(&self) {...}`
- `fn` **`end`** — `pub fn end(self) {...}`

### `hook::profiler::struct`

- `struct` **`ProfileEntry`** — `pub struct ProfileEntry {`
- `struct` **`ProfilerHandle`** — `pub struct ProfilerHandle {`
- `struct` **`ProfilerMark`** — `pub struct ProfilerMark {`

### `hook::suspense::enum`

- `enum` **`SuspensePhase`** — `pub enum SuspensePhase<T> {`

### `hook::suspense::fn`

- `fn` **`use_suspense`** — `pub fn use_suspense<T>() -> SuspenseHandle<T> where T: Clone + PartialEq + Debug + 'static, {...}`

### `hook::suspense::impl`

- `fn` **`new`** — `pub fn new() -> Self {...}`
- `fn` **`resolve_sync`** — `pub fn resolve_sync(&self, value: T) {...}`
- `fn` **`fail`** — `pub fn fail(&self, message: String) {...}`
- `fn` **`reset`** — `pub fn reset(&self) {...}`

### `hook::suspense::struct`

- `struct` **`SuspenseHandle`** — `pub struct SuspenseHandle<T: Clone + PartialEq + 'static> {`

### `hook::throttled_value::enum`

- `enum` **`ThrottleState`** — `pub(crate) enum ThrottleState {`

### `hook::throttled_value::fn`

- `fn` **`use_throttled_value`** — `pub fn use_throttled_value<T>(interval_ms: u32) -> ThrottledValue<T> where T: Clone + PartialEq + Debug + Default + 'static, {...}`

### `hook::throttled_value::impl`

- `fn` **`set`** — `pub fn set(&self, next: T, now_ms: u64) {...}`
- `fn` **`tick`** — `pub fn tick(&self, now_ms: u64) -> bool {...}`
- `fn` **`cancel`** — `pub fn cancel(&self) {...}`
- `fn` **`get`** — `pub fn get(&self) -> T {...}`
- `fn` **`is_throttling`** — `pub fn is_throttling(&self) -> bool {...}`

### `hook::throttled_value::struct`

- `struct` **`ThrottledValue`** — `pub struct ThrottledValue<T: Clone + PartialEq + Default + 'static> {`

### `hook::toggle::impl`

- `fn` **`set_true`** — `pub fn set_true(&self) {...}`
- `fn` **`set_false`** — `pub fn set_false(&self) {...}`
- `fn` **`toggle`** — `pub fn toggle(&self) {...}`
- `fn` **`set`** — `pub fn set(&self, next: bool) {...}`
- `fn` **`get`** — `pub fn get(&self) -> bool {...}`

### `hook::toggle::struct`

- `struct` **`Toggle`** — `pub struct Toggle {`

### `hook::transition::enum`

- `enum` **`TransitionPhase`** — `pub enum TransitionPhase {`

### `hook::transition::impl`

- `fn` **`exited`** — `pub const fn exited() -> Self {...}`
- `fn` **`with_ms`** — `pub const fn with_ms(ms: u32) -> Self {...}`
- `fn` **`with_durations`** — `pub const fn with_durations(enter_ms: u32, exit_ms: u32) -> Self {...}`
- `fn` **`duration_for`** — `pub fn duration_for(&self, phase: TransitionPhase) -> u32 {...}`
- `fn` **`is_animating`** — `pub fn is_animating(&self) -> bool {...}`
- `fn` **`change_config`** — `pub fn change_config(&self, config: TransitionConfig) {...}`
- `fn` **`enter`** — `pub fn enter(&self) {...}`
- `fn` **`exit`** — `pub fn exit(&self) {...}`
- `fn` **`toggle`** — `pub fn toggle(&self) {...}`
- `fn` **`tick`** — `pub fn tick(&self, elapsed_ms: u32) {...}`
- `fn` **`tick_until_done`** — `pub fn tick_until_done(&self, step_ms: u32) {...}`
- `fn` **`reset`** — `pub fn reset(&self) {...}`
- `fn` **`remaining_ms`** — `pub fn remaining_ms(&self) -> u32 {...}`

### `hook::transition::struct`

- `struct` **`TransitionConfig`** — `pub struct TransitionConfig {`
- `struct` **`TransitionState`** — `pub struct TransitionState {`

### `hook::transition::trait`

- `trait` **`HookContextTransitionExt`** — `pub trait HookContextTransitionExt {`

### `hook::use_async::enum`

- `enum` **`AsyncState`** — `pub enum AsyncState<T, L = ()> {`

### `hook::use_async::fn`

- `fn` **`use_async`** — `pub fn use_async<T, L>() -> UseAsyncHandle<T, L> where T: Clone + PartialEq + 'static, L: Clone + PartialEq + HasLoadingHint + 'static, {...}`

### `hook::use_async::impl`

- `fn` **`new_for_fallback`** — `pub(crate) fn new_for_fallback() -> Self {...}`
- `fn` **`state`** — `pub fn state(&self) -> AsyncState<T, L> {...}`
- `fn` **`set_state`** — `pub fn set_state(&self, next: AsyncState<T, L>) {...}`
- `fn` **`refetch`** — `pub fn refetch<F, Fut, E>(&self, factory: F) where F: FnOnce() -> Fut + 'static, Fut: Future<Output = Result<T, E>> + 'static, E: Into<String> + 'static, {...}`

### `hook::use_async::struct`

- `struct` **`UseAsyncHandle`** — `pub struct UseAsyncHandle<T, L> where T: Clone + PartialEq + 'static, L: Clone + PartialEq + HasLoadingHint + 'static, {`
- `struct` **`UseAsyncSlot`** — `pub(crate) struct UseAsyncSlot<T, L> where T: Clone + PartialEq + 'static, L: Clone + PartialEq + HasLoadingHint + 'static, {`

### `hook::use_async::trait`

- `trait` **`HasLoadingHint`** — `pub trait HasLoadingHint: Clone + 'static {`

### `hook::use_async::type`

- `type` **`DefaultLoadingHandle`** — `pub type DefaultLoadingHandle<T> = UseAsyncHandle<T, ()>;`

### `style::css::fn`

- `fn` **`inject_app_global_css`** — `pub fn inject_app_global_css() {...}`

### `component::alert::view::enum`

- `enum` **`AlertVariant`** — `pub enum AlertVariant {`

### `component::alert::view::fn`

- `fn` **`euv_alert`** — `pub fn euv_alert(node: VirtualNode<EuvAlertProps>) -> VirtualNode {...}`

### `component::alert::view::struct`

- `struct` **`EuvAlertProps`** — `pub struct EuvAlertProps {`

### `component::badge::view::fn`

- `fn` **`euv_badge`** — `pub fn euv_badge(node: VirtualNode<EuvBadgeProps>) -> VirtualNode {...}`

### `component::badge::view::struct`

- `struct` **`EuvBadgeProps`** — `pub struct EuvBadgeProps {`

### `component::browser::hook::impl`

- `fn` **`use_browser_state`** — `pub fn use_browser_state() -> UseEuvBrowser {...}`
- `fn` **`local_storage_get`** — `pub fn local_storage_get<K>(key: K) -> Option<String> where K: AsRef<str>, {...}`
- `fn` **`local_storage_set`** — `pub fn local_storage_set<K, V>(key: K, value: V) where K: AsRef<str>, V: AsRef<str>, {...}`
- `fn` **`local_storage_remove`** — `pub(crate) fn local_storage_remove<K>(key: K) where K: AsRef<str>, {...}`
- `fn` **`session_storage_get`** — `pub(crate) fn session_storage_get<K>(key: K) -> Option<String> where K: AsRef<str>, {...}`
- `fn` **`session_storage_set`** — `pub(crate) fn session_storage_set<K, V>(key: K, value: V) where K: AsRef<str>, V: AsRef<str>, {...}`
- `fn` **`session_storage_remove`** — `pub(crate) fn session_storage_remove<K>(key: K) where K: AsRef<str>, {...}`
- `fn` **`clipboard_read_text`** — `pub(crate) async fn clipboard_read_text() -> String {...}`
- `fn` **`clipboard_write_text`** — `pub(crate) async fn clipboard_write_text<T>(text: T) -> bool where T: AsRef<str>, {...}`
- `fn` **`window_inner_size`** — `pub(crate) fn window_inner_size() -> (i32, i32) {...}`
- `fn` **`navigator_user_agent`** — `pub(crate) fn navigator_user_agent() -> String {...}`
- `fn` **`navigator_language`** — `pub(crate) fn navigator_language() -> String {...}`
- `fn` **`location_href`** — `pub(crate) fn location_href() -> String {...}`
- `fn` **`location_origin`** — `pub(crate) fn location_origin() -> String {...}`
- `fn` **`location_pathname`** — `pub(crate) fn location_pathname() -> String {...}`
- `fn` **`on_local_storage_set`** — `pub fn on_local_storage_set(self) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`on_local_storage_get`** — `pub fn on_local_storage_get(self) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`on_local_storage_remove`** — `pub fn on_local_storage_remove(self) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`on_session_storage_set`** — `pub fn on_session_storage_set(self) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`on_session_storage_get`** — `pub fn on_session_storage_get(self) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`on_session_storage_remove`** — `pub fn on_session_storage_remove(self) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`on_clipboard_copy`** — `pub fn on_clipboard_copy(self) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`on_clipboard_paste`** — `pub fn on_clipboard_paste(self) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`on_window_refresh_size`** — `pub fn on_window_refresh_size(self) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`on_console_log`** — `pub fn on_console_log(console_input: Signal<String>) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`on_console_warn`** — `pub fn on_console_warn(console_input: Signal<String>) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`on_console_error`** — `pub fn on_console_error(console_input: Signal<String>) -> Option<Rc<dyn Fn(Event)>> {...}`

### `component::browser::hook::struct`

- `struct` **`UseEuvBrowser`** — `pub struct UseEuvBrowser {`

### `component::button::view::enum`

- `enum` **`EuvButtonVariant`** — `pub enum EuvButtonVariant {`

### `component::button::view::fn`

- `fn` **`euv_button`** — `pub fn euv_button(node: VirtualNode<EuvButtonProps>) -> VirtualNode {...}`

### `component::button::view::struct`

- `struct` **`EuvButtonProps`** — `pub struct EuvButtonProps {`

### `component::camera::hook::enum`

- `enum` **`EuvCameraFacing`** — `pub enum EuvCameraFacing {`

### `component::camera::hook::impl`

- `fn` **`use_camera_state`** — `pub fn use_camera_state() -> UseEuvCamera {...}`
- `fn` **`open`** — `pub(crate) fn open(video_selector: &str, facing: EuvCameraFacing) -> Result<(), String> {...}`
- `fn` **`close`** — `pub(crate) fn close(video_selector: &str) {...}`
- `fn` **`open_and_scan`** — `pub(crate) fn open_and_scan(self, config: Option<&EuvCameraConfig>) {...}`
- `fn` **`switch`** — `pub(crate) fn switch(self, config: Option<&EuvCameraConfig>) {...}`
- `fn` **`start_qr_scan`** — `pub(crate) fn start_qr_scan(self, config: Option<&EuvCameraConfig>) {...}`
- `fn` **`stop_qr_scan`** — `pub(crate) fn stop_qr_scan(self) {...}`
- `fn` **`is_valid_qr_url`** — `pub(crate) fn is_valid_qr_url(text: &str) -> bool {...}`
- `fn` **`extract_hostname`** — `pub(crate) fn extract_hostname(url: &str) -> String {...}`
- `fn` **`is_private_host`** — `pub(crate) fn is_private_host(hostname: &str) -> bool {...}`
- `fn` **`navigate_qr_url`** — `pub(crate) fn navigate_qr_url(url: &str) {...}`
- `fn` **`on_close`** — `pub fn on_close(self, config: Option<&EuvCameraConfig>) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`on_switch`** — `pub fn on_switch(self, config: Option<&EuvCameraConfig>) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`on_open`** — `pub fn on_open(self, config: Option<&EuvCameraConfig>) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`cleanup`** — `pub fn cleanup(self, config: Option<&EuvCameraConfig>) {...}`

### `component::camera::hook::struct`

- `struct` **`UseEuvCamera`** — `pub struct UseEuvCamera {`
- `struct` **`EuvCameraConfig`** — `pub struct EuvCameraConfig {`

### `component::camera::hook::type`

- `type` **`QrDetectedCallback`** — `pub type QrDetectedCallback = Rc<dyn Fn(&str)>;`
- `type` **`CameraErrorCallback`** — `pub type CameraErrorCallback = Rc<dyn Fn(String)>;`

### `component::card::view::fn`

- `fn` **`euv_card`** — `pub fn euv_card(node: VirtualNode<EuvCardProps>) -> VirtualNode {...}`

### `component::card::view::struct`

- `struct` **`EuvCardProps`** — `pub struct EuvCardProps {`

### `component::checkbox::view::fn`

- `fn` **`euv_checkbox`** — `pub fn euv_checkbox(node: VirtualNode<EuvCheckboxProps>) -> VirtualNode {...}`

### `component::checkbox::view::struct`

- `struct` **`EuvCheckboxProps`** — `pub struct EuvCheckboxProps {`

### `component::debug::view::fn`

- `fn` **`euv_debug`** — `pub fn euv_debug(node: VirtualNode<EuvDebugProps>) -> VirtualNode {...}`

### `component::debug::view::struct`

- `struct` **`EuvDebugProps`** — `pub struct EuvDebugProps {`

### `component::debug::view::type`

- `type` **`DebugValueFormatter`** — `pub type DebugValueFormatter = Rc<dyn Fn() -> String>;`

### `component::doc_layout::view::fn`

- `fn` **`euv_doc_layout`** — `pub fn euv_doc_layout(node: VirtualNode<EuvDocLayoutProps>) -> VirtualNode {...}`

### `component::doc_layout::view::struct`

- `struct` **`EuvDocLayoutProps`** — `pub struct EuvDocLayoutProps {`

### `component::drawer::view::fn`

- `fn` **`euv_drawer`** — `pub fn euv_drawer(node: VirtualNode<EuvDrawerProps>) -> VirtualNode {...}`

### `component::drawer::view::struct`

- `struct` **`EuvDrawerProps`** — `pub struct EuvDrawerProps {`

### `component::dropdown::view::fn`

- `fn` **`euv_dropdown`** — `pub fn euv_dropdown(node: VirtualNode<EuvDropdownProps>) -> VirtualNode {...}`

### `component::dropdown::view::struct`

- `struct` **`EuvDropdownItem`** — `pub struct EuvDropdownItem {`
- `struct` **`EuvDropdownProps`** — `pub struct EuvDropdownProps {`

### `component::field::view::fn`

- `fn` **`euv_field`** — `pub fn euv_field(node: VirtualNode<EuvFieldProps>) -> VirtualNode {...}`

### `component::field::view::struct`

- `struct` **`EuvFieldProps`** — `pub struct EuvFieldProps {`

### `component::header::view::fn`

- `fn` **`euv_header`** — `pub fn euv_header(node: VirtualNode<EuvHeaderProps>) -> VirtualNode {...}`

### `component::header::view::struct`

- `struct` **`EuvHeaderProps`** — `pub struct EuvHeaderProps {`

### `component::hero::view::fn`

- `fn` **`euv_hero`** — `pub fn euv_hero(node: VirtualNode<EuvHeroProps>) -> VirtualNode {...}`
- `fn` **`euv_hero_action`** — `pub fn euv_hero_action(node: VirtualNode<EuvHeroActionProps>) -> VirtualNode {...}`
- `fn` **`euv_feature_grid`** — `pub fn euv_feature_grid(node: VirtualNode<EuvFeatureGridProps>) -> VirtualNode {...}`

### `component::hero::view::struct`

- `struct` **`EuvHeroAction`** — `pub struct EuvHeroAction {`
- `struct` **`EuvHeroProps`** — `pub struct EuvHeroProps {`
- `struct` **`EuvFeature`** — `pub struct EuvFeature {`
- `struct` **`EuvHeroActionProps`** — `pub struct EuvHeroActionProps {`
- `struct` **`EuvFeatureGridProps`** — `pub struct EuvFeatureGridProps {`

### `component::info::view::fn`

- `fn` **`euv_info`** — `pub fn euv_info(node: VirtualNode<EuvInfoProps>) -> VirtualNode {...}`

### `component::info::view::struct`

- `struct` **`EuvInfoProps`** — `pub struct EuvInfoProps {`

### `component::input::hook::impl`

- `fn` **`use_toggle`** — `pub fn use_toggle(signal: Signal<bool>) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`on_input_value`** — `pub fn on_input_value(signal: Signal<String>) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`on_change_value`** — `pub fn on_change_value(signal: Signal<String>) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`on_change_checked`** — `pub fn on_change_checked(signal: Signal<bool>) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`on_focus_scroll_into_view`** — `pub fn on_focus_scroll_into_view() -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`on_blur_restore_height`** — `pub fn on_blur_restore_height() -> Option<Rc<dyn Fn(Event)>> {...}`

### `component::input::hook::struct`

- `struct` **`UseEuvInput`** — `pub struct UseEuvInput;`

### `component::input::view::fn`

- `fn` **`euv_input`** — `pub fn euv_input(node: VirtualNode<EuvInputProps>) -> VirtualNode {...}`

### `component::input::view::struct`

- `struct` **`EuvInputProps`** — `pub struct EuvInputProps {`

### `component::layout::hook::impl`

- `fn` **`use_resize`** — `pub fn use_resize() -> Signal<bool> {...}`
- `fn` **`use_drawer_toggle`** — `pub fn use_drawer_toggle(drawer_open: Signal<bool>) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`use_safe_area_fix`** — `pub fn use_safe_area_fix() {...}`
- `fn` **`apply_cached_insets`** — `pub fn apply_cached_insets() {...}`

### `component::layout::hook::static`

- `static` **`SAFE_AREA_INSET_TOP`** — `pub(crate) static SAFE_AREA_INSET_TOP: RefCell<String> = const { RefCell::new(String::new()) };`
- `static` **`SAFE_AREA_INSET_RIGHT`** — `pub(crate) static SAFE_AREA_INSET_RIGHT: RefCell<String> = const { RefCell::new(String::new()) };`
- `static` **`SAFE_AREA_INSET_BOTTOM`** — `pub(crate) static SAFE_AREA_INSET_BOTTOM: RefCell<String> = const { RefCell::new(String::new()) };`
- `static` **`SAFE_AREA_INSET_LEFT`** — `pub(crate) static SAFE_AREA_INSET_LEFT: RefCell<String> = const { RefCell::new(String::new()) };`
- `static` **`NATIVE_FULLSCREEN_ACTIVE`** — `pub(crate) static NATIVE_FULLSCREEN_ACTIVE: Cell<bool> = const { Cell::new(false) };`
- `static` **`NATIVE_FULLSCREEN_EXIT_BY_POPSTATE`** — `pub(crate) static NATIVE_FULLSCREEN_EXIT_BY_POPSTATE: Cell<bool> = const { Cell::new(false) };`

### `component::layout::hook::struct`

- `struct` **`UseEuvLayout`** — `pub struct UseEuvLayout;`

### `component::loading::view::fn`

- `fn` **`euv_loading`** — `pub fn euv_loading(node: VirtualNode<EuvLoadingProps>) -> VirtualNode {...}`

### `component::loading::view::struct`

- `struct` **`EuvLoadingProps`** — `pub struct EuvLoadingProps {`

### `component::logo::view::enum`

- `enum` **`LogoButtonVariant`** — `pub enum LogoButtonVariant {`

### `component::logo::view::fn`

- `fn` **`euv_logo`** — `pub fn euv_logo(node: VirtualNode<EuvLogoProps>) -> VirtualNode {...}`

### `component::logo::view::struct`

- `struct` **`EuvLogoProps`** — `pub struct EuvLogoProps {`

### `component::markdown::view::enum`

- `enum` **`EuvMdBlock`** — `pub enum EuvMdBlock {`
- `enum` **`EuvMdInline`** — `pub enum EuvMdInline {`

### `component::markdown::view::fn`

- `fn` **`euv_markdown`** — `pub fn euv_markdown(node: VirtualNode<EuvMarkdownProps>) -> VirtualNode {...}`
- `fn` **`euv_markdown_blocks`** — `pub fn euv_markdown_blocks(blocks: &'static [EuvMdBlock]) -> VirtualNode {...}`

### `component::markdown::view::struct`

- `struct` **`EuvMarkdownProps`** — `pub struct EuvMarkdownProps {`

### `component::modal::view::fn`

- `fn` **`euv_modal`** — `pub fn euv_modal(node: VirtualNode<EuvModalProps>) -> VirtualNode {...}`

### `component::modal::view::struct`

- `struct` **`EuvModalProps`** — `pub struct EuvModalProps {`

### `component::nav::view::fn`

- `fn` **`euv_nav_item`** — `pub fn euv_nav_item(node: VirtualNode<EuvNavItemProps>) -> VirtualNode {...}`
- `fn` **`euv_mobile_nav_item`** — `pub fn euv_mobile_nav_item(node: VirtualNode<EuvMobileNavItemProps>) -> VirtualNode {...}`
- `fn` **`euv_nav_items`** — `pub fn euv_nav_items(node: VirtualNode<EuvNavItemsProps>) -> VirtualNode {...}`

### `component::nav::view::struct`

- `struct` **`EuvNavItemProps`** — `pub struct EuvNavItemProps {`
- `struct` **`EuvMobileNavItemProps`** — `pub struct EuvMobileNavItemProps {`
- `struct` **`EuvNavItemConfig`** — `pub struct EuvNavItemConfig {`
- `struct` **`EuvNavItemsProps`** — `pub struct EuvNavItemsProps {`

### `component::nav::view::type`

- `type` **`NavItemClickCallback`** — `pub type NavItemClickCallback = Rc<dyn Fn(&str)>;`
- `type` **`NavEventCallback`** — `pub type NavEventCallback = Rc<dyn Fn()>;`
- `type` **`ClickEventHandler`** — `pub type ClickEventHandler = Rc<dyn Fn(Event)>;`

### `component::navbar::view::fn`

- `fn` **`euv_navbar`** — `pub fn euv_navbar(node: VirtualNode<EuvNavbarProps>) -> VirtualNode {...}`
- `fn` **`euv_navbar_link`** — `pub fn euv_navbar_link(node: VirtualNode<EuvNavbarLinkProps>) -> VirtualNode {...}`

### `component::navbar::view::struct`

- `struct` **`EuvNavbarItem`** — `pub struct EuvNavbarItem {`
- `struct` **`EuvNavbarProps`** — `pub struct EuvNavbarProps {`
- `struct` **`EuvNavbarLinkProps`** — `pub struct EuvNavbarLinkProps {`

### `component::pagination::view::fn`

- `fn` **`euv_pagination`** — `pub fn euv_pagination(node: VirtualNode<EuvPaginationProps>) -> VirtualNode {...}`

### `component::pagination::view::struct`

- `struct` **`EuvPaginationItem`** — `pub struct EuvPaginationItem {`
- `struct` **`EuvPaginationProps`** — `pub struct EuvPaginationProps {`

### `component::result::view::fn`

- `fn` **`euv_result`** — `pub fn euv_result(node: VirtualNode<EuvResultProps>) -> VirtualNode {...}`

### `component::result::view::struct`

- `struct` **`EuvResultProps`** — `pub struct EuvResultProps {`

### `component::router::hook::impl`

- `fn` **`use_scroll_to_top`** — `pub fn use_scroll_to_top(route_signal: Signal<String>) {...}`
- `fn` **`use_hash_change`** — `pub fn use_hash_change(route_signal: Signal<String>) {...}`
- `fn` **`use_overlay_history`** — `pub fn use_overlay_history(drawer_open: Signal<bool>, mobile_signal: Signal<bool>) {...}`
- `fn` **`use_scroll_drawer_to_active`** — `pub fn use_scroll_drawer_to_active(drawer_open: Signal<bool>) {...}`
- `fn` **`register_popstate_guard`** — `pub fn register_popstate_guard(guard: Rc<dyn Fn() -> bool>) -> usize {...}`
- `fn` **`overlay_push_state`** — `pub fn overlay_push_state() {...}`
- `fn` **`overlay_back`** — `pub fn overlay_back(navigate_target: Option<String>) {...}`
- `fn` **`overlay_stack_push`** — `pub(crate) fn overlay_stack_push(closer: Rc<dyn Fn()>) {...}`
- `fn` **`overlay_stack_pop`** — `pub(crate) fn overlay_stack_pop() -> Option<Rc<dyn Fn()>> {...}`
- `fn` **`overlay_stack_close`** — `pub fn overlay_stack_close() {...}`
- `fn` **`modal_push`** — `pub fn modal_push(visible: Signal<bool>, closer: Rc<dyn Fn()>) {...}`
- `fn` **`modal_close_via_ui`** — `pub fn modal_close_via_ui(visible: Signal<bool>) {...}`
- `fn` **`open_system_browser`** — `pub fn open_system_browser<U>(url: U) where U: AsRef<str>, {...}`
- `fn` **`external_link_handler`** — `pub fn external_link_handler<U>(url: U) -> NativeEventHandler where U: AsRef<str>, {...}`
- `fn` **`close_drawer_and_navigate`** — `pub fn close_drawer_and_navigate<T>(_drawer_open: Signal<bool>, target: T) where T: AsRef<str>, {...}`

### `component::router::hook::static`

- `static` **`BACK_PENDING`** — `pub(crate) static BACK_PENDING: Cell<bool> = const { Cell::new(false) };`
- `static` **`NAVIGATE_AFTER_BACK`** — `pub(crate) static NAVIGATE_AFTER_BACK: Cell<Option<String>> = const { Cell::new(None) };`
- `static` **`MODAL_STACK`** — `pub(crate) static MODAL_STACK: ModalStack = const { RefCell::new(Vec::new()) };`
- `static` **`OVERLAY_STACK`** — `pub(crate) static OVERLAY_STACK: OverlayStack = const { RefCell::new(Vec::new()) };`
- `static` **`WINDOW_EVENT_DEPTH`** — `pub(crate) static WINDOW_EVENT_DEPTH: Cell<usize> = const { Cell::new(0) };`
- `static` **`DEFERRED_NAVIGATION`** — `pub(crate) static DEFERRED_NAVIGATION: Cell<Option<String>> = const { Cell::new(None) };`
- `static` **`POPSTATE_GUARDS`** — `pub(crate) static POPSTATE_GUARDS: PopstateGuardList = const { RefCell::new(Vec::new()) };`
- `static` **`NEXT_POPSTATE_GUARD_ID`** — `pub(crate) static NEXT_POPSTATE_GUARD_ID: Cell<usize> = const { Cell::new(0) };`

### `component::router::hook::struct`

- `struct` **`Router`** — `pub struct Router;`
- `struct` **`OverlayEntry`** — `pub(crate) struct OverlayEntry {`

### `component::router::hook::type`

- `type` **`ModalStackEntry`** — `pub(crate) type ModalStackEntry = (Signal<bool>, Rc<dyn Fn()>);`
- `type` **`ModalStack`** — `pub(crate) type ModalStack = RefCell<Vec<ModalStackEntry>>;`
- `type` **`OverlayStack`** — `pub(crate) type OverlayStack = RefCell<Vec<OverlayEntry>>;`
- `type` **`PopstateGuard`** — `pub(crate) type PopstateGuard = Rc<dyn Fn() -> bool>;`
- `type` **`PopstateGuardEntry`** — `pub(crate) type PopstateGuardEntry = (usize, PopstateGuard);`
- `type` **`PopstateGuardList`** — `pub(crate) type PopstateGuardList = RefCell<Vec<PopstateGuardEntry>>;`

### `component::router::view::fn`

- `fn` **`euv_routes`** — `pub fn euv_routes(node: VirtualNode<EuvRoutesProps>) -> VirtualNode {...}`
- `fn` **`euv_page_router`** — `pub fn euv_page_router(node: VirtualNode<EuvPageRouterProps>) -> VirtualNode {...}`

### `component::router::view::impl`

- `fn` **`new`** — `pub fn new<F>(path: &'static str, component: F) -> Self where F: Fn() -> VirtualNode + 'static, {...}`
- `fn` **`current_route`** — `pub fn current_route() -> String {...}`
- `fn` **`navigate`** — `pub fn navigate<R>(route: R) where R: AsRef<str>, {...}`
- `fn` **`link_handler`** — `pub fn link_handler<R>(route: R) -> NativeEventHandler where R: AsRef<str>, {...}`
- `fn` **`is_mobile`** — `pub fn is_mobile() -> bool {...}`

### `component::router::view::struct`

- `struct` **`EuvPageRouterProps`** — `pub struct EuvPageRouterProps {`
- `struct` **`EuvRouteConfig`** — `pub struct EuvRouteConfig {`
- `struct` **`EuvRoutesProps`** — `pub struct EuvRoutesProps {`

### `component::sidebar::view::fn`

- `fn` **`euv_sidebar`** — `pub fn euv_sidebar(node: VirtualNode<EuvSidebarProps>) -> VirtualNode {...}`
- `fn` **`euv_sidebar_item`** — `pub fn euv_sidebar_item(node: VirtualNode<EuvSidebarItemProps>) -> VirtualNode {...}`

### `component::sidebar::view::struct`

- `struct` **`EuvSidebarItem`** — `pub struct EuvSidebarItem {`
- `struct` **`EuvSidebarProps`** — `pub struct EuvSidebarProps {`
- `struct` **`EuvSidebarItemProps`** — `pub struct EuvSidebarItemProps {`

### `component::tag::view::enum`

- `enum` **`EuvTagVariant`** — `pub enum EuvTagVariant {`
- `enum` **`EuvTagColor`** — `pub enum EuvTagColor {`

### `component::tag::view::fn`

- `fn` **`euv_tag`** — `pub fn euv_tag(node: VirtualNode<EuvTagProps>) -> VirtualNode {...}`

### `component::tag::view::struct`

- `struct` **`EuvTagProps`** — `pub struct EuvTagProps {`

### `component::theme::hook::impl`

- `fn` **`use_theme_state`** — `pub fn use_theme_state(mobile_signal: Signal<bool>) -> ThemeState {...}`
- `fn` **`use_system_theme_change`** — `pub fn use_system_theme_change(theme_signal: Signal<String>) {...}`
- `fn` **`detect_system_theme`** — `pub fn detect_system_theme() -> String {...}`
- `fn` **`theme_class_name`** — `pub(crate) fn theme_class_name(theme: &str) -> &'static str {...}`
- `fn` **`toggle`** — `pub fn toggle(theme_signal: Signal<String>) -> Option<Rc<dyn Fn(Event)>> {...}`

### `component::theme::hook::struct`

- `struct` **`ThemeState`** — `pub struct ThemeState {`

### `component::toc::view::fn`

- `fn` **`euv_toc`** — `pub fn euv_toc(node: VirtualNode<EuvTocProps>) -> VirtualNode {...}`

### `component::toc::view::struct`

- `struct` **`EuvTocItem`** — `pub struct EuvTocItem {`
- `struct` **`EuvTocProps`** — `pub struct EuvTocProps {`

### `component::touch::hook::impl`

- `fn` **`extract_all`** — `pub fn extract_all(event: &Event) -> Vec<NativeTouchPoint> {...}`
- `fn` **`extract_changed`** — `pub fn extract_changed(event: &Event) -> Vec<NativeTouchPoint> {...}`
- `fn` **`extract_all`** — `pub fn extract_all(event: &Event) -> Vec<NativeTouchPointF64> {...}`

### `component::touch::hook::struct`

- `struct` **`NativeTouchPoint`** — `pub struct NativeTouchPoint {`
- `struct` **`NativeTouchPointF64`** — `pub struct NativeTouchPointF64 {`

### `component::vconsole::hook::enum`

- `enum` **`LogLevel`** — `pub enum LogLevel {`
- `enum` **`LogFilter`** — `pub enum LogFilter {`

### `component::vconsole::hook::fn`

- `fn` **`console_log_ref`** — `pub(crate) fn console_log_ref() -> Option<Rc<RefCell<Vec<ConsoleEntry>>>> {...}`
- `fn` **`install_console_log_ref`** — `pub(crate) fn install_console_log_ref(logs_ref: Rc<RefCell<Vec<ConsoleEntry>>>) {...}`

### `component::vconsole::hook::impl`

- `fn` **`init`** — `pub fn init() {...}`
- `fn` **`log`** — `pub fn log<M>(message: M) where M: AsRef<str>, {...}`
- `fn` **`warn`** — `pub fn warn<M>(message: M) where M: AsRef<str>, {...}`
- `fn` **`error`** — `pub fn error<M>(message: M) where M: AsRef<str>, {...}`
- `fn` **`clear`** — `pub fn clear() {...}`
- `fn` **`get_signal`** — `pub(crate) fn get_signal() -> Option<Signal<Vec<ConsoleEntry>>> {...}`
- `fn` **`fab_on_click`** — `pub(crate) fn fab_on_click(panel_open: Signal<bool>) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`push`** — `pub fn push(entry: ConsoleEntry) {...}`
- `fn` **`badge`** — `pub(crate) fn badge(self) -> &'static str {...}`
- `fn` **`on_filter_all`** — `pub(crate) fn on_filter_all(filter_signal: Signal<LogFilter>) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`on_filter_log`** — `pub(crate) fn on_filter_log(filter_signal: Signal<LogFilter>) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`on_filter_warn`** — `pub(crate) fn on_filter_warn(filter_signal: Signal<LogFilter>) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`on_filter_error`** — `pub(crate) fn on_filter_error(filter_signal: Signal<LogFilter>) -> Option<Rc<dyn Fn(Event)>> {...}`

### `component::vconsole::hook::static`

- `static` **`CONSOLE_LOG_REF`** — `pub(crate) static CONSOLE_LOG_REF: RefCell<Option<Rc<RefCell<Vec<ConsoleEntry>>>>> = const { RefCell::new(None) };`
- `static` **`CONSOLE_LOG_SIGNAL`** — `pub(crate) static CONSOLE_LOG_SIGNAL: SignalCell<Vec<ConsoleEntry>> = SignalCell::none();`

### `component::vconsole::hook::struct`

- `struct` **`Console`** — `pub struct Console;`
- `struct` **`ConsoleEntry`** — `pub struct ConsoleEntry {`

### `component::vconsole::view::fn`

- `fn` **`euv_vconsole_panel`** — `pub fn euv_vconsole_panel(node: VirtualNode<EuvVconsolePanelProps>) -> VirtualNode {...}`
- `fn` **`euv_vconsole_fab`** — `pub fn euv_vconsole_fab(node: VirtualNode<EuvVconsoleFabProps>) -> VirtualNode {...}`
- `fn` **`euv_vconsole_drawer`** — `pub fn euv_vconsole_drawer(node: VirtualNode<EuvVconsoleDrawerProps>) -> VirtualNode {...}`

### `component::vconsole::view::struct`

- `struct` **`EuvVconsolePanelProps`** — `pub struct EuvVconsolePanelProps {`
- `struct` **`EuvVconsoleFabProps`** — `pub struct EuvVconsoleFabProps {`
- `struct` **`EuvVconsoleDrawerProps`** — `pub struct EuvVconsoleDrawerProps {`

### `component::virtual_list::hook::impl`

- `fn` **`use_scroll_state`** — `pub fn use_scroll_state() -> UseVirtualList {...}`
- `fn` **`on_scroll`** — `pub fn on_scroll(self) -> Option<Rc<dyn Fn(Event)>> {...}`
- `fn` **`update_viewport_height`** — `pub fn update_viewport_height(self) {...}`
- `fn` **`schedule_measure`** — `pub fn schedule_measure(self) {...}`
- `fn` **`schedule_measure_by_id`** — `pub(crate) fn schedule_measure_by_id(self, container_id: &str) {...}`
- `fn` **`try_get_container`** — `pub fn try_get_container() -> Option<Element> {...}`
- `fn` **`try_get_container_by_id`** — `pub fn try_get_container_by_id<C>(container_id: C) -> Option<Element> where C: AsRef<str>, {...}`
- `fn` **`compute_visible_range`** — `pub(crate) fn compute_visible_range( scroll_offset: i32, viewport_height: i32, total_count: usize, item_height: i32, overscan_count: usize, ) -> (usize,`

### `component::virtual_list::hook::static`

- `static` **`PENDING_MEASURE`** — `pub(crate) static PENDING_MEASURE: AtomicBool = AtomicBool::new(false);`
- `static` **`mut`** — `pub(crate) static mut PENDING_MEASURE_BY_ID: LazyLock<PendingMeasureCell> = LazyLock::new(|| PendingMeasureCell(UnsafeCell::new(HashSet::new())));`

### `component::virtual_list::hook::struct`

- `struct` **`UseVirtualList`** — `pub struct UseVirtualList {`
- `struct` **`PendingMeasureCell`** — `pub(crate) struct PendingMeasureCell( #[get(pub(crate))]`

### `component::virtual_list::view::fn`

- `fn` **`euv_virtual_list`** — `pub fn euv_virtual_list(node: VirtualNode<EuvVirtualListProps>) -> VirtualNode {...}`

### `component::virtual_list::view::struct`

- `struct` **`EuvVirtualListConfig`** — `pub struct EuvVirtualListConfig {`
- `struct` **`EuvVirtualListProps`** — `pub struct EuvVirtualListProps {`

### `component::virtual_list::view::type`

- `type` **`VirtualListItemRenderer`** — `pub type VirtualListItemRenderer = Rc<dyn Fn(usize) -> VirtualNode>;`
- `type` **`VirtualListScrollHandler`** — `pub type VirtualListScrollHandler = Rc<dyn Fn(i32)>;`
- `type` **`VirtualListRangeHandler`** — `pub type VirtualListRangeHandler = Rc<dyn Fn((usize, usize))>;`
- `type` **`VirtualListConfig`** — `pub type VirtualListConfig = EuvVirtualListConfig;`
- `type` **`VirtualListProps`** — `pub type VirtualListProps = EuvVirtualListProps;`
