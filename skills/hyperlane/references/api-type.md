# http-type 完整 pub API

Source: `type/src/` — auto-extracted from `pub` declarations.

Crate name: `http-type` (目录仍叫 `type/`);use as `hyperlane::http_type::*` 或 `http_type::*`。

### `any::trait`

- `trait` **`AnySend`** — `pub trait AnySend: Any + Send {}`
- `trait` **`AnySendClone`** — `pub trait AnySendClone: Any + Send + Clone {}`
- `trait` **`AnySync`** — `pub trait AnySync: Any + Sync {}`
- `trait` **`AnySyncClone`** — `pub trait AnySyncClone: Any + Sync + Clone {}`
- `trait` **`AnySendSync`** — `pub trait AnySendSync: Any + Send + Sync {}`
- `trait` **`AnySendSyncClone`** — `pub trait AnySendSyncClone: Any + Send + Sync + Clone {}`

### `any::type`

- `type` **`BoxAny`** — `pub type BoxAny = Box<dyn Any>;`
- `type` **`RcAny`** — `pub type RcAny = Rc<dyn Any>;`
- `type` **`ArcAny`** — `pub type ArcAny = Arc<dyn Any>;`
- `type` **`BoxAnySend`** — `pub type BoxAnySend = Box<dyn Any + Send>;`
- `type` **`RcAnySend`** — `pub type RcAnySend = Rc<dyn Any + Send>;`
- `type` **`ArcAnySend`** — `pub type ArcAnySend = Arc<dyn Any + Send>;`
- `type` **`BoxAnySync`** — `pub type BoxAnySync = Box<dyn Any + Sync>;`
- `type` **`RcAnySync`** — `pub type RcAnySync = Rc<dyn Any + Sync>;`
- `type` **`ArcAnySync`** — `pub type ArcAnySync = Arc<dyn Any + Sync>;`
- `type` **`BoxAnySendSync`** — `pub type BoxAnySendSync = Box<dyn Any + Send + Sync>;`
- `type` **`RcAnySendSync`** — `pub type RcAnySendSync = Rc<dyn Any + Send + Sync>;`
- `type` **`ArcAnySendSync`** — `pub type ArcAnySendSync = Arc<dyn Any + Send + Sync>;`

### `arc_mutex::fn`

- `fn` **`arc_mutex`** — `pub fn arc_mutex<T>(data: T) -> ArcMutex<T> {...}`

### `arc_mutex::type`

- `type` **`ArcMutex`** — `pub type ArcMutex<T> = Arc<Mutex<T>>;`

### `arc_rwlock::fn`

- `fn` **`arc_rwlock`** — `pub fn arc_rwlock<T>(data: T) -> ArcRwLock<T> {...}`

### `arc_rwlock::type`

- `type` **`ArcRwLock`** — `pub type ArcRwLock<T> = Arc<RwLock<T>>;`

### `attribute::enum`

- `enum` **`Attribute`** — `pub enum Attribute {`
- `enum` **`InternalAttribute`** — `pub enum InternalAttribute {`

### `attribute::type`

- `type` **`ThreadSafeAttributeStore`** — `pub type ThreadSafeAttributeStore = HashMap<String, ArcAnySendSync>;`

### `box_leak::fn`

- `fn` **`box_leak_new`** — `pub fn box_leak_new<T>(data: T) -> &'static mut T {...}`

### `box_rwlock::fn`

- `fn` **`box_rwlock`** — `pub fn box_rwlock<T>(data: T) -> BoxRwLock<T> {...}`

### `box_rwlock::type`

- `type` **`BoxRwLock`** — `pub type BoxRwLock<T> = Box<RwLock<T>>;`

### `content_type::enum`

- `enum` **`ContentType`** — `pub enum ContentType {`

### `content_type::impl`

