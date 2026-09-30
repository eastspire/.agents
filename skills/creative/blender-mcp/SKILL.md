---
name: blender-mcp
description: "Blender MCP expert for scene inspection, Python scripting, GLTF export, and material/animation extraction. Activate when: (1) using Blender MCP tools (get_scene_info, execute_blender_code, get_viewport_screenshot, export_scene, etc.), (2) writing Blender Python scripts for extraction or manipulation, (3) exporting scenes to GLTF/GLB for web (Three.js, R3F), (4) debugging material or texture export losses, (5) optimizing GLB files with gltf-transform, (6) using asset integrations (PolyHaven, Sketchfab, Hyper3D Rodin, Hunyuan3D). Covers critical export gotchas, material mapping survival, texture optimization pipeline, headless CLI patterns, and known failure modes."
version: 1.0.0
author: vladmdgolam
license: MIT
platforms: [macos, linux, windows]
compatibility: "Requires Blender 3.0+ (tested on 4.5 LTS) with the 'MCP for Blender' add-on enabled, plus the Hermes MCP server 'blender' (uvx mcp-for-blender). Socket port 9876."
prerequisites:
  commands: ["uvx", "blender"]
setup:
  help: "Add-on: `uvx mcp-for-blender install-addon`, then enable 'Interface: MCP for Blender' in Blender Preferences. MCP server: `hermes mcp add blender --command <uvx-abs-path> --env UV_PYTHON_PREFERENCE=only-managed --args mcp-for-blender`."
metadata:
  hermes:
    tags: [Blender, MCP, mcp-for-blender, bpy, 3D, GLTF, GLB, gltf-transform, PolyHaven, Sketchfab, procedural-modeling, texturing]
    related_skills: [blender-3d-modeling, hard-surface-product-modeling, spec-accurate-product-modeling, procedural-game-asset-pipeline]
---

# Blender MCP

## Tool Selection

Use **structured MCP tools** (`get_scene_info`, `get_viewport_screenshot`) for quick inspection.

Use **`execute_blender_code`** for anything non-trivial: hierarchy traversal, material extraction, animation baking, bulk operations. It gives full `bpy` API access and avoids tool schema limitations.

Use **headless CLI** for GLTF exports — the MCP server times out on export operations.

## Health Check (Always First)

1. `get_scene_info` — verify connection (default port 9876)
2. `execute_blender_code` with `print("ok")` — verify Python works
3. `get_viewport_screenshot` — verify viewport capture works

If MCP is unresponsive, check that the Blender MCP addon is enabled and the socket server is running.

## Verified tool names — see `references/mcp-tools.md` for the full 36

Upstream prose in this skill predates the `blender-mcp` -> `mcp-for-blender` rename,
so some names here are wrong. The real ones, measured against a live `list_tools()`:

| Instead of | Actually call | Required args |
|---|---|---|
| `execute_python` | `execute_blender_code` | `code` |
| `screenshot` | `get_viewport_screenshot` | none (optional `max_size`, default 1000) |
| `get_scene_info` (no args) | `get_scene_info` | **`user_prompt`** — omitting it is a hard pydantic validation error, not an empty result |

**`references/mcp-tools.md` is the authority for all 36 tools** — every name, every
argument, every default, generated from the live server. Read it before calling any
tool this skill has not shown you, and believe it over any name in this file.

Two facts that shape every call:
- **Nearly every tool takes an optional `user_prompt` (default `''`)** — pass the real
  request text. `get_scene_info` is the sole exception where it is mandatory.
- **`export_scene` is a first-class export tool** (`filepath`, plus `format`
  default `'glb'`, `object_names`, `selection_only`, `apply_modifiers`) — prefer it
  over hand-rolling `bpy.ops.export_scene.gltf(...)`, which the skill's older
  examples still do.
- `get_addon_status` returns `up_to_date` + `protocol_version` (11); add-on 1.7.

Two Blender-side constraints that cost real time:
- **Screenshots only work in GUI Blender.** The add-on's auto-start timer returns
  early when `bpy.app.background` is true, so `Blender -b` never opens port 9876.
  Headless is for `bpy` scripting only.
