# Design — Moshi French TTS

A consistent desktop design system for the application.

## Genre

Modern-minimal: calm, practical, and study-focused.

## Macrostructure family

- App pages: Workbench — input workspace paired with an audio practice workspace.
- Content pages: Long Document — readable, left-aligned instructional content.

## Theme

- Paper: `oklch(97% 0.008 255)`
- Raised paper: `oklch(99% 0.004 255)`
- Ink: `oklch(22% 0.025 255)`
- Muted ink: `oklch(48% 0.025 255)`
- Rule: `oklch(87% 0.018 255)`
- Accent: `oklch(48% 0.13 255)`
- Focus: `oklch(48% 0.13 255)`

## Typography

- Display: Avenir Next / Segoe UI, weight 700, roman.
- Body: Avenir Next / Segoe UI, weight 400.

## Layout

- Wide: resizable side-by-side panes, French text on the left and audio practice on the right.
- Narrow: the same panes stack vertically, input first.
- All controls maintain a 44 px minimum touch target.

## Motion and interaction

- Functional state changes only; no decorative animation.
- Hovering a word during playback temporarily loops that word; leaving resumes from the following word.
- Each sentence button mirrors its own playback state: play, pause, resume, or preparing.
- Sentence rows are borderless: disclosure toggle first, text in the middle, circular play/pause last.
- IPA and meaning stay collapsed until the row disclosure is opened.
- The playing row alone receives a very light grey background.
- Hover highlighting overrides the moving playback highlight until the pointer leaves the word.
- Clicking a word while playback is stopped immediately starts that sentence from the word.
- Transport controls use a compact media-console rhythm: circular rewind, oversized play/pause, fast-forward, then stop.
- The spoken word uses a quiet cobalt highlight while unspoken interactive words remain blue.
- Long TTS synthesis runs away from the interface thread.
