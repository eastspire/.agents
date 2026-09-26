# hyperlane-core 完整 pub API

Source: `core/src/` — auto-extracted from `pub` declarations.

Re-exported at root via `hyperlane-core::*` (then `hyperlane::*` re-exports it).

### `config::impl`

- `fn` **`from_json`** — `pub fn from_json<C>(json: C) -> Result<Self, serde_json::Error> where C: AsRef<str>, {...}`

### `config::struct`

- `struct` **`ServerConfig`** — `pub struct ServerConfig {`

### `context::impl`

- `fn` **`try_get_route_param`** — `pub fn try_get_route_param<T>(&self, name: T) -> Option<String> where T: AsRef<str>, {...}`
- `fn` **`get_route_param`** — `pub fn get_route_param<T>(&self, name: T) -> String where T: AsRef<str>, {...}`
- `fn` **`try_get_attribute`** — `pub fn try_get_attribute<V>(&self, key: impl AsRef<str>) -> Option<V> where V: AnySendSyncClone, {...}`
- `fn` **`get_attribute`** — `pub fn get_attribute<V>(&self, key: impl AsRef<str>) -> V where V: AnySendSyncClone, {...}`
- `fn` **`set_attribute`** — `pub fn set_attribute<K, V>(&mut self, key: K, value: V) -> &mut Self where K: AsRef<str>, V: AnySendSyncClone, {...}`
- `fn` **`remove_attribute`** — `pub fn remove_attribute<K>(&mut self, key: K) -> &mut Self where K: AsRef<str>, {...}`
- `fn` **`clear_attribute`** — `pub fn clear_attribute(&mut self) -> &mut Self {...}`
- `fn` **`set_task_panic`** — `pub fn set_task_panic(&mut self, panic_data: PanicData) -> &mut Self {...}`
- `fn` **`try_get_task_panic_data`** — `pub fn try_get_task_panic_data(&self) -> Option<PanicData> {...}`
- `fn` **`get_task_panic_data`** — `pub fn get_task_panic_data(&self) -> PanicData {...}`
- `fn` **`set_request_error_data`** — `pub(crate) fn set_request_error_data(&mut self, request_error: RequestError) -> &mut Self {...}`
- `fn` **`try_get_request_error_data`** — `pub fn try_get_request_error_data(&self) -> Option<RequestError> {...}`
- `fn` **`get_request_error_data`** — `pub fn get_request_error_data(&self) -> RequestError {...}`

### `context::struct`

- `struct` **`Context`** — `pub struct Context {`

### `error::enum`

- `enum` **`ServerError`** — `pub enum ServerError {`
- `enum` **`RouteError`** — `pub enum RouteError {`

### `hook::enum`

- `enum` **`HookType`** — `pub enum HookType {`

### `hook::impl`

- `fn` **`wait`** — `pub async fn wait(&self) {...}`
- `fn` **`shutdown`** — `pub async fn shutdown(&self) {...}`
- `fn` **`default_control_handler`** — `pub fn default_control_handler() -> ServerControlHookHandler<()> {...}`
- `fn` **`default_handler`** — `pub fn default_handler() -> ServerHookHandler {...}`
- `fn` **`factory`** — `pub fn factory<R>() -> ServerHookHandler where R: ServerHook, {...}`
- `fn` **`try_get_order`** — `pub fn try_get_order(&self) -> Option<isize> {...}`
- `fn` **`try_get_hook`** — `pub fn try_get_hook(&self) -> Option<ServerHookHandlerFactory> {...}`
- `fn` **`assert_unique_order`** — `pub fn assert_unique_order(list: Vec<HookType>) {...}`

### `hook::struct`

- `struct` **`DefaultServerHook`** — `pub struct DefaultServerHook;`
- `struct` **`Hook`** — `pub struct Hook;`
- `struct` **`ServerControlHook`** — `pub struct ServerControlHook {`

### `hook::trait`

- `trait` **`FnContext`** — `pub trait FnContext<R>: Fn(&mut Context) -> R + Send + Sync {}`
- `trait` **`FnContextPinBox`** — `pub trait FnContextPinBox<T>: FnContext<FutureBox<T>> {}`
- `trait` **`FnContextStatic`** — `pub trait FnContextStatic<Fut, T>: FnContext<Fut> + 'static where Fut: Future<Output = T> + Send, {`
- `trait` **`FutureSendStatic`** — `pub trait FutureSendStatic<T>: Future<Output = T> + Send + 'static {}`
- `trait` **`FutureSend`** — `pub trait FutureSend<T>: Future<Output = T> + Send {}`
- `trait` **`FutureFn`** — `pub trait FutureFn<T>: Fn() -> FutureBox<T> + Send + Sync {}`
- `trait` **`ServerHook`** — `pub trait ServerHook: Send + Sync + 'static {`

### `hook::type`

