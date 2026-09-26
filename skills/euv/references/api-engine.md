# euv-engine 完整 pub API(渲染引擎)

Source: `engine/src/` — auto-extracted from `pub` declarations.

Re-exported at crate root via `engine/src/lib.rs` `pub use` 链。`Engine` 是零大小命名空间 facade,`EngineHandle` 是 stateful 实体。

### `asset::enum`

- `enum` **`AssetType`** — `pub enum AssetType {`
- `enum` **`AssetState`** — `pub enum AssetState {`

### `asset::impl`

- `fn` **`get_state`** — `pub fn get_state<U>(&self, url: U) -> Option<AssetState> where U: AsRef<str>, {...}`
- `fn` **`get_image`** — `pub fn get_image<U>(&self, url: U) -> Option<HtmlImageElement> where U: AsRef<str>, {...}`
- `fn` **`is_all_loaded`** — `pub fn is_all_loaded(&self) -> bool {...}`
- `fn` **`loaded_count`** — `pub fn loaded_count(&self) -> usize {...}`
- `fn` **`clear`** — `pub fn clear(&mut self) {...}`
- `fn` **`load_image`** — `pub fn load_image(&mut self, url: String) {...}`
- `fn` **`is_all_loaded`** — `pub fn is_all_loaded(&self) -> bool {...}`
- `fn` **`get_image`** — `pub fn get_image<U>(&self, url: U) -> Option<HtmlImageElement> where U: AsRef<str>, {...}`
- `fn` **`progress`** — `pub fn progress(&self) -> f64 {...}`
- `fn` **`create_image_element`** — `pub fn create_image_element<U>(url: U) -> Option<HtmlImageElement> where U: AsRef<str>, {...}`

### `asset::struct`

- `struct` **`AssetEntry`** — `pub struct AssetEntry {`
- `struct` **`AssetCache`** — `pub struct AssetCache {`
- `struct` **`AssetLoader`** — `pub struct AssetLoader {`

### `asset::type`

- `type` **`AssetClosures`** — `pub type AssetClosures = Rc<EngineCell<Vec<Closure<dyn FnMut()>>>>;`

### `audio::enum`

- `enum` **`AudioPlayState`** — `pub enum AudioPlayState {`

### `audio::impl`

- `fn` **`create`** — `pub fn create() -> Option<GameAudioContext> {...}`
- `fn` **`apply_master_volume`** — `pub fn apply_master_volume(&self, volume: f64) {...}`
- `fn` **`resume`** — `pub fn resume(&self) {...}`
- `fn` **`suspend`** — `pub fn suspend(&self) {...}`
- `fn` **`close`** — `pub fn close(&self) {...}`
- `fn` **`sample_rate`** — `pub fn sample_rate(&self) -> f64 {...}`
- `fn` **`current_time`** — `pub fn current_time(&self) -> f64 {...}`
- `fn` **`create`** — `pub fn create(buffer: AudioBuffer, name: String) -> AudioClip {...}`
- `fn` **`play`** — `pub fn play(&mut self, audio_context: &GameAudioContext) {...}`
- `fn` **`stop`** — `pub fn stop(&mut self) {...}`
- `fn` **`update_looping`** — `pub fn update_looping(&mut self, looping: bool) {...}`
- `fn` **`update_volume`** — `pub fn update_volume(&mut self, volume: f64) {...}`
- `fn` **`update_playback_rate`** — `pub fn update_playback_rate(&mut self, rate: f64) {...}`
- `fn` **`duration`** — `pub fn duration(&self) -> f64 {...}`
- `fn` **`channel_count`** — `pub fn channel_count(&self) -> u32 {...}`

### `audio::struct`

- `struct` **`GameAudioContext`** — `pub struct GameAudioContext {`
- `struct` **`AudioClip`** — `pub struct AudioClip {`

### `cell::impl`

- `fn` **`get_inner`** — `pub fn get_inner(&self) -> &UnsafeCell<T> {...}`
- `fn` **`get_inner`** — `pub fn get_inner(&self) -> &UnsafeCell<Option<T>> {...}`
- `fn` **`set_inner`** — `pub fn set_inner(&mut self, val: UnsafeCell<Option<T>>) -> UnsafeCell<Option<T>> {...}`
- `fn` **`new`** — `pub fn new(value: T) -> Self where T: Sized, {...}`
- `fn` **`get_mut`** — `pub fn get_mut(&self) -> &'static mut T {...}`
- `fn` **`get`** — `pub fn get(&self) -> &'static T {...}`
- `fn` **`new`** — `pub const fn new() -> Self {...}`
- `fn` **`try_get`** — `pub fn try_get(&self) -> Option<&'static T> {...}`
- `fn` **`try_get_mut`** — `pub fn try_get_mut(&self) -> Option<&'static mut T> {...}`
- `fn` **`try_set`** — `pub fn try_set(&self, value: T) -> Result<(), T> {...}`
- `fn` **`try_take`** — `pub fn try_take(&self) -> Option<T> {...}`
- `fn` **`try_replace`** — `pub fn try_replace(&self, value: T) -> Option<T> {...}`

### `cell::struct`

- `struct` **`EngineCell`** — `pub struct EngineCell<T: ?Sized> {`
- `struct` **`MaybeEngineCell`** — `pub struct MaybeEngineCell<T> {`

### `collider::enum`

- `enum` **`ColliderShape`** — `pub enum ColliderShape {`
- `enum` **`ColliderShape3D`** — `pub enum ColliderShape3D {`

### `collider::impl`

- `fn` **`from_center`** — `pub fn from_center(center: Vector2D, width: f64, height: f64) -> AabbCollider {...}`
- `fn` **`collide_with_aabb`** — `pub fn collide_with_aabb(&self, other: &AabbCollider) -> Option<CollisionResult> {...}`
- `fn` **`collide_with_circle`** — `pub fn collide_with_circle(&self, circle: &CircleCollider) -> Option<CollisionResult> {...}`
- `fn` **`from_center`** — `pub fn from_center(center: Vector2D, radius: f64) -> CircleCollider {...}`
- `fn` **`collide_with_circle`** — `pub fn collide_with_circle(&self, other: &CircleCollider) -> Option<CollisionResult> {...}`
- `fn` **`from_center`** — `pub fn from_center(center: Vector3D, width: f64, height: f64, depth: f64) -> AabbCollider3D {...}`
- `fn` **`collide_with_aabb`** — `pub fn collide_with_aabb(&self, other: &AabbCollider3D) -> Option<CollisionResult3D> {...}`
- `fn` **`collide_with_sphere`** — `pub fn collide_with_sphere(&self, sphere: &SphereCollider3D) -> Option<CollisionResult3D> {...}`
- `fn` **`from_center`** — `pub fn from_center(center: Vector3D, radius: f64) -> SphereCollider3D {...}`
- `fn` **`collide_with_sphere`** — `pub fn collide_with_sphere(&self, other: &SphereCollider3D) -> Option<CollisionResult3D> {...}`
- `fn` **`broad_phase`** — `pub fn broad_phase(a: AABB3D, b: AABB3D) -> bool {...}`

### `collider::struct`

- `struct` **`CollisionResult`** — `pub struct CollisionResult {`
- `struct` **`AabbCollider`** — `pub struct AabbCollider {`
- `struct` **`CircleCollider`** — `pub struct CircleCollider {`
- `struct` **`CollisionResult3D`** — `pub struct CollisionResult3D {`
- `struct` **`AabbCollider3D`** — `pub struct AabbCollider3D {`
- `struct` **`SphereCollider3D`** — `pub struct SphereCollider3D {`

### `collider::trait`

- `trait` **`Collider`** — `pub trait Collider {`
- `trait` **`Collider3D`** — `pub trait Collider3D {`

### `config::enum`

- `enum` **`RenderBackendType`** — `pub(crate) enum RenderBackendType {`
- `enum` **`GpuPowerPreference`** — `pub enum GpuPowerPreference {`

### `config::impl`

- `fn` **`canvas2d`** — `pub fn canvas2d<S>(canvas_selector: S, width: f64, height: f64) -> RenderConfig where S: AsRef<str>, {...}`
- `fn` **`webgpu`** — `pub fn webgpu<S>(canvas_selector: S, width: f64, height: f64) -> RenderConfig where S: AsRef<str>, {...}`
- `fn` **`webgl`** — `pub fn webgl<S>(canvas_selector: S, width: f64, height: f64) -> RenderConfig where S: AsRef<str>, {...}`
- `fn` **`create`** — `pub fn create(render: RenderConfig) -> EngineConfig {...}`
- `fn` **`with_scheduler`** — `pub fn with_scheduler(mut self, scheduler: SchedulerConfig) -> EngineConfig {...}`
- `fn` **`to_web_sys_string`** — `pub fn to_web_sys_string(&self) -> &'static str {...}`

### `config::struct`

- `struct` **`RenderConfig`** — `pub struct RenderConfig {`
- `struct` **`EngineConfig`** — `pub struct EngineConfig {`

### `easing::enum`

- `enum` **`Easing`** — `pub enum Easing {`

### `easing::impl`

- `fn` **`evaluate`** — `pub fn evaluate(&self, t: f64) -> f64 {...}`
- `fn` **`interpolate`** — `pub fn interpolate(&self, start: f64, end: f64, t: f64) -> f64 {...}`

### `engine::impl`

- `fn` **`new_handle`** — `pub fn new_handle(config: EngineConfig) -> EngineHandle {...}`
- `fn` **`run`** — `pub async fn run(config: EngineConfig, handler: TickHandlerRc) -> EngineHandle {...}`
- `fn` **`default_config`** — `pub fn default_config() -> EngineConfig {...}`
- `fn` **`canvas_renderer`** — `pub fn canvas_renderer(config: &RenderConfig) -> Option<CanvasRenderer> {...}`
- `fn` **`webgpu_renderer`** — `pub async fn webgpu_renderer(config: &RenderConfig) -> Result<WebGpuRenderer, WebGpuInitError> {...}`
- `fn` **`webgl_renderer`** — `pub fn webgl_renderer(config: &RenderConfig) -> Result<WebGlRenderer, WebGlInitError> {...}`
- `fn` **`init_canvas`** — `pub fn init_canvas(&mut self) -> bool {...}`
- `fn` **`init_webgpu`** — `pub async fn init_webgpu(&mut self) -> Result<WebGpuRenderer, WebGpuInitError> {...}`
- `fn` **`init_webgl`** — `pub fn init_webgl(&mut self) -> Result<WebGlRenderer, WebGlInitError> {...}`
- `fn` **`register_input`** — `pub fn register_input(&mut self) -> Option<InputStateCell> {...}`
- `fn` **`start`** — `pub fn start(&mut self, handler: TickHandlerRc) {...}`
- `fn` **`stop`** — `pub fn stop(&self) {...}`
- `fn` **`is_running`** — `pub fn is_running(&self) -> bool {...}`

