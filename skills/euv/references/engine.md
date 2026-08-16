---
synced_from: docs-pages/src/euv/usage-introduction/engine.md@0c74235
sync_method: scripts/sync-references.sh
sync_date: 2026-08-16
---

<!--
This file is auto-synced from the upstream docs-pages repo.
Manual edits will be overwritten on the next sync. To pin a custom version
of this reference, add "# manual override:" to its mapping line and the
script will leave it alone.
-->


<Share colorful />

## 概述

```rust
use euv_engine::*;
```

推荐先创建渲染配置，再创建引擎配置：

```rust
let render: RenderConfig = RenderConfig::canvas2d("#game", 800.0, 600.0);
let config: EngineConfig = EngineConfig::create(render);
let mut handle: EngineHandle = Engine::new_handle(config);
let initialized: bool = handle.init_canvas();
if initialized {
    handle.start(handler);
}
```

`RenderConfig::webgl` 和 `EngineHandle::init_webgl` 用于 WebGL 2.0（基于 GLSL `#version 300 es` 着色器），失败时处理 `WebGlInitError`；`RenderConfig::webgpu` 和 `EngineHandle::init_webgpu` 用于 WebGPU（WGSL 着色器），失败时处理 `WebGpuInitError`。生产环境应实现 WebGPU → WebGL 降级路径。只需要标准游戏循环时，也可以直接使用 `Engine::run(config, handler).await`。

## 调度器

```rust
let config: SchedulerConfig = SchedulerConfig::new();
let handle: SchedulerHandle = SchedulerHandle::start(config, handler);
let running: bool = handle.is_running();
let frames: u64 = handle.frame_count();
handle.stop();
```

## 2D 数学与碰撞

```rust
let position: Vector2D = Vector2D::new(10.0, 20.0);
let target: Vector2D = Vector2D::new(100.0, 120.0);
let distance: f64 = position.distance_to(target);
let direction: Vector2D = position.direction_to(target);
let body: RigidBody2D = RigidBody2D::new_dynamic(1, position);
let mut world: PhysicsWorld2D = PhysicsWorld2D::default();
world.add_body(body);
world.step(1.0 / 60.0);
```

3D 对应 API 为 `Vector3D`、`RigidBody3D` 和 `PhysicsWorld3D`。碰撞体使用 `AabbCollider::from_center`、`CircleCollider::from_center`、`AabbCollider3D::from_center` 或 `SphereCollider3D::from_center` 创建。

## Canvas 2D

```rust
let renderer: CanvasRenderer = CanvasRenderer::from_selector("#game", 800.0, 600.0);
let mut list: DrawList = DrawList::create();
list.fill_rect(Vector2D::new(0.0, 0.0), 100.0, 50.0, Color::from_rgb(40, 167, 69));
list.draw_line(Vector2D::zero(), Vector2D::right(), Color::white(), 2.0);
renderer.replay(&list);
```

常用绘制方法包括 `fill_rect`、`stroke_rect`、`fill_circle`、`stroke_circle`、`draw_line`、`fill_text`、`draw_sprite` 和 `draw_image_rect`。使用 `Camera2D::create` 后，可通过 `world_to_screen` 与 `screen_to_world` 转换坐标。

## WebGL

`euv-engine` 0.1.0 提供 `WebGlRenderer` 后端，基于 WebGL 2.0 (`#version 300 es`) 编写 GLSL 着色器，适合需要自定义 shader 的中等复杂度 2D/3D 场景（粒子系统、后处理、几何变换等）。

```rust
use euv_engine::*;

let render: RenderConfig = RenderConfig::webgl("#game-canvas", 800.0, 600.0);
let config: EngineConfig = EngineConfig::create(render);
let mut handle: EngineHandle = Engine::new_handle(config);

match handle.init_webgl() {
    Ok(renderer) => {
        // renderer: WebGlRenderer — 拥有 WebGL2 上下文，可直接编译 shader、绘制几何
        handle.start(handler);
    }
    Err(err) => {
        // WebGlInitError — 浏览器不支持或上下文创建失败
        web_sys::console::error_1(&format!("WebGL init failed: {:?}", err).into());
    }
}
```

### 编译与链接着色器

`WebGlRenderer::create_program(vertex_source, fragment_source)` 一次性完成编译与链接，返回 `Result<WebGlProgram, WebGlProgramError>`，失败时携带 GLSL info log：

