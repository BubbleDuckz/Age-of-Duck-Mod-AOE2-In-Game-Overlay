BUILD ORDERS — Age of Duck v1.19

Getting started
1. Settings > enable Interactive Build Orders.
2. Select build order > choose an order. Select the order again to start tracking at the current villager count.
3. Open build orders folder to add downloaded .json files. Reopen Select build order to refresh the list.
4. The folder is per-user, under the AgeOfDuck application-data folder, not Program Files. Open it from Settings instead of searching for it.
5. The TC/housing Mute control also mutes build-order speech and switches to visual-only instructions (whole-number steps remain for 3 seconds; decimal steps for 10 seconds). The left panel shows the previous three instructions struck through, the current instruction in bold, and the next three in normal text. While speaking, instructions also appear in large text in the upper quarter of the game, staying visible for three seconds after speech ends (a new spoken instruction replaces the previous one). Both overlays stay click-through (except the left panel drag bar). The guide has no background or buttons; text shadows keep it readable. Drag its top bar; both displays scale with Age of Duck. Select an order or open its folder by right-clicking the tray icon.

Create a .json file in that folder using a text editor. Use plain UTF-8 JSON, double quotes, and no comments or trailing commas:

{
  "version": 1,
  "name": "My opening",
  "description": "Optional notes",
  "steps": [
    {"step": "3", "unit": "Villager", "task": "Food"},
    {"step": "4", "unit": "Villager", "task": "Wood"},
    {"step": "19", "unit": "FeudalAge", "task": "ClickUp"},
    {"step": "19.1", "unit": "Custom", "text": "Move four villagers to wood."},
    {"step": "19.2", "unit": "Custom", "text": "Build a barracks when you have 175 wood."},
    {"step": "20", "unit": "Loom"},
    {"step": "21", "unit": "Villager", "task": "Build", "building": "Archery Range"}
  ]
}

Fields
- version: use 1 (schema version, not app version).
- name: title shown in the selector (1–100 characters).
- steps: 1–500 step objects.
- step: a STRING, such as "19", "19.1", "19.2". Whole numbers 1–250 refer to VILLAGERS, not total population. Decimal suffixes are ordered numerically: 19.2 precedes 19.10. Each decimal step must have its whole-number parent in the file. Duplicate IDs are rejected.
- unit: Villager, FeudalAge, CastleAge, ImperialAge, Loom, or Custom.
- task: a spoken role, e.g. Food, Wood, Gold, Stone; use Build plus building for construction.
- text: required for Custom; arbitrary instruction up to 500 characters.
- say: optional override of the displayed/spoken instruction, up to 500 characters.

Progression
- On first reliable count, the app starts at that exact villager number. If enabled at 3, it skips steps 1 and 2; if started mid-game, it does not read the entire opening.
- New villagers release whole-number steps and their decimal follow-ups. Each decimal instruction is spoken once and displayed for at least 10 seconds (longer if its speech needs it), then the next cue starts; they do not wait for another villager. New count steps queue behind any speech already in progress.
- Missing numbers are allowed (the supplied example intentionally has no step 9). No instruction is spoken for an omitted number.
- Villager losses do not rewind or repeat instructions. A new game automatically resets progression while keeping your selected order. The shared TC detector confirms a restarted match clock (including quick opening restarts), or a changed game process. Pauses, alt-tabs and villager losses do not reset it; Selecting the order again resets it to the current count.
- Pause, alt-tab and stale captures pause speech. A temporarily unreadable villager count stops new steps being added but does not interrupt an already queued instruction. An interrupted instruction restarts when valid gameplay resumes.
- Spoken instructions use the installed Windows System.Speech voice. Voice files are generated locally, cached under .voice-cache, and do not require an online TTS account. If speech preparation fails, use Mute for visual-only operation.
- Build-order speech takes priority over TC/housing speech throughout the queued instruction sequence; TC/housing visual reminders remain available.

Limits
The app watches screen pixels. It cannot verify that a villager was assigned correctly, check resources for a custom instruction, perform actions, or know that an age-up was actually clicked. "When 175 wood" is an instruction to you, not a resource-triggered condition. Capture adapts to resolution and aspect ratio by normalizing HUD height and anchoring regions to screen edges. Real 2560x1440 and 3008x1692 screenshots have been validated. Different UI scaling or HUD mods can still suppress recognition safely. Do not treat this as an exact production-event counter: deaths or simultaneous creation/loss can mask increases.

Downloaded JSON is treated as data, never executed. Do not put scripts or commands in it. Files above 1 MB or invalid step formats are rejected. The example is a format demonstration, not a validated competitive strategy.