- `fn` **`get_body_string`** — `pub fn get_body_string<T>(&self, data: &T) -> String where T: Serialize + Debug + Clone + Default + Display, {...}`
- `fn` **`format_content_type_with_charset`** — `pub fn format_content_type_with_charset<T, S>(content_type: T, charset: S) -> String where T: AsRef<str>, S: AsRef<str>, {...}`
- `fn` **`format_content_type_with_charset_declaration`** — `pub fn format_content_type_with_charset_declaration<T, S>( content_type: T, charset_with_key: S, ) -> String where T: AsRef<str>, S: AsRef<str>, {...}`

### `cookie::impl`

- `fn` **`new`** — `pub fn new<N, V>(name: N, value: V) -> Self where N: AsRef<str>, V: AsRef<str>, {...}`
- `fn` **`parse`** — `pub fn parse<C>(cookie: C) -> Self where C: AsRef<str>, {...}`
- `fn` **`set_expires`** — `pub fn set_expires<E>(&mut self, expires: E) -> &mut Self where E: AsRef<str>, {...}`
- `fn` **`set_max_age`** — `pub fn set_max_age<M>(&mut self, max_age: M) -> &mut Self where M: Into<i64>, {...}`
- `fn` **`set_domain`** — `pub fn set_domain<D>(&mut self, domain: D) -> &mut Self where D: AsRef<str>, {...}`
- `fn` **`set_path`** — `pub fn set_path<T>(&mut self, path: T) -> &mut Self where T: AsRef<str>, {...}`
- `fn` **`secure`** — `pub fn secure(&mut self) -> &mut Self {...}`
- `fn` **`http_only`** — `pub fn http_only(&mut self) -> &mut Self {...}`
- `fn` **`disable_secure`** — `pub fn disable_secure(&mut self) -> &mut Self {...}`
- `fn` **`disable_http_only`** — `pub fn disable_http_only(&mut self) -> &mut Self {...}`
- `fn` **`set_same_site`** — `pub fn set_same_site<T>(&mut self, same_site: T) -> &mut Self where T: AsRef<str>, {...}`
- `fn` **`build`** — `pub fn build(&self) -> String {...}`
- `fn` **`parse`** — `pub fn parse<C>(cookie: C) -> Cookies where C: AsRef<str>, {...}`

### `cookie::struct`

- `struct` **`CookieBuilder`** — `pub struct CookieBuilder {`
- `struct` **`Cookie`** — `pub struct Cookie;`

### `cookie::type`

- `type` **`CookieString`** — `pub type CookieString = String;`
- `type` **`CookieKey`** — `pub type CookieKey = String;`
- `type` **`CookieValue`** — `pub type CookieValue = String;`
- `type` **`Cookies`** — `pub type Cookies = HashMapXxHash3_64<CookieKey, CookieValue>;`

### `file_extension::enum`

- `enum` **`FileExtension`** — `pub enum FileExtension {`

### `file_extension::impl`

- `fn` **`parse`** — `pub fn parse<F>(file_extension: F) -> Self where F: AsRef<str>, {...}`
- `fn` **`get_extension_name`** — `pub fn get_extension_name<F>(full_path: F) -> String where F: AsRef<str>, {...}`
- `fn` **`get_content_type`** — `pub fn get_content_type(&self) -> &'static str {...}`

### `hash_map_xx_hash3_64::fn`

- `fn` **`hash_map_xx_hash3_64`** — `pub fn hash_map_xx_hash3_64<K: Eq + Hash, V>() -> HashMapXxHash3_64<K, V> {...}`

### `hash_map_xx_hash3_64::type`

- `type` **`HashMapXxHash3_64`** — `pub type HashMapXxHash3_64<K, V> = HashMap<K, V, BuildHasherDefault<XxHash3_64>>;`

### `hash_set_xx_hash3_64::fn`

- `fn` **`hash_set_xx_hash3_64`** — `pub fn hash_set_xx_hash3_64<K: Eq + Hash>() -> HashSetXxHash3_64<K> {...}`

### `hash_set_xx_hash3_64::type`

- `type` **`HashSetXxHash3_64`** — `pub type HashSetXxHash3_64<K> = HashSet<K, BuildHasherDefault<XxHash3_64>>;`

### `http_status::enum`

