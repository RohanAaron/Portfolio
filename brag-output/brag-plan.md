# Brag Plan: Rohan Aaron Indupally — Robotics/ML Portfolio

## What is this app?
A GitHub portfolio repo for a Virginia Tech robotics MS student — no landing page, just a terminal-styled profile README plus a stack of real graduate/undergraduate robotics and ML projects (fabricated hardware, SLAM, Bayesian inference, generative 3D) each with its own README, code, and images.

## The angle
The repo's own voice already treats itself like a program: `whoami --verbose`, `STATUS: [ONLINE]`, a fake uptime counter. The video leans into that — open it like a system boot sequence, then let the "system" prove itself with three real, numbers-backed projects, and land on the same self-aware joke the README ends on.

## Hook (first 2-3 seconds)
A black terminal screen. Monospace text types itself out line by line, exactly as written in the README:
```
> rohan_indupally.exe
> STATUS: [ONLINE]
```
The cursor blinks once after `[ONLINE]` before the cut.

## Key moments (the middle)
- **CUBIST** — the full pipeline diagram (`graduate/CUBIST/images/Complete_Pipeline_page-0001.jpg`) fills the frame; the number `82.5%` slams in, followed by `p ~ 10⁻⁹` in smaller type underneath — a real statistical-significance flex, not a made-up metric.
- **Bayesian IRL from human corrections** — the belief-simplex plot (`graduate/projects/Bayesian IRL Human Corrections/Images/theta_trajectory_simplex.png`) with a counter that ticks `0% → 100%` accuracy as the trajectory line draws itself across the simplex.
- **ATV gearbox team** — the full-vehicle CAD render (`undergraduate/projects/atv-gearbox-team/images/cad_full_assembly.jpg`) with the line `3rd of 120 teams` dropping in under it.

## Outro / punchline
Cut back to the terminal. Final line types out:
```
> STATUS: still teaching robots to argue with themselves.
> They're winning more arguments now.
```
Hold, then a small final line: `github.com/RohanAaron` (or however the account should be referenced) fades in beneath it.

## User flow worth showing
None — landing-page only (there is no app UI, just a code/docs portfolio). Substituted with the terminal-boot framing device (entry) and the three real project highlights with their actual diagrams/renders and verified numbers (the "product doing its thing" here is the research/hardware itself, shown through its own artifacts).

## Tone
- Preset: `default`
- Creative direction: terminal boot-up meets highlight reel — deadpan technical humor, real hardware, real numbers, no generic "streamline your workflow" language anywhere.
- Interpretation: playful but not silly — the jokes are already baked into the source README's voice, so the video plays it exactly as written rather than adding new jokes. Comfortable pacing (5 scenes, ~4s each), crossfades between the terminal frame and each project, mixed-case type throughout.

## Format: landscape — 1920x1080
## Duration: ~20 seconds

## Visual identity (from the project)
- Background: near-black terminal, `#0d1117` (GitHub dark background convention — no CSS exists in this repo, so this is inferred from the terminal aesthetic the README itself uses)
- Accent: terminal green, `#2ea043` (used for `[ONLINE]`, the diff `+` lines, and stat call-outs)
- Text: off-white, `#e6edf3`
- Display font: a monospace terminal font (e.g. JetBrains Mono / Fira Code) — the entire README is written as literal terminal/code output, so display and body share one monospace family
- Body font: same monospace family
- Strongest visual element: the `whoami --verbose` ASCII block — it's the single most distinctive, on-brand visual in the whole repo and should frame the open and close

## Share copy (draft)
MS robotics student who builds systems that critique and improve their own output — CUBIST pushed 3D generation from 70% to 85% alignment, and yes, the arm actually learns from being nudged.