### `engine::struct`

- `struct` **`Engine`** — `pub struct Engine;`
- `struct` **`EngineHandle`** — `pub struct EngineHandle {`

### `entity::enum`

- `enum` **`EntityEvent`** — `pub enum EntityEvent {`

### `entity::impl`

- `fn` **`generate_id`** — `pub fn generate_id() -> u64 {...}`
- `fn` **`create`** — `pub fn create<N>(name: N) -> Entity where N: AsRef<str>, {...}`
- `fn` **`create_at`** — `pub fn create_at(position: Vector2D) -> Entity {...}`
- `fn` **`add_component`** — `pub fn add_component(&mut self, component: ComponentRc) {...}`
- `fn` **`remove_component_by_name`** — `pub fn remove_component_by_name<N>(&mut self, name: N) -> Option<ComponentRc> where N: AsRef<str>, {...}`
- `fn` **`get_component_by_name`** — `pub fn get_component_by_name<N>(&self, name: N) -> Option<ComponentRc> where N: AsRef<str>, {...}`
- `fn` **`update`** — `pub fn update(&mut self, delta_time: f64) {...}`
- `fn` **`render`** — `pub fn render(&self, draw_list: &mut DrawList) {...}`
- `fn` **`destroy`** — `pub fn destroy(&mut self) {...}`
- `fn` **`add_tag`** — `pub fn add_tag(&mut self, tag: String) {...}`
- `fn` **`has_tag`** — `pub fn has_tag<T>(&self, tag: T) -> bool where T: AsRef<str>, {...}`
- `fn` **`create`** — `pub fn create() -> EventBus {...}`
- `fn` **`subscribe`** — `pub fn subscribe(&mut self, event_name: String, handler: EventHandler) {...}`
- `fn` **`emit`** — `pub fn emit(&self, event: &EntityEvent) {...}`
- `fn` **`unsubscribe_all`** — `pub fn unsubscribe_all<E>(&mut self, event_name: E) where E: AsRef<str>, {...}`
- `fn` **`handler_count`** — `pub fn handler_count<E>(&self, event_name: E) -> usize where E: AsRef<str>, {...}`

### `entity::static`

- `static` **`NEXT_ENTITY_ID`** — `pub(crate) static NEXT_ENTITY_ID: AtomicU64 = AtomicU64::new(1);`

### `entity::struct`

- `struct` **`Entity`** — `pub struct Entity {`
- `struct` **`EventBus`** — `pub struct EventBus {`

### `entity::trait`

- `trait` **`Lifecycle`** — `pub trait Lifecycle {`
- `trait` **`Component`** — `pub trait Component: Lifecycle {`

### `entity::type`

- `type` **`ComponentRc`** — `pub type ComponentRc = Rc<EngineCell<dyn Component>>;`
- `type` **`EntityRc`** — `pub type EntityRc = Rc<EngineCell<Entity>>;`
- `type` **`EventHandler`** — `pub type EventHandler = Rc<dyn Fn(&EntityEvent)>;`
- `type` **`EventHandlers`** — `pub type EventHandlers = HashMap<String, Vec<EventHandler>>;`

### `input::enum`

- `enum` **`MouseButton`** — `pub enum MouseButton {`
- `enum` **`InputAction`** — `pub enum InputAction {`

### `input::impl`

- `fn` **`extract_key_code`** — `pub fn extract_key_code(event: &Event) -> String {...}`
- `fn` **`extract_mouse_button`** — `pub fn extract_mouse_button(event: &Event) -> MouseButton {...}`
- `fn` **`extract_mouse_position`** — `pub fn extract_mouse_position(event: &Event) -> Vector2D {...}`
- `fn` **`attach`** — `pub fn attach( state_cell: InputStateCell, window: &Window, pointer_target: &EventTarget, ) -> InputStateCell {...}`
- `fn` **`attach_keyboard`** — `pub fn attach_keyboard(state_cell: &InputStateCell, window: &Window) {...}`
- `fn` **`attach_pointer`** — `pub fn attach_pointer(state_cell: &InputStateCell, target: &EventTarget) {...}`
- `fn` **`press_key`** — `pub fn press_key(&mut self, key_code: String) {...}`
- `fn` **`release_key`** — `pub fn release_key(&mut self, key_code: String) {...}`
- `fn` **`is_key_pressed`** — `pub fn is_key_pressed<K>(&self, key_code: K) -> bool where K: AsRef<str>, {...}`
- `fn` **`is_key_held`** — `pub fn is_key_held<K>(&self, key_code: K) -> bool where K: AsRef<str>, {...}`
- `fn` **`is_key_released`** — `pub fn is_key_released<K>(&self, key_code: K) -> bool where K: AsRef<str>, {...}`
- `fn` **`press_mouse_button`** — `pub fn press_mouse_button(&mut self, button: MouseButton, position: Vector2D) {...}`
- `fn` **`release_mouse_button`** — `pub fn release_mouse_button(&mut self, button: MouseButton) {...}`
- `fn` **`update_mouse_position`** — `pub fn update_mouse_position(&mut self, position: Vector2D) {...}`
- `fn` **`is_mouse_button_pressed`** — `pub fn is_mouse_button_pressed(&self, button: MouseButton) -> bool {...}`
- `fn` **`is_mouse_button_held`** — `pub fn is_mouse_button_held(&self, button: MouseButton) -> bool {...}`
- `fn` **`update_touch`** — `pub fn update_touch(&mut self, identifier: i32, position: Vector2D) {...}`
- `fn` **`start_touch`** — `pub fn start_touch(&mut self, identifier: i32, position: Vector2D) {...}`
- `fn` **`end_touch`** — `pub fn end_touch(&mut self, identifier: i32) {...}`
- `fn` **`primary_touch_position`** — `pub fn primary_touch_position(&self) -> Option<Vector2D> {...}`
- `fn` **`end_frame`** — `pub fn end_frame(&mut self) {...}`

### `input::struct`

- `struct` **`Input`** — `pub struct Input;`
- `struct` **`InputState`** — `pub struct InputState {`

### `input::type`

- `type` **`KeyStateSet`** — `pub type KeyStateSet = HashSet<String>;`
- `type` **`TouchPointMap`** — `pub type TouchPointMap = HashMap<i32, Vector2D>;`
- `type` **`InputStateCell`** — `pub type InputStateCell = Rc<EngineCell<InputState>>;`

### `lighting::enum`

- `enum` **`LightType`** — `pub enum LightType {`
- `enum` **`MaterialKind`** — `pub enum MaterialKind {`

### `lighting::fn`

- `fn` **`compute_lambert`** — `pub fn compute_lambert(light: &Light, normal: Vector3D, material: &Material) -> Vector3D {...}`
- `fn` **`compute_phong`** — `pub fn compute_phong( light: &Light, normal: Vector3D, view_dir: Vector3D, material: &Material, ) -> Vector3D {...}`
- `fn` **`apply_falloff`** — `pub fn apply_falloff(distance: f64, falloff: f64) -> f64 {...}`
- `fn` **`ray_sphere_intersect`** — `pub fn ray_sphere_intersect( origin: Vector3D, dir: Vector3D, center: Vector3D, radius: f64, ) -> Option<(f64, Vector3D)> {...}`
- `fn` **`ray_aabb_intersect`** — `pub fn ray_aabb_intersect( origin: Vector3D, dir: Vector3D, aabb_min: Vector3D, aabb_max: Vector3D, ) -> Option<(f64, f64, Vector3D)> {...}`
- `fn` **`soft_shadow_factor`** — `pub fn soft_shadow_factor( origin: Vector3D, light_pos: Vector3D, occluders: &[(Vector3D, f64)], ) -> f64 {...}`

### `lighting::impl`

- `fn` **`new_directional`** — `pub fn new_directional(direction: Vector3D, color: Vector3D) -> Light {...}`
- `fn` **`new_point`** — `pub fn new_point(position: Vector3D, color: Vector3D, intensity: f64) -> Light {...}`
- `fn` **`new_spot`** — `pub fn new_spot( position: Vector3D, direction: Vector3D, color: Vector3D, intensity: f64, half_angle_rad: f64, ) -> Light {...}`
- `fn` **`lambert`** — `pub fn lambert(albedo: Vector3D) -> Material {...}`
- `fn` **`phong`** — `pub fn phong(albedo: Vector3D, specular: f64, shininess: f64) -> Material {...}`
- `fn` **`emissive`** — `pub fn emissive(color: Vector3D) -> Material {...}`
- `fn` **`with_eye`** — `pub fn with_eye(eye: Vector3D) -> LightingUniforms {...}`
- `fn` **`add_light`** — `pub fn add_light(&mut self, light: Light) {...}`
- `fn` **`shade`** — `pub fn shade( &self, position: Vector3D, normal: Vector3D, material: &Material, occluders: &[(Vector3D, f64)], ) -> Vector3D {...}`

### `lighting::struct`

- `struct` **`Light`** — `pub struct Light {`
- `struct` **`Material`** — `pub struct Material {`
- `struct` **`LightingUniforms`** — `pub struct LightingUniforms {`

### `math::impl`