- `enum` **`HttpStatus`** — `pub enum HttpStatus {`

### `http_status::impl`

- `fn` **`code`** — `pub fn code(&self) -> ResponseStatusCode {...}`
- `fn` **`phrase`** — `pub fn phrase(code: ResponseStatusCode) -> String {...}`
- `fn` **`same`** — `pub fn same<C>(&self, code_str: C) -> bool where C: AsRef<str>, {...}`

### `http_url::enum`

- `enum` **`HttpUrlError`** — `pub enum HttpUrlError {`

### `http_url::impl`

- `fn` **`parse`** — `pub fn parse<U>(url: U) -> Result<Self, HttpUrlError> where U: AsRef<str>, {...}`

### `http_url::struct`

- `struct` **`HttpUrlComponents`** — `pub struct HttpUrlComponents {`

### `http_version::enum`

- `enum` **`HttpVersion`** — `pub enum HttpVersion {`

### `http_version::impl`

- `fn` **`is_http0_9`** — `pub fn is_http0_9(&self) -> bool {...}`
- `fn` **`is_http1_0`** — `pub fn is_http1_0(&self) -> bool {...}`
- `fn` **`is_http1_1`** — `pub fn is_http1_1(&self) -> bool {...}`
- `fn` **`is_http2`** — `pub fn is_http2(&self) -> bool {...}`
- `fn` **`is_http3`** — `pub fn is_http3(&self) -> bool {...}`
- `fn` **`is_unknown`** — `pub fn is_unknown(&self) -> bool {...}`
- `fn` **`is_http1_1_or_higher`** — `pub fn is_http1_1_or_higher(&self) -> bool {...}`
- `fn` **`is_http`** — `pub fn is_http(&self) -> bool {...}`

### `lifetime::trait`

- `trait` **`Lifetime`** — `pub trait Lifetime {`

### `methods::enum`

- `enum` **`Method`** — `pub enum Method {`

### `methods::impl`

- `fn` **`is_get`** — `pub fn is_get(&self) -> bool {...}`
- `fn` **`is_post`** — `pub fn is_post(&self) -> bool {...}`
- `fn` **`is_put`** — `pub fn is_put(&self) -> bool {...}`
- `fn` **`is_delete`** — `pub fn is_delete(&self) -> bool {...}`
- `fn` **`is_patch`** — `pub fn is_patch(&self) -> bool {...}`
- `fn` **`is_head`** — `pub fn is_head(&self) -> bool {...}`
- `fn` **`is_options`** — `pub fn is_options(&self) -> bool {...}`
- `fn` **`is_connect`** — `pub fn is_connect(&self) -> bool {...}`
- `fn` **`is_trace`** — `pub fn is_trace(&self) -> bool {...}`
- `fn` **`is_unknown`** — `pub fn is_unknown(&self) -> bool {...}`

### `panic::impl`

- `fn` **`from_join_error`** — `pub fn from_join_error(join_error: JoinError) -> Self {...}`

### `panic::struct`

- `struct` **`PanicData`** — `pub struct PanicData {`

### `protocol::impl`

- `fn` **`is_http`** — `pub fn is_http(protocol: &str) -> bool {...}`
- `fn` **`is_https`** — `pub fn is_https(protocol: &str) -> bool {...}`
- `fn` **`get_port`** — `pub fn get_port(protocol: &str) -> u16 {...}`

### `protocol::struct`

- `struct` **`Protocol`** — `pub struct Protocol;`

### `rc_rwlock::fn`

- `fn` **`rc_rwlock`** — `pub fn rc_rwlock<T>(data: T) -> RcRwLock<T> {...}`

### `rc_rwlock::type`

- `type` **`RcRwLock`** — `pub type RcRwLock<T> = Rc<RwLock<T>>;`

### `request::enum`

- `enum` **`RequestError`** — `pub enum RequestError {`

### `request::impl`