```rust
const VERTEX_SRC: &str = r#"#version 300 es
in vec2 a_position;
uniform vec2 u_offset;
void main() {
    gl_Position = vec4(a_position + u_offset, 0.0, 1.0);
}
"#;

const FRAGMENT_SRC: &str = r#"#version 300 es
precision mediump float;
uniform vec4 u_color;
out vec4 outColor;
void main() {
    outColor = u_color;
}
"#;

let program: WebGlProgram = renderer
    .create_program(VERTEX_SRC, FRAGMENT_SRC)
    .expect("shader link");
```

### 设置 uniform

`WebGlRenderer` 提供 uniform 设置便捷方法（vec2 / vec4 / int / float），底层调用 `getUniformLocation` + `uniformXxx`，缺失的 uniform 会被静默忽略（与原生 WebGL 行为一致）：

```rust
renderer.set_uniform_2f(&program, "u_offset", 0.5, 0.0);
renderer.set_uniform_4f(&program, "u_color", 1.0, 0.4, 0.7, 1.0);
renderer.set_uniform_1i(&program, "u_mode", 1);
renderer.set_uniform_1f(&program, "u_time", elapsed);
```

### 常用操作

| 方法                                                     | 说明                                              |
| -------------------------------------------------------- | ------------------------------------------------- |
| `RenderConfig::webgl(selector, width, height)`           | 创建 WebGL 渲染配置                                |
| `EngineHandle::init_webgl()`                             | 初始化 WebGL 后端，返回 `WebGlRenderer`           |
| `handle.init_webgl()?`                                   | `Result<WebGlRenderer, WebGlInitError>`          |
| `WebGlRenderer::create_program(vs, fs)`                  | 编译并链接着色器程序                               |
| `renderer.set_uniform_2f(&prog, name, x, y)`            | 设置 `vec2` uniform                              |
| `renderer.set_uniform_4f(&prog, name, x, y, z, w)`      | 设置 `vec4` uniform                              |
| `renderer.set_uniform_1i(&prog, name, value)`           | 设置 `int` uniform                               |
| `renderer.set_uniform_1f(&prog, name, value)`           | 设置 `float` uniform                             |

> [!tip]
>
> 当浏览器不支持 WebGPU，但 WebGL 2.0 可用时（如 iOS Safari、旧版浏览器），推荐使用 `init_webgl` 作为回退路径。也可以在初始化时同时尝试 `init_webgpu`，失败时回退 `init_webgl`。

## WebGPU

`euv-engine` 0.1.0 还提供 `WebGpuRenderer` 后端，基于 WGSL 编写着色器，适合现代浏览器上的高性能 GPU 渲染场景。

```rust
use euv_engine::*;

let render: RenderConfig = RenderConfig::webgpu("#game-canvas", 800.0, 600.0);
let config: EngineConfig = EngineConfig::create(render);
let mut handle: EngineHandle = Engine::new_handle(config);

match handle.init_webgpu() {
    Ok(renderer) => {
        // renderer: WebGpuRenderer — 提供 WGSL 着色器编译、渲染管线、绑定组等
        handle.start(handler);
    }
    Err(err) => {
        // WebGpuInitError — 浏览器无 WebGPU 支持时降级
        web_sys::console::error_1(&format!("WebGPU init failed: {:?}", err).into());
    }
}
```

### 常用操作

| 方法                                                  | 说明                                              |
| ----------------------------------------------------- | ------------------------------------------------- |
| `RenderConfig::webgpu(selector, width, height)`       | 创建 WebGPU 渲染配置                               |
| `EngineHandle::init_webgpu()`                         | 初始化 WebGPU 后端，返回 `WebGpuRenderer`         |
| `handle.init_webgpu()?`                               | `Result<WebGpuRenderer, WebGpuInitError>`        |

> [!warning]
>
> WebGPU 在 Safari / iOS 上截至 2026 年 8 月仍处于技术预览状态。生产环境应同时实现 `init_webgl` 降级路径。

## 精灵动画

```rust
let sheet: SpriteSheet = SpriteSheet::from_image(image, 32.0, 32.0);
let animation: SpriteAnimation = sheet.animation("walk", vec![0, 1, 2, 3], 10.0, AnimationMode::Loop);
let mut animator: Animator = Animator::create();
animator.play(animation);
animator.update(delta_time);
```

## 资源与音频

`AssetLoader::default()` 管理图片资源；`AssetLoader::load_image` 加载资源，使用 `progress`、`is_all_loaded` 和 `get_image` 查询状态。音频使用 `GameAudioContext::create` 创建上下文，再用 `AudioClip::create`、`play`、`stop` 和 `update_volume` 控制播放。

## 事件与实体

`EventBus::create` 创建事件总线，使用 `subscribe`、`emit`、`unsubscribe_all` 和 `handler_count` 管理事件。实体使用 `Entity::create` 或 `Entity::create_at` 创建，并可通过 `add_component`、`add_tag`、`update`、`render` 与 `destroy` 管理。

