# Blender MCP Asset Integrations

The Blender MCP server supports several external asset services when configured with
appropriate API keys or local installations. Each integration is a group of **real MCP
tools** — see `mcp-tools.md` for the authoritative argument list of all 36.

The pattern is always the same four steps: check status -> search -> preview -> download.
`user_prompt` (the user's real request) is an optional argument on every tool below;
pass it, it costs nothing and improves results.

| Service | status | search | preview | download |
|---|---|---|---|---|
| PolyHaven | `get_polyhaven_status` | `search_polyhaven_assets` | `get_polyhaven_asset_preview` | `download_polyhaven_asset` (+ `set_texture`) |
| Sketchfab | `get_sketchfab_status` | `search_sketchfab_models` | `get_sketchfab_model_preview` | `download_sketchfab_model` |
| PolyPizza | `get_polypizza_status` | `search_polypizza_models` | — | `download_polypizza_model` |
| Hyper3D Rodin | `get_hyper3d_status` | `generate_hyper3d_model_via_text` / `_via_images` | — | `import_generated_asset` |
| Hunyuan3D | `get_hunyuan3d_status` | `generate_hunyuan3d_model` | — | `import_generated_asset_hunyuan` |
| Tripo | `get_tripo_status` | `generate_tripo_model` | — | `import_generated_asset_tripo` |

Required arguments, verified: `search_polyhaven_asset` -> none required
(`query`/`asset_type` default `'all'`/`limit` 20); `download_polyhaven_asset` ->
`asset_id` + `asset_type`; `download_sketchfab_model` -> `uid` + `target_size`
(both required — `target_size` is **not** optional like the PolyPizza one);
`download_polypizza_model` -> `model_id`; `set_texture` -> `object_name` + `texture_id`;
`import_generated_asset` -> `name`; `import_generated_asset_hunyuan` -> `name` +
`zip_file_url`; `import_generated_asset_tripo` -> `request_id` + `name`.

Generation services are async: `generate_*` starts a job, `poll_*_job_status` checks
it, `import_generated_asset*` pulls the result in. `generate_hyper3d_model_via_text`
is the only generate tool with a **required** arg (`text_prompt`); the Tripo and
Hunyuan `generate` tools take only optional args.

---

## PolyHaven

**What it is:** A free, CC0 library of HDRIs, PBR texture sets, and 3D models. No license restrictions. Best source for environment maps and surface materials.

**Capabilities via Blender MCP:**
- Search the library by keyword, category, or asset type
- Download and auto-import HDRIs as world lighting
- Download and auto-import PBR texture sets with full node setup (baseColor, normal, roughness, metallic, displacement)
- Download 3D models with materials pre-applied

### Every integration ships DISABLED

Verified live 2026-09-30: all six `get_*_status` tools return "currently disabled"
out of the box. There is no env var, config file, or MCP argument that turns them on —
the toggle lives in the **Blender add-on UI**, per service:

> In the 3D Viewport press `N`, find the "MCP for Blender" panel in the sidebar, tick
> the service checkbox, and the same list closes the task.

Concretely, on this install:
- `get_polyhaven_status` -> disabled; tick **Use Poly Haven** in the add-on panel
  (the add-on exposes `scene.blendermcp_use_polyhaven`, default `False`).
- `get_sketchfab_status` / `get_polypizza_status` / `get_hyper3d_status` /
  `get_hunyuan3d_status` -> disabled; each has its own panel checkbox, and Poly Pizza
  additionally needs an API key from https://poly.pizza/settings/api
- `get_tripo_status` -> "only available with MCP for Blender **Premium**" — not a
  setting, a paywall. Do not retry it expecting success.

**Two different failure modes — check for both.** A disabled service does not always
return a polite "disabled" message. Verified live 2026-09-30 with everything off:

- `get_sketchfab_status` -> clean prose: "Sketchfab integration is currently disabled..."
- `search_sketchfab_models` -> a **transport error**, not prose:
  `Error searching Sketchfab models: Communication error with Blender: Unknown command type: search_sketchfab_models`

That second shape is the dangerous one: it reads like a broken install rather than a
disabled feature, and sending it to a user as "Sketchfab is broken" would be wrong.
**Always gate on the matching `get_*_status` before any `search_*` / `download_*`.**

**Real calls:**

```
get_polyhaven_status {"user_prompt": "set up a studio HDRI"}
get_polyhaven_categories {"asset_type": "hdris", "user_prompt": "..."}
search_polyhaven_assets {"query": "studio", "asset_type": "hdris", "limit": 10,
                        "user_prompt": "..."}
get_polyhaven_asset_preview {"asset_id": "<id>", "user_prompt": "..."}
download_polyhaven_asset {"asset_id": "<id>", "asset_type": "hdris",
                          "resolution": "1k", "file_format": "exr",
                          "user_prompt": "..."}
```

`asset_type` must be a value `get_polyhaven_categories` reports; supported formats
include `.hdr` / `.exr` for HDRIs. `download_polyhaven_asset` auto-imports and wires
the material, so the bpy below is only for the cases it does not cover (e.g. applying
a downloaded texture set to a material you built yourself).

**Typical usage patterns:**

### Import an HDRI for environment lighting

```python
import bpy

# After MCP downloads the HDRI to a local path:
hdri_path = "/path/to/studio_small_09_4k.exr"

world = bpy.data.worlds["World"]
world.use_nodes = True
nodes = world.node_tree.nodes
links = world.node_tree.links

# Clear existing nodes
nodes.clear()

# Add environment texture
bg_node = nodes.new("ShaderNodeBackground")
env_node = nodes.new("ShaderNodeTexEnvironment")
out_node = nodes.new("ShaderNodeOutputWorld")
map_node = nodes.new("ShaderNodeMapping")
coord_node = nodes.new("ShaderNodeTexCoord")

env_node.image = bpy.data.images.load(hdri_path)

links.new(coord_node.outputs["Generated"], map_node.inputs["Vector"])
links.new(map_node.outputs["Vector"], env_node.inputs["Vector"])
links.new(env_node.outputs["Color"], bg_node.inputs["Color"])
links.new(bg_node.outputs["Background"], out_node.inputs["Surface"])

bg_node.inputs["Strength"].default_value = 1.0
print("HDRI loaded:", hdri_path)
```

### Import a PBR texture set onto a material

```python
import bpy, os

# After MCP downloads the texture set to a local directory:
tex_dir = "/path/to/concrete_layers_02_1k/"

mat = bpy.data.materials.new(name="ConcreteLayers")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
nodes.clear()

bsdf = nodes.new("ShaderNodeBsdfPrincipled")
output = nodes.new("ShaderNodeOutputMaterial")
links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

def load_tex(fname, colorspace="sRGB"):
    path = os.path.join(tex_dir, fname)
    if not os.path.exists(path):
        return None
    img = bpy.data.images.load(path)
    img.colorspace_settings.name = colorspace
    node = nodes.new("ShaderNodeTexImage")
    node.image = img
    return node

base_color = load_tex("concrete_layers_02_diff_1k.jpg", "sRGB")
roughness  = load_tex("concrete_layers_02_rough_1k.jpg", "Non-Color")
normal_img = load_tex("concrete_layers_02_nor_gl_1k.jpg", "Non-Color")
disp_img   = load_tex("concrete_layers_02_disp_1k.jpg", "Non-Color")

if base_color:
    links.new(base_color.outputs["Color"], bsdf.inputs["Base Color"])
if roughness:
    links.new(roughness.outputs["Color"], bsdf.inputs["Roughness"])
if normal_img:
    normal_map = nodes.new("ShaderNodeNormalMap")
    links.new(normal_img.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])

print("Material setup complete:", mat.name)
```

**Notes:**
- PolyHaven textures are CC0 — safe to include in commercial projects
- Always choose 1K or 2K resolution downloads; 4K+ will need resizing before GLB export
- Displacement maps are not supported in GLTF — skip or bake to normal map

---

## Sketchfab

**What it is:** A marketplace and community for 3D models. Free and paid assets. Requires a Sketchfab access token for download.

**Capabilities via Blender MCP:**
- Search the library by keyword
- Download licensed models (free and purchased) directly into Blender
- Auto-import with materials

**Configuration:** Set your Sketchfab API token in the Blender MCP addon settings before use.

**Real calls:**

```
get_sketchfab_status {"user_prompt": "..."}
search_sketchfab_models {"query": "chair", "count": 20, "downloadable": true,
                         "user_prompt": "..."}
get_sketchfab_model_preview {"uid": "<uid>", "user_prompt": "..."}
download_sketchfab_model {"uid": "<uid>", "target_size": 2.0, "user_prompt": "..."}
```

`target_size` is required and is a scale factor in metres — Sketchfab models arrive at
wildly different real-world scales, so set it deliberately.

**Typical usage pattern:**

### Search and import a model

```python
# MCP handles search and download internally.
# After import, verify the object landed correctly:
import bpy, json

imported = []
for obj in bpy.context.scene.objects:
    imported.append({
        "name": obj.name,
        "type": obj.type,
        "materials": [s.material.name for s in obj.material_slots if s.material],
    })

print(json.dumps(imported, indent=2))
```

**Post-import checklist:**
- Check for missing textures: `File → External Data → Report Missing Files`
- Verify scale (Sketchfab models often come in at wrong scale — check bounding box)
- Check material nodes for non-Principled BSDF shaders (some imports use Diffuse BSDF, which exports poorly)

**Convert imported Diffuse BSDF to Principled for better export:**

```python
import bpy

for mat in bpy.data.materials:
    if not mat.use_nodes:
        continue
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    diffuse_nodes = [n for n in nodes if n.type == 'BSDF_DIFFUSE']
    for diff_node in diffuse_nodes:
        # Create Principled BSDF in its place
        princ = nodes.new('ShaderNodeBsdfPrincipled')
        princ.location = diff_node.location
        # Re-wire inputs
        for link in mat.node_tree.links:
            if link.to_node == diff_node:
                if link.to_socket.name == 'Color':
                    links.new(link.from_socket, princ.inputs['Base Color'])
                elif link.to_socket.name == 'Normal':
                    links.new(link.from_socket, princ.inputs['Normal'])
            if link.from_node == diff_node:
                links.new(princ.outputs['BSDF'], link.to_socket)
        nodes.remove(diff_node)
        print(f"Converted Diffuse BSDF in {mat.name}")
```

---

## Hyper3D Rodin

**What it is:** AI-powered 3D model generation from text descriptions or reference images. Produces watertight meshes with PBR textures.

**Capabilities via Blender MCP:**
- Generate a 3D model from a text prompt
- Generate a 3D model from one or more reference images
- Import generated model directly into the current Blender scene

**Typical usage patterns:**

### Generate from text prompt

```
# MCP tool call (handled internally by the integration):
# Prompt: "A medieval iron lantern with glass panels, hanging chain, aged patina"
# Format: GLB
# Resolution: Medium (512 texture)
```

After import, verify and adjust:

```python
import bpy, json

# Find the newly imported object (usually the most recently added)
latest = sorted(bpy.data.objects, key=lambda o: o.name)[-1]
print("Imported:", latest.name)
print("Vertices:", len(latest.data.vertices) if latest.data else "N/A")
print("Materials:", [s.material.name for s in latest.material_slots if s.material])
```

### Generate from reference image

```
# MCP tool call:
# Image: /path/to/reference_photo.jpg
# Prompt: "Stylized low-poly tree with autumn leaves"
# Format: GLB
```

**Post-generation workflow:**

```python
import bpy

# Rodin models often come in with Y-up orientation; correct for Blender Z-up:
obj = bpy.context.active_object
if obj:
    obj.rotation_euler[0] = 0  # reset X rotation if double-applied
    bpy.ops.object.transform_apply(rotation=True)

# Check poly count — Rodin tends to produce dense meshes
for obj in bpy.context.selected_objects:
    if obj.type == 'MESH':
        print(f"{obj.name}: {len(obj.data.polygons)} faces")
```

**Notes:**
- Rodin outputs are good starting points but often need decimation for web use
- PBR textures from Rodin export cleanly to GLTF (no procedural nodes)
- Generation time varies: 30 seconds to several minutes depending on complexity

**Decimate after Rodin import:**

```python
import bpy

obj = bpy.context.active_object
mod = obj.modifiers.new("Decimate", "DECIMATE")
mod.ratio = 0.3  # reduce to 30% of original face count
# Do NOT apply modifier before export — set export_apply=False
print(f"Decimation modifier added. Effective faces: ~{len(obj.data.polygons) * mod.ratio:.0f}")
```

---

## Hunyuan3D

**What it is:** Tencent's open-source 3D generation model. Runs locally. Accepts text prompts, images, or both. Produces detailed meshes with high-quality texture generation.

**Capabilities via Blender MCP:**
- Generate 3D assets from text prompts
- Generate from single or multiple reference images
- Combined text + image conditioning for style control
- Import directly into Blender scene

**Typical usage patterns:**

### Text + image generation (best quality)

```
# MCP tool call:
# Image: /path/to/concept_art.png
# Prompt: "Game-ready sci-fi crate, metallic, worn edges, sticker decals"
# Steps: 50  (more steps = more detail, slower)
```

### Post-import material inspection

```python
import bpy, json

# Hunyuan3D typically outputs a single mesh with baked texture atlas
result = []
for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    mats = []
    for slot in obj.material_slots:
        if not slot.material or not slot.material.use_nodes:
            continue
        mat_info = {"name": slot.material.name, "textures": []}
        for node in slot.material.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                mat_info["textures"].append({
                    "image": node.image.name,
                    "size": list(node.image.size),
                    "filepath": node.image.filepath,
                })
        mats.append(mat_info)
    result.append({"object": obj.name, "materials": mats})

print(json.dumps(result, indent=2))
```

**Notes:**
- Hunyuan3D runs locally — requires significant VRAM (16 GB+ recommended for full quality)
- Outputs often use a single UV-unwrapped texture atlas — ideal for GLTF (no procedural nodes)
- Texture baking is already done; export to GLTF proceeds without baking steps
- Local generation avoids API rate limits and keeps assets private

**Quality comparison (approximate):**

| Scenario | Hyper3D Rodin | Hunyuan3D |
|----------|---------------|-----------|
| Speed | Cloud, ~1-3 min | Local, ~2-10 min |
| Texture quality | Good | Very good |
| Geometry quality | Clean, watertight | Dense, may need decimation |
| Privacy | Cloud API | Fully local |
| Cost | API credits | Hardware cost only |
| Best for | Quick iteration | Final assets |

---

## Integration Comparison

| Integration | Asset type | Free? | Requires auth? | Best use case |
|-------------|-----------|-------|---------------|---------------|
| PolyHaven | HDRIs, textures, models | Yes (CC0) | No | Environment setup, surface materials |
| Sketchfab | Models (any) | Free tier + paid | Yes (API token) | Finding specific objects |
| Hyper3D Rodin | AI-generated models | Credits | Yes (API key) | Concept-to-3D, fast iteration |
| Hunyuan3D | AI-generated models | Free (local) | No | High-quality local generation |