- `fn` **`get_http_status`** — `pub fn get_http_status(&self) -> HttpStatus {...}`
- `fn` **`get_http_status_code`** — `pub fn get_http_status_code(&self) -> ResponseStatusCode {...}`
- `fn` **`from_json`** — `pub fn from_json<C>(json: C) -> Result<RequestConfig, serde_json::Error> where C: AsRef<str>, {...}`
- `fn` **`low_security`** — `pub fn low_security() -> Self {...}`
- `fn` **`high_security`** — `pub fn high_security() -> Self {...}`
- `fn` **`get_http_first_line`** — `pub(crate) fn get_http_first_line( line: &str, ) -> Result<(RequestMethod, &str, RequestVersion), RequestError> {...}`
- `fn` **`check_http_path_size`** — `pub(crate) fn check_http_path_size(path: &str, max_size: usize) -> Result<(), RequestError> {...}`
- `fn` **`get_http_query`** — `pub(crate) fn get_http_query( path: &str, query_index: Option<usize>, hash_index: Option<usize>, ) -> &str {...}`
- `fn` **`get_http_path`** — `pub(crate) fn get_http_path( path: &str, query_index: Option<usize>, hash_index: Option<usize>, ) -> RequestPath {...}`
- `fn` **`get_http_querys`** — `pub(crate) fn get_http_querys(query: &str) -> RequestQuerys {...}`
- `fn` **`check_http_header_count`** — `pub(crate) fn check_http_header_count( count: usize, max_count: usize, ) -> Result<(), RequestError> {...}`
- `fn` **`check_http_header_key_size`** — `pub(crate) fn check_http_header_key_size( key: &str, max_size: usize, ) -> Result<(), RequestError> {...}`
- `fn` **`check_http_header_value_size`** — `pub(crate) fn check_http_header_value_size( value: &str, max_size: usize, ) -> Result<(), RequestError> {...}`
- `fn` **`check_http_body_size`** — `pub(crate) fn check_http_body_size( value: &str, max_size: usize, ) -> Result<usize, RequestError> {...}`
- `fn` **`get_http_headers`** — `pub(crate) async fn get_http_headers<R>( reader: &mut R, config: &RequestConfig, ) -> Result<(RequestHeaders, RequestHost, usize), RequestError> where R: AsyncBufRe`
- `fn` **`get_http_body`** — `pub(crate) async fn get_http_body( reader: &mut BufReader<&mut TcpStream>, content_size: usize, ) -> Result<RequestBody, RequestError> {...}`
- `fn` **`try_get_query`** — `pub fn try_get_query<K>(&self, key: K) -> Option<RequestQuerysValue> where K: AsRef<str>, {...}`
- `fn` **`get_query`** — `pub fn get_query<K>(&self, key: K) -> RequestQuerysValue where K: AsRef<str>, {...}`
- `fn` **`try_get_header`** — `pub fn try_get_header<K>(&self, key: K) -> Option<RequestHeadersValue> where K: AsRef<str>, {...}`
- `fn` **`get_header`** — `pub fn get_header<K>(&self, key: K) -> RequestHeadersValue where K: AsRef<str>, {...}`
- `fn` **`try_get_header_front`** — `pub fn try_get_header_front<K>(&self, key: K) -> Option<RequestHeadersValueItem> where K: AsRef<str>, {...}`
- `fn` **`get_header_front`** — `pub fn get_header_front<K>(&self, key: K) -> RequestHeadersValueItem where K: AsRef<str>, {...}`
- `fn` **`try_get_header_back`** — `pub fn try_get_header_back<K>(&self, key: K) -> Option<RequestHeadersValueItem> where K: AsRef<str>, {...}`
- `fn` **`get_header_back`** — `pub fn get_header_back<K>(&self, key: K) -> RequestHeadersValueItem where K: AsRef<str>, {...}`
- `fn` **`try_get_header_size`** — `pub fn try_get_header_size<K>(&self, key: K) -> Option<usize> where K: AsRef<str>, {...}`
- `fn` **`get_header_size`** — `pub fn get_header_size<K>(&self, key: K) -> usize where K: AsRef<str>, {...}`
- `fn` **`get_headers_values_size`** — `pub fn get_headers_values_size(&self) -> usize {...}`
- `fn` **`get_headers_size`** — `pub fn get_headers_size(&self) -> usize {...}`
- `fn` **`has_header`** — `pub fn has_header<K>(&self, key: K) -> bool where K: AsRef<str>, {...}`
- `fn` **`has_header_value`** — `pub fn has_header_value<K, V>(&self, key: K, value: V) -> bool where K: AsRef<str>, V: AsRef<str>, {...}`
- `fn` **`try_get_cookies`** — `pub fn try_get_cookies(&self) -> Option<Cookies> {...}`
- `fn` **`get_cookies`** — `pub fn get_cookies(&self) -> Cookies {...}`
- `fn` **`try_get_cookie`** — `pub fn try_get_cookie<K>(&self, key: K) -> Option<CookieValue> where K: AsRef<str>, {...}`
- `fn` **`get_cookie`** — `pub fn get_cookie<K>(&self, key: K) -> CookieValue where K: AsRef<str>, {...}`
- `fn` **`get_upgrade_type`** — `pub fn get_upgrade_type(&self) -> UpgradeType {...}`
- `fn` **`get_body_string`** — `pub fn get_body_string(&self) -> String {...}`
- `fn` **`try_get_body_json`** — `pub fn try_get_body_json<T>(&self) -> Result<T, serde_json::Error> where T: DeserializeOwned, {...}`
- `fn` **`get_body_json`** — `pub fn get_body_json<T>(&self) -> T where T: DeserializeOwned, {...}`
- `fn` **`is_ws_upgrade_type`** — `pub fn is_ws_upgrade_type(&self) -> bool {...}`
- `fn` **`is_h2c_upgrade_type`** — `pub fn is_h2c_upgrade_type(&self) -> bool {...}`
- `fn` **`is_tls_upgrade_type`** — `pub fn is_tls_upgrade_type(&self) -> bool {...}`
- `fn` **`is_unknown_upgrade_type`** — `pub fn is_unknown_upgrade_type(&self) -> bool {...}`
- `fn` **`is_enable_keep_alive`** — `pub fn is_enable_keep_alive(&self) -> bool {...}`
- `fn` **`is_disable_keep_alive`** — `pub fn is_disable_keep_alive(&self) -> bool {...}`