## 空间查询

```rust
let mut grid: SpatialHashGrid2D = SpatialHashGrid2D::with_default_size();
grid.insert(0, Vector2D::zero(), Vector2D::new(10.0, 10.0));
let candidates: Vec<usize> = grid.query(Vector2D::zero(), Vector2D::new(20.0, 20.0));
grid.clear();
```

3D 使用 `SpatialHashGrid3D`，调用方式相同但坐标参数为 `Vector3D`。

`euv-engine` 是一个基于 euv 框架构建的高性能 2D/3D 游戏引擎，专为 WebAssembly 设计。它提供 ECS 风格实体系统、固定时间步游戏循环、Canvas 渲染、物理模拟、碰撞检测、精灵动画、音频和资源加载等功能。

通过 `cargo add euv-engine` 或在工作区中引用即可使用。

```toml
[dependencies]
euv-engine = "*"
```

```rust
use euv_engine::*;
```

> [!tip]
>
> `euv-engine` 依赖 `euv` 核心库，可与 `euv-ui` 组件库在 euv 应用中混合使用。

## 快速开始

### 1. 创建游戏循环

通过 `SchedulerHandle::start` 启动固定时间步游戏循环，传入 `SchedulerConfig` 和实现了 `TickHandler` trait 的处理器：

```rust
use euv_engine::*;
use std::rc::Rc;
use std::cell::RefCell;

struct MyGame {
    frame_count: u64,
}

impl TickHandler for MyGame {
    fn on_update(&mut self, delta_time: f64) {
        // 固定时间步更新逻辑（每秒 60 次）
        // 所有游戏逻辑、物理、状态变更均应在此处执行
        self.frame_count += 1;
    }

    fn on_render(&mut self, interpolation: f64) {
        // 每帧渲染（可变帧率，interpolation 为 0.0~1.0 的插值因子）
        // 在此处绘制 Canvas
    }
}

// 启动游戏循环
let config: SchedulerConfig = SchedulerConfig::new(1.0 / 60.0, 0.25);
let handler: TickHandlerRc = Rc::new(RefCell::new(MyGame { frame_count: 0 }));
let handle: SchedulerHandle = SchedulerHandle::start(config, handler);

// 停止游戏循环
// handle.stop();
```

`scheduler` 使用 `requestAnimationFrame` 驱动循环，采用固定时间步（如 1/60 秒），确保物理和游戏逻辑以确定性的速率更新，同时渲染帧率适应显示设备。

### SchedulerConfig

| 字段             | 类型  | 说明                                          |
| ---------------- | ----- | --------------------------------------------- |
| `fixed_timestep` | `f64` | 固定模拟时间步（秒），如 `1.0 / 60.0` 为 60Hz |
| `max_frame_time` | `f64` | 最大帧时间限制（秒），超时时开始丢弃更新      |

### SchedulerHandle 方法

| 方法                                      | 返回值            | 说明                         |
| ----------------------------------------- | ----------------- | ---------------------------- |
| `SchedulerHandle::start(config, handler)` | `SchedulerHandle` | 启动游戏循环                 |
| `handle.stop()`                           | `()`              | 停止游戏循环并取消动画帧请求 |
| `handle.is_running()`                     | `bool`            | 检查调度器是否正在运行       |
| `handle.update_count()`                   | `u64`             | 返回累计固定更新步数         |
| `handle.frame_count()`                    | `u64`             | 返回累计渲染帧数             |

## 实体与组件

引擎提供 ECS 风格实体系统，通过 `Entity` 结构体和 `Component` trait 定义游戏对象和行为。

### Entity

`Entity` 管理一组组件，每个实体具有唯一 ID、名称、世界变换、标签和活跃状态。

```rust
// 创建实体
let player: Entity = Entity::create("player");
let enemy: Entity = Entity::create_at(Vector2D::new(100.0, 200.0));

// 标签
player.add_tag("friendly".to_string());
player.has_tag("friendly"); // true
```

| 方法                                    | 说明                     |
| --------------------------------------- | ------------------------ |
| `Entity::create(name)`                  | 创建以 `name` 命名的实体 |
| `Entity::create_at(position)`           | 在指定位置创建实体       |
| `entity.add_tag(tag)`                   | 添加标签                 |
| `entity.has_tag(tag)`                   | 检查标签                 |
| `entity.add_component(component)`       | 添加组件                 |
| `entity.get_component_by_name(name)`    | 按名称查找组件           |
| `entity.remove_component_by_name(name)` | 按名称移除组件           |
| `entity.update(delta_time)`             | 更新所有组件             |
| `entity.render(context)`                | 渲染所有组件             |
| `entity.destroy()`                      | 销毁所有组件             |

