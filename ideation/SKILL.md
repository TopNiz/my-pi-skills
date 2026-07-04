---
name: ideation
description: Record, detail, and track your ideas using Apple Notes.app. Quick-log an idea as a note, create dedicated idea notes with details, and add more notes later. All syncs across iPhone, iPad, and Mac via iCloud automatically.
allowed-tools: read write edit bash
compatibility: opencode
---

# 💡 Ideation Skill (Apple Notes)

A personal idea tracker for pi that uses **Apple Notes.app** as its backend. Every idea becomes a note in the `Ideas` folder, synced to all your devices via iCloud — accessible from your iPhone, iPad, and Mac.

> ## ✅ Why Apple Notes?
>
> - **iCloud sync** — ideas appear on all your devices instantly
> - **Rich text** — bold, lists, images, links, checklists
> - **Searchable** — native Notes search across all your devices
> - **No extra setup** — you already use Notes.app

---

## 🚀 Quick Start

No setup needed. The skill creates an `Ideas` folder in Notes.app on first use.

### Preflight: confirm GUI session access

Before using AppleScript against Notes, check you're in a GUI session (especially important over SSH):

```bash
osascript -e 'tell application "Finder" to name of desktop' >/dev/null 2>&1 && echo "GUI_SESSION_OK" || echo "GUI_UNAVAILABLE"
```

If the result is not `GUI_SESSION_OK`, explain the limitation and ask the user to run the command from a local macOS terminal.

### Verify Notes.app access

```bash
osascript -e 'tell application "Notes" to get name of every folder'
```

If this returns a list of folders (including `Ideas` or not), everything works.

---

## 📋 Commands Reference

### 1. Quick-log an idea

Creates a new note in the `Ideas` folder with a title and a short description.

> **User says:** *"Record this idea: a mobile app that scans plants and tells you when to water them"*
>
> **Action:** Create a new note named `🌱 Plant Scanner App` in the `Ideas` folder.

```applescript
tell application "Notes"
    -- Ensure Ideas folder exists
    if not (exists folder "Ideas") then
        make new folder with properties {name:"Ideas"}
    end if
    
    -- Create the new idea note
    make new note at folder "Ideas" with properties {name:"🌱 Plant Scanner App", body:"<div>🌱 <b>Plant Scanner App</b></div><div><br></div><div>A mobile app that scans plants and tells you when to water them.</div><div><br></div><div><i>Recorded: YYYY-MM-DD HH:MM</i></div>"}
end tell
```

**Naming convention:**
- Use an emoji prefix for visual scanning in Notes (🌱 💡 🚀 📱 🎨 etc.)
- Title case, descriptive but concise
- Example: `🌱 Plant Scanner App`, `💡 AI Recipe Generator`, `🚀 SaaS for Freelancers`

---

### 2. Create a detailed idea note

When the user gives details, create a well-structured note with sections.

> **User says:** *"I want to give details on the plant scanner app — it should use the camera to identify plants, then give watering schedules based on plant type and season"*
>
> **Action:** Create or update a note with structured sections.

```applescript
tell application "Notes"
    if not (exists folder "Ideas") then
        make new folder with properties {name:"Ideas"}
    end if
    
    make new note at folder "Ideas" with properties {name:"🌱 Plant Scanner App", body:"
        <div>🌱 <b>Plant Scanner App</b></div>
        <div><br></div>
        <div><b>🎯 Concept</b></div>
        <div>A mobile app that uses the phone's camera to identify plants, then provides customized watering schedules based on plant type and current season.</div>
        <div><br></div>
        <div><b>🔑 Key Features</b></div>
        <ul>
            <li>Camera-based plant identification</li>
            <li>Personalized watering calendar</li>
            <li>Seasonal adjustments</li>
            <li>Push notifications for watering reminders</li>
        </ul>
        <div><br></div>
        <div><i>Created: YYYY-MM-DD HH:MM</i></div>
    "}
end tell
```

**Structure template for an idea note:**
```html
<div>🎯 <b>Concept</b></div>
<div>One-liner description</div>
<div><br></div>

<div><b>🔑 Key Features</b></div>
<ul>
    <li>Feature 1</li>
    <li>Feature 2</li>
</ul>
<div><br></div>

<div><b>📝 Notes</b></div>
<div>Timestamped updates...</div>
```

---

### 3. Add more notes to an existing idea

Append content to an existing idea note by finding it and updating its body.

> **User says:** *"Add a note to the plant scanner idea: we could also use the phone's flash as a grow light for dark environments"*
>
> **Action:** Find the note by name, append the new content.