### `request::struct`

- `struct` **`RequestConfig`** — `pub struct RequestConfig {`
- `struct` **`Request`** — `pub struct Request {`

### `request::type`

- `type` **`RequestMethod`** — `pub type RequestMethod = Method;`
- `type` **`RequestHost`** — `pub type RequestHost = String;`
- `type` **`RequestVersion`** — `pub type RequestVersion = HttpVersion;`
- `type` **`RequestPath`** — `pub type RequestPath = String;`
- `type` **`RequestQuerysKey`** — `pub type RequestQuerysKey = String;`
- `type` **`RequestQuerysValue`** — `pub type RequestQuerysValue = String;`
- `type` **`RequestQuerys`** — `pub type RequestQuerys = HashMapXxHash3_64<RequestQuerysKey, RequestQuerysValue>;`
- `type` **`RequestBody`** — `pub type RequestBody = Vec<u8>;`
- `type` **`RequestBodyString`** — `pub type RequestBodyString = String;`
- `type` **`RequestHeadersKey`** — `pub type RequestHeadersKey = String;`
- `type` **`RequestHeadersValueItem`** — `pub type RequestHeadersValueItem = String;`
- `type` **`RequestHeadersValue`** — `pub type RequestHeadersValue = VecDeque<RequestHeadersValueItem>;`
- `type` **`RequestHeaders`** — `pub type RequestHeaders = HashMapXxHash3_64<RequestHeadersKey, RequestHeadersValue>;`
- `type` **`RwLockReadGuardRequest`** — `pub type RwLockReadGuardRequest<'a> = RwLockReadGuard<'a, Request>;`
- `type` **`RwLockWriteGuardRequest`** — `pub type RwLockWriteGuardRequest<'a> = RwLockWriteGuard<'a, Request>;`