### Component trait

自定义组件实现 `Component` trait：

```rust
use euv_engine::*;

struct MovementComponent {
    speed: f64,
}

impl Component for MovementComponent {
    fn on_start(&mut self) {
        // 组件添加到活跃实体时调用
    }

    fn on_update(&mut self, delta_time: f64) {
        // 每帧更新，delta_time 为固定时间步长
    }

    fn on_render(&self, context: &CanvasRenderingContext2d, transform: &Transform2D) {
        // 在 Canvas 上绘制
    }

    fn on_destroy(&mut self) {
        // 组件销毁时清理
    }

    fn name(&self) -> &str {
        "MovementComponent"
    }
}
```

组件通过 `entity.add_component()` 附加，框架自动调用生命周期方法。

## 场景管理

通过 `SceneManager` 注册和管理多个游戏场景。

```rust
use euv_engine::*;
use std::rc::Rc;
use std::cell::RefCell;

struct MenuScene;

impl Scene for MenuScene {
    fn on_enter(&mut self) {
        // 进入场景时调用
    }
    fn on_exit(&mut self) {
        // 离开场景时调用
    }
    fn on_update(&mut self, delta_time: f64) {
        // 场景更新逻辑
    }
    fn on_render(&self, context: &CanvasRenderingContext2d) {
        // 场景渲染
    }
    fn name(&self) -> &str {
        "menu"
    }
}

let mut manager: SceneManager = SceneManager::new();

// 注册场景
let menu: SceneRc = SceneManager::create_scene(MenuScene);
manager.register("menu".to_string(), menu);

// 切换到场景
manager.switch_to("menu");

// 每帧调用
manager.update(1.0 / 60.0);
manager.render(&context);
```

| 方法                                | 说明                 |
| ----------------------------------- | -------------------- |
| `SceneManager::new()`               | 创建新的场景管理器   |
| `SceneManager::create_scene(scene)` | 包装场景为 `SceneRc` |
| `manager.register(name, scene)`     | 注册场景             |
| `manager.switch_to(name)`           | 立即切换到指定场景   |
| `manager.request_transition(name)`  | 请求延迟场景切换     |
| `manager.update(delta_time)`        | 更新当前场景         |
| `manager.render(context)`           | 渲染当前场景         |
| `manager.has_scene(name)`           | 检查场景是否已注册   |
| `manager.current_name()`            | 获取当前场景名       |

## 输入管理

通过 `Input` 和 `InputState` 管理键盘、鼠标和触摸输入。

```rust
let mut input_state: InputState = InputState::new();

// 在事件回调中更新输入状态
input_state.press_key("Space".to_string());
input_state.press_mouse_button(MouseButton::Left, Vector2D::new(100.0, 200.0));

// 在更新逻辑中检查输入
input_state.is_key_pressed("Space");
input_state.is_key_held("ArrowLeft");
input_state.is_mouse_button_held(MouseButton::Left);

// 在事件中提取数据
let key_code: String = Input::extract_key_code(&event);
let mouse_pos: Vector2D = Input::extract_mouse_position(&event);

// 每帧结束时清理
input_state.end_frame();
```

### Input 方法

| 方法                                    | 返回值        | 说明                   |
| --------------------------------------- | ------------- | ---------------------- |
| `Input::extract_key_code(&event)`       | `String`      | 从键盘事件提取按键代码 |
| `Input::extract_mouse_button(&event)`   | `MouseButton` | 从鼠标事件提取按钮     |
| `Input::extract_mouse_position(&event)` | `Vector2D`    | 从鼠标事件提取坐标     |

### InputState 方法

| 方法                                   | 说明                       |
| -------------------------------------- | -------------------------- |
| `press_key(key_code)`                  | 记录按键按下               |
| `release_key(key_code)`                | 记录按键释放               |
| `is_key_pressed(key_code)`             | 检查按键是否在本帧按下     |
| `is_key_held(key_code)`                | 检查按键是否按住           |
| `is_key_released(key_code)`            | 检查按键是否在本帧释放     |
| `press_mouse_button(button, position)` | 记录鼠标按钮按下           |
| `release_mouse_button(button)`         | 记录鼠标按钮释放           |
| `is_mouse_button_pressed(button)`      | 检查鼠标按钮是否在本帧按下 |
| `is_mouse_button_held(button)`         | 检查鼠标按钮是否按住       |
| `update_mouse_position(position)`      | 更新鼠标位置并计算 delta   |
| `start_touch(identifier, position)`    | 记录触摸开始               |
| `end_touch(identifier)`                | 记录触摸结束               |
| `end_frame()`                          | 清理帧数据                 |

