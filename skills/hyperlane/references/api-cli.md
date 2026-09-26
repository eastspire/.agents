# hyperlane-cli 完整 pub API

Source: `cli/src/` — auto-extracted from `pub` declarations.

**注意**:`hyperlane-cli` 只提供 `watch / new / template / help / version` 5 个子命令。`bump / sync / fmt / publish` 由外部 `crate-cli` 提供。

### `command::enum`

- `enum` **`CommandType`** — `pub enum CommandType {`

### `config::fn`

- `fn` **`parse_args`** — `pub fn parse_args() -> Args {...}`

### `config::struct`

- `struct` **`Args`** — `pub struct Args {`

### `help::fn`

- `fn` **`print_help`** — `pub fn print_help() {...}`

### `logger::impl`

- `fn` **`init`** — `pub fn init(level_filter: log::LevelFilter) {...}`

### `logger::static`

- `static` **`LOGGER`** — `pub(crate) static LOGGER: Logger = Logger;`

### `logger::struct`

- `struct` **`Logger`** — `pub struct Logger;`

### `new::enum`

- `enum` **`NewError`** — `pub enum NewError {`

### `new::fn`

- `fn` **`execute_new`** — `pub async fn execute_new(project_name: &str) -> Result<(), NewError> {...}`

### `new::impl`

- `fn` **`new`** — `pub fn new(project_name: String) -> Self {...}`

### `new::struct`

- `struct` **`NewProjectConfig`** — `pub struct NewProjectConfig {`

### `template::enum`

- `enum` **`TemplateType`** — `pub enum TemplateType {`
- `enum` **`ModelSubType`** — `pub enum ModelSubType {`
- `enum` **`TemplateError`** — `pub enum TemplateError {`

### `template::fn`

- `fn` **`execute_template`** — `pub async fn execute_template( template_type: TemplateType, component_name: &str, model_sub_type: Option<ModelSubType>, ) -> Result<(), TemplateError> {...}`

### `template::impl`

- `fn` **`new`** — `pub fn new( template_type: TemplateType, component_name: String, model_sub_type: Option<ModelSubType>, ) -> Self {...}`

### `template::struct`

- `struct` **`TemplateConfig`** — `pub struct TemplateConfig {`

### `version::fn`

- `fn` **`print_version`** — `pub fn print_version() {...}`

### `watch::fn`

- `fn` **`execute_watch`** — `pub async fn execute_watch() -> Result<(), io::Error> {...}`