### `response::enum`

- `enum` **`ResponseError`** — `pub enum ResponseError {`

### `response::impl`

- `fn` **`try_get_header`** — `pub fn try_get_header<K>(&self, key: K) -> Option<ResponseHeadersValue> where K: AsRef<str>, {...}`
- `fn` **`get_header`** — `pub fn get_header<K>(&self, key: K) -> ResponseHeadersValue where K: AsRef<str>, {...}`
- `fn` **`try_get_header_front`** — `pub fn try_get_header_front<K>(&self, key: K) -> Option<ResponseHeadersValueItem> where K: AsRef<str>, {...}`
- `fn` **`get_header_front`** — `pub fn get_header_front<K>(&self, key: K) -> ResponseHeadersValueItem where K: AsRef<str>, {...}`
- `fn` **`try_get_header_back`** — `pub fn try_get_header_back<K>(&self, key: K) -> Option<ResponseHeadersValueItem> where K: AsRef<str>, {...}`
- `fn` **`get_header_back`** — `pub fn get_header_back<K>(&self, key: K) -> ResponseHeadersValueItem where K: AsRef<str>, {...}`
- `fn` **`has_header`** — `pub fn has_header<K>(&self, key: K) -> bool where K: AsRef<str>, {...}`
- `fn` **`has_header_value`** — `pub fn has_header_value<K, V>(&self, key: K, value: V) -> bool where K: AsRef<str>, V: AsRef<str>, {...}`
- `fn` **`get_headers_size`** — `pub fn get_headers_size(&self) -> usize {...}`
- `fn` **`try_get_header_size`** — `pub fn try_get_header_size<K>(&self, key: K) -> Option<usize> where K: AsRef<str>, {...}`
- `fn` **`get_header_size`** — `pub fn get_header_size<K>(&self, key: K) -> usize where K: AsRef<str>, {...}`
- `fn` **`get_headers_values_size`** — `pub fn get_headers_values_size(&self) -> usize {...}`
- `fn` **`get_body_string`** — `pub fn get_body_string(&self) -> String {...}`
- `fn` **`try_get_body_json`** — `pub fn try_get_body_json<T>(&self) -> Result<T, serde_json::Error> where T: DeserializeOwned, {...}`
- `fn` **`get_body_json`** — `pub fn get_body_json<T>(&self) -> T where T: DeserializeOwned, {...}`
- `fn` **`set_header`** — `pub fn set_header<K, V>(&mut self, key: K, value: V) -> &mut Self where K: AsRef<str>, V: AsRef<str>, {...}`
- `fn` **`add_header`** — `pub fn add_header<K, V>(&mut self, key: K, value: V) -> &mut Self where K: AsRef<str>, V: AsRef<str>, {...}`
- `fn` **`remove_header`** — `pub fn remove_header<K>(&mut self, key: K) -> &mut Self where K: AsRef<str>, {...}`
- `fn` **`remove_header_value`** — `pub fn remove_header_value<K, V>(&mut self, key: K, value: V) -> &mut Self where K: AsRef<str>, V: AsRef<str>, {...}`
- `fn` **`clear_headers`** — `pub fn clear_headers(&mut self) -> &mut Self {...}`
- `fn` **`try_get_cookies`** — `pub fn try_get_cookies(&self) -> Option<Cookies> {...}`
- `fn` **`get_cookies`** — `pub fn get_cookies(&self) -> Cookies {...}`
- `fn` **`try_get_cookie`** — `pub fn try_get_cookie<K>(&self, key: K) -> Option<CookieValue> where K: AsRef<str>, {...}`
- `fn` **`get_cookie`** — `pub fn get_cookie<K>(&self, key: K) -> CookieValue where K: AsRef<str>, {...}`
- `fn` **`build`** — `pub fn build(&mut self) -> ResponseData {...}`

### `response::struct`

- `struct` **`Response`** — `pub struct Response {`

### `response::type`