## 物理模拟

通过 `PhysicsWorld2D`（或 `PhysicsWorld3D`）管理 2D（或 3D）物理世界。

```rust
let config: PhysicsConfig = PhysicsConfig::new(
    Vector2D::new(0.0, 980.0), // 重力（像素/秒²）
    0.01,                       // 线性阻尼
    0.1,                        // 角阻尼
);

let mut world: PhysicsWorld2D = PhysicsWorld2D::new(config);

// 创建刚体
let body: RigidBody2D = RigidBody2D::new(
    1,                              // id
    Vector2D::new(400.0, 300.0),    // position
    Vector2D::new(0.0, 0.0),        // velocity
    Vector2D::new(0.0, 0.0),        // force_accumulator
    0.0,                            // rotation
    0.0,                            // angular_velocity
    1.0,                            // mass
    1.0,                            // inverse_mass
    0.5,                            // restitution（弹力系数，0.0~1.0）
    0.3,                            // friction（摩擦系数）
    BodyType::Dynamic,              // 刚体类型：Dynamic / Static / Kinematic
    None,                           // collider（可选碰撞体）
);
```

| 字段/方法                       | 说明                               |
| ------------------------------- | ---------------------------------- |
| `PhysicsConfig.gravity`         | 重力加速度向量                     |
| `PhysicsConfig.linear_damping`  | 线速度阻尼系数                     |
| `PhysicsConfig.angular_damping` | 角速度阻尼系数                     |
| `RigidBody2D.mass`              | 质量（0 = 静态刚体）               |
| `RigidBody2D.restitution`       | 弹力系数（0.0~1.0）                |
| `RigidBody2D.friction`          | 摩擦系数                           |
| `RigidBody2D.body_type`         | `Dynamic` / `Static` / `Kinematic` |

## 碰撞检测

通过 `Collider` trait 实现碰撞检测，支持 AABB 和圆形两种形状。

```rust
// 检查点是否在碰撞体内
collider.contains_point(Vector2D::new(50.0, 50.0));
```

| 方法                             | 说明                              |
| -------------------------------- | --------------------------------- |
| `collider.shape()`               | 返回形状类型（`Aabb` / `Circle`） |
| `collider.bounding_box()`        | 返回包围盒                        |
| `collider.contains_point(point)` | 判断点是否在内部                  |
| `collider.center()`              | 返回中心点                        |

## 精灵与动画

通过 `SpriteSheet`、`SpriteFrame`、`SpriteAnimation` 和 `Animator` 管理精灵动画。

```rust
// 定义精灵帧
let frame: SpriteFrame = SpriteFrame::new(
    Rect::new(0.0, 0.0, 32.0, 32.0),   // 源矩形
    0.1,                                  // 帧时长（秒）
);

// 创建动画片段
let walk_anim: SpriteAnimation = SpriteAnimation::new(
    "walk".to_string(),
    vec![frame],
    AnimationMode::Loop,    // Loop / Once / PingPong
);

// 推荐：用 Animator::create() + play() 启动，避免手填 7 个字段
let mut animator: Animator = Animator::create();
animator.play(walk_anim);
```

| 动画模式                  | 说明              |
| ------------------------- | ----------------- |
| `AnimationMode::Loop`     | 循环播放          |
| `AnimationMode::Once`     | 单次播放          |
| `AnimationMode::PingPong` | 正向→反向交替循环 |

## 数学工具

通过 `Numeric`、`Vector2D`、`Vector3D`、`Transform2D`、`Transform3D`、`Rect`、`Color`、`Circle` 等类型提供基础数学和几何运算。

```rust
// 数学工具
Numeric::clamp(15.0, 0.0, 10.0);       // 10.0
Numeric::lerp(0.0, 100.0, 0.5);        // 50.0
Numeric::deg_to_rad(180.0);             // π
Numeric::rad_to_deg(3.14159);          // 180.0

// 2D 向量
let v1: Vector2D = Vector2D::new(3.0, 4.0);
let v2: Vector2D = Vector2D::new(1.0, 2.0);
let sum: Vector2D = v1 + v2;        // 向量加法
let dot: f64 = v1.dot(v2);          // 点积
let len: f64 = v1.magnitude();      // 长度（标量）
let norm: Vector2D = v1.normalized(); // 归一化（返回新向量）
let mut v1_mut: Vector2D = v1;      // 若需就地归一化
v1_mut.normalize();                 // mutate 自身

// 变换
let transform: Transform2D = Transform2D::identity();
// position、rotation、scale 可通过 lombok Data 宏生成的 getter 访问
// 例如：transform.get_position() / transform.get_rotation() / transform.get_scale()
```

