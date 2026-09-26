# euv-docs 完整 pub API

Source: `docs/src/` — auto-extracted from `pub` declarations.

### `lib`

- `fn` **`main`** — `pub fn main() {...}`

### `data::struct`

- `struct` **`DocsFeature`** — `pub struct DocsFeature {`
- `struct` **`DocsStat`** — `pub struct DocsStat {`
- `struct` **`DocsPage`** — `pub struct DocsPage {`
- `struct` **`DocsLocale`** — `pub struct DocsLocale {`
- `struct` **`DocsSite`** — `pub struct DocsSite {`

### `router::fn`

- `fn` **`parse_route`** — `pub(crate) fn parse_route(raw: &str) -> (String, Option<String>) {...}`
- `fn` **`locale_of`** — `pub(crate) fn locale_of(route: &str) -> &'static DocsLocale {...}`
- `fn` **`find_page`** — `pub(crate) fn find_page(route: &str) -> Option<&'static DocsPage> {...}`
- `fn` **`scope_for`** — `pub(crate) fn scope_for( items: &'static [EuvSidebarItem], route: &str, ) -> Option<&'static [EuvSidebarItem]> {...}`
- `fn` **`flatten_links`** — `pub(crate) fn flatten_links(items: &'static [EuvSidebarItem]) -> Vec<&'static EuvSidebarItem> {...}`
- `fn` **`route_in_locale`** — `pub(crate) fn route_in_locale(route: &str, target: &'static DocsLocale) -> String {...}`

### `bin::docs::fn`

- `fn` **`parse_args`** — `pub fn parse_args() -> Result<Args, String> {...}`
- `fn` **`run`** — `pub fn run(args: &Args) -> Result<(), String> {...}`
- `fn` **`print_usage`** — `pub fn print_usage() {...}`

### `bin::docs::struct`

- `struct` **`Args`** — `pub struct Args {`

### `component::doc_page::view::fn`

- `fn` **`docs_main`** — `pub(crate) fn docs_main(node: VirtualNode<DocsPageProps>) -> VirtualNode {...}`
- `fn` **`docs_doc_page`** — `pub(crate) fn docs_doc_page(node: VirtualNode<DocsPageProps>) -> VirtualNode {...}`

### `component::doc_page::view::struct`

- `struct` **`DocsPageProps`** — `pub(crate) struct DocsPageProps {`

### `component::home_page::view::fn`

- `fn` **`docs_home_page`** — `pub(crate) fn docs_home_page(node: VirtualNode<DocsPageProps>) -> VirtualNode {...}`
- `fn` **`docs_stats_row`** — `pub(crate) fn docs_stats_row(node: VirtualNode<DocsStatsRowProps>) -> VirtualNode {...}`
- `fn` **`docs_feature_card`** — `pub(crate) fn docs_feature_card(node: VirtualNode<DocsFeatureProps>) -> VirtualNode {...}`
- `fn` **`docs_feature_grid`** — `pub(crate) fn docs_feature_grid(node: VirtualNode<DocsFeatureGridProps>) -> VirtualNode {...}`

### `component::home_page::view::struct`

- `struct` **`DocsFeatureProps`** — `pub struct DocsFeatureProps {`
- `struct` **`DocsFeatureGridProps`** — `pub struct DocsFeatureGridProps {`
- `struct` **`DocsStatsRowProps`** — `pub struct DocsStatsRowProps {`

### `component::layout::view::fn`

- `fn` **`app`** — `pub(crate) fn app() -> VirtualNode {...}`
- `fn` **`docs_desktop_shell`** — `pub(crate) fn docs_desktop_shell(node: VirtualNode<DocsShellProps>) -> VirtualNode {...}`
- `fn` **`docs_mobile_shell`** — `pub(crate) fn docs_mobile_shell(node: VirtualNode<DocsShellProps>) -> VirtualNode {...}`

### `component::layout::view::struct`

- `struct` **`DocsShellProps`** — `pub(crate) struct DocsShellProps {`

### `component::not_found::view::fn`

- `fn` **`docs_not_found`** — `pub(crate) fn docs_not_found(node: VirtualNode<DocsPageProps>) -> VirtualNode {...}`

### `component::password_gate::view::fn`

- `fn` **`docs_password_gate`** — `pub(crate) fn docs_password_gate(node: VirtualNode<DocsPasswordGateProps>) -> VirtualNode {...}`
- `fn` **`is_unlocked`** — `pub(crate) fn is_unlocked(route: &str) -> bool {...}`

### `component::password_gate::view::struct`

- `struct` **`DocsPasswordGateProps`** — `pub(crate) struct DocsPasswordGateProps {`
