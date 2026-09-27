# euv-cli 完整 pub API

Source: `cli/src/` — auto-extracted from `pub` declarations.

### `main`

- `fn` **`main`** — `pub async fn main() -> Result<(), EuvError> {...}`

### `build::enum`

- `enum` **`Action`** — `pub enum Action {`
- `enum` **`BuildMode`** — `pub enum BuildMode {`
- `enum` **`Mode`** — `pub enum Mode {`
- `enum` **`ReloadEvent`** — `pub enum ReloadEvent {`

### `build::fn`

- `fn` **`has_build_mode_flag`** — `pub fn has_build_mode_flag(wasm_pack_args: &[String]) -> bool {...}`
- `fn` **`filter_euv_args`** — `pub fn filter_euv_args(wasm_pack_args: &[String]) -> Vec<String> {...}`
- `fn` **`reconcile_args`** — `pub fn reconcile_args(args: &mut ModeArgs) {...}`
- `fn` **`resolve_build_mode`** — `pub fn resolve_build_mode(args: &ModeArgs) -> BuildMode {...}`
- `fn` **`build_mode_to_flag`** — `pub fn build_mode_to_flag(build_mode: BuildMode) -> &'static str {...}`
- `fn` **`resolve_out_name`** — `pub fn resolve_out_name(args: &ModeArgs) -> String {...}`
- `fn` **`resolve_serving_root`** — `pub async fn resolve_serving_root(args: &ModeArgs) -> PathBuf {...}`
- `fn` **`resolve_serving_route_prefix`** — `pub fn resolve_serving_route_prefix(args: &ModeArgs) -> String {...}`
- `fn` **`resolve_import_path`** — `pub fn resolve_import_path(args: &ModeArgs) -> String {...}`
- `fn` **`resolve_out_dir`** — `pub fn resolve_out_dir(args: &ModeArgs) -> PathBuf {...}`
- `fn` **`run_build_only_pipeline`** — `pub async fn run_build_only_pipeline(args: &ModeArgs) -> Result<(), EuvError> {...}`
- `fn` **`clean_out_dir`** — `pub async fn clean_out_dir(out_dir: &Path) {...}`
- `fn` **`run_build_pipeline`** — `pub async fn run_build_pipeline( args: &ModeArgs, reload_tx: Option<&broadcast::Sender<ReloadEvent>>, ) -> Result<String, EuvError> {...}`
- `fn` **`watch_and_build`** — `pub(crate) async fn watch_and_build(state: Arc<AppState>) -> Result<(), EuvError> {...}`
- `fn` **`build_wasm`** — `pub async fn build_wasm(args: &ModeArgs) -> Result<(), EuvError> {...}`
- `fn` **`print_banner`** — `pub fn print_banner(action: Action) {...}`
- `fn` **`print_server_urls`** — `pub(crate) fn print_server_urls(config: &ServerUrlConfig) {...}`
- `fn` **`run_hyperlane_fmt`** — `pub async fn run_hyperlane_fmt() -> Result<(), EuvError> {...}`

### `build::inline`

- `fn` **`build_inline_bridge`** — `pub(crate) async fn build_inline_bridge( pkg_dir: &Path, js_name: &str, wasm_url: &str, ) -> Result<String, EuvError> {...}`
- `fn` **`build_module_fallback_bridge`** — `pub(crate) fn build_module_fallback_bridge(import_path: &str) -> String {...}`
- `fn` **`inline_bridge_disabled`** — `pub(crate) fn inline_bridge_disabled() -> bool {...}`
- `fn` **`extract_exported_function_names`** — `pub fn extract_exported_function_names(source: &str) -> Vec<String> {...}`
- `fn` **`is_namespace_import`** — `pub fn is_namespace_import(rest: &str) -> bool {...}`
- `fn` **`extract_namespace_alias`** — `pub fn extract_namespace_alias(rest: &str) -> Option<&str> {...}`
- `fn` **`extract_import_spec`** — `pub fn extract_import_spec(rest: &str) -> Option<&str> {...}`

### `build::struct`

- `struct` **`Cli`** — `pub struct Cli {`
- `struct` **`ModeArgs`** — `pub struct ModeArgs {`
- `struct` **`FmtArgs`** — `pub struct FmtArgs {`
- `struct` **`ServerUrlConfig`** — `pub(crate) struct ServerUrlConfig {`

### `error::enum`

