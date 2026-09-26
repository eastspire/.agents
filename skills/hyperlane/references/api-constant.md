# http-constant 完整 pub API

Source: `constant/src/` — HTTP 常量集合(BODY / COMMON / HEADER / METHOD / STATUS / VERSION / PATH / QUERY 等)。

Crate name: `http-constant`. **全部都是 `pub use` re-export** — 真正的常量定义在 `constant/src/<name>.rs`,每个文件一个常量数组。

## 模块清单

- `body/mod` — re-export
- `common/mod` — re-export
- `content_type_value/mod` — re-export
- `file_extension/mod` — re-export
- `header_key/mod` — re-export
- `header_value/mod` — re-export
- `http2/mod` — re-export
- `http_status/mod` — re-export
- `http_version/mod` — re-export
- `method/mod` — re-export
- `path/mod` — re-export
- `protocol/mod` — re-export
- `query/mod` — re-export
- `session/mod` — re-export

## 用法

```rust
use hyperlane::http_constant::{
    HEADER_CONTENT_TYPE, HEADER_HOST, METHOD_GET, METHOD_POST,
    STATUS_200, STATUS_404, VERSION_HTTP_1_1,
};
```