## 音频

通过 `GameAudioContext` 和 `AudioClip` 管理音频播放和音量控制。

```rust
let audio_ctx: GameAudioContext = GameAudioContext::create();

// 设置主音量（0.0~1.0）
audio_ctx.apply_master_volume(0.5);

// 控制音频上下文生命周期
audio_ctx.resume();
audio_ctx.suspend();
audio_ctx.close();

// 查询音频信息
let sample_rate: f64 = audio_ctx.sample_rate();
let current_time: f64 = audio_ctx.current_time();

// 创建并播放音频片段
let clip: AudioClip = AudioClip::create(buffer, "explosion".to_string());
clip.play(&audio_ctx);
```

## 资源加载

通过 `AssetLoader` 和 `AssetCache` 加载和管理图片资源。

```rust
use euv_engine::*;

// 直接构造图片元素（不缓存）
let image: Option<HtmlImageElement> =
    AssetLoader::create_image_element("assets/player.png");

// 或使用 AssetLoader 异步加载（load_image 是 &mut self，同步入队 + 通过 onload 回调完成）
let mut loader: AssetLoader = AssetLoader::default();
loader.load_image("assets/player.png".to_string());
// 检查加载进度
let progress: f64 = loader.progress();
let is_done: bool = loader.is_all_loaded();
```

| 类型          | 说明                                  |
| ------------- | ------------------------------------- |
| `AssetLoader` | 异步资源加载器，将资源存入共享缓存    |
| `AssetCache`  | 资源缓存，按 URL 键值存储已加载的资源 |

## Renderable trait

实现了 `Renderable` trait 的类型可以在 Canvas 上绘制。

```rust
pub trait Renderable {
    fn draw(&self, context: &CanvasRenderingContext2d, transform: &Transform2D);
}
```

## 与 euv 集成

`euv-engine` 可以在 euv 应用中作为独立游戏循环运行，通过 Canvas 渲染：

```rust
use euv::*;
use euv_engine::*;

// 在 euv 组件中获取 canvas 元素并启动引擎
let canvas: HtmlCanvasElement = document().unwrap()
    .get_element_by_id("game-canvas")
    .unwrap()
    .dyn_into::<HtmlCanvasElement>()
    .unwrap();
let context: CanvasRenderingContext2d = canvas
    .get_context("2d")
    .unwrap()
    .unwrap()
    .dyn_into()
    .unwrap();

// 创建游戏处理器
struct Game;
impl TickHandler for Game {
    fn on_update(&mut self, dt: f64) {}
    fn on_render(&mut self, interpolation: f64) {}
}

// 启动循环
let handle = SchedulerHandle::start(
    SchedulerConfig::new(1.0 / 60.0, 0.25),
    Rc::new(RefCell::new(Game)),
);
```

## 空间哈希网格

通过 `SpatialHashGrid2D` 和 `SpatialHashGrid3D` 实现宽阶段碰撞剔除，将碰撞检测从 O(n²) 降低到近 O(n)：

```rust
// 创建 2D 空间哈希网格
let mut grid: SpatialHashGrid2D = SpatialHashGrid2D::create(64.0);
// 或使用默认 cell size
let mut grid: SpatialHashGrid2D = SpatialHashGrid2D::with_default_size();

// 插入条目（使用世界空间 AABB）
grid.insert(0, Vector2D::new(0.0, 0.0), Vector2D::new(32.0, 32.0));

// 查询候选索引
let candidates: Vec<usize> = grid.query(
    Vector2D::new(0.0, 0.0),
    Vector2D::new(64.0, 64.0),
);

// 清空网格
grid.clear();
```

`SpatialHashGrid3D` 用法相同，只是 `insert` 和 `query` 接收 `Vector3D` 参数。

## 实体事件总线

通过 `EventBus` 实现实体间的解耦通信，支持 `EntityEvent` 事件订阅和广播：

```rust
use euv_engine::*;

let mut bus: EventBus = EventBus::create();

// 订阅事件（handler 类型是 Rc<dyn Fn(&EntityEvent)>）
bus.subscribe(
    "player_jump".to_string(),
    Rc::new(|event: &EntityEvent| {
        web_sys::console::log_1(&"Player jumped".into());
        let _ = event;
    }),
);

// 发布事件
bus.emit(&EntityEvent::Custom {
    name: "player_jump".to_string(),
    data: "".to_string(),
});

// 取消所有订阅
bus.unsubscribe_all("player_jump");

// 查询订阅者数量
let count: usize = bus.handler_count("player_jump");
```

### EntityEvent 变体

