# http-request 完整 pub API(客户端)

Source: `request/src/` — auto-extracted from `pub` declarations.

Crate name: `http-request` (目录仍叫 `request/`).

### `common::enum`

- `struct` **`Body`** — `pub struct Body {`
- `fn` **`empty`** — `pub const fn empty() -> Self {...}`
- `fn` **`from_bytes`** — `pub fn from_bytes<B: Into<Vec<u8>>>(bytes: B) -> Self {...}`
- `fn` **`as_slice`** — `pub fn as_slice(&self) -> &[u8] {...}`
- `fn` **`as_str`** — `pub fn as_str(&self) -> Option<&str> {...}`

### `response::struct`

- `struct` **`HttpResponse`** — `pub struct HttpResponse {`
- `fn` **`from_bytes`** — `pub fn from_bytes(response: &[u8]) -> Self {...}`
- `fn` **`is_success`** — `pub fn is_success(&self) -> bool {...}`
- `fn` **`is_redirect`** — `pub fn is_redirect(&self) -> bool {...}`
- `fn` **`get_header`** — `pub fn get_header<K: AsRef<str>>(&self, key: K) -> Option<&str> {...}`
- `fn` **`text`** — `pub fn text(&self) -> String {...}`
- `fn` **`bytes`** — `pub fn bytes(&self) -> &[u8] {...}`
- `fn` **`decode`** — `pub fn decode(&self, buffer_size: usize) -> HttpResponse {...}`

### `response::type`

- `type` **`HttpResponseHeaders`** — `pub type HttpResponseHeaders = HashMapXxHash3_64<String, String>;`
- `type` **`ResponseBody`** — `pub type ResponseBody = Vec<u8>;`
- `type` **`ResponseData`** — `pub type ResponseData = Vec<u8>;`
- `type` **`ResponseDataString`** — `pub type ResponseDataString = String;`
- `fn` **`new_response_headers`** — `pub fn new_response_headers() -> HttpResponseHeaders {...}`

### `request::config::struct`

- `struct` **`RequestConfig`** — `pub struct RequestConfig {`
- `fn` **`set_buffer_size`** — `pub fn set_buffer_size(&mut self, v: usize) -> &mut Self {...}`
- `fn` **`get_buffer_size`** — `pub fn get_buffer_size(&self) -> usize {...}`
- `fn` **`set_timeout`** — `pub fn set_timeout(&mut self, v: u64) -> &mut Self {...}`
- `fn` **`get_timeout`** — `pub fn get_timeout(&self) -> u64 {...}`
- `fn` **`set_max_redirect_times`** — `pub fn set_max_redirect_times(&mut self, v: usize) -> &mut Self {...}`
- `fn` **`get_max_redirect_times`** — `pub fn get_max_redirect_times(&self) -> usize {...}`
- `fn` **`set_http_version`** — `pub fn set_http_version(&mut self, v: HttpVersion) -> &mut Self {...}`
- `fn` **`get_http_version`** — `pub fn get_http_version(&self) -> &HttpVersion {...}`
- `fn` **`set_redirect`** — `pub fn set_redirect(&mut self, v: bool) -> &mut Self {...}`
- `fn` **`get_redirect`** — `pub fn get_redirect(&self) -> bool {...}`
- `fn` **`set_decode`** — `pub fn set_decode(&mut self, v: bool) -> &mut Self {...}`
- `fn` **`get_decode`** — `pub fn get_decode(&self) -> bool {...}`
- `fn` **`set_proxy`** — `pub fn set_proxy(&mut self, v: Option<Proxy>) -> &mut Self {...}`
- `fn` **`get_proxy`** — `pub fn get_proxy(&self) -> &Option<Proxy> {...}`

### `request::http_request::impl`