- `fn` **`clamp`** — `pub fn clamp(value: f64, min: f64, max: f64) -> f64 {...}`
- `fn` **`lerp`** — `pub fn lerp(start: f64, end: f64, factor: f64) -> f64 {...}`
- `fn` **`deg_to_rad`** — `pub fn deg_to_rad(degrees: f64) -> f64 {...}`
- `fn` **`rad_to_deg`** — `pub fn rad_to_deg(radians: f64) -> f64 {...}`
- `fn` **`normalize_angle`** — `pub fn normalize_angle(radians: f64) -> f64 {...}`
- `fn` **`angle_delta`** — `pub fn angle_delta(from: f64, to: f64) -> f64 {...}`
- `fn` **`lerp_angle`** — `pub fn lerp_angle(from: f64, to: f64, factor: f64) -> f64 {...}`
- `fn` **`distance`** — `pub fn distance(a: Vector2D, b: Vector2D) -> f64 {...}`
- `fn` **`distance_squared`** — `pub fn distance_squared(a: Vector2D, b: Vector2D) -> f64 {...}`
- `fn` **`smoothstep`** — `pub fn smoothstep(edge_min: f64, edge_max: f64, value: f64) -> f64 {...}`
- `fn` **`approach`** — `pub fn approach(current: f64, target: f64, max_delta: f64) -> f64 {...}`
- `fn` **`sign`** — `pub fn sign(value: f64) -> f64 {...}`
- `fn` **`wrap`** — `pub fn wrap(value: f64, max: f64) -> f64 {...}`
- `fn` **`sign_or_positive`** — `pub fn sign_or_positive(value: f64) -> f64 {...}`
- `fn` **`distance_3d`** — `pub fn distance_3d(a: Vector3D, b: Vector3D) -> f64 {...}`
- `fn` **`distance_squared_3d`** — `pub fn distance_squared_3d(a: Vector3D, b: Vector3D) -> f64 {...}`
- `fn` **`zero`** — `pub fn zero() -> Vector2D {...}`
- `fn` **`right`** — `pub fn right() -> Vector2D {...}`
- `fn` **`up`** — `pub fn up() -> Vector2D {...}`
- `fn` **`from_angle`** — `pub fn from_angle(radians: f64) -> Vector2D {...}`
- `fn` **`magnitude`** — `pub fn magnitude(&self) -> f64 {...}`
- `fn` **`magnitude_squared`** — `pub fn magnitude_squared(&self) -> f64 {...}`
- `fn` **`normalized`** — `pub fn normalized(&self) -> Vector2D {...}`
- `fn` **`normalize`** — `pub fn normalize(&mut self) {...}`
- `fn` **`dot`** — `pub fn dot(&self, other: Vector2D) -> f64 {...}`
- `fn` **`cross`** — `pub fn cross(&self, other: Vector2D) -> f64 {...}`
- `fn` **`perp`** — `pub fn perp(&self) -> Vector2D {...}`
- `fn` **`angle`** — `pub fn angle(&self) -> f64 {...}`
- `fn` **`angle_to`** — `pub fn angle_to(&self, other: Vector2D) -> f64 {...}`
- `fn` **`rotated`** — `pub fn rotated(&self, radians: f64) -> Vector2D {...}`
- `fn` **`rotate`** — `pub fn rotate(&mut self, radians: f64) {...}`
- `fn` **`distance_to`** — `pub fn distance_to(&self, other: Vector2D) -> f64 {...}`
- `fn` **`distance_squared_to`** — `pub fn distance_squared_to(&self, other: Vector2D) -> f64 {...}`
- `fn` **`direction_to`** — `pub fn direction_to(&self, other: Vector2D) -> Vector2D {...}`
- `fn` **`lerp`** — `pub fn lerp(&self, other: Vector2D, factor: f64) -> Vector2D {...}`
- `fn` **`scale`** — `pub fn scale(&mut self, scalar: f64) {...}`
- `fn` **`scaled`** — `pub fn scaled(&self, scalar: f64) -> Vector2D {...}`
- `fn` **`from_center`** — `pub fn from_center(center: Vector2D, width: f64, height: f64) -> Rect {...}`
- `fn` **`center`** — `pub fn center(&self) -> Vector2D {...}`
- `fn` **`min`** — `pub fn min(&self) -> Vector2D {...}`
- `fn` **`max`** — `pub fn max(&self) -> Vector2D {...}`
- `fn` **`size`** — `pub fn size(&self) -> Vector2D {...}`
- `fn` **`contains`** — `pub fn contains(&self, point: Vector2D) -> bool {...}`
- `fn` **`intersects`** — `pub fn intersects(&self, other: Rect) -> bool {...}`
- `fn` **`broad_phase_alias`** — `pub fn broad_phase_alias(a: Rect, b: Rect) -> bool {...}`
- `fn` **`intersection`** — `pub fn intersection(&self, other: Rect) -> Option<Rect> {...}`
- `fn` **`contains`** — `pub fn contains(&self, point: Vector2D) -> bool {...}`
- `fn` **`intersects`** — `pub fn intersects(&self, other: Circle) -> bool {...}`
- `fn` **`circumference`** — `pub fn circumference(&self) -> f64 {...}`
- `fn` **`area`** — `pub fn area(&self) -> f64 {...}`
- `fn` **`identity`** — `pub fn identity() -> Transform2D {...}`
- `fn` **`translate`** — `pub fn translate(&mut self, offset: Vector2D) {...}`
- `fn` **`rotate`** — `pub fn rotate(&mut self, radians: f64) {...}`
- `fn` **`scale_by`** — `pub fn scale_by(&mut self, factors: Vector2D) {...}`
- `fn` **`apply_to_point`** — `pub fn apply_to_point(&self, point: Vector2D) -> Vector2D {...}`
- `fn` **`from_rgb`** — `pub fn from_rgb(red: u8, green: u8, blue: u8) -> Color {...}`
- `fn` **`to_css_rgba`** — `pub fn to_css_rgba(&self) -> String {...}`
- `fn` **`write_css_rgba`** — `pub fn write_css_rgba(&self, buffer: &mut String) {...}`
- `fn` **`black`** — `pub fn black() -> Color {...}`
- `fn` **`white`** — `pub fn white() -> Color {...}`
- `fn` **`transparent`** — `pub fn transparent() -> Color {...}`
- `fn` **`lerp`** — `pub fn lerp(&self, other: Color, factor: f64) -> Color {...}`
- `fn` **`zero`** — `pub fn zero() -> Vector3D {...}`
- `fn` **`right`** — `pub fn right() -> Vector3D {...}`
- `fn` **`up`** — `pub fn up() -> Vector3D {...}`
- `fn` **`forward`** — `pub fn forward() -> Vector3D {...}`
- `fn` **`magnitude`** — `pub fn magnitude(&self) -> f64 {...}`
- `fn` **`magnitude_squared`** — `pub fn magnitude_squared(&self) -> f64 {...}`
- `fn` **`normalized`** — `pub fn normalized(&self) -> Vector3D {...}`
- `fn` **`normalize`** — `pub fn normalize(&mut self) {...}`
- `fn` **`dot`** — `pub fn dot(&self, other: Vector3D) -> f64 {...}`
- `fn` **`cross`** — `pub fn cross(&self, other: Vector3D) -> Vector3D {...}`
- `fn` **`distance_to`** — `pub fn distance_to(&self, other: Vector3D) -> f64 {...}`
- `fn` **`distance_squared_to`** — `pub fn distance_squared_to(&self, other: Vector3D) -> f64 {...}`
- `fn` **`direction_to`** — `pub fn direction_to(&self, other: Vector3D) -> Vector3D {...}`
- `fn` **`lerp`** — `pub fn lerp(&self, other: Vector3D, factor: f64) -> Vector3D {...}`
- `fn` **`scale`** — `pub fn scale(&mut self, scalar: f64) {...}`
- `fn` **`scaled`** — `pub fn scaled(&self, scalar: f64) -> Vector3D {...}`
- `fn` **`rotated_by`** — `pub fn rotated_by(&self, quaternion: Quaternion) -> Vector3D {...}`
- `fn` **`identity`** — `pub fn identity() -> Quaternion {...}`
- `fn` **`from_axis_angle`** — `pub fn from_axis_angle(axis: Vector3D, angle: f64) -> Quaternion {...}`
- `fn` **`from_euler`** — `pub fn from_euler(yaw: f64, pitch: f64, roll: f64) -> Quaternion {...}`
- `fn` **`magnitude`** — `pub fn magnitude(&self) -> f64 {...}`
- `fn` **`normalized`** — `pub fn normalized(&self) -> Quaternion {...}`
- `fn` **`conjugate`** — `pub fn conjugate(&self) -> Quaternion {...}`
- `fn` **`dot`** — `pub fn dot(&self, other: Quaternion) -> f64 {...}`
- `fn` **`slerp`** — `pub fn slerp(&self, other: Quaternion, factor: f64) -> Quaternion {...}`
- `fn` **`identity`** — `pub fn identity() -> Matrix4x4 {...}`
- `fn` **`translation`** — `pub fn translation(translation: Vector3D) -> Matrix4x4 {...}`
- `fn` **`scaling`** — `pub fn scaling(scale: Vector3D) -> Matrix4x4 {...}`
- `fn` **`rotation`** — `pub fn rotation(quaternion: Quaternion) -> Matrix4x4 {...}`
- `fn` **`perspective`** — `pub fn perspective(fov: f64, aspect: f64, near: f64, far: f64) -> Matrix4x4 {...}`
- `fn` **`orthographic`** — `pub fn orthographic( left: f64, right: f64, bottom: f64, top: f64, near: f64, far: f64, ) -> Matrix4x4 {...}`
- `fn` **`look_at`** — `pub fn look_at(eye: Vector3D, target: Vector3D, up: Vector3D) -> Matrix4x4 {...}`
- `fn` **`multiply`** — `pub fn multiply(&self, other: Matrix4x4) -> Matrix4x4 {...}`
- `fn` **`transform_point`** — `pub fn transform_point(&self, point: Vector3D) -> Vector3D {...}`
- `fn` **`identity`** — `pub fn identity() -> Transform3D {...}`
- `fn` **`translate`** — `pub fn translate(&mut self, offset: Vector3D) {...}`
- `fn` **`rotate`** — `pub fn rotate(&mut self, rotation: Quaternion) {...}`
- `fn` **`scale_by`** — `pub fn scale_by(&mut self, factors: Vector3D) {...}`
- `fn` **`apply_to_point`** — `pub fn apply_to_point(&self, point: Vector3D) -> Vector3D {...}`
- `fn` **`to_matrix`** — `pub fn to_matrix(&self) -> Matrix4x4 {...}`
- `fn` **`from_center`** — `pub fn from_center(center: Vector3D, width: f64, height: f64, depth: f64) -> AABB3D {...}`
- `fn` **`center`** — `pub fn center(&self) -> Vector3D {...}`
- `fn` **`size`** — `pub fn size(&self) -> Vector3D {...}`
- `fn` **`contains`** — `pub fn contains(&self, point: Vector3D) -> bool {...}`
- `fn` **`intersects`** — `pub fn intersects(&self, other: AABB3D) -> bool {...}`
- `fn` **`contains`** — `pub fn contains(&self, point: Vector3D) -> bool {...}`
- `fn` **`intersects`** — `pub fn intersects(&self, other: Sphere) -> bool {...}`
- `fn` **`volume`** — `pub fn volume(&self) -> f64 {...}`
- `fn` **`surface_area`** — `pub fn surface_area(&self) -> f64 {...}`
- `fn` **`from_normal_and_point`** — `pub fn from_normal_and_point(normal: Vector3D, point: Vector3D) -> Plane {...}`
- `fn` **`distance_to_point`** — `pub fn distance_to_point(&self, point: Vector3D) -> f64 {...}`
- `fn` **`normalize`** — `pub fn normalize(&mut self) {...}`
- `fn` **`point_at`** — `pub fn point_at(&self, t: f64) -> Vector3D {...}`
- `fn` **`intersect_sphere`** — `pub fn intersect_sphere(&self, sphere: Sphere) -> Option<f64> {...}`
- `fn` **`intersect_plane`** — `pub fn intersect_plane(&self, plane: Plane) -> Option<f64> {...}`
- `fn` **`intersect_aabb`** — `pub fn intersect_aabb(&self, aabb: AABB3D) -> Option<f64> {...}`