```applescript
tell application "Notes"
    set ideaNote to first note of folder "Ideas" whose name contains "Plant Scanner"
    set currentBody to body of ideaNote
    set newBody to currentBody & "
        <div><br></div>
        <div>---</div>
        <div><b>📝 Note — YYYY-MM-DD HH:MM</b></div>
        <div>We could also use the phone's flash as a grow light for dark environments.</div>
    "
    set body of ideaNote to newBody
end tell
```

---

### 4. List all ideas

List all notes in the `Ideas` folder.

> **User says:** *"Show me my ideas"* or *"List my ideas"*
>
> **Action:** List all notes in the `Ideas` folder.

```applescript
tell application "Notes"
    set ideaNotes to notes of folder "Ideas"
    set output to ""
    repeat with n in ideaNotes
        set output to output & "• " & name of n & return
    end repeat
    return output
end tell
```

---

### 5. View details of a specific idea

Read the full body of an idea note.

> **User says:** *"Show me details of the plant scanner idea"*
>
> **Action:** Find the note, return its body.

```applescript
tell application "Notes"
    set ideaNote to first note of folder "Ideas" whose name contains "Plant Scanner"
    set noteBody to body of ideaNote
    return "📄 " & name of ideaNote & return & "---" & return & noteBody
end tell
```

---

### 6. Search ideas

Search across all idea notes for a keyword.

> **User says:** *"Find ideas about plants"*
>
> **Action:** Search all notes in the Ideas folder whose name or body contains the keyword.

```applescript
tell application "Notes"
    set matches to every note of folder "Ideas" whose name contains "plant"
    -- Also search body by iterating and checking with text
    set allNotes to notes of folder "Ideas"
    repeat with n in allNotes
        if body of n contains "plant" then
            -- matched
        end if
    end repeat
end tell
```

---

## 🧠 Tips for the Agent

### Finding the right note (fuzzy matching)

When the user refers to an existing idea, search by partial name match:

```applescript
-- Try exact first, then fall back to contains
set ideaNote to first note of folder "Ideas" whose name contains "<keyword>"
```

If multiple notes match, list them and ask the user to clarify.

### Emoji prefix convention

Use emoji prefixes for visual scanning. Common ones:

| Emoji | When to use |
|---|---|
| 🌱 | New/growing idea (default) |
| 💡 | A clever insight or solution |
| 🚀 | A scalable / startup-worthy idea |
| 📱 | App or mobile idea |
| 🎨 | Design, creative, or UI idea |
| 🛠️ | Tool, utility, or automation idea |
| 🤖 | AI / ML related idea |
| 📊 | Data or analytics idea |

### First-time setup

On first use, ensure the `Ideas` folder exists:

```bash
osascript -e '
tell application "Notes"
    if not (exists folder "Ideas") then
        make new folder with properties {name:"Ideas"}
        return "Created Ideas folder"
    else
        return "Ideas folder already exists"
    end if
end tell
'
```

### Body format (HTML)

Apple Notes uses HTML for note bodies. Keep it simple:

- `<div>` for paragraphs and line breaks
- `<b>` for **bold** (headings)
- `<ul><li>` for lists
- `<br>` for spacing
- `<hr>` or `---` for section separators (Note: `<hr>` may not render — use `<div>---</div>` instead)

---

## 🧹 Maintenance

### Archive old ideas

Move old idea notes to an `Archive` folder (create it if needed):

```applescript
tell application "Notes"
    if not (exists folder "Archive") then
        make new folder with properties {name:"Archive"}
    end if
    move note "<name>" to folder "Archive"
end tell
```

Only do this if the user explicitly asks.

### Delete an idea

```applescript
tell application "Notes"
    delete (first note of folder "Ideas" whose name contains "<keyword>")
end tell
```

⚠️ Always confirm with the user before deleting.

---

## 📱 Cross-Device Usage

Because Apple Notes syncs via iCloud:

- **iPhone/iPad** → Open Notes.app → `Ideas` folder → all notes are there
- **Mac** → Same as above
- **iCloud.com** → Access from any browser
- **Spotlight** → Search your idea by name from anywhere

No extra steps needed — the skill creates notes directly in Notes.app, and iCloud handles the rest.

---

## 🔒 Privacy

All ideas live in your Apple Notes account, synced through your personal iCloud. Nothing is stored in Git, written to disk by this skill, or shared anywhere. The skill only communicates with Notes.app on your local machine via AppleScript.