- `trait` **`AsyncReadWrite`** — `pub(crate) trait AsyncReadWrite: AsyncRead + AsyncWrite + Unpin + Send {}`
- `trait` **`ReadWrite`** — `pub(crate) trait ReadWrite: Read + Write {}`
- `type` **`BoxAsyncReadWrite`** — `pub(crate) type BoxAsyncReadWrite = Box<dyn AsyncReadWrite>;`
- `type` **`BoxReadWrite`** — `pub(crate) type BoxReadWrite = Box<dyn ReadWrite>;`
- `fn` **`send`** — `pub fn send(&mut self) -> RequestResult {...}`
- `fn` **`send_async`** — `pub async fn send_async(&mut self) -> RequestResult {...}`
- `fn` **`parse_url`** — `pub(crate) fn parse_url(&self) -> Result<HttpUrlComponents, RequestError> {...}`
- `fn` **`full_path`** — `pub(crate) fn full_path(&self) -> String {...}`
- `fn` **`protocol_lower`** — `pub(crate) fn protocol_lower(config: &RequestConfig) -> String {...}`
- `fn` **`header_bytes`** — `pub(crate) fn header_bytes(&self, body_length: usize) -> Vec<u8> {...}`
- `fn` **`body_bytes`** — `pub(crate) fn body_bytes(&self) -> Vec<u8> {...}`
- `fn` **`send_sync`** — `pub(crate) fn send_sync(&mut self) -> RequestResult {...}`

### `request::http_request::struct`

- `type` **`RequestResult`** — `pub type RequestResult = Result<HttpResponse, RequestError>;`
- `struct` **`HttpRequest`** — `pub struct HttpRequest {`
- `fn` **`get`** — `pub fn get(url: impl Into<String>) -> Self {...}`
- `fn` **`post`** — `pub fn post(url: impl Into<String>) -> Self {...}`
- `fn` **`set_method`** — `pub fn set_method(&mut self, method: Method) -> &mut Self {...}`
- `fn` **`set_url`** — `pub fn set_url(&mut self, url: impl Into<String>) -> &mut Self {...}`
- `fn` **`set_header`** — `pub fn set_header<K: AsRef<str>, V: AsRef<str>>(&mut self, key: K, value: V) -> &mut Self {...}`
- `fn` **`remove_header`** — `pub fn remove_header<K: AsRef<str>>(&mut self, key: K) -> &mut Self {...}`
- `fn` **`clear_headers`** — `pub fn clear_headers(&mut self) -> &mut Self {...}`
- `fn` **`set_body`** — `pub fn set_body(&mut self, body: Body) -> &mut Self {...}`
- `fn` **`set_config`** — `pub fn set_config(&mut self, config: RequestConfig) -> &mut Self {...}`
- `fn` **`get_method`** — `pub fn get_method(&self) -> Method {...}`
- `fn` **`get_url`** — `pub fn get_url(&self) -> String {...}`
- `fn` **`get_url_ref`** — `pub fn get_url_ref(&self) -> &str {...}`
- `fn` **`get_headers`** — `pub fn get_headers(&self) -> HashMap<String, String> {...}`
- `fn` **`get_headers_ref`** — `pub fn get_headers_ref(&self) -> &HashMap<String, String> {...}`
- `fn` **`get_body`** — `pub fn get_body(&self) -> Body {...}`
- `fn` **`get_body_ref`** — `pub fn get_body_ref(&self) -> &Body {...}`
- `fn` **`get_config`** — `pub fn get_config(&self) -> RequestConfig {...}`
- `fn` **`get_config_ref`** — `pub fn get_config_ref(&self) -> &RequestConfig {...}`
- `fn` **`get_config_mut`** — `pub fn get_config_mut(&mut self) -> &mut RequestConfig {...}`
- `fn` **`get_tmp_ref`** — `pub(crate) fn get_tmp_ref(&self) -> &Tmp {...}`
- `fn` **`get_tmp_mut`** — `pub(crate) fn get_tmp_mut(&mut self) -> &mut Tmp {...}`

### `request::http_request::trait`