- **The add-on must be enabled before Blender starts.** Writing the enable flag into
  `userpref.blend` from a `--background` run is not enough for an already-running
  GUI instance — restart it, or nothing listens on 9876.

## Two tools you will reach for first

**`export_scene`** — measured working, use it instead of hand-writing
`bpy.ops.export_scene.gltf(...)`:
```
export_scene {"filepath": "/abs/out.glb", "format": "glb",
              "object_names": ["Cube"], "selection_only": false,
              "apply_modifiers": true, "user_prompt": "..."}
```
Returns `{"path", "bytes", "exported": [...], "selection_only"}`. `format` defaults to
`"glb"`; it can also write `gltf`.

**`bpy_api_lookup`** — needs an **exact type identifier**, not prose. `"bevel modifier"`
returns `{"error": "Unknown type: bevel modifier", "did_you_mean": []}` with no
suggestion to fall back on. Use `"BEVEL"`, `"ShaderNodeTexNoise"`, or another real
`bl_idname`. When it fails there is no recovery path — go to
`describe_node_type` with the `bl_idname` instead, which does work:
`describe_node_type {"bl_idname": "ShaderNodeTexNoise"}` returns label, tree it
instantiates in, and the full property list.

## Complete Export Workflow

This is the end-to-end linear narrative. Follow these steps in order. Do not skip steps.

### Step 1: Health Check

Confirm MCP is alive before touching anything else:

```bash
# In MCP tool call:
get_scene_info {"user_prompt": "..."}   # user_prompt is REQUIRED
execute_blender_code {"code": "print('ok')"}
get_viewport_screenshot
```

