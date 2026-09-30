---
name: blender-3d-modeling
description: Model 3D objects in Blender headless via bpy.
version: 1.0.0
license: MIT
---

# Blender 4.5 Headless 3D Modeling via Python API (bpy)

## Core workflow
1. Set scene units with `scene.unit_settings` — `scale_length=1.0`, `length_unit='METERS'` works for whole-mesh SI units. Pick ONE unit system per script and stick to it.
2. Build geometry with `bpy.data.meshes.new()` + `mesh.from_pydata(verts, edges, faces)`, or `bmesh` for topology-aware ops. Never mix raw mesh and bmesh on the same object without re-syncing.
3. Apply transforms with `bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)` AFTER setting `.location`/`.scale` so bbox math works.
4. Use `obj.modifiers.new(type, name)` for Subdivision (SUBSURF), Solidify (SOLIDIFY thickness in scene units), Mirror (MIRROR). Smooth shading: `bpy.ops.object.shade_smooth()`.
5. Render: prefer Cycles when Solidify thickness matters. EEVEE ignores Solidify thickness. Always set `scene.cycles.samples` low (32) for previews.
6. Look-at camera: `direction = target - cam.location; rot_quat = direction.to_track_quat('-Z', 'Y'); cam.rotation_euler = rot_quat.to_euler()`. Avoid raw Euler when aiming at a non-axis target.

## Pitfalls learned (Blender 4.5)
- **bmesh.ops.create_torus does NOT exist** — build torus geometry manually with parametrized loops.
- **bmesh.ops.create_cylinder takes only `segments` and `radius1/radius2`, no size param** — for a cube use `bpy.ops.mesh.primitive_cube_add`.
- **bmesh.ops.create_cone also takes only `segments/radius1/radius2`** — same caveat.
- **bmesh.ops.create_uvsphere** works fine for round hubs.
- **Blender 4.5 renamed BSDF inputs**: `Clearcoat` → `Coat Weight`, `Clearcoat Roughness` → `Coat Roughness`, `Transmission` → `Transmission Weight`. Check `bsdf.inputs.keys()` first.
- **apply_transforms** bakes location into vertices. Re-set location AFTER apply if you need an offset.
- **Material mapping** — keep an explicit `name -> material` dict and a final pass that reports skipped names. Easy to miss objects.
- **Cycles + dark metallic paint** renders black without enough light. For dark scenes: raise `world.background.strength` to 0.4-0.6 with cool gray color, exposure ~0.3.
- **Emission strengths > 2** can blow out EEVEE/Cycles preview. Keep taillights/headlights ≤ 1.5.
- **Solidify thickness in scene units** — 25 in mm-domain = 25 meters. Always confirm units first.
- **Solidify on box-cross-section explodes bbox** — when the cross-section is a rectangle (4 sharp corners), Solidify duplicates the corner vertices and offsets them outward, making the body suddenly 5× wider than intended. Use Subsurf alone for box-shaped lofts.
- **Camera framing for vehicles** — a 4.7m car needs ≥8m camera distance with 35mm lens, and 14m+ for top-down (because the car projects wider in screen space when viewed from above).

## Cross-section design

For car-body lofts, use a **4-sided rounded rectangle** (bottom / right / top / left), NOT a circle. Real cars have flat sides, fenders bulge outward, the bottom is flat. Profile walking:
```python
n_side = n_ring // 4
for i in range(n_ring):
    side = i // n_side          # 0=bottom, 1=right, 2=top, 3=left
    idx = i % n_side
    u = idx / (n_side - 1)      # 0..1 along this side
    # right/left sides: apply fender bulge
    fender = math.sin(u * math.pi)
    y = ±yh * (1.0 + bulge * fender)
```
Vary `bulge` per station: rear haunch (x_norm ~0.22) bulges most, front fender (x_norm ~0.85) sharper.

**Cap the bulge factor.** With `n_ring=16` and a flat box-section, a `bulge > 0.05` makes the side silhouette stick out past the roof z, producing the "two disconnected humps" artifact in side view. Keep `bulge_max ≤ 0.05` for box lofts.

## Know the methodological ceiling

**A box-section loft can match overall bbox dimensions but will never replicate a hand-sculpted NURBS body.** Real production car bodies are continuous Bezier surfaces with hand-tuned curvature continuity. A 19-station box loft produces visible flat-plate silhouettes and "broken" silhouette continuity between stations, no matter how many times stations are tuned. If the user wants photoreal silhouette fidelity, a procedural script is the wrong tool — switch to Blender GUI sculpting, grease pencil, or import a community-made model from Sketchfab. Don't burn time iterating on stations when the gap is methodological.

## Camera spherical coords

Azimuth + elevation (around Y up) is much easier than hand-rolled Euler:
```python
cx = dist * cos(el) * cos(az)
cy = dist * cos(el) * sin(az)
cz = dist * sin(el)
direction = (target - cam.location).normalized()
rot_quat = direction.to_track_quat('-Z', 'Y')
cam.rotation_euler = rot_quat.to_euler()
```
For top-down, use elevation=89° (not 90°) to avoid gimbal lock.

## Render pipeline patterns
- `bpy.ops.wm.save_as_mainfile(filepath=...)` to checkpoint before render.
- Camera list iteration: build one camera per angle, assign `scene.camera` before `bpy.ops.render.render(write_still=True)`.
- For headless multi-render: chain `bpy.ops.render.render(write_still=True)` calls in one process (faster than spawning Blender per render).