- `trait` **`AsyncReadWrite`** — `pub(crate) trait AsyncReadWrite: AsyncRead + AsyncWrite + Unpin + Send {}`
- `trait` **`ReadWrite`** — `pub(crate) trait ReadWrite: Read + Write {}`
- `trait` **`AsyncRequestTrait`** — `pub trait AsyncRequestTrait: Send + Debug {`
- `trait` **`RequestTrait`** — `pub trait RequestTrait: Send + Debug {`

### `request::http_request::type`

- `type` **`RequestHeadersKey`** — `pub type RequestHeadersKey = String;`
- `type` **`RequestHeadersValue`** — `pub type RequestHeadersValue = String;`
- `type` **`RequestHeaders`** — `pub type RequestHeaders = HashMapXxHash3_64<RequestHeadersKey, RequestHeadersValue>;`

### `request::parser::fn`

- `fn` **`split_multi_byte`** — `pub(crate) fn split_multi_byte<'a>(data: &'a [u8], delimiter: &'a [u8]) -> Vec<&'a [u8]> {...}`
- `fn` **`split_whitespace`** — `pub(crate) fn split_whitespace(input: &[u8]) -> Vec<&[u8]> {...}`
- `fn` **`build_http_request`** — `pub(crate) fn build_http_request( method: &str, path: String, header_bytes: Vec<u8>, body_bytes: Option<Vec<u8>>, http_version_str: String, ) -> Vec<u8> {...}`
- `fn` **`parse_chunked_body`** — `pub(crate) fn parse_chunked_body(body_bytes: &[u8]) -> Vec<u8> {...}`
- `fn` **`find_double_crlf`** — `pub(crate) fn find_double_crlf(data: &[u8], start: usize) -> Option<usize> {...}`
- `fn` **`find_pattern_case_insensitive`** — `pub(crate) fn find_pattern_case_insensitive(haystack: &[u8], needle: &[u8]) -> Option<usize> {...}`
- `fn` **`find_crlf`** — `pub(crate) fn find_crlf(data: &[u8], start: usize) -> Option<usize> {...}`
- `fn` **`get_content_length`** — `pub(crate) fn get_content_length(response_bytes: &[u8]) -> usize {...}`
- `fn` **`is_chunked_encoding`** — `pub(crate) fn is_chunked_encoding(headers_bytes: &[u8]) -> bool {...}`
- `fn` **`parse_decimal_bytes`** — `pub(crate) fn parse_decimal_bytes(bytes: &[u8]) -> usize {...}`
- `fn` **`parse_status_code`** — `pub(crate) fn parse_status_code(status_bytes: &[u8]) -> usize {...}`
- `fn` **`calculate_buffer_capacity`** — `pub(crate) fn calculate_buffer_capacity( response_bytes: &[u8], n: usize, current_capacity: usize, ) -> usize {...}`
- `fn` **`parse_response_headers`** — `pub(crate) fn parse_response_headers( headers_bytes: &[u8], http_version_bytes: &[u8], location_sign_key: &[u8], content_length: &mut usize, redirect_url: &mut Option<Vec<u8>>,`

### `request::proxy::impl`

- `fn` **`new`** — `pub(crate) fn new(stream: BoxAsyncReadWrite, pre_read_data: Vec<u8>) -> Self {...}`
- `fn` **`new`** — `pub(crate) fn new(stream: BoxReadWrite, pre_read_data: Vec<u8>) -> Self {...}`

### `request::proxy::struct`

- `enum` **`ProxyType`** — `pub enum ProxyType {`
- `struct` **`Proxy`** — `pub struct Proxy {`
- `fn` **`http`** — `pub fn http<H: AsRef<str>>(host: H, port: u16) -> Self {...}`
- `fn` **`https`** — `pub fn https<H: AsRef<str>>(host: H, port: u16) -> Self {...}`
- `fn` **`socks5`** — `pub fn socks5<H: AsRef<str>>(host: H, port: u16) -> Self {...}`
- `fn` **`auth`** — `pub fn auth<U: AsRef<str>, P: AsRef<str>>(mut self, username: U, password: P) -> Self {...}`
- `struct` **`ProxyTunnelStream`** — `pub struct ProxyTunnelStream {`
- `struct` **`SyncProxyTunnelStream`** — `pub struct SyncProxyTunnelStream {`