| 变体                                    | 说明                        |
| --------------------------------------- | --------------------------- |
| `Collision { other_id, normal, depth }` | 实体与其他实体发生碰撞      |
| `TriggerEnter { tag }`                  | 进入标记为 `tag` 的触发区域 |
| `TriggerExit { tag }`                   | 离开标记为 `tag` 的触发区域 |
| `Spawn`                                 | 实体被生成到场景            |
| `Destroy`                               | 实体被销毁并从场景移除      |
| `Custom { name, data }`                 | 自定义事件，携带字符串数据  |

## Canvas 2D 渲染

`CanvasRenderer` 封装 2D Canvas 上下文，提供填充/描边/变换/文字/渐变/阴影等基础绘图能力。从 CSS 选择器构造，自动获取上下文并创建 `Camera2D`：

```rust
use euv_engine::*;

// 从选择器构造（宽 800px × 高 600px）
let mut renderer: CanvasRenderer = CanvasRenderer::from_selector("#game-canvas", 800.0, 600.0)
    .expect("canvas not found");

// 清屏（深蓝背景）
renderer.clear_color("#0f172a");

// 状态管理
renderer.save();
renderer.set_fill_color("#4f46e5");
renderer.fill_rect(Vector2D::new(100.0, 100.0), 200.0, 80.0);
renderer.restore();

// 摄像机控制
renderer.apply_camera();
let camera: Camera2D = renderer.get_camera();
let screen: Vector2D = camera.world_to_screen(Vector2D::new(50.0, 50.0));

// 文本绘制
renderer.set_font(CanvasRenderer::font(18.0, "sans-serif"));
renderer.fill_text("Hello euv", Vector2D::new(20.0, 30.0));

// 渐变
let gradient: LinearGradient = LinearGradient::create(
    Vector2D::new(0.0, 0.0),
    Vector2D::new(200.0, 0.0),
    vec![(0.0, "#4f46e5".to_string()), (1.0, "#7c3aed".to_string())],
);
renderer.set_linear_gradient_fill(&gradient);
renderer.fill_rect(Vector2D::new(0.0, 200.0), 200.0, 100.0);
```

### CanvasRenderer 方法

| 方法                                                                                     | 说明                                      |
| ---------------------------------------------------------------------------------------- | ----------------------------------------- |
| `CanvasRenderer::from_selector(selector, w, h) -> Option<CanvasRenderer>`                | 从选择器构造（**核心入口**）              |
| `CanvasRenderer::font(size, family) -> String` / `default_font() -> String`              | 生成/获取默认 CSS 字体字符串              |
| `CanvasRenderer::detect_dpr() -> f64`                                                    | 检测设备像素比（DPR）                     |
| `save() / restore()`                                                                     | 上下文状态栈                              |
| `clear() / clear_color(color)`                                                           | 清屏                                      |
| `set_fill_color / set_stroke_color / set_line_width / set_global_alpha / set_blend_mode` | 样式                                      |
| `set_shadow / clear_shadow`                                                              | 阴影                                      |
| `fill_rect / stroke_rect / fill_circle / stroke_circle / draw_line / fill_text`          | 基础图形                                  |
| `draw_image / draw_image_rect`                                                           | 绘制 `HtmlImageElement`                   |
| `set_linear_gradient_fill / set_radial_gradient_fill` + 同 stroke 变体                   | 渐变                                      |
| `apply_camera()`                                                                         | 应用内置 `Camera2D` 变换到上下文          |
| `get_camera() -> Camera2D`                                                               | 访问摄像机（lombok Data 宏生成的 getter） |

## Camera

`Camera2D` 和 `Camera3D` 负责世界坐标与屏幕坐标的转换，并提供视图/投影矩阵（3D）：

```rust
// 2D 摄像机
let mut camera: Camera2D = Camera2D::create(800.0, 600.0);
camera.translate(Vector2D::new(10.0, 0.0));
camera.zoom_by(1.5);
let world_pos: Vector2D = camera.screen_to_world(Vector2D::new(400.0, 300.0));

// 3D 摄像机（position → target）
let mut camera3d: Camera3D = Camera3D::create(
    Vector3D::new(0.0, 0.0, 5.0),     // eye position
    Vector3D::new(0.0, 0.0, 0.0),     // target
    800.0,                            // viewport_width
    600.0,                            // viewport_height
);
let view_proj: Matrix4x4 = camera3d.view_proj_matrix();
let in_view: bool = camera3d.in_frustum(Vector3D::new(1.0, 1.0, 1.0));
camera3d.orbit(0.1, 0.05); // 旋转 yaw/pitch
```

## 物理仿真（完整 API）