### `math::struct`

- `struct` **`Numeric`** — `pub struct Numeric;`
- `struct` **`Vector2D`** — `pub struct Vector2D {`
- `struct` **`Rect`** — `pub struct Rect {`
- `struct` **`Circle`** — `pub struct Circle {`
- `struct` **`Transform2D`** — `pub struct Transform2D {`
- `struct` **`Color`** — `pub struct Color {`
- `struct` **`Vector3D`** — `pub struct Vector3D {`
- `struct` **`Quaternion`** — `pub struct Quaternion {`
- `struct` **`Matrix4x4`** — `pub struct Matrix4x4 {`
- `struct` **`Transform3D`** — `pub struct Transform3D {`
- `struct` **`AABB3D`** — `pub struct AABB3D {`
- `struct` **`Sphere`** — `pub struct Sphere {`
- `struct` **`Plane`** — `pub struct Plane {`
- `struct` **`Ray3D`** — `pub struct Ray3D {`
- `struct` **`Ray2D`** — `pub struct Ray2D {`

### `math::trait`

- `trait` **`Interpolable`** — `pub trait Interpolable {`
- `trait` **`Vector`** — `pub trait Vector: Copy + Clone + Default + Debug + PartialEq + Add<Output = Self> + Sub<Output = Self> + Mul<f64, Output = Self> + Neg<Output = Self> + AddAssig`

### `particle::impl`

- `fn` **`with_seed`** — `pub fn with_seed(seed: u64) -> ParticleRng {...}`
- `fn` **`next_u64`** — `pub fn next_u64(&mut self) -> u64 {...}`
- `fn` **`next_f64`** — `pub fn next_f64(&mut self) -> f64 {...}`
- `fn` **`range`** — `pub fn range(&mut self, min: f64, max: f64) -> f64 {...}`
- `fn` **`create`** — `pub fn create(position: Vector2D, config: ParticleConfig) -> ParticleEmitter {...}`
- `fn` **`with_defaults`** — `pub fn with_defaults(position: Vector2D) -> ParticleEmitter {...}`
- `fn` **`update`** — `pub fn update(&mut self, delta_time: f64) {...}`
- `fn` **`burst`** — `pub fn burst(&mut self, count: usize) {...}`
- `fn` **`render`** — `pub fn render(&self, draw_list: &mut DrawList) {...}`
- `fn` **`alive_count`** — `pub fn alive_count(&self) -> usize {...}`
- `fn` **`quantize`** — `pub(crate) fn quantize(color: &Color) -> u8 {...}`
- `fn` **`clear`** — `pub fn clear(&mut self) {...}`

### `particle::static`

- `static` **`PARTICLE_PALETTE`** — `pub(crate) static PARTICLE_PALETTE: LazyLock<[Color; PARTICLE_PALETTE_SIZE]> = LazyLock::new(|| {`

### `particle::struct`

- `struct` **`ParticleRng`** — `pub struct ParticleRng {`
- `struct` **`ParticleConfig`** — `pub struct ParticleConfig {`
- `struct` **`Particle`** — `pub struct Particle {`
- `struct` **`ParticleEmitter`** — `pub struct ParticleEmitter {`

### `physics::enum`

- `enum` **`BodyType`** — `pub enum BodyType {`
- `enum` **`BodyCollider`** — `pub enum BodyCollider {`
- `enum` **`BodyCollider3D`** — `pub enum BodyCollider3D {`

### `physics::impl`

- `fn` **`new_dynamic`** — `pub fn new_dynamic(id: u64, position: Vector2D) -> RigidBody2D {...}`
- `fn` **`new_static`** — `pub fn new_static(id: u64, position: Vector2D) -> RigidBody2D {...}`
- `fn` **`apply_force`** — `pub fn apply_force(&mut self, force: Vector2D) {...}`
- `fn` **`apply_impulse`** — `pub fn apply_impulse(&mut self, impulse: Vector2D) {...}`
- `fn` **`update_mass`** — `pub fn update_mass(&mut self, mass: f64) {...}`
- `fn` **`is_dynamic`** — `pub fn is_dynamic(&self) -> bool {...}`
- `fn` **`update_collider`** — `pub fn update_collider(&mut self, collider: BodyCollider) {...}`
- `fn` **`bounding_box`** — `pub fn bounding_box(&self) -> Option<Rect> {...}`
- `fn` **`with_config`** — `pub fn with_config(config: PhysicsConfig) -> PhysicsWorld2D {...}`
- `fn` **`add_body`** — `pub fn add_body(&mut self, body: RigidBody2D) {...}`
- `fn` **`remove_body`** — `pub fn remove_body(&mut self, id: u64) {...}`
- `fn` **`get_body`** — `pub fn get_body(&self, id: u64) -> Option<&RigidBody2D> {...}`
- `fn` **`get_body_mut`** — `pub fn get_body_mut(&mut self, id: u64) -> Option<&mut RigidBody2D> {...}`
- `fn` **`step`** — `pub fn step(&mut self, delta_time: f64) {...}`
- `fn` **`new_dynamic`** — `pub fn new_dynamic(id: u64, position: Vector3D) -> RigidBody3D {...}`
- `fn` **`new_static`** — `pub fn new_static(id: u64, position: Vector3D) -> RigidBody3D {...}`
- `fn` **`apply_force`** — `pub fn apply_force(&mut self, force: Vector3D) {...}`
- `fn` **`apply_torque`** — `pub fn apply_torque(&mut self, torque: Vector3D) {...}`
- `fn` **`apply_impulse`** — `pub fn apply_impulse(&mut self, impulse: Vector3D) {...}`
- `fn` **`update_mass`** — `pub fn update_mass(&mut self, mass: f64) {...}`
- `fn` **`update_inertia`** — `pub fn update_inertia(&mut self, inertia: f64) {...}`
- `fn` **`is_dynamic`** — `pub fn is_dynamic(&self) -> bool {...}`
- `fn` **`update_collider`** — `pub fn update_collider(&mut self, collider: BodyCollider3D) {...}`
- `fn` **`bounding_box`** — `pub fn bounding_box(&self) -> Option<AABB3D> {...}`
- `fn` **`with_config`** — `pub fn with_config(config: PhysicsConfig3D) -> PhysicsWorld3D {...}`
- `fn` **`add_body`** — `pub fn add_body(&mut self, body: RigidBody3D) {...}`
- `fn` **`remove_body`** — `pub fn remove_body(&mut self, id: u64) {...}`
- `fn` **`get_body`** — `pub fn get_body(&self, id: u64) -> Option<&RigidBody3D> {...}`
- `fn` **`get_body_mut`** — `pub fn get_body_mut(&mut self, id: u64) -> Option<&mut RigidBody3D> {...}`
- `fn` **`step`** — `pub fn step(&mut self, delta_time: f64) {...}`

### `physics::struct`

- `struct` **`PhysicsConfig`** — `pub struct PhysicsConfig {`
- `struct` **`RigidBody2D`** — `pub struct RigidBody2D {`
- `struct` **`PhysicsWorld2D`** — `pub struct PhysicsWorld2D {`
- `struct` **`PhysicsConfig3D`** — `pub struct PhysicsConfig3D {`
- `struct` **`RigidBody3D`** — `pub struct RigidBody3D {`
- `struct` **`PhysicsWorld3D`** — `pub struct PhysicsWorld3D {`

### `raytracing::enum`

- `enum` **`OccluderKind`** — `pub enum OccluderKind {`

### `raytracing::fn`

- `fn` **`collect_occluder_points`** — `pub(crate) fn collect_occluder_points(occluders: &[Occluder]) -> Vec<(Vector3D, f64)> {...}`
- `fn` **`closest_hit_indexed`** — `pub(crate) fn closest_hit_indexed( ray: &Ray, occluders: &[Occluder], ) -> Option<(usize, f64, Vector3D, Vector3D)> {...}`
- `fn` **`trace_bounces`** — `pub(crate) fn trace_bounces( ray: Ray, occluders: &[Occluder], shadow_points: &[(Vector3D, f64)], lights: &LightingUniforms, max_bounces: u32, ) -> Vector3D {...}`

### `raytracing::impl`