### `request::request_builder::struct`

- `struct` **`RequestBuilder`** — `pub struct RequestBuilder {`
- `fn` **`new`** — `pub fn new() -> Self {...}`
- `fn` **`get`** — `pub fn get(&mut self, url: impl Into<String>) -> &mut Self {...}`
- `fn` **`post`** — `pub fn post(&mut self, url: impl Into<String>) -> &mut Self {...}`
- `fn` **`method`** — `pub fn method(&mut self, method: Method) -> &mut Self {...}`
- `fn` **`url`** — `pub fn url(&mut self, url: impl Into<String>) -> &mut Self {...}`
- `fn` **`header`** — `pub fn header<K: AsRef<str>, V: AsRef<str>>(&mut self, key: K, value: V) -> &mut Self {...}`
- `fn` **`headers`** — `pub fn headers<K, V>(&mut self, headers: HashMap<K, V>) -> &mut Self where K: AsRef<str>, V: AsRef<str>, {...}`
- `fn` **`remove_header`** — `pub fn remove_header<K: AsRef<str>>(&mut self, key: K) -> &mut Self {...}`
- `fn` **`clear_headers`** — `pub fn clear_headers(&mut self) -> &mut Self {...}`
- `fn` **`body`** — `pub fn body<B: Into<Vec<u8>>>(&mut self, bytes: B) -> &mut Self {...}`
- `fn` **`body_text`** — `pub fn body_text<T: Into<String>>(&mut self, text: T) -> &mut Self {...}`
- `fn` **`body_json`** — `pub fn body_json<V: serde::Serialize>(&mut self, value: &V) -> &mut Self {...}`
- `fn` **`timeout`** — `pub fn timeout(&mut self, ms: u64) -> &mut Self {...}`
- `fn` **`buffer_size`** — `pub fn buffer_size(&mut self, n: usize) -> &mut Self {...}`
- `fn` **`http1_1_only`** — `pub fn http1_1_only(&mut self) -> &mut Self {...}`
- `fn` **`http2_only`** — `pub fn http2_only(&mut self) -> &mut Self {...}`
- `fn` **`redirect`** — `pub fn redirect(&mut self) -> &mut Self {...}`
- `fn` **`no_redirect`** — `pub fn no_redirect(&mut self) -> &mut Self {...}`
- `fn` **`max_redirect_times`** — `pub fn max_redirect_times(&mut self, n: usize) -> &mut Self {...}`
- `fn` **`decode`** — `pub fn decode(&mut self) -> &mut Self {...}`
- `fn` **`no_decode`** — `pub fn no_decode(&mut self) -> &mut Self {...}`
- `fn` **`proxy`** — `pub fn proxy(&mut self, proxy: Proxy) -> &mut Self {...}`
- `fn` **`no_proxy`** — `pub fn no_proxy(&mut self) -> &mut Self {...}`
- `fn` **`build`** — `pub fn build(&mut self) -> HttpRequest {...}`

### `request::tmp::struct`

- `struct` **`Tmp`** — `pub struct Tmp {`
- `fn` **`visit_url_ref`** — `pub(crate) fn visit_url_ref(&self) -> &HashSet<String> {...}`
- `fn` **`visit_url_mut`** — `pub(crate) fn visit_url_mut(&mut self) -> &mut HashSet<String> {...}`
- `fn` **`root_cert_clone`** — `pub(crate) fn root_cert_clone(&self) -> RootCertStore {...}`

### `utils::encode::fn`

- `fn` **`base64_encode`** — `pub(crate) fn base64_encode(input: &[u8]) -> String {...}`