If any step fails, stop and fix MCP connectivity first. See [Known Errors](#known-errors--workarounds).

### Step 2: Inspect Scene

Run the full hierarchy extraction to understand what you're working with:

```python
import bpy, json

def extract_hierarchy(obj, depth=0):
    data = {
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "rotation": list(obj.rotation_euler),
        "scale": list(obj.scale),
        "visible": not obj.hide_viewport,
        "children": [],
    }
    if obj.type == 'MESH' and obj.data:
        data["vertices"] = len(obj.data.vertices)
        data["faces"] = len(obj.data.polygons)
        data["materials"] = [slot.material.name for slot in obj.material_slots if slot.material]
    if obj.type == 'LIGHT':
        data["light_type"] = obj.data.type
        data["energy"] = obj.data.energy
        data["color"] = list(obj.data.color)
    for mod in obj.modifiers:
        if mod.type == 'ARRAY':
            data.setdefault("modifiers", []).append({
                "type": "ARRAY",
                "count": mod.count,
                "offset_object": mod.offset_object.name if mod.offset_object else None,
            })
    for child in obj.children:
        data["children"].append(extract_hierarchy(child, depth + 1))
    return data

scene_data = {
    "name": bpy.context.scene.name,
    "fps": bpy.context.scene.render.fps,
    "frame_start": bpy.context.scene.frame_start,
    "frame_end": bpy.context.scene.frame_end,
    "objects": [],
}
for obj in bpy.context.scene.objects:
    if obj.parent is None:
        scene_data["objects"].append(extract_hierarchy(obj))

print(json.dumps(scene_data, indent=2))
```

Look for:
- Array modifiers (will balloon file size if baked — must replicate at runtime)
- Objects with many vertices (risk of slow export or large GLB)
- Hidden objects you may or may not want to export
- Missing materials (empty `material_slots`)

### Step 3: Verify Materials

Run the material extraction to catch export-lossy setups before committing to an export:

```python
import bpy, json

def extract_materials():
    materials = []
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        info = {"name": mat.name, "nodes": [], "warnings": []}
        has_principled = False
        for node in mat.node_tree.nodes:
            node_data = {"type": node.type, "name": node.name}
            if node.type == 'BSDF_PRINCIPLED':
                has_principled = True
                for inp in node.inputs:
                    if inp.is_linked:
                        node_data[inp.name] = "linked"
                    elif hasattr(inp, 'default_value'):
                        val = inp.default_value
                        try:
                            node_data[inp.name] = list(val)
                        except TypeError:
                            node_data[inp.name] = float(val)
            if node.type == 'TEX_IMAGE' and node.image:
                node_data["image"] = node.image.filepath
                node_data["size"] = [node.image.size[0], node.image.size[1]]
                if node.image.size[0] > 2048:
                    info["warnings"].append(f"Large texture: {node.image.filepath} ({node.image.size[0]}x{node.image.size[1]})")
            if node.type in ('TEX_NOISE', 'TEX_VORONOI', 'TEX_WAVE', 'TEX_MUSGRAVE'):
                info["warnings"].append(f"Procedural texture node '{node.name}' ({node.type}) will be LOST on GLTF export")
            if node.type == 'VALTORGB':  # Color Ramp
                info["warnings"].append(f"Color Ramp '{node.name}' remapping will be LOST on GLTF export")
        if not has_principled:
            info["warnings"].append("No Principled BSDF found — export result unpredictable")
        info["nodes"].append(node_data)
        materials.append(info)
    return materials

result = extract_materials()
for mat in result:
    if mat["warnings"]:
        print(f"WARN [{mat['name']}]: {'; '.join(mat['warnings'])}")
print(json.dumps(result, indent=2))
```

Review all warnings before proceeding. Decide: bake procedural textures now, or patch materials at runtime after export.

### Step 4: Export via Headless CLI

The MCP server cannot handle GLTF exports (timeout). Always use headless CLI:

```bash
# Use 'blender' if it's on PATH, otherwise use the platform-specific path:
#   macOS:   /Applications/Blender.app/Contents/MacOS/Blender
#   Windows: "C:\Program Files\Blender Foundation\Blender 4.x\blender.exe"
#   Linux:   /usr/bin/blender
blender \
  --background "/path/to/scene.blend" \
  --python-expr "
import bpy, os
export_path = '/path/to/output.glb'
os.makedirs(os.path.dirname(os.path.abspath(export_path)), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=export_path,
    export_format='GLB',
    export_apply=False,
    export_animations=True,
    export_nla_strips=True,
    export_cameras=True,
    export_lights=False,
    export_draco_mesh_compression_enable=False,
)
size_mb = os.path.getsize(export_path) / 1024 / 1024
print(f'Export complete: {export_path} ({size_mb:.1f} MB)')
"
```

**Critical flags:**
- `export_apply=False` — do not bake modifiers (Array modifier turns 1 MB into 56 MB)
- `export_draco_mesh_compression_enable=False` — apply Draco later via gltf-transform
- Quote all paths that may contain spaces

### Step 5: Optimize with gltf-transform

Run after a successful export. Always use individual steps, never `optimize`:

```bash
# 1. Inspect raw export first
npx @gltf-transform/cli inspect output.glb

# 2. Resize textures (max 1K for web/mobile)
npx @gltf-transform/cli resize output.glb resized.glb --width 1024 --height 1024

# 3. WebP compression (quality 90 preserves detail)
npx @gltf-transform/cli webp resized.glb webp.glb --quality 90

# 4. Draco mesh compression (LAST — irreversible)
npx @gltf-transform/cli draco webp.glb final.glb

# 5. Inspect final result
npx @gltf-transform/cli inspect final.glb
```

Expected size reduction: ~22 MB raw → ~3.7 MB (WebP) → ~1 MB (Draco). See [references/texture-optimization.md](references/texture-optimization.md) for detailed metrics.

### Step 6: Validate

Run the full Post-Export Validation checklist below before shipping.

## Post-Export Validation Checklist

After every export, verify the following before handing off the GLB for integration:

- [ ] **File size is reasonable** — raw GLB under 30 MB, optimized GLB under 5 MB for typical web scenes. Flag anything above these thresholds.
- [ ] **Inspect with gltf-transform CLI** — run `npx @gltf-transform/cli inspect final.glb` and check: mesh count, texture count, texture sizes, animation count, accessor sizes. No unexpected duplication.
- [ ] **Visual test in Babylon.js Sandbox** — drag-and-drop the GLB at [sandbox.babylonjs.com](https://sandbox.babylonjs.com). Verify: mesh renders correctly, textures appear, animations play, no black/pink materials.
- [ ] **No Three.js console errors** — load in a minimal Three.js GLTFLoader test page and check browser console. Common errors: `THREE.GLTFLoader: Unknown extension`, missing texture files, unsupported Draco version.
- [ ] **Materials spot-check** — pick 3–5 materials and visually confirm roughness, metalness, and base color look correct. Compare against Blender viewport render. Flag any that look flat or overly shiny.
- [ ] **Animation spot-check** — if the scene has animations, verify at least one plays correctly in Babylon.js Sandbox or Three.js. Check frame count matches expected.
- [ ] **Name mapping verified** — if runtime code references mesh names, confirm the names match after GLTF export transformation (spaces → underscores, dots removed). See [Critical Rule 5](#5-gltf-name-mapping).
- [ ] **No missing textures** — check Babylon.js Sandbox network tab. No 404s for texture files. All textures should be packed inside the GLB.

## Examples

### Example 1: Export Character Rig with Animations

**Scenario:** You have a humanoid character with armature, 3 NLA actions (idle, walk, run), PBR texture set, and a weapon attached via parenting. You need a web-ready GLB for a Three.js scene.

**Step 1: Health check and scene inspection**

```bash
# MCP tool calls
get_scene_info {"user_prompt": "..."}   # user_prompt is REQUIRED
execute_blender_code {"code": "print('ok')"}
```

**Step 2: Inspect the rig**

```python
import bpy, json

# Check armature and NLA strips
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        print(f"Armature: {obj.name}")
        if obj.animation_data:
            print(f"  Active action: {obj.animation_data.action.name if obj.animation_data.action else 'None'}")
            for track in obj.animation_data.nla_tracks:
                print(f"  NLA track: {track.name}")
                for strip in track.strips:
                    print(f"    Strip: {strip.name}, frames {strip.frame_start}-{strip.frame_end}")
```

**Step 3: Check materials for export losses**

Run the material extraction above. For a character, watch for:
- Procedural skin texture nodes (Noise → color variation) — these will be lost
- Color Ramp on roughness for fabric — will be lost, roughness will look flat
- Decision: bake procedural variations to image textures, or patch roughness values at runtime

**Step 4: Export**

```bash
blender \
  --background "/path/to/character.blend" \
  --python-expr "
import bpy, os, tempfile
export_dir = tempfile.gettempdir()
bpy.ops.export_scene.gltf(
    filepath=os.path.join(export_dir, 'character.glb'),
    export_format='GLB',
    export_apply=False,
    export_animations=True,
    export_nla_strips=True,
    export_cameras=False,
    export_lights=False,
    export_draco_mesh_compression_enable=False,
    export_skins=True,
    export_morph=True,
)
print('done:', os.path.getsize(os.path.join(export_dir, 'character.glb')) / 1024 / 1024, 'MB')
"
```

**Step 5: Verify animations exported**

```bash
npx @gltf-transform/cli inspect character.glb | grep -i anim
```

Expected output: 3 animations (Idle, Walk, Run). If 0, check that NLA strips are muted or the tracks are set to solo.

**Step 6: Optimize**

```bash
npx @gltf-transform/cli resize character.glb char_resized.glb --width 1024 --height 1024
npx @gltf-transform/cli webp char_resized.glb char_webp.glb --quality 90
npx @gltf-transform/cli draco char_webp.glb character_final.glb
```

**Step 7: Runtime animation setup (Three.js)**

```javascript
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import * as THREE from 'three';

const dracoLoader = new DRACOLoader();
dracoLoader.setDecoderPath('/draco/');

const loader = new GLTFLoader();
loader.setDRACOLoader(dracoLoader);

loader.load('/character_final.glb', (gltf) => {
    const mixer = new THREE.AnimationMixer(gltf.scene);
    const clips = gltf.animations; // [Idle, Walk, Run]
    const idleAction = mixer.clipAction(clips.find(c => c.name === 'Idle'));
    idleAction.play();
    // Animate mixer in render loop: mixer.update(delta)
});
```

---

### Example 2: Debug Material Export Loss (Roughness Looks Flat)

**Scenario:** After export, a metal panel material looks uniformly flat and shiny in Three.js. In Blender it had interesting roughness variation from a Noise Texture → Color Ramp → roughness input.

**Step 1: Confirm the problem in Blender**

```python
import bpy, json

mat = bpy.data.materials.get("MetalPanel")
if mat and mat.use_nodes:
    for node in mat.node_tree.nodes:
        print(f"Node: {node.type} - {node.name}")
        for inp in node.inputs:
            if inp.is_linked:
                print(f"  Input '{inp.name}': linked to something")
```

Expected output reveals:
```
Node: BSDF_PRINCIPLED - Principled BSDF
  Input 'Roughness': linked to something
Node: VALTORGB - Color Ramp         <-- this will NOT export
Node: TEX_NOISE - Noise Texture     <-- this will NOT export
```

**Step 2: Understand what GLTF received**

The export exports the Principled BSDF's roughness input. When linked to a Color Ramp, GLTF exporter takes the **default_value of the input socket** (fallback), which is typically `0.5` — perfectly flat.

**Step 3A: Fix by baking in Blender (best quality)**

```python
import bpy

# Select the object
obj = bpy.data.objects["MetalPanelMesh"]
bpy.context.view_layer.objects.active = obj
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)

# Create a new image to bake into
bake_img = bpy.data.images.new("MetalPanel_roughness_baked", width=1024, height=1024)
bake_img.colorspace_settings.name = 'Non-Color'

# Add image texture node to material
mat = obj.active_material
nodes = mat.node_tree.nodes
img_node = nodes.new('ShaderNodeTexImage')
img_node.image = bake_img
nodes.active = img_node

# Bake roughness (use ROUGHNESS pass or EMIT trick)
bpy.context.scene.cycles.bake_type = 'ROUGHNESS'
bpy.ops.object.bake(type='ROUGHNESS', save_mode='INTERNAL')

# Save baked image
import tempfile, os
bake_path = os.path.join(tempfile.gettempdir(), 'MetalPanel_roughness_baked.png')
bake_img.filepath_raw = bake_path
bake_img.file_format = 'PNG'
bake_img.save()
print(f"Baked roughness to {bake_path}")
```

Then connect the new image texture node to the Roughness input and re-export.

**Step 3B: Fix at runtime in Three.js (quick patch)**

If you cannot bake, override the material roughness after load:

```javascript
loader.load('/metal_panel.glb', (gltf) => {
    gltf.scene.traverse((child) => {
        if (child.isMesh && child.material) {
            const mats = Array.isArray(child.material) ? child.material : [child.material];
            mats.forEach(mat => {
                if (mat.name === 'MetalPanel') {
                    // Instead of flat 0.5, set a textured roughness or varied value
                    mat.roughness = 0.3;  // adjust to match intended look
                    mat.metalness = 0.9;
                    mat.needsUpdate = true;
                }
            });
        }
    });
});
```

**Step 4: Verify fix**

Re-export and run validation checklist. In Babylon.js Sandbox, compare the metal panel material against a Blender viewport screenshot to confirm roughness variation is preserved.

## Critical Rules

### 1. MCP Server Times Out on Exports

The Blender MCP server cannot handle GLTF exports — they exceed the timeout. Always use headless CLI:

```bash
blender --background "scene.blend" --python-expr "
import bpy, os
export_path = 'output.glb'
os.makedirs(os.path.dirname(export_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=export_path,
    export_format='GLB',
    export_apply=False,
    export_animations=True,
    export_nla_strips=True,
    export_cameras=True,
    export_lights=False,
    export_draco_mesh_compression_enable=False,
)
print(f'Size: {os.path.getsize(export_path)/1024/1024:.1f} MB')
"
```

### 2. Do NOT Apply Modifiers on Export

Set `export_apply=False`. Array modifiers (circular patterns, linear repeats) balloon file size when baked. Replicate them at runtime instead.

Example: 16 roller instances via Array modifier = ~1 MB GLB. Baked = ~56 MB GLB.

### 3. Export WITHOUT Draco First

If you plan to optimize with `gltf-transform`, export without Draco compression. Re-encoding existing Draco corrupts meshes. Apply Draco as the final step.

### 4. Procedural Textures Don't Export to GLTF

These Blender node setups are **lost** on export:

| Node Setup | What's Lost | Workaround |
|------------|-------------|------------|
| Noise Texture → roughness | Entire procedural chain | Bake to texture, or shader patch at runtime |
| Color Ramp on roughness texture | Value remapping range | Manual roughness values, or runtime remap |
| Procedural bump (Noise → Bump) | Bump detail | Bake normal map in Blender |
| Mix Shader with complex factor | Blend logic | Simplify to single BSDF before export |

**What DOES export:** flat roughness/metallic values, image textures (without Color Ramp remapping), baked normal maps, PBR texture sets (baseColor, metallicRoughness, normal).

### 5. GLTF Name Mapping

Blender names are transformed in GLTF:
- Spaces → underscores
- Dots → removed
- Trailing spaces → trailing underscore

| Blender | GLTF |
|---------|------|
| `RINGS ball L` | `RINGS_ball_L` |
| `Sphere.003` | `Sphere003` |
| `RINGS L.001` | `RINGS_L001` |
| `RINGS S ` (trailing space) | `RINGS_S_` |

Always check names in the exported GLB, not Blender, when referencing meshes in code.

### 6. Never Use gltf-transform `optimize`

The `optimize` command includes `simplify` which destroys mesh geometry. Use individual steps instead:

```bash
# Resize textures (max 1024x1024)
npx @gltf-transform/cli resize input.glb resized.glb --width 1024 --height 1024

# WebP texture compression
npx @gltf-transform/cli webp resized.glb webp.glb --quality 90

# Draco mesh compression (LAST step)
npx @gltf-transform/cli draco webp.glb output.glb
```

### 7. Quote Paths with Spaces

Blender project paths often contain spaces. Always double-quote:
```bash
blender --background "$HOME/Downloads/blend 3/scene.blend" ...
```

## Scene Extraction Pattern

Full hierarchy with materials, transforms, and modifiers:

```python
import bpy, json

def extract_hierarchy(obj, depth=0):
    data = {
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "rotation": list(obj.rotation_euler),
        "scale": list(obj.scale),
        "visible": not obj.hide_viewport,
        "children": [],
    }
    if obj.type == 'MESH' and obj.data:
        data["vertices"] = len(obj.data.vertices)
        data["faces"] = len(obj.data.polygons)
        data["materials"] = [slot.material.name for slot in obj.material_slots if slot.material]
    if obj.type == 'LIGHT':
        data["light_type"] = obj.data.type
        data["energy"] = obj.data.energy
        data["color"] = list(obj.data.color)
        if obj.data.type == 'AREA':
            data["size"] = obj.data.size
            data["size_y"] = obj.data.size_y
    # Array modifiers (important for runtime replication)
    for mod in obj.modifiers:
        if mod.type == 'ARRAY':
            data.setdefault("modifiers", []).append({
                "type": "ARRAY",
                "count": mod.count,
                "offset_object": mod.offset_object.name if mod.offset_object else None,
            })
    for child in obj.children:
        data["children"].append(extract_hierarchy(child, depth + 1))
    return data

scene_data = {
    "name": bpy.context.scene.name,
    "fps": bpy.context.scene.render.fps,
    "frame_start": bpy.context.scene.frame_start,
    "frame_end": bpy.context.scene.frame_end,
    "objects": [],
}

for obj in bpy.context.scene.objects:
    if obj.parent is None:
        scene_data["objects"].append(extract_hierarchy(obj))

print(json.dumps(scene_data, indent=2))
```

## Material Extraction Pattern

```python
import bpy, json

def extract_materials():
    materials = []
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        info = {"name": mat.name, "nodes": []}
        for node in mat.node_tree.nodes:
            node_data = {"type": node.type, "name": node.name}
            if node.type == 'BSDF_PRINCIPLED':
                for inp in node.inputs:
                    if inp.is_linked:
                        node_data[inp.name] = "linked"
                    elif hasattr(inp, 'default_value'):
                        val = inp.default_value
                        try:
                            node_data[inp.name] = list(val)
                        except TypeError:
                            node_data[inp.name] = float(val)
            if node.type == 'TEX_IMAGE' and node.image:
                node_data["image"] = node.image.filepath
                node_data["size"] = [node.image.size[0], node.image.size[1]]
            info["nodes"].append(node_data)
        materials.append(info)
    return materials

print(json.dumps(extract_materials(), indent=2))
```

## Animation Keyframe Extraction

```python
import bpy, json

def extract_animation(obj):
    if not obj.animation_data or not obj.animation_data.action:
        return None
    tracks = []
    for fc in obj.animation_data.action.fcurves:
        keyframes = []
        for kp in fc.keyframe_points:
            keyframes.append({
                "frame": int(kp.co[0]),
                "value": float(kp.co[1]),
                "interpolation": kp.interpolation,
            })
        tracks.append({
            "data_path": fc.data_path,
            "index": fc.array_index,
            "keyframes": keyframes,
        })
    return {"object": obj.name, "tracks": tracks}

animations = []
for obj in bpy.data.objects:
    anim = extract_animation(obj)
    if anim:
        animations.append(anim)

print(json.dumps(animations, indent=2))
```

## GLTF Export Settings Reference

| Setting | Value | Why |
|---------|-------|-----|
| `export_format` | `'GLB'` | Single binary file |
| `export_apply` | `False` | Don't bake modifiers (Array, etc.) |
| `export_animations` | `True` | Include animation data |
| `export_nla_strips` | `True` | Bake NLA strips into actions |
| `export_cameras` | `True` | Include camera rigs |
| `export_lights` | `False` | Handle lights in runtime (Three.js/R3F) |
| `export_draco_mesh_compression_enable` | `False` | Apply Draco later via gltf-transform |

## Texture Optimization Pipeline

Target: smallest GLB with acceptable visual quality.

```
Blender export (no Draco) → resize (1K max) → WebP (q90) → Draco
   ~22 MB                    ~3.7 MB           ~3.7 MB      ~1 MB
```

Key insights:
- 4K textures (4096x4096) = ~89 MB GPU memory per texture. 1K = ~5.6 MB. **16x reduction**.
- PNG metallicRoughness textures compress well to WebP at quality 85-90.
- Mobile GPUs (Adreno, Mali) benefit most from texture downscaling.
- Inspect with: `npx @gltf-transform/cli inspect model.glb`

See [references/texture-optimization.md](references/texture-optimization.md) for concrete commands and quality metrics.

## Asset Integrations

Available through Blender MCP when configured:

| Integration | Capabilities |
|-------------|-------------|
| **PolyHaven** | Search, download, import free HDRIs, textures, and 3D models with auto material setup |
| **Sketchfab** | Search and download models (requires access token) |
| **Hyper3D Rodin** | Generate 3D models from text descriptions or reference images |
| **Hunyuan3D** | Create 3D assets from text prompts, images, or both |

See [references/asset-integrations.md](references/asset-integrations.md) for usage examples and workflow patterns.

## Known Errors & Workarounds

See [references/errors.md](references/errors.md) for complete error tables.

## Data Output

- `print()` + `json.dumps()` for small results (scene info, single object)
- Use `tempfile.gettempdir()` for large extraction results (full hierarchy, animation data, material reports)
- Always include metadata: scene name, fps, frame range, Blender version