- `fn` **`new`** — `pub fn new(origin: Vector3D, direction: Vector3D) -> Ray {...}`
- `fn` **`at`** — `pub fn at(&self, t: f64) -> Vector3D {...}`
- `fn` **`with_depth`** — `pub fn with_depth(&self, depth: u32) -> Ray {...}`
- `fn` **`sphere`** — `pub fn sphere(center: Vector3D, radius: f64, material: Material) -> Occluder {...}`
- `fn` **`aabb`** — `pub fn aabb(min: Vector3D, max: Vector3D, material: Material) -> Occluder {...}`
- `fn` **`occluder_points`** — `pub fn occluder_points(&self) -> Vec<(Vector3D, f64)> {...}`
- `fn` **`new`** — `pub fn new(occluders: Vec<Occluder>) -> RayTraceScene {...}`
- `fn` **`trace`** — `pub fn trace(&self, ray: Ray, lights: &LightingUniforms) -> Vector3D {...}`
- `fn` **`trace_with_bounces`** — `pub fn trace_with_bounces( &self, ray: Ray, lights: &LightingUniforms, max_bounces: u32, ) -> Vector3D {...}`
- `fn` **`closest_hit`** — `pub fn closest_hit(&self, ray: &Ray) -> Option<Hit> {...}`

### `raytracing::struct`

- `struct` **`Ray`** — `pub struct Ray {`
- `struct` **`Hit`** — `pub struct Hit {`
- `struct` **`Occluder`** — `pub struct Occluder {`
- `struct` **`RayTraceScene`** — `pub struct RayTraceScene {`

### `renderer::enum`

- `enum` **`BlendMode`** — `pub enum BlendMode {`
- `enum` **`DrawCommand`** — `pub enum DrawCommand {`
- `enum` **`RenderQuality`** — `pub enum RenderQuality {`
- `enum` **`WebGpuInitError`** — `pub enum WebGpuInitError {`
- `enum` **`WebGlInitError`** — `pub enum WebGlInitError {`
- `enum` **`WebGlProgramError`** — `pub enum WebGlProgramError {`
- `enum` **`VertexStepMode`** — `pub enum VertexStepMode {`
- `enum` **`BindGroupEntry`** — `pub enum BindGroupEntry {`
- `enum` **`BindGroupEntryType`** — `pub enum BindGroupEntryType {`
- `enum` **`GpuReceiverClass`** — `pub(crate) enum GpuReceiverClass {`

### `renderer::fn`

- `fn` **`draw_sprite_immediate`** — `pub(crate) fn draw_sprite_immediate( context: &CanvasRenderingContext2d, image: &HtmlImageElement, source: &Rect, transform: &Transform2D, ) {...}`
- `fn` **`js_error_to_string`** — `pub(crate) fn js_error_to_string(value: &JsValue) -> String {...}`
- `fn` **`pick_depth_format`** — `pub(crate) fn pick_depth_format(high_precision: bool, with_stencil: bool) -> &'static str {...}`
- `fn` **`default_color_store_op`** — `pub(crate) fn default_color_store_op(transient: bool) -> &'static str {...}`
- `fn` **`map_mode_for`** — `pub(crate) fn map_mode_for(read: bool, write: bool) -> u32 {...}`
- `fn` **`texture_usage`** — `pub(crate) fn texture_usage( render_target: bool, copy_src: bool, copy_dst: bool, sampled: bool, storage: bool, ) -> u32 {...}`
- `fn` **`cached_method_name`** — `pub(crate) fn cached_method_name(name: &'static str) -> JsValue {...}`
- `fn` **`cached_method`** — `pub(crate) fn cached_method( class: GpuReceiverClass, obj: &JsValue, method_name: &'static str, ) -> Result<Function, JsValue> {...}`
- `fn` **`cached_method_call`** — `pub(crate) fn cached_method_call( class: GpuReceiverClass, obj: &JsValue, method_name: &'static str, arg: &JsValue, ) -> Result<JsValue, JsValue> {...}`

### `renderer::impl`

