# Phase 04a - Prompt Template Design

## Goal

Define the default prompt templates that are copied into each project `prompt/` folder. Users can edit these Markdown files later, but the app should ship with a coherent baseline aligned with the pipeline.

## Global Rules

Every prompt should:

- Ask for JSON only.
- Refer to IDs exactly as provided.
- Never invent glossary_ID, item_ID, segment_ID, speaker, or listener IDs.
- Use `null` when information is unclear.
- Preserve source text meaning; do not summarize unless the task asks for segmentation.
- Keep output minimal and schema-shaped.

## `json_policy.md`

```md
You must return valid JSON only.

Rules:
- Do not wrap the answer in Markdown.
- Do not add explanations, comments, or prose outside JSON.
- Use the exact IDs supplied in the input.
- If a required value is unknown, use null.
- Do not invent IDs.
- Do not include fields that are not in the requested schema unless the schema explicitly allows them.
- If the task asks for an array, return an array even when there is only one item.
```

## `segment_source.md`

Used by the Tkinter source preparer sub-app with the big LLM.

```md
# Task
Split the chapter into coherent novel translation segments.

# Segmentation Criteria
A segment should end at one of these natural boundaries:
- End of an event, scene beat, timeskip, or point that does not affect the next event.
- POV change.
- End of a large dialogue exchange without cutting through the dialogue.

# Hard Rules
- Do not rewrite the source.
- Do not omit content.
- Do not split inside a sentence.
- Avoid splitting in the middle of a dialogue exchange.
- Preserve paragraph order.

# Output Schema
[
  {
    "chapter": "[CHAPTER]",
    "name": "[CHAPTER_NAME]",
    "segment": "001",
    "content": "segment source text"
  }
]

# Source
[SOURCE_TEXT]
```

## `extract_glossary.md`

Used with small LLM over sub-items.

```md
# Task
Extract glossary candidates from the sub-item.

# Include
- Character names and aliases.
- Titles, epithets, sects, locations, organizations.
- Weapons, artifacts, magic, skills, techniques, named attacks.
- Important concepts that should be translated consistently.

# Exclude
- Generic common words.
- Full sentences.
- One-off descriptive phrases unless they are clearly named concepts.

[JSON_OUTPUT_POLICY]

# Allowed Types
character, alias, title, epithet, location, organization, weapon, artifact, magic, skill, technique, named_attack, concept, other

# Output Schema
[
  {
    "draft_glossary_ID": null,
    "sub_item_ID": "[SUB_ITEM_ID]",
    "source": "source term",
    "type": "character"
  }
]

# Sub-item
[SUB_ITEM]
```

## `extract_relationship.md`

Used with big LLM per segment.

```md
# Task
Extract directed relationship and pronoun information between character glossary entries in this segment.

# Character Identity Rule
Only use characters from [GLOSSARY_SEGMENT_CHARACTERS].
Use glossary_ID values exactly as provided.
Do not create new characters.
If a person is mentioned but not in the character glossary list, ignore them or use null where the schema allows it.

# Relationship Time
The time value is the current segment timestamp. It represents the point where this relationship state first appears.

# What To Extract
- speaker: the character who uses the pronoun or holds the directed relationship.
- listener: the target character.
- type: ally, enemy, neutral, unknown, love, family.
- relationship: short natural-language label, such as "teacher", "student", "enemy", "older sister".
- pronoun: how speaker refers to self or addresses listener in this context.
- alias_pronoun: alternative pronouns/forms if explicitly present.

[JSON_OUTPUT_POLICY]

# Output Schema
[
  {
    "relationship_ID": null,
    "speaker": "glossary_ID",
    "listener": "glossary_ID",
    "type": "ally",
    "relationship": "short relationship label",
    "pronoun": "pronoun or address term",
    "alias_pronoun": [],
    "time": "[TIME_KEY]",
    "source_segment_ID": "[SEGMENT_ID]"
  }
]

# Character Glossary
[GLOSSARY_SEGMENT_CHARACTERS]

# Segment
[SEGMENT_TEXT]
```

## `label_dialogue.md`

Used with big LLM per segment. This prompt must not require existing relationship data.

```md
# Task
Label each dialogue item with speaker and listener.

# Character Identity Rule
Only use characters from [GLOSSARY_SEGMENT_CHARACTERS].
Use glossary_ID values exactly as provided.
Do not invent IDs.
Use null when speaker or listener is unclear.

# Output Rules
- Return labels for dialogue items only.
- Do not return full dialogue text.
- Do not infer relationship type here.

[JSON_OUTPUT_POLICY]

# Output Schema
[
  {
    "item_ID": "dialogue item ID",
    "speaker": "glossary_ID or null",
    "listener": "glossary_ID or null",
    "human_review": false
  }
]

# Character Glossary
[GLOSSARY_SEGMENT_CHARACTERS]

# Segment Items
[SEGMENT_ITEMS]
```

## `translate.md`

Used with big LLM per item.

```md
# Task
Translate the item into the target language.

# Translation Goals
- Preserve meaning, tone, and narrative flow.
- Use glossary translations exactly when provided.
- Respect dialogue labels and pronoun context.
- Do not add explanations.
- Do not omit content.

# Dialogue Context
If this is a dialogue item, speaker/listener and pronoun context are required inputs. If pronoun context is null, translate naturally but do not invent relationship facts.

[JSON_OUTPUT_POLICY]

# Output Schema
{
  "item_ID": "[ITEM_ID]",
  "trans_text": "translated text"
}

# Item Type
[ITEM_TYPE]

# Dialogue Label
[DIALOGUE_LABEL]

# Pronoun Context
[PRONOUN_CONTEXT]

# Glossary For Item
[GLOSSARY_FOR_ITEM]

# Source Item
[ITEM_TEXT]
```

## Acceptance Criteria

- All six prompt templates exist in default app assets.
- Creating a project copies these templates to project `prompt/`.
- Prompt Studio can render every placeholder used above.
- Translation prompt uses canonical `item_ID`; app may still normalize legacy `item_id` on paste.

