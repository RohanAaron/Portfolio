# Hyperframes Composition Brief: Rohan Aaron Indupally — Robotics/ML Portfolio

## Objective
Create a short launch-style brag video for Rohan Aaron Indupally's robotics/ML portfolio repo — no product UI exists, so the video is built entirely from the repo's own terminal-styled README voice plus real project artifacts (diagrams, plots, CAD renders).

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080
- Duration: ~20 seconds

## Source Material
- Project root: `/home/user/Portfolio`
- Primary files read: `README.md` (root profile), `graduate/CUBIST/README.md`, `graduate/projects/Bayesian IRL Human Corrections/README.md`, `undergraduate/projects/atv-gearbox-team/README.md`
- Product name: Rohan Aaron Indupally (portfolio repo, no separate product name)
- Tagline / strongest claim: "Teaching machines to see, understand, and refine themselves." (root README subtitle)
- Key UI or visual moment to recreate: the root README's `whoami --verbose` terminal block — black background, monospace, `> ` prompt lines, `STATUS: [ONLINE]` in green
- Copy that must appear verbatim:
  - `> rohan_indupally.exe`
  - `> STATUS: [ONLINE]`
  - `82.5%` and `p ~ 10⁻⁹` (from CUBIST's human-study/statistical-significance results)
  - `0% → 100%` (Bayesian IRL accuracy progression)
  - `3rd of 120 teams` (ATV gearbox team design-evaluation placement)

## Creative Direction
- Tone preset: default
- Creative direction: terminal boot-up meets highlight reel — deadpan technical humor lifted verbatim from the source README, real hardware, real numbers, no invented claims
- Interpretation: playful but not silly; comfortable pacing (5 scenes, ~4s each); crossfades between the terminal frame and each project; mixed-case type throughout; the jokes are the README's own voice, not new ones
- Angle: The repo already narrates itself like a running program (`whoami --verbose`, `STATUS: [ONLINE]`, a fake uptime counter). The video opens like a system boot sequence, lets the "system" prove itself with three real, numbers-backed projects, and closes on the same self-aware joke the README ends on.
- Hook: Black terminal screen. `> rohan_indupally.exe` types out, then `> STATUS: [ONLINE]` types beneath it in accent green. Cursor blinks once.
- Outro / punchline: Terminal reappears. `> STATUS: still teaching robots to argue with themselves.` then `> They're winning more arguments now.` type out; `github.com/RohanAaron` fades in small beneath in accent green.
- Avoid:
  - Generic SaaS language ("streamline your workflow" etc.)
  - Abstract filler visuals — every scene must show a real repo artifact (the terminal text itself counts)
  - Any invented UI, mockup, or product screen — this repo has no app; do not fabricate one

## Visual Identity
- Background: near-black terminal, `#0d1117`
- Text: off-white, `#e6edf3`
- Accent: terminal green, `#2ea043`
- Display font: monospace terminal font (e.g. JetBrains Mono / Fira Code) — the whole source README is written as literal terminal output, so one monospace family carries the entire video
- Body font: same monospace family
- Visual references from the project:
  - `graduate/CUBIST/images/Complete_Pipeline_page-0001.jpg` (pipeline diagram)
  - `graduate/projects/Bayesian IRL Human Corrections/Images/theta_trajectory_simplex.png` (belief trajectory plot)
  - `undergraduate/projects/atv-gearbox-team/images/cad_full_assembly.jpg` (full-vehicle CAD render)

## Storyboard
Use the storyboard in `brag-output/brag-plan.md` as the creative contract.

Scene summary:
1. Boot — 4s — terminal boot lines type in sequence, must read `> rohan_indupally.exe` then `> STATUS: [ONLINE]`
2. Highlight: CUBIST — 4s — pipeline diagram image, `82.5%` slams in then `p ~ 10⁻⁹` settles beneath
3. Highlight: Bayesian IRL — 4s — simplex plot image, counter ticks `0% → 100%` while trajectory line draws
4. Highlight: ATV gearbox — 4s — CAD render, `3rd of 120 teams` drops in beneath it
5. Outro — 4s — terminal reappears, two status lines type out, then `github.com/RohanAaron` fades in

## Audio
- Audio role: warm, upbeat rhythmic bed under a mostly text/visual video; SFX carry the terminal-boot feel
- Audio arc: quiet/low under the boot (Scene 1), lifts slightly across the three highlights (Scenes 2-4), lifts once more and settles into a fade-out under the outro (Scene 5)
- Music: `happy-beats-business-moves-vol-10-by-ende-dot-app.mp3` (copied into `brag-output/composition/assets/music/`), trimmed to ~20s
- Music treatment: low bed volume at start so typed lines read clearly; slight lift entering Scene 2; gentle swell/fade into and under Scene 5's final lines
- Music cue guidance: bundled preset at `.claude/skills/brag/assets/music/cues/happy-beats-business-moves-vol-10-by-ende-dot-app.music-cues.json` (also `.md`). Tempo 109.96 BPM. Strong cues at 15.82s, 18.01s, 18.55s, 20.19s, 20.74s fall inside the Scene 4→5 transition and Scene 5 itself — good targets for the outro's first status line and/or the github-handle reveal. Full beat grid runs ~0.54-0.55s apart (0.27, 0.82, 1.37, 1.90, 2.46...) — usable for the three stat reveals in Scenes 2-4 if each stat still gets its full reading-time floor (short label ~0.8s settled) rather than re-triggering every beat.
- Audio-reactive treatment: subtle — terminal cursor blink and the accent-green glow on stat numbers may breathe slightly with music energy; nothing waveform-literal, no equalizer bars
- Audio-coupled moments:
  - Scene 1 (boot) — hook types character-by-character with key-tick SFX
  - Scene 2 (CUBIST) — `82.5%` slam gets a light impact/accent hit; pipeline image entrance gets a UI click/switch
  - Scene 3 (Bayesian IRL) — counter ticks `0%→100%` matched to soft counting SFX, resolving on a clean tone at 100%
  - Scene 4 (ATV) — CAD render settle gets one satisfying metal/impact SFX; ranking line drop-in gets a light UI tick
  - Scene 5 (outro) — both status lines type with the same key-tick treatment as Scene 1, bookending the video; github handle fades in under the music's fade-out
- SFX selection guidance: mechanical-keyboard keypress ticks for all typed terminal text (`assets/sfx/keyboard/`), clean UI click/switch for scene transitions and image entrances (`assets/sfx/ui/`), one metal/impact hit for the real-hardware CAD reveal (`assets/sfx/impact/`)
- SFX analysis guidance: `.claude/skills/brag/assets/sfx/sfx-analysis.md` / `.json` — prefer lower high-frequency-risk sounds since the keyboard ticks repeat across two scenes
- Exact SFX choice: Hyperframes should choose filenames, timestamps, density, and volume based on the implemented animation
- Audio files: copy the chosen music (done) and any Hyperframes-selected SFX into `brag-output/composition/assets/`

## Hyperframes Instructions
Load the composition-building Hyperframes domain skills — `hyperframes-core` (composition contract + `data-*` timing), `hyperframes-animation` (motion), `hyperframes-creative` (design spec, beats, audio-reactive), `hyperframes-keyframes` (seek-safe keyframes), and `hyperframes-cli` (lint/check/render). `/brag` is its own workflow: do not enter the `hyperframes` entry-point intent interview and do not route into its generic promo / launch-video workflow. Prefer native Hyperframes conventions over anything in `/brag`.

Requirements:
- Show at least one real UI, copy, or visual element from the source project (the terminal README text and the three project images/diagrams satisfy this — do not fabricate a UI that doesn't exist).
- Keep all text readable in the final render.
- Keep the video within 15-25 seconds.
- Include the planned music/SFX layer (not disabled by the user).
- Treat `/brag` audio notes as guidance, not a fixed cue sheet. Choose SFX after the visual animation exists.
- Treat music cue metadata as optional timing hints. Ignore cues that hurt readability, scene pacing, or the story.
- Major reveals may move toward nearby strong cues within about 0.15s. Smaller entrances may align to nearby beat points within about 0.10s. Use only 1-3 strong cue locks in this ~20s video.
- Use SFX to support motion and interaction: card/UI sounds for image reveals, a short announcement/impact cue for major payoffs (the stat slams, the CAD reveal), key/click sounds for the typed terminal text.
- Honor the planned fade-in/fade-out and volume-lift treatment described above.
- When music is present, use the Hyperframes audio-reactive workflow for subtle, restrained visual response (glow/presence on stat numbers or the terminal cursor) — avoid waveform/equalizer visuals, musical-note graphics, particle systems, strobing, or heavy pulsing.
- Use local assets (the copied music file, the three project images referenced above, any SFX selected) for all media dependencies.
- Run `hyperframes check` before render — it is brag's single gate.
