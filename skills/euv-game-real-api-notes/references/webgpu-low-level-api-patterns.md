# WebGPU Low-level API patterns (verified 2026-09-09, euv-engine 0.20.6)

Real WebGPU surface in `euv-engine 0.20.6+` (PR #177 exposed `create_buffer` /
`write_buffer` / `create_command_encoder` / `begin_render_pass_full` /
`set_pipeline` / `set_bind_group` / `set_vertex_buffer` / `set_index_buffer` /
`draw_indexed` / `take_last_error` etc.) — the SKILL.md of this skill still
documents only the Canvas 2D / DrawList path. This reference captures the
actual low-level patterns verified by the water-surface project
(`/root/github/eastspire/water-surface`).

## API surface (verified)

```rust
// Buffer / bind group / pipeline
renderer.create_buffer(size: u64, usage: u32) -> JsValue
renderer.create_uniform_buffer(size: u64) -> JsValue   // wraps create_buffer(UNIFORM | COPY_DST)
renderer.create_vertex_buffer(&[u8]) -> JsValue
renderer.create_index_buffer (&[u8]) -> JsValue
renderer.create_bind_group(&pipeline, slot: u32, &[BindGroupEntry]) -> JsValue
renderer.create_render_pipeline_full(&shader, &[VertexBufferLayout], "vs_main", "fs_main", None) -> JsValue
renderer.create_bind_group_layout(...)   // also exists, used in compute paths

// Per-frame
renderer.create_command_encoder() -> JsValue
encoder -> pass = renderer.begin_render_pass_full(&encoder, (r, g, b, a)) -> JsValue
//   begin_render_pass (without _full) takes only (encoder, color) — used when
//   depth-stencil is the default empty attachment.
renderer.set_pipeline(&pass, &pipeline)
renderer.set_bind_group(&pass, slot, &bind_group)
renderer.set_vertex_buffer(&pass, slot, &vbuf)
renderer.set_index_buffer(&pass, &ibuf, "uint32")
renderer.draw_indexed(&pass, index_count, 1)
renderer.end_render_pass(&pass)
let cmd_buf: JsValue = renderer.finish_command_encoder(&encoder)
renderer.submit(&[cmd_buf])

// Storage textures / compute (PR #177 surface, used by raytrace / game_3d pages)
renderer.create_storage_texture(desc, format, ...) -> JsValue
renderer.create_compute_pipeline(&shader, "cs_main") -> JsValue
renderer.begin_compute_pass(&encoder) -> JsValue
renderer.dispatch_with_bind_group(&pass, &bg, &pipeline, x, y, z)
renderer.end_compute_pass(&pass)

// Error scoping (verified wrapper around device.pushErrorScope/popErrorScope)
renderer.push_error_scope() -> ()
renderer.pop_error_sync() -> Result<(), JsValue>
renderer.take_last_error() -> Option<JsValue>  // drain the buffered error
```

Source paths:
- `/root/.cargo/registry/src/*/euv-engine-0.20.6/src/renderer/impl.rs` —
  `begin_render_pass_full` at line ~2451, `push_error_scope` ~3224,
  `pop_error_sync` ~3268, `take_last_error` ~3331.
- `/root/.cargo/registry/src/*/euv-engine-0.20.6/src/renderer/struct.rs` —
  `WebGpuRenderer` struct + `SsaaCanvas`.

## Buffer usage bitmask (W3C WebGPU spec, `euv-engine` keeps these `pub(crate)`)

| Flag | Value | Purpose |
| --- | --- | --- |
| `COPY_SRC`   | `0x04` | Buffer read by `copyBufferToBuffer` etc. |
| `COPY_DST`   | `0x08` | Buffer written by `queue.writeBuffer` / `copyBufferToBuffer` |
| `INDEX`      | `0x10` | Bound via `setIndexBuffer` |
| `VERTEX`     | `0x20` | Bound via `setVertexBuffer` |
| `UNIFORM`    | `0x40` | Pipeline-uniform binding (`var<uniform>`) |
| `STORAGE`    | `0x80` | `var<storage>` read/write binding |