- `type` **`HookHandler`** — `pub type HookHandler<T> = Arc<dyn FnContextPinBox<T>>;`
- `type` **`HookHandlerChain`** — `pub type HookHandlerChain<T> = Vec<HookHandler<T>>;`
- `type` **`FutureBox`** — `pub type FutureBox<T> = Pin<Box<dyn Future<Output = T> + Send>>;`
- `type` **`ServerControlHookHandler`** — `pub type ServerControlHookHandler<T> = Arc<dyn FutureFn<T>>;`
- `type` **`ServerHookHandlerFactory`** — `pub type ServerHookHandlerFactory = fn() -> ServerHookHandler;`
- `type` **`ServerHookHandler`** — `pub type ServerHookHandler = Arc<dyn Fn(&mut Stream, &mut Context) -> FutureBox<Status> + Send + Sync>;`
- `type` **`ServerHookList`** — `pub type ServerHookList = Vec<ServerHookHandler>;`
- `type` **`ServerHookMap`** — `pub type ServerHookMap = HashMapXxHash3_64<String, ServerHookHandler>;`
- `type` **`ServerHookPatternRoute`** — `pub type ServerHookPatternRoute = HashMapXxHash3_64<usize, Vec<(RoutePattern, ServerHookHandler)>>;`

### `route::enum`

- `enum` **`RouteSegment`** — `pub enum RouteSegment {`

### `route::impl`

- `fn` **`new`** — `pub(crate) fn new(route: &str) -> Result<RoutePattern, RouteError> {...}`
- `fn` **`try_match_path`** — `pub(crate) fn try_match_path(&self, path: &str) -> Option<RouteParams> {...}`
- `fn` **`is_static`** — `pub(crate) fn is_static(&self) -> bool {...}`
- `fn` **`is_dynamic`** — `pub(crate) fn is_dynamic(&self) -> bool {...}`
- `fn` **`segment_count`** — `pub(crate) fn segment_count(&self) -> usize {...}`
- `fn` **`has_tail_regex`** — `pub(crate) fn has_tail_regex(&self) -> bool {...}`
- `fn` **`new`** — `pub(crate) fn new() -> Self {...}`
- `fn` **`add`** — `pub(crate) fn add(&mut self, pattern: &str, hook: ServerHookHandler) -> Result<(), RouteError> {...}`
- `fn` **`try_resolve_route`** — `pub fn try_resolve_route<'a>( &'a self, ctx: &mut Context, path: &str, ) -> Option<&'a ServerHookHandler> {...}`

### `route::struct`

- `struct` **`RoutePattern`** — `pub struct RoutePattern( #[get]`
- `struct` **`RouteMatcher`** — `pub struct RouteMatcher {`

### `route::type`

- `type` **`RouteParams`** — `pub type RouteParams = HashMapXxHash3_64<String, String>;`
- `type` **`RouteSegmentList`** — `pub type RouteSegmentList = Vec<RouteSegment>;`
- `type` **`PathComponentList`** — `pub(crate) type PathComponentList<'a> = Vec<&'a str>;`

### `server::impl`

- `fn` **`handle_hook`** — `pub fn handle_hook(&mut self, hook: HookType) {...}`
- `fn` **`config_from_json`** — `pub fn config_from_json<C>(&mut self, json: C) -> &mut Self where C: AsRef<str>, {...}`
- `fn` **`server_config`** — `pub fn server_config(&mut self, config: ServerConfig) -> &mut Self {...}`
- `fn` **`request_config`** — `pub fn request_config(&mut self, config: RequestConfig) -> &mut Self {...}`
- `fn` **`task_panic`** — `pub fn task_panic<S>(&mut self) -> &mut Self where S: ServerHook, {...}`
- `fn` **`request_error`** — `pub fn request_error<S>(&mut self) -> &mut Self where S: ServerHook, {...}`
- `fn` **`route`** — `pub fn route<S>(&mut self, path: impl AsRef<str>) -> &mut Self where S: ServerHook, {...}`
- `fn` **`request_middleware`** — `pub fn request_middleware<S>(&mut self) -> &mut Self where S: ServerHook, {...}`
- `fn` **`response_middleware`** — `pub fn response_middleware<S>(&mut self) -> &mut Self where S: ServerHook, {...}`
- `fn` **`format_bind_address`** — `pub fn format_bind_address<H>(host: H, port: u16) -> String where H: AsRef<str>, {...}`
- `fn` **`try_flush_stdout`** — `pub fn try_flush_stdout() -> io::Result<()> {...}`
- `fn` **`flush_stdout`** — `pub fn flush_stdout() {...}`
- `fn` **`try_flush_stderr`** — `pub fn try_flush_stderr() -> io::Result<()> {...}`
- `fn` **`flush_stderr`** — `pub fn flush_stderr() {...}`
- `fn` **`try_flush_stdout_and_stderr`** — `pub fn try_flush_stdout_and_stderr() -> io::Result<()> {...}`
- `fn` **`flush_stdout_and_stderr`** — `pub fn flush_stdout_and_stderr() {...}`
- `fn` **`handle_request_middleware`** — `pub(super) async fn handle_request_middleware( &self, stream: &mut Stream, ctx: &mut Context, ) -> bool {...}`
- `fn` **`handle_route_matcher`** — `pub(super) async fn handle_route_matcher( &self, stream: &mut Stream, ctx: &mut Context, path: &str, ) -> bool {...}`
- `fn` **`handle_response_middleware`** — `pub(super) async fn handle_response_middleware( &self, stream: &mut Stream, ctx: &mut Context, ) -> bool {...}`
- `fn` **`handle_request_error`** — `pub async fn handle_request_error( &self, stream: &mut Stream, ctx: &mut Context, error: &RequestError, ) {...}`
- `fn` **`run`** — `pub async fn run(&self) -> Result<ServerControlHook, Box<ServerError>> {...}`

### `server::struct`

- `struct` **`Server`** — `pub struct Server {`
