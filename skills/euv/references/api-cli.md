# euv-cli 完整 pub API

Source: `cli/src/` — auto-extracted from `pub` declarations.

### `main`

- `fn` **`main`** — `pub async fn main() -> Result<(), EuvError> {...}`

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