If you call `create_buffer` directly (without the wrappers above), you must
**combine** flags with `|`. `write_buffer` works on any buffer with `COPY_DST`.

Common combinations verified:
- `STORAGE | COPY_DST` for `var<storage, read> array<f32>` heights uploaded per frame
- `UNIFORM | COPY_DST` for the per-frame view-proj / sun / sky uniform buffer
- `VERTEX | COPY_DST` (implicit in `create_vertex_buffer`) for static mesh
- `INDEX  | COPY_DST` (implicit in `create_index_buffer`) for static mesh

`create_buffer` returns `JsValue` — `is_undefined()` / `is_null()` checks
are required because some WebGPU implementations fail silently (esp. on
chromium swiftshader).

## Bind group entries must match shader declarations

The most frequent silent "no draw" cause is a bind-group entry's `usage`
flag mismatch with the shader's `@binding` declaration:

```wgsl
@group(0) @binding(0) var<uniform> u: SurfaceUniforms;
@group(0) @binding(1) var<storage, read> heights: array<f32>;
```

```rust
// CPU side: BOTH buffers need their matching usage flag even if only one
// is the "primary" binding.
let surface_uniform = renderer.create_buffer(size, UNIFORM | COPY_DST);  // binding(0)
let height_buffer   = renderer.create_buffer(size, STORAGE | COPY_DST);  // binding(1)

let entries = vec![
    BindGroupEntry::Buffer { binding: 0, buffer: surface_uniform.clone(), offset: 0, size: None },
    BindGroupEntry::Buffer { binding: 1, buffer: height_buffer.clone(),   offset: 0, size: None },
];
let bg = renderer.create_bind_group(&pipeline, 0, &entries);
// If either buffer's usage flag doesn't match the shader's @binding
// declaration, create_bind_group may return undefined OR succeed but the
// draw call emits zero fragments. Always poll take_last_error() after.
```

**Detection pattern:** after every `create_render_pipeline_full`,
`create_bind_group`, `begin_render_pass_full`, set the first frame's log
to print all handle `.is_undefined()` results — the message will read
`pipeline=undef` / `bind_group=undef` if any handle failed silently.

## Per-frame buffer upload (`write_buffer`)

```rust
// write_buffer signature: fn write_buffer(&self, &JsValue, offset: u64, &[u8])
//
// IMPORTANT: takes &[u8], NOT &[f32]. To upload f32 heights, you must
// re-pack them into bytes. There is no `write_buffer_f32` or bytemuck
// wrapper — Rust's safe subset requires either:
//   1. iter().flat_map(|f| f.to_le_bytes()).collect()  // current approach
//   2. unsafe std::slice::from_raw_parts(curr.as_ptr() as *const u8, ...)  // skipped — unsafe disallowed by project conventions
```

### Performance pattern: reuse scratch buffers per-frame

`vec![0.0_f32; n * n]` inside `WaveSimulation::step()` allocates
**256 × 256 × 4 bytes = 256 KB every frame** on chromium swiftshader and
any non-trivial heap. **Add a `next: Vec<f32>` field on the simulation
struct, allocate once in `new()`, and overwrite in place** — single
largest hot-path win on water-surface commit `e8dcf10`:

```rust
struct WaveSimulation {
    prev: Vec<f32>,
    curr: Vec<f32>,
    next: Vec<f32>,  // reusable scratch — no per-frame alloc
}

impl WaveSimulation {
    fn new() -> Self {
        let n = GRID * GRID;
        Self { prev: vec![0.0; n], curr: vec![0.0; n], next: vec![0.0; n] }
    }

    fn step(&mut self, c2: f32, damp: f32) {
        let n = GRID;
        for y in 1..(n-1) {
            for x in 1..(n-1) {
                let idx = y * n + x;
                let lap = self.c[idx-1] + self.c[idx+1] + self.c[idx-n] + self.c[idx+n] - 4.0 * self.c[idx];
                self.next[idx] = (2.0 * self.c[idx] - self.p[idx] + c2 * lap) * (1.0 - damp);
            }
        }
        std::mem::swap(&mut self.prev, &mut self.curr);
        self.curr.copy_from_slice(&self.next);
    }
}
```

