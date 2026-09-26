# http-compress 完整 pub API

Source: `compress/src/` — auto-extracted from `pub` declarations.

Crate name: `http-compress`. 提供 Brotli / Deflate / Gzip 编解码。

### `brotli::fn`

- `fn` **`encode`** — `pub fn encode(data: &'_ [u8]) -> Cow<'_, [u8]> {...}`
- `fn` **`decode`** — `pub fn decode(data: &'_ [u8], buffer_size: usize) -> Cow<'_, [u8]> {...}`

### `compress::enum`

- `enum` **`Compress`** — `pub enum Compress {`

### `compress::impl`

- `fn` **`is_unknown`** — `pub fn is_unknown(&self) -> bool {...}`
- `fn` **`from`** — `pub fn from(header: &HashMap<String, String, BuildHasherDefault<XxHash3_64>>) -> Self {...}`
- `fn` **`decode`** — `pub fn decode<'a>(&self, data: &'a [u8], buffer_size: usize) -> Cow<'a, [u8]> {...}`
- `fn` **`encode`** — `pub fn encode<'a>(&self, data: &'a [u8], buffer_size: usize) -> Cow<'a, [u8]> {...}`

### `deflate::fn`

- `fn` **`encode`** — `pub fn encode(data: &'_ [u8], buffer_size: usize) -> Cow<'_, [u8]> {...}`
- `fn` **`decode`** — `pub fn decode(data: &'_ [u8], buffer_size: usize) -> Cow<'_, [u8]> {...}`

### `gzip::fn`

- `fn` **`encode`** — `pub fn encode(data: &'_ [u8], buffer_size: usize) -> Cow<'_, [u8]> {...}`
- `fn` **`decode`** — `pub fn decode(data: &'_ [u8], buffer_size: usize) -> Cow<'_, [u8]> {...}`
