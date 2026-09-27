# Eddy Sentence Practice

Independent installable iPhone PWA at `https://eddychang0630.github.io/eddy-flashcards/sentences/`.
The vocabulary PWA stays at the repository root. The sentence app has its own manifest ID, icon, start URL, service-worker scope, IndexedDB progress, and backup format.

## Sources

- `YYYYMMDD/english_class_notes.md`: only the ten numbered, Eddy-attributed Better Expressions from each recorded class.
- `grammar_guides.json`: the agent must add one reusable pattern per new class sentence and a specific explanation when the note lacks a correction point. Missing guides block sync.
- `lesson_topics.json`: short topic labels by lesson date.
- `scenarios.json`: separately curated question/answer practice, not tutor quotations.
- `data.json` and `audio/*.mp3`: generated output. Corrected class sentences and both scenario lines use locally rendered Kokoro `am_puck` speech. Original incorrect class wording is never synthesized.

## Daily sync

After the final class notes pass `tools/note_structure.py`, add the new date's ten grammar guides and topic, then run from this repository root:

```powershell
python .\sentences\sync_sentences.py --notes-root "C:\Users\User\Desktop\English class 整理重點"
```

The script validates all class sources, generates missing audio locally, verifies every MP3, writes deterministic card IDs, and commits/pushes only sentence data, audio, and their source guides/topics/scenarios. If any validation or audio step fails, do not claim the sentence app was updated. `KOKORO_PYTHON` can override the local model runtime. Use `--local-only` for a dry run without Git publication.

The iPhone install step is Safari > Share > Add to Home Screen on the sentence URL. Add the root vocabulary URL separately to get two icons. Review progress is local to each device; use Export/Import in the app to move or restore it.

For frontend changes, install dependencies with `pnpm install`, then `pnpm run build` and commit the built `app.js`. The daily data-only sync does not require Node.