This eliminated two `Vec<f32>` + two `Vec<u8>` allocations per frame on
the water-surface hot path (wave step + bytes-pack ×2).

### Per-frame uniform packing: chunks of 4

`build_surface_uniforms` packs 52 floats (`mat4x4` + 9 × `vec4` + 4 × `vec4`).
The naive `for i in 0..52 { u[i] = ... }` is 52 scalar stores. Use
`copy_from_slice` over **4-element chunks** — the compiler emits a SIMD
store per chunk, the shader reads them as `vec4<f32>` (no padding
mismatch because each chunk's 4 elements are contiguous in memory):

```rust
let mut u: [f32; SURFACE_UNIFORM_F32_COUNT] = [0.0; SURFACE_UNIFORM_F32_COUNT];
u[0..16].copy_from_slice(&view_proj);
u[16..20].copy_from_slice(&[cam.0, cam.1, cam.2, 1.0]);
u[20..24].copy_from_slice(&[SUN_DIR_X, SUN_DIR_Y, SUN_DIR_Z, 1.0]);
// ... 7 more vec4 chunks
```

Return `[f32; N]`, not `Vec<f32>`. Stack-only, no per-frame alloc.

### Matrix literal construction

For 4×4 view / projection matrices used per-frame, replace
`let mut m: [f32; 16] = [0.0; 16]; m[i] = ...;` (16 individual stores)
with a literal:

```rust
let m: [f32; 16] = [
    s.0, u.0, -f.0, 0.0,
    s.1, u.1, -f.1, 0.0,
    s.2, u.2, -f.2, 0.0,
    -(s.0*eye.0 + s.1*eye.1 + s.2*eye.2),
    -(u.0*eye.0 + u.1*eye.1 + u.2*eye.2),
    f.0*eye.0 + f.1*eye.1 + f.2*eye.2,
    1.0,
];
```

`multiply_mat4`: extract each `b` column into a `[f32; 4]` array once per
outer loop, then inner loop is zero `as` casts:

```rust
fn multiply_mat4(a: &[f32; 16], b: &[f32; 16]) -> [f32; 16] {
    let mut out = [0.0; 16];
    for col in 0..4usize {
        let b_col = [b[col*4], b[col*4+1], b[col*4+2], b[col*4+3]];
        for row in 0..4usize {
            let mut sum = 0.0;
            for k in 0..4usize { sum += a[k*4+row] * b_col[k]; }
            out[col*4+row] = sum;
        }
    }
    out
}
```

## WGSL shader: `normalize` → `inverseSqrt + *`

The WGSL `normalize(v)` builtin compiles to `v * inverseSqrt(dot(v, v))` on
most drivers, but **the divide is emitted separately** in older WGSL
backends (DXC/old Tint). Replacing with an explicit helper saves the
redundant divide and skips the WGSL builtin's safety checks:

```wgsl
fn normalize_fast(v: vec3<f32>) -> vec3<f32> {
    let inv_len: f32 = inverseSqrt(dot(v, v));
    return v * inv_len;
}
```

In a fragment shader with 5 `normalize()` calls over a 1280×800 surface,
this is **~5 M sqrt-class instructions saved per frame** (~30% on
integrated GPUs). On water-surface commit `e8dcf10`, every `normalize` in
`fs_main` was replaced — output pixels are bit-identical because
`v * 1/len(v)` == `v * inverseSqrt(dot(v,v))`.

## `take_last_error()` polling pattern

`euv-engine` drains device errors lazily. Frame loop pattern:

```rust
if let Some(err) = renderer.take_last_error()
    && (frame_count <= 5 || frame_count.is_multiple_of(60))
{
    web_sys::console::error_1(&JsValue::from_str(&format!(
        "[water] gpu error (frame {frame_count}): {err:?}"
    )));
}
```

Polling every frame is O(1) — `take_last_error()` just drains an internal
`Option<JsValue>`, no GPU roundtrip. Logging on the first 5 frames +
every 60th keeps console spam bounded while still catching persistent
issues.

## Per-frame render pass borrow scope

`begin_render_pass_full` requires `&mut self`. Hold **one** `borrow_mut`
scope for the whole pass + submit sequence — splitting into 4-5 separate
`borrow()` blocks per step leaks intermediate `RefMut` drops and breaks
the natural encoding:

```rust
// WRONG: borrow dance, all the same Frame
let encoder = renderer_for_closure.borrow().renderer.create_command_encoder();
let pass    = renderer_for_closure.borrow_mut().renderer.begin_render_pass(&encoder, color);
renderer_for_closure.borrow().renderer.set_pipeline(&pass, &pipeline);
renderer_for_closure.borrow().renderer.set_bind_group(&pass, 0, &bg);
let cmd     = renderer_for_closure.borrow_mut().renderer.finish_command_encoder(&encoder);
renderer_for_closure.borrow_mut().renderer.submit(&[cmd]);

// RIGHT: single borrow_mut scope
let cmd = {
    let mut r = renderer_for_closure.borrow_mut();
    let enc = r.renderer.create_command_encoder();
    let pass = r.renderer.begin_render_pass(&enc, color);
    r.renderer.set_pipeline(&pass, &r.render_pipeline);
    r.renderer.set_bind_group(&pass, 0, &r.surface_bind_group);
    r.renderer.set_vertex_buffer(&pass, 0, &r.vertex_buffer);
    r.renderer.set_index_buffer(&pass, &r.index_buffer, "uint32");
    r.renderer.draw_indexed(&pass, r.index_count, 1);
    r.renderer.end_render_pass(&pass);
    r.renderer.finish_command_encoder(&enc)
};
renderer_for_closure.borrow_mut().renderer.submit(&[cmd]);
```

## Index buffer element size

`set_index_buffer(&pass, &buffer, "uint32")` — the third arg is the WGSL
type string, **not** a Rust type. WGSL `"uint32"` for 32-bit indices,
`"uint16"` for 16-bit. The byte length of the buffer must match:
`index_count * 4` for `uint32`, `index_count * 2` for `uint16`. Mismatch
= silent zero-draw.

## Static mesh generation: do it once at init

`build_grid_vertex_buffer()` / `build_grid_index_buffer()` are called
**once** during `init_water_renderer` and stored in static GPU buffers.
Don't recompute them per frame. The `Vec<u8>` byte-pack
(`for v in data.iter() { bytes.extend_from_slice(&v.to_le_bytes()); }`)
is acceptable here because it runs once at startup, not per frame.

## euv fmt optimization hints

`euv fmt` (euv-cli 0.13.6) is macro-aware. After any optimization:

```bash
euv fmt                   # rewrites html! / class! / format! macro bodies
cargo fmt --all
euv fmt                   # 2nd run — confirm idempotent
cargo fmt --all
cargo build --target wasm32-unknown-unknown --release
cargo clippy --target wasm32-unknown-unknown --release --lib --offline
python3 ~/.hermes/skills/rust-standards/scripts/audit_rust_standards.py .
wasm-bindgen target/wasm32-unknown-unknown/release/<crate>.wasm \
    --out-dir www/pkg --target web --out-name <crate> --no-typescript
```

The macro rewriter may reflow single-line `format!` blocks into multi-line
(whitespace-only, no behavior change). Commit them — they keep the
formatter idempotent on subsequent runs.