- `type` **`ResponseBody`** — `pub type ResponseBody = Vec<u8>;`
- `type` **`ResponseBodyString`** — `pub type ResponseBodyString = String;`
- `type` **`ResponseHeadersKey`** — `pub type ResponseHeadersKey = String;`
- `type` **`ResponseHeadersValueItem`** — `pub type ResponseHeadersValueItem = String;`
- `type` **`ResponseHeadersValue`** — `pub type ResponseHeadersValue = VecDeque<ResponseHeadersValueItem>;`
- `type` **`ResponseHeaders`** — `pub type ResponseHeaders = HashMapXxHash3_64<ResponseHeadersKey, ResponseHeadersValue>;`
- `type` **`ResponseVersion`** — `pub type ResponseVersion = HttpVersion;`
- `type` **`ResponseStatusCode`** — `pub type ResponseStatusCode = usize;`
- `type` **`ResponseReasonPhrase`** — `pub type ResponseReasonPhrase = String;`
- `type` **`ResponseData`** — `pub type ResponseData = Vec<u8>;`
- `type` **`ResponseDataString`** — `pub type ResponseDataString = String;`
- `type` **`RwLockReadGuardResponse`** — `pub type RwLockReadGuardResponse<'a> = RwLockReadGuard<'a, Response>;`
- `type` **`RwLockWriteGuardResponse`** — `pub type RwLockWriteGuardResponse<'a> = RwLockWriteGuard<'a, Response>;`

### `status::enum`

- `enum` **`Status`** — `pub enum Status {`

### `status::impl`

- `fn` **`is_continue`** — `pub fn is_continue(&self) -> bool {...}`
- `fn` **`is_reject`** — `pub fn is_reject(&self) -> bool {...}`

### `stream::impl`

- `fn` **`is_keep_alive`** — `pub fn is_keep_alive(&self, keep_alive: bool) -> bool {...}`
- `fn` **`try_get_http_request`** — `pub async fn try_get_http_request(&mut self) -> Result<Request, RequestError> {...}`
- `fn` **`try_get_websocket_request`** — `pub async fn try_get_websocket_request(&mut self) -> Result<RequestBody, RequestError> {...}`
- `fn` **`get_websocket_from_stream`** — `pub(crate) async fn get_websocket_from_stream( &mut self, buffer: &mut [u8], duration_opt: Option<Duration>, is_client_response: &mut bool, ) -> Result<Option<u`
- `fn` **`try_send`** — `pub async fn try_send<D>(&mut self, data: D) -> Result<(), ResponseError> where D: AsRef<[u8]>, {...}`
- `fn` **`send`** — `pub async fn send<D>(&mut self, data: D) where D: AsRef<[u8]>, {...}`
- `fn` **`try_send_list`** — `pub async fn try_send_list<I, D>(&mut self, data_iter: I) -> Result<(), ResponseError> where I: IntoIterator<Item = D>, D: AsRef<[u8]>, {...}`
- `fn` **`send_list`** — `pub async fn send_list<I, D>(&mut self, data_iter: I) where I: IntoIterator<Item = D>, D: AsRef<[u8]>, {...}`
- `fn` **`try_flush`** — `pub async fn try_flush(&mut self) -> Result<(), ResponseError> {...}`
- `fn` **`flush`** — `pub async fn flush(&mut self) {...}`

### `stream::struct`

- `struct` **`Stream`** — `pub struct Stream {`

### `stream::type`

- `type` **`ArcStream`** — `pub type ArcStream = Arc<TcpStream>;`
- `type` **`SocketHost`** — `pub type SocketHost = IpAddr;`
- `type` **`SocketPort`** — `pub type SocketPort = u16;`

### `task::impl`

- `fn` **`new`** — `pub fn new(worker_count: usize) -> Self {...}`
- `fn` **`try_spawn_local`** — `pub fn try_spawn_local<F>(&self, index_opt: Option<usize>, hook: F) -> bool where F: Future<Output = ()> + Send + 'static, {...}`
- `fn` **`shutdown`** — `pub fn shutdown(&self) {...}`

### `task::struct`

- `struct` **`Task`** — `pub struct Task {`