## Audio direction
- Role: warm, upbeat rhythmic bed under a mostly-visual/text video; SFX carry the terminal-boot feel
- Music: `happy-beats-business-moves-vol-10-by-ende-dot-app.mp3` (60s bundled track, ~110 BPM — trimmed to the video's ~20s) — energetic enough to carry a highlight reel without fighting the deadpan terminal humor
- Music treatment: starts at 0s under the boot sequence at a low bed volume so the typed lines are the focus; volume lifts slightly entering the three project highlights; short swell/fade going into the outro
- Music cue guidance: preset read from `assets/music/cues/happy-beats-business-moves-vol-10-by-ende-dot-app.music-cues.json`. Tempo 109.96 BPM. Strong cues at 15.82s, 18.01s, 18.55s land inside the outro window and are good targets for the final "STATUS: still teaching robots..." line and the github handle reveal. Beat grid runs roughly every 0.54-0.55s (e.g. 0.27, 0.82, 1.37, 1.90...) — usable for the three stat/number reveals during the highlight scenes if kept to a floor of ~0.8s hold per number (i.e. snap the reveal to a beat, then hold across the next beat or two rather than re-triggering every beat).
- Audio-reactive treatment: subtle — the terminal cursor blink and the accent-green glow on stat numbers may breathe slightly with the beat; nothing waveform-literal
- SFX posture: moderate — mechanical-keyboard keypress ticks under the typed terminal lines (`assets/sfx/keyboard/`), a clean UI click/switch on each scene transition (`assets/sfx/ui/`), one satisfying metal/impact hit under the ATV CAD reveal (`assets/sfx/impact/`) since it's real hardware
- Audio-coupled moments: the hook types character-by-character with key ticks; each of the three stat numbers (82.5%, 0%→100%, 3rd/120) counts/slams in on a beat with a light UI sound; final two outro lines type out with the same key-tick treatment as the hook, bookending the video
- Restraint rule: no music swell or SFX hit should ever land before its text is done typing — audio follows the text, never rushes it; keep the bed low enough that it never competes with the typed lines

## Storyboard

### Scene 1 — Boot — 4s
Black terminal screen. `> rohan_indupally.exe` types out character-by-character, then `> STATUS: [ONLINE]` types beneath it in accent green. Cursor blinks once after `[ONLINE]` settles.
Sequential/interaction: yes — two lines type in sequence, one after the other, not simultaneously.
Audio intent: establish focus and curiosity — quiet, precise, a little tense before the reveal.
Audio-coupled idea: key-tick SFX synced to each typed character; a soft low music bed fades in under the first line.
Music: low bed, "happy-beats-business-moves-vol-10" intro.
Transition mood: clean → Scene 2

### Scene 2 — Highlight: CUBIST — 4s
`graduate/CUBIST/images/Complete_Pipeline_page-0001.jpg` fills most of the frame. `82.5%` slams in large over it, `p ~ 10⁻⁹` settles in smaller type just beneath.
Sequential/interaction: yes — the percentage arrives first and holds, then the p-value line arrives right after (not simultaneous).
Audio intent: the first real "proof" moment — a confident, satisfying hit.
Audio-coupled idea: UI click/switch SFX on the pipeline image entrance; a light impact/accent SFX under the `82.5%` slam.
Transition mood: clean crossfade → Scene 3

### Scene 3 — Highlight: Bayesian IRL — 4s
`graduate/projects/Bayesian IRL Human Corrections/Images/theta_trajectory_simplex.png` fills the frame. A counter ticks from `0%` to `100%` accuracy as the belief trajectory line appears to draw itself across the simplex.
Sequential/interaction: yes — the counter increments and the trajectory line grows in tandem, not a static overlay.
Audio intent: momentum — the sense of something converging in real time.
Audio-coupled idea: soft counting/tick SFX matched to the counter's increments, resolving on a clean tone at `100%`.
Transition mood: clean crossfade → Scene 4

### Scene 4 — Highlight: ATV gearbox — 4s
`undergraduate/projects/atv-gearbox-team/images/cad_full_assembly.jpg` fills the frame. `3rd of 120 teams` drops in beneath the vehicle render.
Sequential/interaction: yes — the CAD render settles first, then the ranking line drops in under it a beat later.
Audio intent: physical, tactile payoff — this one is real hardware, not just a plot.
Audio-coupled idea: a single satisfying metal/impact SFX timed to the CAD render's settle; light UI tick under the ranking line's drop-in.
Transition mood: clean → Scene 5

### Scene 5 — Outro — 4s
Cut back to the black terminal frame from Scene 1. Two new lines type out:
```
> STATUS: still teaching robots to argue with themselves.
> They're winning more arguments now.
```
Hold, then `github.com/RohanAaron` fades in small beneath, in accent green.
Sequential/interaction: yes — the two status lines type in sequence, then the handle fades in after both have settled (not before).
Audio intent: the punchline landing, then a clean, confident close.
Audio-coupled idea: key-tick SFX matches the typed lines exactly as in Scene 1, bookending the video; music aligns its lift-and-settle to the strong cues around 18.0-18.6s under these lines, with a gentle fade-out under the final handle reveal.
Transition mood: soft (hold to black)

**Music mood for this video:** upbeat
**Audio summary:** A low, confident "happy beats" bed frames the whole video — quiet and precise under the terminal boot and outro, a touch more present under the three project highlights — while mechanical-keyboard ticks and clean UI/impact SFX carry every typed line, stat reveal, and scene change so the video always feels driven by what's on screen, never by the music.
