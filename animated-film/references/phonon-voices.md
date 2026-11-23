# Local narration with Gradium Phonon

Use the official [ptts runtime](https://github.com/gradium-ai/xn-ptts) with downloads from Hugging Face. A GGUF file needs Phonon's runtime and its matching configuration, tokenizer and voice assets; it is not interchangeable with a generic GGUF loader.

## Models and practical defaults

These are skill defaults, not claims that one voice is objectively best. Follow the user's chosen language, voice and gender first.

| Film language | Hugging Face model | Default voice | Female alternative |
|---|---|---|---|
| French | `gradium/phonon-40m-fr` | Augustin | Noémie |
| English (US) | `gradium/phonon-31m-en` | Easton | Zoey |
| English (UK) | `gradium/phonon-31m-en` | Alfie | Maeve |
| German | `gradium/phonon-40m-de` | Anton | Nele |
| Spanish (Spain) | `gradium/phonon-40m-es` | Marcos | Noa |
| Spanish (Mexico) | `gradium/phonon-40m-es` | Lalo | Rebeca |
| Portuguese (Brazil) | `gradium/phonon-40m-pt` | Davi | Manuela-Lu |
| Mixed English/French/German/Spanish/Portuguese | `gradium/phonon-40m-multilingual` | Choose a catalog voice for the main language | Preview language changes |

`gradium/phonon-40m-en` is another English option. The 31M English model is Apache-2.0; the 40M models are CC BY-NC 4.0 and gated. Check the model card for the intended use, especially commercial films. The film library's permission for commercial films does not override a speech model's licence. If the selected model is unsuitable, explain and offer a licensed engine or user-provided recording.

Ollama's `phonon:latest` denotes its English package, not a French or multilingual model. Ollama platform support differs from `ptts`; an MLX error on Windows does not mean Phonon cannot run there. The official `ptts` q8 CPU path successfully generated French narration on PC Master in this workflow. Check the installed runtime's capabilities before promising GPU acceleration.

## Voice menu

French male: **Augustin**, Arnaud, Jules, Baptiste, Lucien, Marius.

French female: **Noémie**, Coralie, Tiphaine, Maëlys, Orianne, Solène, Ninon, Lilou, Hélène.

For the complete current catalog, accents, gender metadata and audio previews, consult [gradium/phonon-voices](https://huggingface.co/gradium/phonon-voices) or `uvx ptts --list-voices`. Voice names do not switch the model's supported language. English character voices are also available; verify suitability with a preview. Do not promise arbitrary emotion or pitch control: selecting a voice, adjusting pace and editing pauses are supported choices; free-form acting directions are not a documented ptts control.

## Setup and generation

Check `hf auth whoami` on the actual rendering machine. For gated models, the user must accept the model's Hugging Face access conditions using the same account, then authenticate there with `hf auth login`. Login and model access are separate. A 403 `GatedRepo` after login usually requires accepting that specific model's conditions. Keep tokens in the machine's Hugging Face credential cache, never in the project, skill, logs or chat.

With `uv` available:

```sh
uvx ptts --help
uvx ptts --model hf://gradium/phonon-40m-fr --lang fr --quant q8_0 --voice Augustin --seed 217 "Bonjour, Monsieur du Corbeau." -o preview.wav
```

On Windows PowerShell, use `& "$env:USERPROFILE/.local/bin/uv.exe" tool run ptts ...` if `uvx` is not on PATH. The installed runtime used `q8_0`; some documentation uses `q8`, so inspect `--help` rather than assuming the spelling. The runtime downloads and caches the model and selected catalog embedding. For a local model directory, preserve all companion files. Record the runtime version, model revision, voice and generation settings in the project for reproducibility.

Use normal pace by default. `--condition duration_delta=0.3` requests slower delivery; `-0.3` requests faster. Start with modest adjustments and check pronunciation. Create pauses in the edit rather than inserting instructions into spoken text. Users can request another voice/gender/accent, supported language, pace, pauses, narrator/character assignments, their own recording, a voice sample comparison, or no narration. Voice cloning/design is a separate Gradium workflow and requires a suitable authorized voice source; do not imply that supplying any WAV to these checkpoints automatically enables cloning.

Generate by sentence or verse group, preserve WAV clips, measure their durations, and rebuild captions and shots from those timings. Export a voice-only `narration.wav`. Compare an ASR transcription with the intended speech; distinguish homophone spelling from missing words. Check final mixing and audio peaks after encoding.

Sources: [model collection](https://huggingface.co/collections/gradium/phonon), [French model](https://huggingface.co/gradium/phonon-40m-fr), [voice catalog](https://huggingface.co/gradium/phonon-voices), [CLI reference](https://github.com/gradium-ai/xn-ptts/blob/main/docs/cli.md).
