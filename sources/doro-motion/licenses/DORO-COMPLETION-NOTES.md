# Doro Motion 1.1.3 — local release

- Nap 805182028 uses the accepted six-pose body roll: 635 ms entry, original 2000 ms loop, 605 ms recovery.
- Nap/inactive use native phased playback. A normal request during entrance finishes the 635 ms entry before recovery; loop responses start recovery immediately.
- The native nap exit uses its fixed original endpoint as the first recovery frame; the HTML current-frame bridge is preview control logic, not new runtime behavior.
- Start uses the door performance and no longer randomly chooses the two old spider start variants. Turn-start choices are unchanged.
- Thumbs keeps the original eight repaired frames and native 800 ms source timing, with the accepted entry/recovery.
- Dance replaces the existing long-turn and may20 dance assignments; other movement-break/friday/leave-work choices are unchanged.
- Wine replaces the existing wine artwork at cue_birthday_2. Existing birthday pool, weights and main party/cake choice are unchanged; no new birthday event or candidate is enabled.
- Sleep reminder choice cue_sleep_1 uses the finite nap performance; inactive and nap use its sustained phases.
- Approval, work variants, handling, landing, movement, moods, bedtime, input geometry and scheduling are unchanged.
- This mixed-source/LINE-derived pack is local and personal-use only; no gallery or public release upload.
