# Agent Pet gallery

Standalone `.agentpet` packs for [Agent Pet](https://github.com/WindyWin/vpet-agent-pet).
Download a pack from [Releases](https://github.com/WindyWin/agent-pet-gallery/releases),
then use Settings → Pet → Import and review its terms. Requires the phase 2 pack importer.

| Pet | Artwork terms | Distribution decision |
| --- | --- | --- |
| Fat Cat | CC0-1.0, shuaa (megupets) | Included with original credit and terms |
| Kuro | CC0-1.0, Agent Pet contributors | Included; drawing source in scripts/draw_kuro.py |
| Yun | CC0-1.0, Agent Pet contributors | Included; drawing source in scripts/draw_yun.py |
| Whale Girl | CC-BY-NC-SA-4.0, 上善无形 / ZipZipPipe; animation by Multimodal-AI-Companion | Noncommercial distribution only; full attribution and upstream notices retained |
| Bocchi | No source or redistributable terms present in the app repository | Not included; authors can use Agent Pet's workshop converter with their own local art and terms |

Art and metadata were moved from application commit b9dd37a3 without changing the
frames or their catalog mapping. Each archive embeds its own licence text.
Whale Girl remains subject to the upstream attribution, noncommercial and
share-alike conditions; the repository's Apache-2.0 code licence does not apply
to artwork. Upstream claims of original-creator permission are recorded in the
terms and have not been independently verified.

## Build and publish

On Linux, with a phase 2 compatible `agent-pet` binary:

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
