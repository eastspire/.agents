# mcp-for-blender — verified tool reference

Generated from a live `list_tools()` call against `uvx mcp-for-blender` on this
machine (Blender 4.5.4 LTS, add-on 1.7, protocol 11), 2026-09-30. Do not hand-edit:
if a name or argument here disagrees with the server, the server is right.

## The `user_prompt` trap

**Almost every tool takes an optional `user_prompt` (default `''`).** It is the
user's own request text, forwarded to the model for better context. Pass the real
request — it improves results and costs nothing.

**`get_scene_info` is the one tool where it is required.** Omitting it returns a
pydantic validation error, not an empty scene:

```
Error executing tool get_scene_info: 1 validation error for get_scene_infoArguments
user_prompt   Field required [type=missing, input_value={}, input_type=dict]
```

## Tool groups

### Scene inspection

`get_addon_status`
  - `user_prompt` (string, default `''`)

`get_scene_info`
  - `**user_prompt**` (string)

`get_object_info`
  - `**object_name**` (string)
  - `user_prompt` (string, default `''`)

`get_viewport_screenshot`
  - `max_size` (integer, default `1000`)
  - `user_prompt` (string, default `''`)

### Python execution

`execute_blender_code`
  - `**code**` (string)
  - `user_prompt` (string, default `''`)

`bpy_api_lookup`
  - `**query**` (string)
  - `user_prompt` (string, default `''`)

`describe_node_type`
  - `**bl_idname**` (string)
  - `property_overrides` (object)
  - `user_prompt` (string, default `''`)

### Export

`export_scene`
  - `**filepath**` (string)
  - `format` (string, default `'glb'`)
  - `object_names` (array)
  - `selection_only` (boolean, default `False`)
  - `apply_modifiers` (boolean, default `True`)
  - `user_prompt` (string, default `''`)

### PolyHaven (CC0 HDRIs / PBR / models)

`get_polyhaven_status`
  - `user_prompt` (string, default `''`)

`get_polyhaven_categories`
  - `asset_type` (string, default `'hdris'`)
  - `user_prompt` (string, default `''`)

`search_polyhaven_assets`
  - `query` (string)
  - `asset_type` (string, default `'all'`)
  - `category` (string)
  - `attributes` (object)
  - `min_size_m` (number)
  - `limit` (integer, default `20`)
  - `user_prompt` (string, default `''`)

`get_polyhaven_asset_preview`
  - `**asset_id**` (string)
  - `user_prompt` (string, default `''`)

`download_polyhaven_asset`
  - `**asset_id**` (string)
  - `**asset_type**` (string)
  - `resolution` (string, default `'1k'`)
  - `file_format` (string)
  - `user_prompt` (string, default `''`)

`set_texture`
  - `**object_name**` (string)
  - `**texture_id**` (string)
  - `user_prompt` (string, default `''`)

### Sketchfab

`get_sketchfab_status`
  - `user_prompt` (string, default `''`)

`search_sketchfab_models`
  - `**query**` (string)
  - `categories` (string)
  - `count` (integer, default `20`)
  - `downloadable` (boolean, default `True`)
  - `user_prompt` (string, default `''`)

`get_sketchfab_model_preview`
  - `**uid**` (string)
  - `user_prompt` (string, default `''`)

`download_sketchfab_model`
  - `**uid**` (string)
  - `**target_size**` (number)
  - `user_prompt` (string, default `''`)

### PolyPizza

`get_polypizza_status`
  - `user_prompt` (string, default `''`)

`search_polypizza_models`
  - `query` (string, default `''`)
  - `category` (string)
  - `licence` (string)
  - `animated` (boolean, default `False`)
  - `limit` (integer, default `20`)
  - `user_prompt` (string, default `''`)

`download_polypizza_model`
  - `**model_id**` (string)
  - `normalize_size` (boolean, default `False`)
  - `target_size` (number, default `1.0`)
  - `user_prompt` (string, default `''`)

### Hyper3D Rodin (text-to-3D / image-to-3D)

`get_hyper3d_status`
  - `user_prompt` (string, default `''`)

`generate_hyper3d_model_via_text`
  - `**text_prompt**` (string)
  - `bbox_condition` (array)
  - `user_prompt` (string, default `''`)

`generate_hyper3d_model_via_images`
  - `input_image_paths` (array)
  - `input_image_urls` (array)
  - `bbox_condition` (array)
  - `user_prompt` (string, default `''`)

`poll_rodin_job_status`
  - `subscription_key` (string)
  - `request_id` (string)

`import_generated_asset`
  - `**name**` (string)
  - `task_uuid` (string)
  - `request_id` (string)

### Hunyuan3D

`get_hunyuan3d_status`
  - `user_prompt` (string, default `''`)

`generate_hunyuan3d_model`
  - `text_prompt` (string)
  - `input_image_url` (string)
  - `quality` (string)
  - `user_prompt` (string, default `''`)

`poll_hunyuan_job_status`
  - `job_id` (string)

`import_generated_asset_hunyuan`
  - `**name**` (string)
  - `**zip_file_url**` (string)

### Tripo

`get_tripo_status`
  - `user_prompt` (string, default `''`)

`generate_tripo_model`
  - `text_prompt` (string)
  - `input_image_url` (string)
  - `quality` (string)
  - `user_prompt` (string, default `''`)

`poll_tripo_job_status`
  - `**request_id**` (string)

`import_generated_asset_tripo`
  - `**request_id**` (string)
  - `**name**` (string)

### Other

`record_trajectory_feedback`
  - `**feedback**` (string)
  - `correction_text` (string)
  - `step_index` (integer)
  - `user_prompt` (string, default `''`)

`disable_telemetry`
  - `user_prompt` (string, default `''`)

## Provenance

Regenerate with:

```bash
# 1. start Blender GUI (headless never opens 9876)
# 2. dump the live schema
python - <<'EOF'
import asyncio, os, json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def main():
    env = dict(os.environ); env['UV_PYTHON_PREFERENCE'] = 'only-managed'
    p = StdioServerParameters(command='/Users/sqs/.hermes/bin/uvx',
        args=['mcp-for-blender'], env=env)
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            for t in (await s.list_tools()).tools:
                print(t.name, json.dumps(t.input_schema))
EOF
```