- `enum` **`EuvError`** — `pub enum EuvError {`

### `fmt::enum`

- `enum` **`FmtMode`** — `pub enum FmtMode {`

### `fmt::fn`

- `fn` **`format_source`** — `pub(crate) fn format_source(source: &str) -> FmtResult {...}`
- `fn` **`format_euv_macros`** — `pub fn format_euv_macros<S>(source: S) -> String where S: AsRef<str>, {...}`
- `fn` **`format_macro_body`** — `pub fn format_macro_body<B>(body: B) -> String where B: AsRef<str>, {...}`
- `fn` **`format_dir`** — `pub async fn format_dir(path: &Path, mode: FmtMode) -> Result<(), EuvError> {...}`

### `fmt::struct`

- `struct` **`FmtResult`** — `pub(crate) struct FmtResult {`

### `hmr::impl`

- `fn` **`new`** — `pub fn new() -> Self {...}`
- `fn` **`from_entries`** — `pub fn from_entries<I>(entries: I) -> Self where I: IntoIterator<Item = (String, String)>, {...}`
- `fn` **`set`** — `pub fn set<K, V>(&mut self, key: K, value: V) where K: Into<String>, V: Into<String>, {...}`
- `fn` **`get`** — `pub fn get(&self, key: &str) -> Option<&str> {...}`
- `fn` **`remove`** — `pub fn remove(&mut self, key: &str) -> Option<String> {...}`
- `fn` **`clear`** — `pub fn clear(&mut self) {...}`
- `fn` **`len`** — `pub fn len(&self) -> usize {...}`
- `fn` **`is_empty`** — `pub fn is_empty(&self) -> bool {...}`
- `fn` **`contains`** — `pub fn contains(&self, key: &str) -> bool {...}`
- `fn` **`iter`** — `pub fn iter(&self) -> impl Iterator<Item = (&str, &str)> {...}`

### `hmr::struct`

- `struct` **`HmrState`** — `pub struct HmrState {`

### `logger::impl`

- `fn` **`init`** — `pub fn init(level_filter: log::LevelFilter) {...}`

### `logger::static`

- `static` **`LOGGER`** — `pub static LOGGER: Logger = Logger;`

### `logger::struct`

- `struct` **`Logger`** — `pub struct Logger;`

### `mode::fn`

- `fn` **`build_mode`** — `pub async fn build_mode(mut args: ModeArgs) -> Result<(), EuvError> {...}`
- `fn` **`fmt_mode`** — `pub async fn fmt_mode(args: FmtArgs) -> Result<(), EuvError> {...}`
- `fn` **`run_mode`** — `pub async fn run_mode(mut args: ModeArgs) -> Result<(), EuvError> {...}`

### `server::fn`

- `fn` **`set_global_state`** — `pub(crate) fn set_global_state(state: Arc<AppState>) -> Result<(), EuvError> {...}`
- `fn` **`get_global_state`** — `pub(crate) fn get_global_state() -> Option<Arc<AppState>> {...}`
- `fn` **`generate_html`** — `pub(crate) async fn generate_html(config: &HtmlConfig) -> Result<String, EuvError> {...}`
- `fn` **`resolve_www_dir`** — `pub async fn resolve_www_dir(www_dir: &Path) -> PathBuf {...}`
- `fn` **`resolve_pkg_dir`** — `pub fn resolve_pkg_dir(args: &ModeArgs) -> PathBuf {...}`
- `fn` **`resolve_file_in_base`** — `pub async fn resolve_file_in_base(base: &Path, path: &str) -> Option<PathBuf> {...}`

### `server::static`

- `static` **`APP_STATE`** — `pub(crate) static APP_STATE: OnceLock<Arc<AppState>> = OnceLock::new();`

### `server::struct`

- `struct` **`AppState`** — `pub(crate) struct AppState {`
- `struct` **`HtmlConfig`** — `pub(crate) struct HtmlConfig {`
- `struct` **`RequestMiddleware`** — `pub(crate) struct RequestMiddleware;`
- `struct` **`ResponseMiddleware`** — `pub(crate) struct ResponseMiddleware;`
- `struct` **`IndexRoute`** — `pub(crate) struct IndexRoute;`
- `struct` **`RootRoute`** — `pub(crate) struct RootRoute;`
- `struct` **`ReloadRoute`** — `pub(crate) struct ReloadRoute;`
