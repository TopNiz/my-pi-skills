---
name: animated-film
description: Create short animated films entirely in code using Lemo-Opuscar's style library. Use for a film, animation, promo, or explainer; style selection; or creating a custom film style. Not for editing or converting existing videos.
---

# Animated Film

Create the user's film in a project folder in their current workspace, using the maintained [Lemo-Opuscar](https://github.com/lemomo-ai/lemo-opuscar) library for style definitions, production guidance, and render tools. The film's story and assets must be about the user's subject; do not reuse a demo film's story, shots, or timeline.

## Prepare the library

Use the library already present if the current folder is a Lemo-Opuscar clone. Otherwise use `~/lemo-opuscar`, cloning the public repository when it is absent. Keep the clone sparse if practical; the library's official Codex/Claude skill setup script is available in `plugin/skills/lemo-opuscar/scripts/setup.sh` and handles library discovery and updates. Do not overwrite a non-library folder. Tell the user if setup cannot proceed.

Read the library's `AGENTS.md` first and follow it, then consult `DIRECTOR.md`, `TECHNIQUE.md`, `core/README.md`, and the chosen style's `STYLE.md` as their workflow requires. Check `~/lemo-my-styles/README.md` for user-created styles when it exists. Use the library gallery to help choose: https://lemomo-ai.github.io/lemo-opuscar/.

Install system software only when necessary and with the user's authorization. The documented baseline is Node 20+, ffmpeg 7+, and Python 3.11+ or `uv`; library packages can be installed in its managed environment. Add voice, music, style-specific packages, image generation, sample packs, or external source material only when the chosen film requires them. Explain any external data or media source and its licence before fetching it.

## Direct and produce

- Speak with the user in the language they use. If they provide a clear brief and style, proceed without asking redundant questions. If the style is open, recommend two or three that suit the subject and link the gallery. Ask one compact set of questions for genuinely missing choices (such as style, length, language, voice, aspect ratio, assets, and whether they want a storyboard), using practical defaults where appropriate.
- Respect the chosen `STYLE.md` invariants. Default to 30–60 seconds, 1920×1080 at 24 fps, and voice/subtitles in the user's language unless the brief or style says otherwise. Explain the added time and resource cost before undertaking a substantially longer film.
- Before opening the style demo's `DEMO.md` or source, write a project-local `TREATMENT.md`: compare a few distinct story structures, choose one, set the logline and arc, list timed shots and beats, and map music and sound. For documentary styles that need real material first, follow the exception in the library's `AGENTS.md` and style guide.
- Build the film in its own project folder, never inside the library's `styles/`. Use the demo only to learn reusable production techniques after the treatment; do not copy its story, characters, shots, props, or timing. Render and inspect style frames, then the final film. If a storyboard is requested, render it in the real style and wait for approval before full production.
- Make the picture deterministic frame by frame. Design sound alongside picture; mix narration, music, ambience, and foley deliberately. Follow the library's delivery checklist and leave source, treatment, and final output together in the project folder.

## Rights and delivery

The user's finished film is theirs. Third-party material keeps its own licence; check each source and preserve credits where required. Do not extract or reuse the six excluded narration tracks, Anthropic's Clawd character, third-party marks, or other excluded materials documented in the library's `LICENSE` and credits. The repository's code is MIT; its guides/prompts are CC BY-NC 4.0 with additional permission for making films, and its demo films/stills are CC BY 4.0 subject to stated exceptions. Do not redistribute the library or its adapted guides as a product. Follow current `LICENSE` and per-asset credits if licensing matters.

When done, give the user the project folder and final film path, summarize the style and key production choices, and disclose any production or rights limitation that affected the result.