`PhysicsWorld2D` 的 `step` 是推进物理的关键调用，每帧触发：

```rust
use euv_engine::*;

let mut world: PhysicsWorld2D = PhysicsWorld2D::default();

// 推荐：用 new_dynamic / new_static 构造刚体（无需手填 12 字段）
let mut player: RigidBody2D = RigidBody2D::new_dynamic(1, Vector2D::new(100.0, 100.0));
player.update_collider(BodyCollider::Aabb(AabbCollider::from_center(
    Vector2D::new(100.0, 100.0), 32.0, 32.0,
)));

// add_body 会消费 body 自身。后续 mutate 通过 world.get_body_mut(id) 拿可变引用
world.add_body(player);

if let Some(player_ref) = world.get_body_mut(1) {
    player_ref.apply_force(Vector2D::new(0.0, -980.0));  // 重力
}

// 每帧推进（包含 resolve_collisions）
world.step(1.0 / 60.0);
```

### PhysicsWorld2D 方法

| 方法                                                                                    | 说明                                  |
| --------------------------------------------------------------------------------------- | ------------------------------------- |
| `PhysicsWorld2D::default() / new(config) / with_config(config)`                         | 构造                                  |
| `add_body(body)` / `remove_body(id)`                                                    | 增删刚体                              |
| `get_body(id) -> Option<&RigidBody2D>` / `get_body_mut(id) -> Option<&mut RigidBody2D>` | 访问                                  |
| `step(delta_time)`                                                                      | **推进物理并自动 resolve_collisions** |

### RigidBody2D 操作

| 方法                                             | 说明                           |
| ------------------------------------------------ | ------------------------------ |
| `RigidBody2D::new_dynamic(id, position) -> Self` | 动态刚体快捷构造               |
| `RigidBody2D::new_static(id, position) -> Self`  | 静态刚体快捷构造               |
| `apply_force(force) / apply_impulse(impulse)`    | 受力（仅 Dynamic 生效）        |
| `update_mass(mass)`                              | 动态更新质量（`0` = 转为静态） |
| `update_collider(BodyCollider)`                  | 挂载碰撞体                     |
| `is_dynamic() -> bool`                           | 查询类型                       |
| `bounding_box() -> Option<Rect>`                 | 当前包围盒                     |

`PhysicsWorld3D` / `RigidBody3D` 的方法集合与 2D 一致，3D 版本的 `apply_force` / `apply_torque` 接收 `Vector3D`，碰撞体为 `AabbCollider3D` / `SphereCollider3D`，包围盒类型为 `AABB3D`。

## 精灵动画操作

`Animator` 控制动画播放，`SpriteSheet` 负责从图片切帧：

```rust
use euv_engine::*;

let image: HtmlImageElement = AssetLoader::create_image_element("assets/hero.png")
    .expect("image not found");
let sheet: SpriteSheet = SpriteSheet::from_image(image, 32.0, 32.0);

// 创建动画（10..18 帧，默认 duration 0.1s）
let walk: SpriteAnimation = sheet.animation("walk", 10, 18, AnimationMode::Loop);

// 播放
let mut animator: Animator = Animator::create();
animator.play(walk);

// 每帧推进 + 绘制
// 实际调用方传入 context（Canvas 2D 上下文）和 transform（entity 的 Transform2D）
let delta_time: f64 = 1.0 / 60.0;
animator.update(delta_time);
// animator.draw(&context, &sheet, &transform);  // 见 CanvasRenderer 节
```

### Animator 方法

| 方法                                                  | 说明                                      |
| ----------------------------------------------------- | ----------------------------------------- |
| `Animator::create() -> Animator`                      | 默认 paused 状态                          |
| `play(animation)` / `pause()` / `resume()` / `stop()` | 播放控制（`stop` = 重置 + paused）        |
| `update(delta_time)`                                  | 推进帧（每帧调用）                        |
| `current_frame_source() -> Option<Rect>`              | 当前帧源矩形                              |
| `draw(ctx, sheet, transform)`                         | 按当前状态绘制（含 flip_x / flip_y 支持） |

### SpriteSheet 方法

| 方法                                                       | 说明                                |
| ---------------------------------------------------------- | ----------------------------------- |
| `SpriteSheet::from_image(image, frame_w, frame_h) -> Self` | 自动计算 columns/rows               |
| `frame_source(index) -> Rect`                              | 第 index 帧的源矩形                 |
| `frame(index) -> SpriteFrame`                              | 第 index 帧（默认 duration = 0.1s） |
| `animation(name, start, end, mode) -> SpriteAnimation`     | 创建动画片段                        |
| `draw_frame(ctx, index, transform)`                        | 绘制单帧                            |

<Bottom />
