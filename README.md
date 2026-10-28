# Agent Pet gallery

Standalone `.agentpet` packs for [Agent Pet](https://github.com/WindyWin/vpet-agent-pet).
Download a pack from [Releases](https://github.com/WindyWin/agent-pet-gallery/releases),
then use Settings → Pet → Import and review its terms. Requires an Agent Pet build
with the phase 4 gallery migration ([app PR #111](https://github.com/WindyWin/vpet-agent-pet/pull/111)).
Older builds still reserve these pet ids in their artwork index and reject their import.

| Pet | Artwork terms | Distribution decision |
| --- | --- | --- |
| Fat Cat | CC0-1.0, shuaa (megupets) | Included with original credit and terms |
| Kuro | CC0-1.0, Agent Pet contributors | Included; drawing source in scripts/draw_kuro.py |
| Yun | CC0-1.0, Agent Pet contributors | Included; drawing source in scripts/draw_yun.py |
| Doro + Doro Events | Menyou uploads on emoji.gg; Basic License captured on one sample page, original artists unverified | Local reviewed sources and packs prepared; redistribution terms need review before publication |
| Whale Girl | CC-BY-NC-SA-4.0, 上善无形 / ZipZipPipe; animation by Multimodal-AI-Companion | Noncommercial distribution only; full attribution and upstream notices retained |
| Bocchi | No source or redistributable terms present in the app repository | Not included; authors can use Agent Pet's workshop converter with their own local art and terms |

Art and metadata were moved from application commit b9dd37a3 without changing the
frames or their catalog mapping. Each archive embeds its own licence text.
Whale Girl remains subject to the upstream attribution, noncommercial and
share-alike conditions; the repository's Apache-2.0 code licence does not apply
to artwork. Upstream claims of original-creator permission are recorded in the
terms and have not been independently verified.

## Build and publish

On Linux, with the phase 4 VPet-only `agent-pet` binary:

```bash
python scripts/verify_assets.py
python scripts/build_gallery.py --app /path/to/agent-pet --tag v1.0.0
```

The build validates every pack, imports each archive in a fresh per-user data
folder, and generates archives, previews and `index.json` in `dist/`. Tag pushes
run the same checks and publish all artifacts together. Update `pack.json.version`
when changing a pack and use a new gallery release tag; never overwrite old
release assets. The validator commit is pinned in CI and should be advanced
explicitly when the pack format changes.

The version-1 source index uses `schema_version: 1` and `packs: [...]`. Each
entry carries kind, id, version, name, description, author, licence, preview and
download HTTPS URLs, byte count, SHA-256, catalog schema and minimum app version.
This establishes the concrete producer format for the phase 5 source browser.

Drawing Kuro/Yun requires pycairo and Pillow; importing Whale Girl from the user's
local source requires Pillow. Authoring helpers retain the application's catalog
and cue rules; scripts/new_pet.py can scaffold a new assets folder. `src/animation/`
contains the vocabulary snapshot used by those helpers, not application code.

## Doro review import

`sources/doro/review.json` preserves the user's 76 approved assignments and its
original SHA-256. `sources/doro/originals/` and `audit.json` retain the 90 selected
originals, their per-image source URLs, uploader, frame delays and hashes.

```sh
python3 scripts/import_doro_review.py --review /path/to/doro-review.json --collection /path/to/doro-emoji-gg
```

Run the importer in a fresh checkout without `assets/doro` or `plugins/doro-events`.
It verifies source hashes, coalesces GIF frames and exports lossless PNG RGBA on a
192 × 192 canvas, bottom aligned at y=176 without scaling. Existing pixels and
backgrounds are preserved for every `auto` selection; no background removal was
performed. `sources/doro/mapping.json` records cue/state coverage and conversion
policy. The zero-delay `dorothink3` animation uses the preview's 100 ms per frame.
Identical PNGs share a file and consecutive duplicate frames merge their delays.
Empty phase overrides reuse the main clip, as shown in the review tool.

Touch regions and wander settings have initial coordinates for that shared
canvas. The twelve approved moves retain their selected sources and mirror flags;
speed/edge anchors are conservative authoring defaults and can be tuned on desktop.

`assets/doro` produces the pet; `plugins/doro-events` produces the optional companion
for `break-buddy`, `deploy_succeeded`, `tests_failed` and `build_succeeded`. Install
Doro, restart, then install and enable Doro Events. Custom events still require an
external script, for example `agent-pet emit --custom deploy_succeeded`. Installing
this plugin does not connect CI or send events automatically.

Build with Agent Pet 0.18.7 or later, whose validator supports the tool cues and
bedtime mappings. Both packs include a preview image and full provenance terms.
No Doro release has been published by this change.

For a local Doro-only build:

```sh
python3 scripts/build_gallery.py --app /path/to/agent-pet --only doro doro-events --output dist/doro-review --tag v1.1.0-doro-preview
```

The `break-buddy` rules join the pet's built-in response pool, as required by the
current event-rule format; they do not replace its movement-break fallback.
`index.json` contains release URLs prepared for that tag, not a claim that those
URLs are already published. Import the two local `.agentpet` files for testing.
