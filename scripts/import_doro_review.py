#!/usr/bin/env python3
"""Import a Doro review into reproducible gallery pet and companion-plugin sources.

Transcodes the approved original PNG/GIFs without changing their existing backgrounds.
Requires ImageMagick; never downloads art or writes to installed app data.
"""
import argparse
import hashlib
import json
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CANVAS = 192
GROUND = 176
TERMS = "DORO-ARTWORK-TERMS.md"
AUTHOR = "Menyou (emoji.gg uploader); original artists unverified"
LICENSE = "LicenseRef-EmojiGG-Basic"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class Catalog:
    def __init__(self, folder, pet, prepared, audit, plugin=False):
        self.folder, self.pet, self.prepared, self.audit, self.plugin = folder, pet, prepared, audit, plugin
        self.document = dict(schema_version=2, sequences=[], states={}, playback={}, variants={}, cues={})
        if not plugin: self.document["asset_root"] = "assets/" + pet
        self.cache, self.files, self.mapping = {}, {}, {}

    def sequence(self, entry, state, asset=None):
        asset = asset or entry["asset"]
        a = self.audit[asset]
        key = (asset, entry["speed"], entry["hold_ms"] if a["frames"] == 1 else None, entry["mirror"])
        if key in self.cache: return self.cache[key]
        name = Path(asset).stem + "-" + hashlib.sha256(json.dumps(key).encode()).hexdigest()[:8]
        frames = []
        durations = [entry["hold_ms"]] if a["frames"] == 1 else [ms or 100 for ms in a["frame_durations_ms"]]
        for file, ms in zip(self.prepared[(asset, entry["mirror"])], durations, strict=True):
            raw = file.read_bytes(); digest = hashlib.sha256(raw).hexdigest()
            relative = "frames/" + digest + ".png"
            target = self.folder / relative
            if not target.exists(): target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
            path = relative if self.plugin else f"assets/{self.pet}/" + relative
            self.files[path] = dict(path=path, bytes=len(raw), sha256=digest)
            duration = max(1, min(60000, math.floor(ms / entry["speed"] + .5)))
            if frames and frames[-1]["path"] == path and frames[-1]["duration_ms"] + duration <= 60000:
                frames[-1]["duration_ms"] += duration
            else: frames.append(dict(path=path, duration_ms=duration))
        sequence = dict(path=name, state=state, frames=frames, duration_ms=sum(f["duration_ms"] for f in frames))
        self.document["sequences"].append(sequence); self.cache[key] = name
        return name

    def choice(self, entry, state, mode):
        loop = self.sequence(entry, state)
        paths = [self.sequence(entry, state, entry.get("enter_asset")) if entry.get("enter_asset") else loop,
                 loop, self.sequence(entry, state, entry.get("exit_asset")) if entry.get("exit_asset") else loop] if mode == "phased" else [loop]
        return dict(sequences=paths, weight=entry["weight"])

    def state(self, name, assignment, mode="once", after="idle", loops=0):
        choices = [self.choice(e, name, mode) for e in assignment["entries"]]
        self.document["states"][name] = choices[0]["sequences"]
        self.document["playback"][name] = dict(mode=mode, after=after, weight=choices[0]["weight"])
        if loops: self.document["playback"][name]["loops"] = loops
        if len(choices) > 1: self.document["variants"][name] = choices[1:]
        return name

    def finish(self):
        write(self.folder / "animations.json", self.document)
        if not self.plugin:
            files = sorted(self.files.values(), key=lambda f:f["path"])
            write(self.folder / "manifest.json", dict(schema_version=1, file_count=len(files), total_bytes=sum(f["bytes"] for f in files), files=files))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--collection", type=Path, required=True)
    parser.add_argument("--version", default="1.0.0")
    args = parser.parse_args()
    review, collection = read(args.review), args.collection.resolve()
    if review.get("schema_version") != 1 or review.get("pack_id") != "doro": raise SystemExit("Expected Doro review schema 1")
    assignments = review["assignments"]
    pending = [k for k,a in assignments.items() if a["status"] == "pending"]
    if pending: raise SystemExit("Unreviewed assignments: " + ", ".join(pending))
    assignments = {k:a for k,a in assignments.items() if a["status"] == "approved"}
    audit = {Path(a["file"]).name:a for a in read(collection / "metadata/audit.json")["assets"]}
    contract = read(ROOT / "src/animation/cues.json")["cues"]
    for key, shape in contract.items():
        if shape["kind"] == "state" and "cue:"+key not in assignments: raise SystemExit("Missing state cue: " + key)
    assets = set()
    combinations = set()
    for key, a in assignments.items():
        if not a["entries"]: raise SystemExit("Empty approved assignment: " + key)
        for e in a["entries"]:
            if e["background"] in {"remove-bg", "manual"}: raise SystemExit("Prepare background edits before importing: " + e["asset"])
            if not isinstance(e["weight"], int) or not 1 <= e["weight"] <= 1000 or e["speed"] not in {.5,.75,1,1.25,1.5,2}:
                raise SystemExit("Invalid weight/speed")
            if not isinstance(e["hold_ms"],int) or not 20 <= e["hold_ms"] <= 60000: raise SystemExit("Invalid hold")
            for asset in [e["asset"], e.get("enter_asset"), e.get("exit_asset")]:
                if not asset: continue
                if asset not in audit or Path(asset).name != asset: raise SystemExit("Unknown asset: " + asset)
                source = collection / audit[asset]["file"]
                if hashlib.sha256(source.read_bytes()).hexdigest() != audit[asset]["sha256"]: raise SystemExit("Source checksum changed: " + asset)
                if audit[asset]["width"] > CANVAS or audit[asset]["height"] > GROUND: raise SystemExit("Source exceeds shared canvas")
                assets.add(asset); combinations.add((asset, e["mirror"]))
    pet_folder, plugin_folder = ROOT / "assets/doro", ROOT / "plugins/doro-events"
    if pet_folder.exists() or plugin_folder.exists(): raise SystemExit("Doro output already exists; keep it or generate in a fresh checkout")
    provenance = ROOT / "sources/doro"
    provenance.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.review, provenance / "review.json")
    write(provenance / "audit.json", dict(assets=[audit[a] for a in sorted(assets)]))
    shutil.copyfile(collection / "metadata/source-terms-sample.json", provenance / "source-terms-sample.json")
    for asset in sorted(assets):
        target = provenance / "originals" / asset; target.parent.mkdir(exist_ok=True)
        shutil.copyfile(collection / audit[asset]["file"], target)
    terms = """# Doro artwork: local reviewed emoji collection

These images were uploaded by Menyou on emoji.gg. Uploader credit is not an
assertion of authorship. Original artists and full redistribution permissions
have not been independently verified. The code repository's Apache-2.0 licence
does not apply to this artwork. This local package grants no additional rights.

The sample page https://emoji.gg/emoji/25686-doro displayed Basic License on
2026-10-28, allowing use on Discord, Slack and platforms where users are not
charged for access to the emoji. Only this sample page's terms were captured;
this is not confirmation of the terms for the remaining artworks. Review the
original creators' terms before redistribution or publication.

The reviewed originals and per-image source URLs, uploader and SHA-256 are kept
in sources/doro in the gallery authoring repository. Pack frames are lossless
PNG transcodes with transparent canvas padding. Existing image backgrounds are
retained; no new illustration or background segmentation was performed.

## Included image sources

"""
    terms += "\n".join(f"- {a}: {audit[a]['page']} (uploader: {audit[a]['uploader']})" for a in sorted(assets)) + "\n"
    (ROOT / "licenses" / TERMS).write_text(terms, encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="doro-convert-") as temporary:
        def convert(pair):
            asset, mirror = pair; output = Path(temporary) / (asset + ("-flipped" if mirror else "")); output.mkdir()
            cmd = ["magick", str(collection / audit[asset]["file"]), "-coalesce", "-alpha", "on"]
            if mirror: cmd.append("-flop")
            cmd += ["-background", "none", "-gravity", "south", "-extent", f"{CANVAS}x{GROUND}", "-gravity", "north", "-extent", f"{CANVAS}x{CANVAS}", "-strip", "-define", "png:color-type=6", "+adjoin", str(output / "frame-%04d.png")]
            subprocess.run(cmd, check=True, capture_output=True)
            frames = sorted(output.glob("*.png"))
            if len(frames) != audit[asset]["frames"]: raise ValueError("Frame count mismatch: " + asset)
            return pair, frames
        with ThreadPoolExecutor(max_workers=4) as pool: prepared = dict(pool.map(convert, sorted(combinations)))
        pet = Catalog(pet_folder, "doro", prepared, audit)
        plugin = Catalog(plugin_folder, "doro", prepared, audit, plugin=True)
        mapping, rules = {}, []
        for key, a in assignments.items():
            if key.startswith(("mood:", "bedtime:")): continue
            name = key.replace(":", "_").replace("-", "_")
            if key.startswith("cue:"):
                cue = key[4:]; shape = contract[cue]
                if shape["kind"] == "state":
                    state = "idle" if cue == "idle" else name
                    pet.state(state, a, shape["mode"], shape["after"]); pet.document["cues"][cue] = state; mapping[key] = [state]
                else:
                    pool = []
                    for i,e in enumerate(a["entries"]):
                        state = f"{name}_{i+1}"; pet.state(state, dict(entries=[e]))
                        pool.append(dict(state=state,weight=e["weight"]))
                    pet.document["cues"][cue] = pool; mapping[key] = [p["state"] for p in pool]
            elif key.startswith("touch:"):
                pet.state(name, a, "phased"); mapping[key] = [name]
            elif key.startswith("ambient:"):
                pet.state(name, a); mapping[key] = [name]
                pet.document.setdefault("ambient",{}).setdefault("fidgets",[]).append(dict(state=name,weight=1,min_idle_s=30))
            elif key.startswith("move:"):
                move = key[5:]; pet.state(name, a, "phased", loops=2); mapping[key] = [name]
                right = move.endswith("right"); side = "right" if right else "left"
                speed = 55 if move.startswith("trot") else 25 if move.startswith(("trudge","crawl")) else 36
                spec = dict(state=name, speed=[speed if right else -speed,0], room={side:CANVAS},keep={side:CANVAS//3})
                if move.startswith("climb"):
                    up = "_up_" in move
                    vertical = "top" if up else "bottom"
                    spec.update(speed=[0,-25 if up else 25],wall=dict(side=side,at=32 if side=="left" else 160),near={side:40},room={vertical:CANVAS},keep={vertical:CANVAS//3})
                if move.startswith("trot"): spec["mood"]="happy"
                if move.startswith("trudge"): spec["mood"]="poor"
                pet.document.setdefault("moves",dict(scale=CANVAS,list=[]))["list"].append(spec)
                pet.document.setdefault("ambient",{}).setdefault("fidgets",[]).append(dict(state=name,weight=1,min_idle_s=240 if move.startswith("climb") else 120))
            elif key.startswith(("custom:","trigger:")):
                trigger = key[8:] if key.startswith("trigger:") else key
                mapping[key] = []
                for i,e in enumerate(a["entries"]):
                    state = "doro-events." + name + f"_{i+1}"; plugin.state(state,dict(entries=[e])); mapping[key].append(state)
                    rule = dict(on=trigger,state=state,weight=e["weight"])
                    if trigger.startswith("custom:"): rule["cooldown_ms"]=a["cooldown_ms"]
                    if a["say"]: rule["say"]=a["say"]
                    rules.append(rule)
            else: raise SystemExit("Unknown assignment: " + key)
        for key,a in assignments.items():
            if key.startswith("mood:"):
                _,mood,cue = key.split(":"); state=pet.document["cues"][cue]
                pet.document.setdefault("moods",{}).setdefault(mood,{})[state]=[pet.choice(e,state,contract[cue]["mode"]) for e in a["entries"]]
                mapping[key]=[state]
            elif key.startswith("bedtime:"):
                cue=key[8:]; state=pet.document["cues"][cue]
                pet.document.setdefault("bedtime",{})[state]=[pet.choice(e,state,contract[cue]["mode"]) for e in a["entries"]]
                mapping[key]=[state]
        pet.document.setdefault("ambient",{})["sleep_after_s"]=300
        pet.document["touch"]=dict(scale=CANVAS,regions=[dict(state="touch_pinch",tap=False,rect=[54,65,30,30]),dict(state="touch_touch_head",rect=[40,45,110,75]),dict(state="touch_touch_body",rect=[50,123,90,40])],fall=dict(left="touch_fall_left",right="touch_fall_right"),edge=dict(left=dict(state="touch_edge_left",at=64),right=dict(state="touch_edge_right",at=128)))
        pet.finish(); plugin.finish()
        metadata=dict(kind="pet",id="doro",name="Doro",author=AUTHOR,license=LICENSE,version=args.version,schema=2,minAppVersion="0.18.7",terms="licenses/"+TERMS,source="emoji.gg reviewed collection")
        write(pet_folder / "pack.json",metadata)
        write(pet_folder / "pet.json",dict(schema_version=1,id="doro",name="Doro",author=AUTHOR,url="https://emoji.gg/emoji/25686-doro",terms=TERMS,preview="preview.png"))
        idle_entry=assignments["cue:idle"]["entries"][0]
        shutil.copyfile(prepared[(idle_entry["asset"],idle_entry["mirror"])][0],pet_folder/"preview.png")
        pluginmeta={**metadata,"kind":"plugin","id":"doro-events","name":"Doro Events","pet":"doro"}
        write(plugin_folder/"pack.json",pluginmeta)
        write(plugin_folder/"plugin.json",dict(schema_version=1,id="doro-events",name="Doro Events",version=args.version,author=AUTHOR,license=LICENSE,pet="doro",min_app_version="0.18.7"))
        write(plugin_folder/"events.json",dict(schema_version=1,rules=rules))
        shutil.copyfile(pet_folder/"preview.png",plugin_folder/"preview.png")
        write(provenance/"mapping.json",dict(review_sha256=hashlib.sha256(args.review.read_bytes()).hexdigest(),canvas=[CANVAS,CANVAS],ground_y=GROUND,background_policy="preserve original pixels and alpha; transparent padding only",zero_delay_ms=100,slot_states=mapping,pet_sequences=len(pet.document["sequences"]),unique_pet_pngs=len(pet.files),plugin_rules=len(rules)))
    print(f"Imported {len(assignments)} approvals, {len(assets)} originals → assets/doro + plugins/doro-events")


if __name__ == "__main__": main()