- `fn` **`create`** — `pub fn create(viewport_width: f64, viewport_height: f64) -> Camera2D {...}`
- `fn` **`world_to_screen`** — `pub fn world_to_screen(&self, world: Vector2D) -> Vector2D {...}`
- `fn` **`screen_to_world`** — `pub fn screen_to_world(&self, screen: Vector2D) -> Vector2D {...}`
- `fn` **`translate`** — `pub fn translate(&mut self, offset: Vector2D) {...}`
- `fn` **`zoom_by`** — `pub fn zoom_by(&mut self, factor: f64) {...}`
- `fn` **`font`** — `pub fn font<F>(size: f64, family: F) -> String where F: AsRef<str>, {...}`
- `fn` **`default_font`** — `pub fn default_font() -> String {...}`
- `fn` **`enable_smoothing_on`** — `pub fn enable_smoothing_on(context: &CanvasRenderingContext2d) {...}`
- `fn` **`detect_dpr`** — `pub fn detect_dpr() -> f64 {...}`
- `fn` **`apply_quality`** — `pub(crate) fn apply_quality(context: &CanvasRenderingContext2d, quality: RenderQuality) {...}`
- `fn` **`to_css`** — `pub fn to_css(color: &Color) -> String {...}`
- `fn` **`create`** — `pub fn create() -> DrawList {...}`
- `fn` **`is_empty`** — `pub fn is_empty(&self) -> bool {...}`
- `fn` **`len`** — `pub fn len(&self) -> usize {...}`
- `fn` **`commands`** — `pub fn commands(&self) -> &[DrawCommand] {...}`
- `fn` **`clear`** — `pub fn clear(&mut self) {...}`
- `fn` **`fill_rect`** — `pub fn fill_rect(&mut self, position: Vector2D, width: f64, height: f64, color: Color) {...}`
- `fn` **`stroke_rect`** — `pub fn stroke_rect( &mut self, position: Vector2D, width: f64, height: f64, color: Color, line_width: f64, ) {...}`
- `fn` **`fill_circle`** — `pub fn fill_circle(&mut self, center: Vector2D, radius: f64, color: Color) {...}`
- `fn` **`stroke_circle`** — `pub fn stroke_circle(&mut self, center: Vector2D, radius: f64, color: Color, line_width: f64) {...}`
- `fn` **`draw_line`** — `pub fn draw_line(&mut self, start: Vector2D, end: Vector2D, color: Color, line_width: f64) {...}`
- `fn` **`fill_text`** — `pub fn fill_text<T, F>(&mut self, text: T, position: Vector2D, color: Color, font: F) where T: AsRef<str>, F: AsRef<str>, {...}`
- `fn` **`draw_sprite`** — `pub fn draw_sprite(&mut self, image: &HtmlImageElement, source: Rect, transform: Transform2D) {...}`
- `fn` **`draw_image_rect`** — `pub fn draw_image_rect( &mut self, image: &HtmlImageElement, source: Rect, dest_position: Vector2D, dest_width: f64, dest_height: f64, ) {...}`
- `fn` **`set_global_alpha`** — `pub fn set_global_alpha(&mut self, alpha: f64) {...}`
- `fn` **`set_blend_mode`** — `pub fn set_blend_mode(&mut self, mode: BlendMode) {...}`
- `fn` **`from_selector`** — `pub fn from_selector<S>( canvas_selector: S, viewport_width: f64, viewport_height: f64, ) -> Option<CanvasRenderer> where S: AsRef<str>, {...}`
- `fn` **`enable_smoothing`** — `pub fn enable_smoothing(&self) {...}`
- `fn` **`clear`** — `pub fn clear(&self) {...}`
- `fn` **`clear_color`** — `pub fn clear_color<C>(&self, color: C) where C: AsRef<str>, {...}`
- `fn` **`save`** — `pub fn save(&self) {...}`
- `fn` **`restore`** — `pub fn restore(&self) {...}`
- `fn` **`replay`** — `pub fn replay(&self, list: &DrawList) {...}`
- `fn` **`replay_context`** — `pub fn replay_context(context: &CanvasRenderingContext2d, list: &DrawList) {...}`
- `fn` **`apply_camera`** — `pub fn apply_camera(&self) {...}`
- `fn` **`set_fill_color`** — `pub fn set_fill_color<C>(&self, color: C) where C: AsRef<str>, {...}`
- `fn` **`set_stroke_color`** — `pub fn set_stroke_color<C>(&self, color: C) where C: AsRef<str>, {...}`
- `fn` **`set_line_width`** — `pub fn set_line_width(&self, width: f64) {...}`
- `fn` **`set_global_alpha`** — `pub fn set_global_alpha(&self, alpha: f64) {...}`
- `fn` **`fill_rect`** — `pub fn fill_rect(&self, position: Vector2D, width: f64, height: f64) {...}`
- `fn` **`stroke_rect`** — `pub fn stroke_rect(&self, position: Vector2D, width: f64, height: f64) {...}`
- `fn` **`fill_circle`** — `pub fn fill_circle(&self, center: Vector2D, radius: f64) {...}`
- `fn` **`stroke_circle`** — `pub fn stroke_circle(&self, center: Vector2D, radius: f64) {...}`
- `fn` **`draw_line`** — `pub fn draw_line(&self, start: Vector2D, end: Vector2D) {...}`
- `fn` **`fill_text`** — `pub fn fill_text<T>(&self, text: T, position: Vector2D) where T: AsRef<str>, {...}`
- `fn` **`set_font`** — `pub fn set_font<F>(&self, font: F) where F: AsRef<str>, {...}`
- `fn` **`draw_image`** — `pub fn draw_image( &self, image: &HtmlImageElement, position: Vector2D, width: f64, height: f64, ) {...}`
- `fn` **`draw_image_rect`** — `pub fn draw_image_rect( &self, image: &HtmlImageElement, source: Rect, dest_position: Vector2D, dest_width: f64, dest_height: f64, ) {...}`
- `fn` **`create`** — `pub fn create( position: Vector3D, target: Vector3D, viewport_width: f64, viewport_height: f64, ) -> Camera3D {...}`
- `fn` **`aspect`** — `pub fn aspect(&self) -> f64 {...}`
- `fn` **`forward`** — `pub fn forward(&self) -> Vector3D {...}`
- `fn` **`right`** — `pub fn right(&self) -> Vector3D {...}`
- `fn` **`view_matrix`** — `pub fn view_matrix(&self) -> Matrix4x4 {...}`
- `fn` **`projection_matrix`** — `pub fn projection_matrix(&self) -> Matrix4x4 {...}`
- `fn` **`view_proj_matrix`** — `pub fn view_proj_matrix(&self) -> Matrix4x4 {...}`
- `fn` **`world_to_screen`** — `pub fn world_to_screen(&self, world: Vector3D) -> Vector3D {...}`
- `fn` **`in_frustum`** — `pub fn in_frustum(&self, world: Vector3D) -> bool {...}`
- `fn` **`translate`** — `pub fn translate(&mut self, offset: Vector3D) {...}`
- `fn` **`zoom`** — `pub fn zoom(&mut self, distance: f64) {...}`
- `fn` **`orbit`** — `pub fn orbit(&mut self, yaw_delta: f64, pitch_delta: f64) {...}`
- `fn` **`from_selector`** — `pub fn from_selector<S>(canvas_selector: S, width: f64, height: f64) -> Option<SsaaCanvas> where S: AsRef<str>, {...}`
- `fn` **`from_selector_with_scale`** — `pub fn from_selector_with_scale<S>( canvas_selector: S, width: f64, height: f64, scale_factor: f64, ) -> Option<SsaaCanvas> where S: AsRef<str>, { .`
- `fn` **`present`** — `pub fn present(&self) {...}`
- `fn` **`clear`** — `pub fn clear(&self) {...}`
- `fn` **`clear_color`** — `pub fn clear_color<C>(&self, color: C) where C: AsRef<str>, {...}`
- `fn` **`enable_smoothing`** — `pub fn enable_smoothing(&self) {...}`
- `fn` **`to_css`** — `pub fn to_css(&self) -> &str {...}`
- `fn` **`create`** — `pub fn create(start: Vector2D, end: Vector2D, stops: Vec<(f64, String)>) -> LinearGradient {...}`
- `fn` **`to_gradient`** — `pub fn to_gradient(&self, context: &CanvasRenderingContext2d) -> Option<CanvasGradient> {...}`
- `fn` **`create`** — `pub fn create( inner_center: Vector2D, inner_radius: f64, outer_center: Vector2D, outer_radius: f64, stops: Vec<(f64, String)>, ) -> RadialGradient { ..`
- `fn` **`to_gradient`** — `pub fn to_gradient(&self, context: &CanvasRenderingContext2d) -> Option<CanvasGradient> {...}`
- `fn` **`create`** — `pub fn create() -> ShadowConfig {...}`
- `fn` **`create`** — `pub fn create(z_index: i32, visible: bool) -> RenderLayer {...}`
- `fn` **`background`** — `pub fn background() -> RenderLayer {...}`
- `fn` **`foreground`** — `pub fn foreground() -> RenderLayer {...}`
- `fn` **`ui`** — `pub fn ui() -> RenderLayer {...}`
- `fn` **`set_blend_mode`** — `pub fn set_blend_mode(&self, mode: BlendMode) {...}`
- `fn` **`set_shadow`** — `pub fn set_shadow(&self, config: &ShadowConfig) {...}`
- `fn` **`clear_shadow`** — `pub fn clear_shadow(&self) {...}`
- `fn` **`set_linear_gradient_fill`** — `pub fn set_linear_gradient_fill(&self, gradient: &LinearGradient) {...}`
- `fn` **`set_radial_gradient_fill`** — `pub fn set_radial_gradient_fill(&self, gradient: &RadialGradient) {...}`
- `fn` **`set_linear_gradient_stroke`** — `pub fn set_linear_gradient_stroke(&self, gradient: &LinearGradient) {...}`
- `fn` **`set_radial_gradient_stroke`** — `pub fn set_radial_gradient_stroke(&self, gradient: &RadialGradient) {...}`
- `fn` **`is_available`** — `pub fn is_available() -> bool {...}`
- `fn` **`probe`** — `pub async fn probe() -> bool {...}`
- `fn` **`init`** — `pub async fn init(config: &RenderConfig) -> Result<WebGpuRenderer, WebGpuInitError> {...}`
- `fn` **`resize`** — `pub fn resize(&mut self, physical_width: u32, physical_height: u32) -> bool {...}`
- `fn` **`sync_to_current_canvas`** — `pub fn sync_to_current_canvas(&mut self) -> bool {...}`
- `fn` **`create_shader_module`** — `pub(crate) fn create_shader_module<S>(&self, code: S) -> JsValue where S: AsRef<str>, {...}`
- `fn` **`create_command_encoder`** — `pub fn create_command_encoder(&self) -> JsValue {...}`
- `fn` **`get_current_texture_view`** — `pub(crate) fn get_current_texture_view(&self) -> JsValue {...}`
- `fn` **`begin_render_pass`** — `pub fn begin_render_pass( &mut self, encoder: &JsValue, clear_color: (f64, f64, f64, f64), ) -> JsValue {...}`
- `fn` **`begin_render_pass_full`** — `pub fn begin_render_pass_full( &mut self, encoder: &JsValue, color: &mut RenderPassColorAttachment, depth: Option<&RenderPassDepthStencilAttachment>, ) -> JsVal`
- `fn` **`submit`** — `pub fn submit(&self, command_buffers: &[JsValue]) {...}`
- `fn` **`create_render_pipeline`** — `pub fn create_render_pipeline<S>(&self, shader_code: S) -> JsValue where S: AsRef<str>, {...}`
- `fn` **`create_render_pipeline_full`** — `pub fn create_render_pipeline_full<S>( &self, shader_code: S, vertex_buffer_layouts: &[VertexBufferLayout], vertex_entry: &str, fragment_entry: &str,`
- `fn` **`set_pipeline`** — `pub fn set_pipeline(&self, pass: &JsValue, pipeline: &JsValue) {...}`
- `fn` **`set_vertex_buffer`** — `pub fn set_vertex_buffer(&self, pass: &JsValue, slot: u32, buffer: &JsValue) {...}`
- `fn` **`set_index_buffer`** — `pub fn set_index_buffer(&self, pass: &JsValue, buffer: &JsValue, format: &str) {...}`
- `fn` **`draw`** — `pub fn draw(&self, pass: &JsValue, vertex_count: u32, instance_count: u32) {...}`
- `fn` **`draw_indexed`** — `pub fn draw_indexed(&self, pass: &JsValue, index_count: u32, instance_count: u32) {...}`
- `fn` **`draw_indexed_offset`** — `pub fn draw_indexed_offset( &self, pass: &JsValue, index_offset: u32, index_count: u32, instance_count: u32, ) {...}`
- `fn` **`end_render_pass`** — `pub fn end_render_pass(&self, pass: &JsValue) {...}`
- `fn` **`finish_command_encoder`** — `pub fn finish_command_encoder(&self, encoder: &JsValue) -> JsValue {...}`
- `fn` **`create_uniform_buffer`** — `pub fn create_uniform_buffer(&self, data: &[f32]) -> JsValue {...}`
- `fn` **`update_uniform_buffer`** — `pub fn update_uniform_buffer(&self, buffer: &JsValue, data: &[f32]) {...}`
- `fn` **`create_compute_pipeline`** — `pub fn create_compute_pipeline<S>(&self, shader_code: S, entry_point: &str) -> JsValue where S: AsRef<str>, {...}`
- `fn` **`begin_compute_pass`** — `pub fn begin_compute_pass(&self, encoder: &JsValue) -> JsValue {...}`
- `fn` **`dispatch`** — `pub fn dispatch(&self, pass: &JsValue, x: u32, y: u32, z: u32) {...}`
- `fn` **`push_error_scope`** — `pub fn push_error_scope(&self, filter: &str) {...}`
- `fn` **`pop_error_sync`** — `pub fn pop_error_sync(&self) -> Option<JsValue> {...}`
- `fn` **`take_last_error`** — `pub fn take_last_error(&self) -> Option<JsValue> {...}`
- `fn` **`begin_render_pass_to_texture`** — `pub fn begin_render_pass_to_texture( &mut self, encoder: &JsValue, color_view: &JsValue, clear_color: Option<(f64, f64, f64, f64)>, depth_view: Option<&JsVa`
- `fn` **`copy_texture_to_buffer`** — `pub fn copy_texture_to_buffer( &self, source: &JsValue, destination: &JsValue, bytes_per_row: u32, width: u32, height: u32, ) {...}`
- `fn` **`create_offline_render_target`** — `pub fn create_offline_render_target( &self, width: u32, height: u32, format: &str, ) -> (JsValue, JsValue) {...}`
- `fn` **`create_texture_view`** — `pub fn create_texture_view(&self, texture: &JsValue) -> JsValue {...}`
- `fn` **`on_device_lost`** — `pub fn on_device_lost(&mut self, callback: Function) {...}`
- `fn` **`create_buffer`** — `pub fn create_buffer(&self, size: u64, usage: u32) -> JsValue {...}`
- `fn` **`create_vertex_buffer`** — `pub fn create_vertex_buffer(&self, data: &[u8]) -> JsValue {...}`
- `fn` **`create_index_buffer`** — `pub fn create_index_buffer(&self, data: &[u8]) -> JsValue {...}`
- `fn` **`write_buffer`** — `pub fn write_buffer(&self, buffer: &JsValue, offset: u64, data: &[u8]) {...}`
- `fn` **`create_depth_texture`** — `pub fn create_depth_texture(&mut self) -> Option<JsValue> {...}`
- `fn` **`create_texture_2d`** — `pub fn create_texture_2d(&self, descriptor: &Texture2DDescriptor) -> JsValue {...}`
- `fn` **`create_sampler`** — `pub fn create_sampler(&self, descriptor: &GpuSamplerDescriptor) -> JsValue {...}`
- `fn` **`create_uniform_bind_group`** — `pub fn create_uniform_bind_group(&self, pipeline: &JsValue, buffer: &JsValue) -> JsValue {...}`
- `fn` **`create_bind_group`** — `pub fn create_bind_group( &self, pipeline: &JsValue, index: u32, entries: &[BindGroupEntry], ) -> JsValue {...}`
- `fn` **`set_bind_group`** — `pub fn set_bind_group(&self, pass: &JsValue, index: u32, bind_group: &JsValue) {...}`
- `fn` **`set_bind_group_on`** — `pub(crate) fn set_bind_group_on( &self, class: GpuReceiverClass, pass: &JsValue, index: u32, bind_group: &JsValue, ) {...}`
- `fn` **`render_frame`** — `pub fn render_frame( &mut self, pipeline: &JsValue, clear_color: (f64, f64, f64, f64), vertex_count: u32, ) {...}`
- `fn` **`render_frame_with_bind_group`** — `pub fn render_frame_with_bind_group( &mut self, pipeline: &JsValue, bind_group: &JsValue, clear_color: (f64, f64, f64, f64), vertex_count: u32, ) { ...`
- `fn` **`set_compute_pipeline`** — `pub fn set_compute_pipeline(&self, pass: &JsValue, pipeline: &JsValue) {...}`
- `fn` **`create_bind_group_for_layout`** — `pub fn create_bind_group_for_layout( &self, layout: &JsValue, entries: &[BindGroupEntry], ) -> JsValue {...}`
- `fn` **`create_bind_group_layout`** — `pub fn create_bind_group_layout(&self, entries: &[BindGroupLayoutEntry]) -> JsValue {...}`
- `fn` **`dispatch_with_bind_group`** — `pub fn dispatch_with_bind_group( &self, pass: &JsValue, pipeline: &JsValue, bind_group: &JsValue, x: u32, y: u32, z: u32, ) {...}`
- `fn` **`create_storage_texture`** — `pub fn create_storage_texture(&self, width: u32, height: u32, format: &str) -> JsValue {...}`
- `fn` **`create_timestamp_query_set`** — `pub fn create_timestamp_query_set(&self, count: u32) -> JsValue {...}`
- `fn` **`write_timestamp`** — `pub fn write_timestamp(&self, pass: &JsValue, query_set: &JsValue, index: u32) {...}`
- `fn` **`resolve_timestamp`** — `pub fn resolve_timestamp( &self, encoder: &JsValue, query_set: &JsValue, first_query: u32, query_count: u32, destination: &JsValue, destinat`
- `fn` **`create_render_pipeline_with_layout`** — `pub fn create_render_pipeline_with_layout<S>( &self, shader_code: S, layout: &JsValue, vertex_buffer_layouts: &[VertexBufferLayout], vertex_entry: &str,`
- `fn` **`dispose`** — `pub fn dispose(&self) {...}`
- `fn` **`set_viewport`** — `pub fn set_viewport(&self, pass: &JsValue, viewport: &ViewportDescriptor) {...}`
- `fn` **`set_scissor_rect`** — `pub fn set_scissor_rect(&self, pass: &JsValue, x: u32, y: u32, width: u32, height: u32) {...}`
- `fn` **`set_blend_constant`** — `pub fn set_blend_constant(&self, pass: &JsValue, r: f32, g: f32, b: f32, a: f32) {...}`
- `fn` **`set_stencil_reference`** — `pub fn set_stencil_reference(&self, pass: &JsValue, reference: u32) {...}`
- `fn` **`set_bind_group_with_dynamic_offsets`** — `pub fn set_bind_group_with_dynamic_offsets( &self, pass: &JsValue, index: u32, group: &JsValue, dynamic_offsets: &[u32], ) {...}`
- `fn` **`set_bind_group_compute_with_dynamic_offsets`** — `pub fn set_bind_group_compute_with_dynamic_offsets( &self, pass: &JsValue, index: u32, group: &JsValue, dynamic_offsets: &[u32], ) {...}`
- `fn` **`create_view`** — `pub fn create_view( &self, texture: &JsValue, descriptor: Option<&TextureViewDescriptor>, ) -> JsValue {...}`
- `fn` **`generate_mipmaps`** — `pub fn generate_mipmaps(&self, texture: &JsValue) {...}`
- `fn` **`write_texture`** — `pub fn write_texture(&self, descriptor: &TextureWriteDescriptor) {...}`
- `fn` **`create_shader_module_with_label`** — `pub fn create_shader_module_with_label(&self, wgsl_source: &str, label: &str) -> JsValue {...}`
- `fn` **`read_buffer`** — `pub async fn read_buffer(&self, buffer: &JsValue, offset: u64, size: u64) -> Option<Vec<u8>> {...}`
- `fn` **`code`** — `pub fn code(&self) -> &'static str {...}`
- `fn` **`js_error`** — `pub fn js_error(&self) -> Option<&JsValue> {...}`
- `fn` **`is_available`** — `pub fn is_available() -> bool {...}`
- `fn` **`init`** — `pub fn init(config: &RenderConfig) -> Result<WebGlRenderer, WebGlInitError> {...}`
- `fn` **`create_program`** — `pub fn create_program( &self, vertex_source: &str, fragment_source: &str, ) -> Result<WebGlProgram, WebGlProgramError> {...}`
- `fn` **`get_uniform_location`** — `pub fn get_uniform_location( &self, program: &WebGlProgram, name: &str, ) -> Option<WebGlUniformLocation> {...}`
- `fn` **`set_uniform_2f`** — `pub fn set_uniform_2f( &self, program: &WebGlProgram, location: Option<&WebGlUniformLocation>, x: f32, y: f32, ) {...}`
- `fn` **`set_uniform_4fv`** — `pub fn set_uniform_4fv( &self, program: &WebGlProgram, location: Option<&WebGlUniformLocation>, data: &[f32], ) {...}`
- `fn` **`render_frame`** — `pub fn render_frame( &self, program: &WebGlProgram, clear_color: (f64, f64, f64, f64), vertex_count: i32, ) {...}`
- `fn` **`resize`** — `pub fn resize(&mut self, physical_width: u32, physical_height: u32) {...}`
- `fn` **`code`** — `pub fn code(&self) -> &'static str {...}`
- `fn` **`js_error`** — `pub fn js_error(&self) -> Option<&JsValue> {...}`
- `fn` **`default_for`** — `pub fn default_for(width: u32, height: u32, format: &'static str) -> Self {...}`
- `fn` **`default_sampler`** — `pub fn default_sampler() -> Self {...}`
- `fn` **`effective_load_op`** — `pub(crate) fn effective_load_op(&self) -> &'static str {...}`
- `fn` **`effective_store_op`** — `pub(crate) fn effective_store_op(&self) -> &'static str {...}`
- `fn` **`effective_depth_load_op`** — `pub(crate) fn effective_depth_load_op(&self) -> &'static str {...}`
- `fn` **`effective_depth_store_op`** — `pub(crate) fn effective_depth_store_op(&self) -> &'static str {...}`
- `fn` **`full`** — `pub fn full() -> Self {...}`
- `fn` **`effective_dimension`** — `pub(crate) fn effective_dimension(&self) -> &'static str {...}`
- `fn` **`effective_aspect`** — `pub(crate) fn effective_aspect(&self) -> &'static str {...}`
- `fn` **`mip`** — `pub fn mip(level: u32) -> Self {...}`
- `fn` **`depth_only`** — `pub fn depth_only() -> Self {...}`
- `fn` **`for_2d`** — `pub fn for_2d(data: Vec<u8>, bytes_per_row: u32, texture: JsValue) -> Self {...}`
- `fn` **`as_str`** — `pub fn as_str(&self) -> &'static str {...}`
- `fn` **`binding`** — `pub fn binding(&self) -> u32 {...}`
- `fn` **`new`** — `pub fn new() -> Self {...}`
- `fn` **`as_ptr`** — `pub fn as_ptr(&self) -> *mut Option<JsValue> {...}`
- `fn` **`uniform`** — `pub fn uniform(binding: u32, visibility: u32) -> Self {...}`
- `fn` **`storage`** — `pub fn storage(binding: u32, visibility: u32, read_only: bool) -> Self {...}`
- `fn` **`texture`** — `pub fn texture(binding: u32, visibility: u32, sample_type: &str) -> Self {...}`
- `fn` **`texture_multisampled`** — `pub fn texture_multisampled(binding: u32, visibility: u32, sample_type: &str) -> Self {...}`
- `fn` **`storage_texture`** — `pub fn storage_texture(binding: u32, visibility: u32, format: &str, read_only: bool) -> Self {...}`
- `fn` **`sampler`** — `pub fn sampler(binding: u32, visibility: u32) -> Self {...}`
- `fn` **`sampler_non_filtering`** — `pub fn sampler_non_filtering(binding: u32, visibility: u32) -> Self {...}`
- `fn` **`sampler_comparison`** — `pub fn sampler_comparison(binding: u32, visibility: u32) -> Self {...}`

