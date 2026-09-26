# hyperlane-macros 完整 proc_macro 签名(77 个)

Source: `macros/src/lib.rs`。

## 完整列表

| proc_macro | 类型 | 签名 |
|---|---|---|
| `try_get_websocket_request` | `#[proc_macro_attribute]` | `pub fn try_get_websocket_request(attr: TokenStream, item: TokenStream)` |
| `try_get_http_request` | `#[proc_macro_attribute]` | `pub fn try_get_http_request(attr: TokenStream, item: TokenStream)` |
| `is_get_method` | `#[proc_macro_attribute]` | `pub fn is_get_method(_attr: TokenStream, item: TokenStream)` |
| `is_post_method` | `#[proc_macro_attribute]` | `pub fn is_post_method(_attr: TokenStream, item: TokenStream)` |
| `is_put_method` | `#[proc_macro_attribute]` | `pub fn is_put_method(_attr: TokenStream, item: TokenStream)` |
| `is_delete_method` | `#[proc_macro_attribute]` | `pub fn is_delete_method(_attr: TokenStream, item: TokenStream)` |
| `is_patch_method` | `#[proc_macro_attribute]` | `pub fn is_patch_method(_attr: TokenStream, item: TokenStream)` |
| `is_head_method` | `#[proc_macro_attribute]` | `pub fn is_head_method(_attr: TokenStream, item: TokenStream)` |
| `is_options_method` | `#[proc_macro_attribute]` | `pub fn is_options_method(_attr: TokenStream, item: TokenStream)` |
| `is_connect_method` | `#[proc_macro_attribute]` | `pub fn is_connect_method(_attr: TokenStream, item: TokenStream)` |
| `is_trace_method` | `#[proc_macro_attribute]` | `pub fn is_trace_method(_attr: TokenStream, item: TokenStream)` |
| `is_unknown_method` | `#[proc_macro_attribute]` | `pub fn is_unknown_method(_attr: TokenStream, item: TokenStream)` |
| `methods` | `#[proc_macro_attribute]` | `pub fn methods(attr: TokenStream, item: TokenStream)` |
| `is_http0_9_version` | `#[proc_macro_attribute]` | `pub fn is_http0_9_version(_attr: TokenStream, item: TokenStream)` |
| `is_http1_0_version` | `#[proc_macro_attribute]` | `pub fn is_http1_0_version(_attr: TokenStream, item: TokenStream)` |
| `is_http1_1_version` | `#[proc_macro_attribute]` | `pub fn is_http1_1_version(_attr: TokenStream, item: TokenStream)` |
| `is_http2_version` | `#[proc_macro_attribute]` | `pub fn is_http2_version(_attr: TokenStream, item: TokenStream)` |
| `is_http3_version` | `#[proc_macro_attribute]` | `pub fn is_http3_version(_attr: TokenStream, item: TokenStream)` |
| `is_http1_1_or_higher_version` | `#[proc_macro_attribute]` | `pub fn is_http1_1_or_higher_version(_attr: TokenStream, item: TokenStream)` |
| `is_http_version` | `#[proc_macro_attribute]` | `pub fn is_http_version(_attr: TokenStream, item: TokenStream)` |
| `is_unknown_version` | `#[proc_macro_attribute]` | `pub fn is_unknown_version(_attr: TokenStream, item: TokenStream)` |
| `is_ws_upgrade_type` | `#[proc_macro_attribute]` | `pub fn is_ws_upgrade_type(_attr: TokenStream, item: TokenStream)` |
| `is_h2c_upgrade_type` | `#[proc_macro_attribute]` | `pub fn is_h2c_upgrade_type(_attr: TokenStream, item: TokenStream)` |
| `is_tls_upgrade_type` | `#[proc_macro_attribute]` | `pub fn is_tls_upgrade_type(_attr: TokenStream, item: TokenStream)` |
| `is_unknown_upgrade_type` | `#[proc_macro_attribute]` | `pub fn is_unknown_upgrade_type(_attr: TokenStream, item: TokenStream)` |
| `response_status_code` | `#[proc_macro_attribute]` | `pub fn response_status_code(attr: TokenStream, item: TokenStream)` |
| `response_reason_phrase` | `#[proc_macro_attribute]` | `pub fn response_reason_phrase(attr: TokenStream, item: TokenStream)` |
| `response_header` | `#[proc_macro_attribute]` | `pub fn response_header(attr: TokenStream, item: TokenStream)` |
| `response_body` | `#[proc_macro_attribute]` | `pub fn response_body(attr: TokenStream, item: TokenStream)` |
| `clear_response_headers` | `#[proc_macro_attribute]` | `pub fn clear_response_headers(_attr: TokenStream, item: TokenStream)` |
| `response_version` | `#[proc_macro_attribute]` | `pub fn response_version(attr: TokenStream, item: TokenStream)` |
| `closed` | `#[proc_macro_attribute]` | `pub fn closed(_attr: TokenStream, item: TokenStream)` |
| `filter` | `#[proc_macro_attribute]` | `pub fn filter(attr: TokenStream, item: TokenStream)` |
| `reject` | `#[proc_macro_attribute]` | `pub fn reject(attr: TokenStream, item: TokenStream)` |
| `host` | `#[proc_macro_attribute]` | `pub fn host(attr: TokenStream, item: TokenStream)` |
| `reject_host` | `#[proc_macro_attribute]` | `pub fn reject_host(attr: TokenStream, item: TokenStream)` |
| `referer` | `#[proc_macro_attribute]` | `pub fn referer(attr: TokenStream, item: TokenStream)` |
| `reject_referer` | `#[proc_macro_attribute]` | `pub fn reject_referer(attr: TokenStream, item: TokenStream)` |
| `prologue_hooks` | `#[proc_macro_attribute]` | `pub fn prologue_hooks(attr: TokenStream, item: TokenStream)` |
| `epilogue_hooks` | `#[proc_macro_attribute]` | `pub fn epilogue_hooks(attr: TokenStream, item: TokenStream)` |
| `request_body` | `#[proc_macro_attribute]` | `pub fn request_body(attr: TokenStream, item: TokenStream)` |
| `request_body_json_result` | `#[proc_macro_attribute]` | `pub fn request_body_json_result(attr: TokenStream, item: TokenStream)` |
| `request_body_json` | `#[proc_macro_attribute]` | `pub fn request_body_json(attr: TokenStream, item: TokenStream)` |
| `try_get_attribute` | `#[proc_macro_attribute]` | `pub fn try_get_attribute(attr: TokenStream, item: TokenStream)` |
| `attribute` | `#[proc_macro_attribute]` | `pub fn attribute(attr: TokenStream, item: TokenStream)` |
| `attributes` | `#[proc_macro_attribute]` | `pub fn attributes(attr: TokenStream, item: TokenStream)` |
| `try_get_task_panic_data` | `#[proc_macro_attribute]` | `pub fn try_get_task_panic_data(attr: TokenStream, item: TokenStream)` |
| `task_panic_data` | `#[proc_macro_attribute]` | `pub fn task_panic_data(attr: TokenStream, item: TokenStream)` |
| `try_get_request_error_data` | `#[proc_macro_attribute]` | `pub fn try_get_request_error_data(attr: TokenStream, item: TokenStream)` |
| `request_error_data` | `#[proc_macro_attribute]` | `pub fn request_error_data(attr: TokenStream, item: TokenStream)` |
| `try_get_route_param` | `#[proc_macro_attribute]` | `pub fn try_get_route_param(attr: TokenStream, item: TokenStream)` |
| `route_param` | `#[proc_macro_attribute]` | `pub fn route_param(attr: TokenStream, item: TokenStream)` |
| `route_params` | `#[proc_macro_attribute]` | `pub fn route_params(attr: TokenStream, item: TokenStream)` |
| `try_get_request_query` | `#[proc_macro_attribute]` | `pub fn try_get_request_query(attr: TokenStream, item: TokenStream)` |
| `request_query` | `#[proc_macro_attribute]` | `pub fn request_query(attr: TokenStream, item: TokenStream)` |
| `request_querys` | `#[proc_macro_attribute]` | `pub fn request_querys(attr: TokenStream, item: TokenStream)` |
| `try_get_request_header` | `#[proc_macro_attribute]` | `pub fn try_get_request_header(attr: TokenStream, item: TokenStream)` |
| `request_header` | `#[proc_macro_attribute]` | `pub fn request_header(attr: TokenStream, item: TokenStream)` |
| `request_headers` | `#[proc_macro_attribute]` | `pub fn request_headers(attr: TokenStream, item: TokenStream)` |
| `try_get_request_cookie` | `#[proc_macro_attribute]` | `pub fn try_get_request_cookie(attr: TokenStream, item: TokenStream)` |
| `request_cookie` | `#[proc_macro_attribute]` | `pub fn request_cookie(attr: TokenStream, item: TokenStream)` |
| `request_cookies` | `#[proc_macro_attribute]` | `pub fn request_cookies(attr: TokenStream, item: TokenStream)` |
| `request_version` | `#[proc_macro_attribute]` | `pub fn request_version(attr: TokenStream, item: TokenStream)` |
| `request_path` | `#[proc_macro_attribute]` | `pub fn request_path(attr: TokenStream, item: TokenStream)` |
| `hyperlane` | `#[proc_macro_attribute]` | `pub fn hyperlane(attr: TokenStream, item: TokenStream)` |
| `route` | `#[proc_macro_attribute]` | `pub fn route(attr: TokenStream, item: TokenStream)` |
| `request_middleware` | `#[proc_macro_attribute]` | `pub fn request_middleware(attr: TokenStream, item: TokenStream)` |
| `response_middleware` | `#[proc_macro_attribute]` | `pub fn response_middleware(attr: TokenStream, item: TokenStream)` |
| `task_panic` | `#[proc_macro_attribute]` | `pub fn task_panic(attr: TokenStream, item: TokenStream)` |
| `request_error` | `#[proc_macro_attribute]` | `pub fn request_error(attr: TokenStream, item: TokenStream)` |
| `prologue_macros` | `#[proc_macro_attribute]` | `pub fn prologue_macros(attr: TokenStream, item: TokenStream)` |
| `epilogue_macros` | `#[proc_macro_attribute]` | `pub fn epilogue_macros(attr: TokenStream, item: TokenStream)` |
| `try_send` | `#[proc_macro_attribute]` | `pub fn try_send(attr: TokenStream, item: TokenStream)` |
| `send` | `#[proc_macro_attribute]` | `pub fn send(attr: TokenStream, item: TokenStream)` |
| `try_flush` | `#[proc_macro_attribute]` | `pub fn try_flush(_attr: TokenStream, item: TokenStream)` |
| `flush` | `#[proc_macro_attribute]` | `pub fn flush(_attr: TokenStream, item: TokenStream)` |
| `context` | `#[proc_macro]` | `pub fn context(input: TokenStream)` |