### `task::type`

- `type` **`AsyncTask`** — `pub type AsyncTask = Pin<Box<dyn Future<Output = ()> + Send + 'static>>;`

### `upgrade_type::enum`

- `enum` **`UpgradeType`** — `pub enum UpgradeType {`

### `upgrade_type::impl`

- `fn` **`is_ws`** — `pub fn is_ws(&self) -> bool {...}`
- `fn` **`is_h2c`** — `pub fn is_h2c(&self) -> bool {...}`
- `fn` **`is_tls`** — `pub fn is_tls(&self) -> bool {...}`
- `fn` **`is_unknown`** — `pub fn is_unknown(&self) -> bool {...}`

### `websocket_frame::enum`

- `enum` **`WebSocketOpcode`** — `pub enum WebSocketOpcode {`

### `websocket_frame::impl`

- `fn` **`from_u8`** — `pub fn from_u8(opcode: u8) -> Self {...}`
- `fn` **`to_u8`** — `pub fn to_u8(&self) -> u8 {...}`
- `fn` **`is_control`** — `pub fn is_control(&self) -> bool {...}`
- `fn` **`is_data`** — `pub fn is_data(&self) -> bool {...}`
- `fn` **`is_continuation`** — `pub fn is_continuation(&self) -> bool {...}`
- `fn` **`is_text`** — `pub fn is_text(&self) -> bool {...}`
- `fn` **`is_binary`** — `pub fn is_binary(&self) -> bool {...}`
- `fn` **`is_close`** — `pub fn is_close(&self) -> bool {...}`
- `fn` **`is_ping`** — `pub fn is_ping(&self) -> bool {...}`
- `fn` **`is_pong`** — `pub fn is_pong(&self) -> bool {...}`
- `fn` **`is_reserved`** — `pub fn is_reserved(&self) -> bool {...}`
- `fn` **`decode_ws_frame`** — `pub fn decode_ws_frame<D>(data: D) -> Option<(WebSocketFrame, usize)> where D: AsRef<[u8]>, {...}`
- `fn` **`create_frame_list`** — `pub fn create_frame_list<D>(data: D) -> Vec<ResponseBody> where D: AsRef<[u8]>, {...}`
- `fn` **`sha1`** — `pub fn sha1<D>(data: D) -> [u8; 20] where D: AsRef<[u8]>, {...}`
- `fn` **`try_generate_accept_key`** — `pub fn try_generate_accept_key<K>(key: K) -> Option<String> where K: AsRef<str>, {...}`
- `fn` **`generate_accept_key`** — `pub fn generate_accept_key<K>(key: K) -> String where K: AsRef<str>, {...}`
- `fn` **`try_base64_encode`** — `pub fn try_base64_encode<D>(data: D) -> Option<String> where D: AsRef<[u8]>, {...}`
- `fn` **`base64_encode`** — `pub fn base64_encode<D>(data: D) -> String where D: AsRef<[u8]>, {...}`
- `fn` **`is_continuation_opcode`** — `pub fn is_continuation_opcode(&self) -> bool {...}`
- `fn` **`is_text_opcode`** — `pub fn is_text_opcode(&self) -> bool {...}`
- `fn` **`is_binary_opcode`** — `pub fn is_binary_opcode(&self) -> bool {...}`
- `fn` **`is_close_opcode`** — `pub fn is_close_opcode(&self) -> bool {...}`
- `fn` **`is_ping_opcode`** — `pub fn is_ping_opcode(&self) -> bool {...}`
- `fn` **`is_pong_opcode`** — `pub fn is_pong_opcode(&self) -> bool {...}`
- `fn` **`is_reserved_opcode`** — `pub fn is_reserved_opcode(&self) -> bool {...}`
- `fn` **`build_full_frame`** — `pub(crate) fn build_full_frame( &self, full_frame: &mut Vec<u8>, ) -> Result<Option<RequestBody>, RequestError> {...}`

### `websocket_frame::struct`

- `struct` **`WebSocketFrame`** — `pub struct WebSocketFrame {`