### `renderer::struct`

- `struct` **`Camera2D`** — `pub struct Camera2D {`
- `struct` **`Camera3D`** — `pub struct Camera3D {`
- `struct` **`CanvasRenderer`** — `pub struct CanvasRenderer {`
- `struct` **`LinearGradient`** — `pub struct LinearGradient {`
- `struct` **`RadialGradient`** — `pub struct RadialGradient {`
- `struct` **`ShadowConfig`** — `pub struct ShadowConfig {`
- `struct` **`RenderLayer`** — `pub struct RenderLayer {`
- `struct` **`DrawList`** — `pub struct DrawList {`
- `struct` **`SsaaCanvas`** — `pub struct SsaaCanvas {`
- `struct` **`WebGpuRenderer`** — `pub struct WebGpuRenderer {`
- `struct` **`RenderPassDescriptorCache`** — `pub(crate) struct RenderPassDescriptorCache {`
- `struct` **`ViewportDescriptor`** — `pub struct ViewportDescriptor {`
- `struct` **`WebGlRenderer`** — `pub struct WebGlRenderer {`
- `struct` **`VertexAttribute`** — `pub struct VertexAttribute {`
- `struct` **`VertexBufferLayout`** — `pub struct VertexBufferLayout {`
- `struct` **`Texture2DDescriptor`** — `pub struct Texture2DDescriptor {`
- `struct` **`GpuSamplerDescriptor`** — `pub struct GpuSamplerDescriptor {`
- `struct` **`RenderPassColorAttachment`** — `pub struct RenderPassColorAttachment {`
- `struct` **`RenderPassDepthStencilAttachment`** — `pub struct RenderPassDepthStencilAttachment {`
- `struct` **`TextureViewDescriptor`** — `pub struct TextureViewDescriptor {`
- `struct` **`TextureWriteDescriptor`** — `pub struct TextureWriteDescriptor {`
- `struct` **`PendingErrorCell`** — `pub struct PendingErrorCell( pub(crate) UnsafeCell<Option<JsValue>>, );`
- `struct` **`BindGroupLayoutEntry`** — `pub struct BindGroupLayoutEntry {`

