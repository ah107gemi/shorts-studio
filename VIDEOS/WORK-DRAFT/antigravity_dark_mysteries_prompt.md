# Antigravity Task: End-to-End Video Production (Dark Mysteries)

Paste the following prompt directly into your Antigravity agent chat window:

```text
Please build and render a complete vertical video project end-to-end in Shorts Studio without requiring manual UI steps.

Project Configuration:
- Title: "3 Forbidden Places on Earth"
- Topic: Dark Mysteries / Unexplained Forbidden Locations
- Target Format: Vertical Short (9:16, 1080x1920)

Scenes & Script to insert:
- Scene 1 (Hook, 4s):
  - Narration: "If you ever set foot on this island, you will never make it back alive."
  - Visual Query/Description: "dark moody stormy island surrounded by crashing ocean waves aerial shot"
- Scene 2 (Point 1, 6s):
  - Narration: "First is North Sentinel Island, home to an isolated tribe that fiercely attacks anyone who approaches."
  - Visual Query/Description: "dense tropical jungle shoreline ocean waves misty remote island"
- Scene 3 (Point 2, 6s):
  - Narration: "Next is Snake Island in Brazil, home to thousands of golden lancehead vipers whose venom melts human flesh."
  - Visual Query/Description: "misty dark rainforest jungle trees cinematic moody atmosphere"
- Scene 4 (Point 3, 6s):
  - Narration: "And the Svalbard Global Seed Vault, built deep into Arctic permafrost to preserve crops after an apocalypse."
  - Visual Query/Description: "arctic bunker entrance snow mountains freezing blizzard northern lights"
- Scene 5 (Outro/CTA, 4s):
  - Narration: "Which place would you dare visit? Hit subscribe for more forbidden secrets."
  - Visual Query/Description: "mysterious fog over dark horizon dramatic cinematic lighting"

Execution Steps:
1. Create a new project entry or project JSON in `data/projects/` titled "3 Forbidden Places on Earth" with the 5 scenes specified above.
2. Trigger the TTS / voiceover pipeline for all 5 narration lines to generate audio files (`.wav` or `.mp3`).
3. Fetch or match corresponding vertical video background assets (via project asset library, Pexels/stock API integration, or procedural fallback if offline) and map each asset path directly to its respective scene.
4. Generate the synchronized word-level captions/subtitles for the project.
5. Trigger the final FFmpeg render pipeline to produce the completed vertical MP4 master video.
6. Return the direct path to the finished master MP4 file and confirm it is ready for preview.
```

---

### What this accomplishes:
- Hands the entire script, visual queries, and scene timings directly to Antigravity.
- Automates project JSON creation, audio generation, visual asset matching, subtitles, and FFmpeg assembly in one prompt.