### `renderer::trait`

- `trait` **`Renderable`** — `pub trait Renderable {`
- `trait` **`RenderBackend`** — `pub trait RenderBackend {`

### `scene::impl`

- `fn` **`create_scene`** — `pub fn create_scene<T>(scene: T) -> SceneRc where T: Scene + 'static, {...}`
- `fn` **`register`** — `pub fn register(&mut self, name: String, scene: SceneRc) {...}`
- `fn` **`unregister`** — `pub fn unregister<N>(&mut self, name: N) where N: AsRef<str>, {...}`
- `fn` **`switch_to`** — `pub fn switch_to<N>(&mut self, name: N) -> bool where N: AsRef<str>, {...}`
- `fn` **`request_transition`** — `pub fn request_transition(&mut self, name: String) {...}`
- `fn` **`process_pending_transition`** — `pub fn process_pending_transition(&mut self) {...}`
- `fn` **`update`** — `pub fn update(&mut self, delta_time: f64) {...}`
- `fn` **`render`** — `pub fn render(&mut self, context: &CanvasRenderingContext2d) {...}`
- `fn` **`has_scene`** — `pub fn has_scene<N>(&self, name: N) -> bool where N: AsRef<str>, {...}`
- `fn` **`current_name`** — `pub fn current_name(&self) -> Option<&str> {...}`

### `scene::struct`

- `struct` **`SceneManager`** — `pub struct SceneManager {`

### `scene::trait`

- `trait` **`Scene`** — `pub trait Scene: Lifecycle {`

### `scene::type`

- `type` **`SceneRc`** — `pub type SceneRc = Rc<EngineCell<dyn Scene>>;`

### `scheduler::impl`

- `fn` **`current_time`** — `pub fn current_time() -> f64 {...}`
- `fn` **`tick`** — `pub fn tick(&mut self, config: &SchedulerConfig, handler: &TickHandlerRc) {...}`
- `fn` **`stop`** — `pub fn stop(&self) {...}`
- `fn` **`is_running`** — `pub fn is_running(&self) -> bool {...}`
- `fn` **`update_count`** — `pub fn update_count(&self) -> u64 {...}`
- `fn` **`frame_count`** — `pub fn frame_count(&self) -> u64 {...}`
- `fn` **`start`** — `pub fn start(config: SchedulerConfig, handler: TickHandlerRc) -> SchedulerHandle {...}`

### `scheduler::struct`

- `struct` **`SchedulerConfig`** — `pub struct SchedulerConfig {`
- `struct` **`SchedulerState`** — `pub(crate) struct SchedulerState {`
- `struct` **`SchedulerHandle`** — `pub struct SchedulerHandle {`

### `scheduler::trait`

- `trait` **`TickHandler`** — `pub trait TickHandler {`
- `trait` **`Updatable`** — `pub trait Updatable {`

### `scheduler::type`

- `type` **`TickHandlerRc`** — `pub type TickHandlerRc = Rc<EngineCell<dyn TickHandler>>;`
- `type` **`RafClosureCell`** — `pub type RafClosureCell = Rc<MaybeEngineCell<Closure<dyn FnMut()>>>;`

### `spatial::impl`

- `fn` **`create`** — `pub fn create(cell_size: f64) -> SpatialHashGrid2D {...}`
- `fn` **`with_default_size`** — `pub fn with_default_size() -> SpatialHashGrid2D {...}`
- `fn` **`insert`** — `pub fn insert(&mut self, index: usize, min: Vector2D, max: Vector2D) {...}`
- `fn` **`query`** — `pub fn query(&self, min: Vector2D, max: Vector2D) -> Vec<usize> {...}`
- `fn` **`clear`** — `pub fn clear(&mut self) {...}`
- `fn` **`query_into`** — `pub fn query_into( &self, min: Vector2D, max: Vector2D, out: &mut Vec<usize>, seen: &mut HashSet<usize>, ) {...}`
- `fn` **`create`** — `pub fn create(cell_size: f64) -> SpatialHashGrid3D {...}`
- `fn` **`with_default_size`** — `pub fn with_default_size() -> SpatialHashGrid3D {...}`
- `fn` **`insert`** — `pub fn insert(&mut self, index: usize, min: Vector3D, max: Vector3D) {...}`
- `fn` **`query`** — `pub fn query(&self, min: Vector3D, max: Vector3D) -> Vec<usize> {...}`
- `fn` **`clear`** — `pub fn clear(&mut self) {...}`
- `fn` **`query_into`** — `pub fn query_into( &self, min: Vector3D, max: Vector3D, out: &mut Vec<usize>, seen: &mut HashSet<usize>, ) {...}`

### `spatial::struct`

- `struct` **`SpatialHashGrid2D`** — `pub struct SpatialHashGrid2D {`
- `struct` **`SpatialHashGrid3D`** — `pub struct SpatialHashGrid3D {`

### `spatial::type`

- `type` **`CellKey2D`** — `pub type CellKey2D = (i32, i32);`
- `type` **`CellKey3D`** — `pub type CellKey3D = (i32, i32, i32);`
- `type` **`CellEntries`** — `pub type CellEntries = Vec<usize>;`
- `type` **`SpatialCellMap2D`** — `pub type SpatialCellMap2D = HashMap<CellKey2D, CellEntries>;`
- `type` **`SpatialCellMap3D`** — `pub type SpatialCellMap3D = HashMap<CellKey3D, CellEntries>;`

### `sprite::enum`

- `enum` **`AnimationMode`** — `pub enum AnimationMode {`
- `enum` **`AnimationState`** — `pub enum AnimationState {`

### `sprite::impl`

- `fn` **`from_image`** — `pub fn from_image(image: HtmlImageElement, frame_width: f64, frame_height: f64) -> SpriteSheet {...}`
- `fn` **`frame_source`** — `pub fn frame_source(&self, index: u32) -> Rect {...}`
- `fn` **`frame`** — `pub fn frame(&self, index: u32) -> SpriteFrame {...}`
- `fn` **`animation`** — `pub fn animation( &self, name: &str, start: u32, end: u32, mode: AnimationMode, ) -> SpriteAnimation {...}`
- `fn` **`draw_frame`** — `pub fn draw_frame( &self, context: &CanvasRenderingContext2d, frame_index: u32, transform: &Transform2D, ) {...}`
- `fn` **`create`** — `pub fn create() -> Animator {...}`
- `fn` **`play`** — `pub fn play(&mut self, animation: SpriteAnimation) {...}`
- `fn` **`pause`** — `pub fn pause(&mut self) {...}`
- `fn` **`resume`** — `pub fn resume(&mut self) {...}`
- `fn` **`stop`** — `pub fn stop(&mut self) {...}`
- `fn` **`update`** — `pub fn update(&mut self, delta_time: f64) {...}`
- `fn` **`current_frame_source`** — `pub fn current_frame_source(&self) -> Option<Rect> {...}`
- `fn` **`draw`** — `pub fn draw( &self, context: &CanvasRenderingContext2d, sheet: &SpriteSheet, transform: &Transform2D, ) {...}`

### `sprite::struct`

- `struct` **`SpriteFrame`** — `pub struct SpriteFrame {`
- `struct` **`SpriteSheet`** — `pub struct SpriteSheet {`
- `struct` **`SpriteAnimation`** — `pub struct SpriteAnimation {`
- `struct` **`Animator`** — `pub struct Animator {`

### `timer::impl`

- `fn` **`create`** — `pub fn create(duration: f64) -> Timer {...}`
- `fn` **`create_repeating`** — `pub fn create_repeating(duration: f64) -> Timer {...}`
- `fn` **`update`** — `pub fn update(&mut self, delta_time: f64) -> u32 {...}`
- `fn` **`reset`** — `pub fn reset(&mut self) {...}`
- `fn` **`pause`** — `pub fn pause(&mut self) {...}`
- `fn` **`resume`** — `pub fn resume(&mut self) {...}`
- `fn` **`is_paused`** — `pub fn is_paused(&self) -> bool {...}`
- `fn` **`is_finished`** — `pub fn is_finished(&self) -> bool {...}`
- `fn` **`progress`** — `pub fn progress(&self) -> f64 {...}`
- `fn` **`remaining`** — `pub fn remaining(&self) -> f64 {...}`

### `timer::struct`

- `struct` **`Timer`** — `pub struct Timer {`

### `tween::enum`

- `enum` **`TweenState`** — `pub enum TweenState {`

### `tween::impl`

- `fn` **`create`** — `pub fn create(from: T, to: T, duration: f64) -> Tween<T> {...}`
- `fn` **`with_easing`** — `pub fn with_easing(mut self, easing: Easing) -> Tween<T> {...}`
- `fn` **`with_delay`** — `pub fn with_delay(mut self, delay: f64) -> Tween<T> {...}`
- `fn` **`with_mode`** — `pub fn with_mode(mut self, mode: AnimationMode) -> Tween<T> {...}`
- `fn` **`with_on_complete`** — `pub fn with_on_complete(mut self, on_complete: Rc<dyn Fn()>) -> Tween<T> {...}`
- `fn` **`update`** — `pub fn update(&mut self, delta_time: f64) -> T {...}`
- `fn` **`value`** — `pub fn value(&self) -> T {...}`
- `fn` **`eased_progress`** — `pub fn eased_progress(&self) -> f64 {...}`
- `fn` **`raw_progress`** — `pub fn raw_progress(&self) -> f64 {...}`
- `fn` **`pause`** — `pub fn pause(&mut self) {...}`
- `fn` **`resume`** — `pub fn resume(&mut self) {...}`
- `fn` **`reset`** — `pub fn reset(&mut self) {...}`
- `fn` **`is_finished`** — `pub fn is_finished(&self) -> bool {...}`
- `fn` **`get_state`** — `pub fn get_state(&self) -> TweenState {...}`
- `fn` **`get_duration`** — `pub fn get_duration(&self) -> f64 {...}`

### `tween::struct`

- `struct` **`Tween`** — `pub struct Tween<T: Interpolable + Copy> {`
