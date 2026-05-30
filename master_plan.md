# Novel Translation Studio - Master Plan

Tài liệu này là kế hoạch tổng cho dự án Novel Translation Studio, viết dựa trên `Novel Studio Blueprint.txt` và các yêu cầu bổ sung ngày 2026-05-30. Scope của tài liệu là lên kế hoạch triển khai, không code app.

## 1. North Star

Novel Translation Studio là ứng dụng offline, một người dùng, dùng để dịch tiểu thuyết dài kỳ theo hướng bán tự động. Mục tiêu không phải là "ném cả chương cho AI dịch", mà là băm văn bản thành các đơn vị đủ nhỏ, kiểm soát glossary, quan hệ nhân vật, đại từ xưng hô, rồi dịch từng item bằng prompt có ngữ cảnh chính xác.

Ứng dụng phải giúp người dùng:

- Chuẩn hóa source và segment trước khi xử lý.
- Tách văn bản thành skeleton, item, sub-item có ID ổn định.
- Extract glossary bằng small LLM.
- Human-review glossary, merge alias, link các glossary cùng khái niệm.
- Extract relationship, pronoun và label dialogue bằng big LLM.
- Dựng relationship canvas dạng node graph có timeline.
- Dịch item theo batch bằng OpenAI-compatible API hoặc thao tác copy/paste thủ công.
- Polish bản dịch theo từng item và export ra file đọc được.

## 2. Scope

### In scope cho MVP

- App chính: Python backend + FastAPI API + React frontend.
- Canvas: React Flow.
- Source preparer sub-app: Python Tkinter, chạy riêng, giao diện đơn giản.
- File-based project database bằng JSON/Markdown files, không cần DB server.
- Offline-first, single-user. Có thể share nguyên folder project, nhưng không hỗ trợ nhiều người sửa cùng lúc.
- UI ban đầu bằng tiếng Anh.
- Dark mode là theme chủ đạo.
- LLM provider theo chuẩn OpenAI-compatible.
- Tách small LLM và big LLM ngay từ đầu:
  - Small LLM: glossary extraction, ưu tiên local LM Studio hoặc server tương thích OpenAI.
  - Big LLM: source segmentation, relationship extraction, dialogue label, translation, ưu tiên GPT hoặc provider tương thích OpenAI.
- Prompt files lưu cục bộ ở `prompt/*.md`, người dùng edit được.
- Prompt Studio hỗ trợ 2 mode:
  - Manual mode: app tạo prompt, người dùng copy sang chat, paste kết quả về, validate rồi save.
  - API mode: app tự gọi provider, điền kết quả vào khung result, người dùng save.
- Config batch chỉ cần cho người dùng nhập số lượng batch/concurrency mong muốn.

### Out of scope cho MVP

- Realtime collaboration.
- Cloud account, sync server, permission system.
- Mobile app.
- Full bilingual UI.
- Advanced QA/Fix pipeline sau dịch.
- Complex version control giống Git.
- Multi-provider abstraction quá cầu kỳ. Chỉ cần OpenAI-compatible là đủ.

## 3. Product Shape

App chính nên có left navigation cố định và các scene sau:

1. Project Manager
   - Tạo project.
   - Chọn genre.
   - Nhập metadata cơ bản.
   - Mở project folder có sẵn.

2. Import Source
   - Import `volume.XX.json`.
   - Import `volume.XX.segment.json`.
   - Validate schema, chapter order, segment order, empty content, duplicate ID.

3. Workflow Dashboard
   - Hiển thị pipeline theo volume.
   - Mỗi bước có status: not_started, ready, running, needs_review, completed, failed.
   - Cho phép chạy lại từng bước.

4. Prompt Studio
   - Split screen.
   - Left: chọn task, chọn input scope, tạo prompt.
   - Right: result editor để paste hoặc nhận API output.
   - Nút `Generate Prompt`, `Copy`, `Run via API`, `Validate`, `Save`.

5. Database Editor
   - Edit glossary, draft glossary, item glossary, segment glossary, relationships, dialogue labels, translations.
   - Có filter, search, validation.

6. Relationship Canvas
   - React Flow canvas.
   - Node là character lấy từ glossary type `character`.
   - Edge lấy từ relationship/pronoun.
   - Timeline slider bên dưới.
   - Kéo timeline tới chapter/segment nào thì render state relationship tại thời điểm đó.

7. Polish Center
   - Regenerate văn bản từ skeleton + translations.
   - Edit inline từng item.
   - Preview theo chapter/volume.

8. Export
   - Export TXT, Markdown, HTML.
   - EPUB có thể là MVP-late hoặc phase sau nếu muốn giảm rủi ro.

9. Config
   - Small LLM provider.
   - Big LLM provider.
   - API key/base URL/model.
   - Batch count.
   - Max token per sub-item.
   - Prompt folder path nếu cần.

## 4. Recommended Stack

Backend:

- Python 3.12+
- FastAPI
- Pydantic v2
- Uvicorn
- httpx hoặc OpenAI Python SDK cho OpenAI-compatible calls
- orjson/ujson optional, không bắt buộc
- pathlib + atomic file write

Frontend:

- React + Vite + TypeScript
- React Flow cho canvas
- TanStack Query cho API state
- Zustand hoặc Redux Toolkit nhẹ cho local UI state
- Vanilla CSS + CSS Variables cho MVP. Lý do: ít magic, dễ debug, dark mode chủ đạo rõ ràng, AI coder ít bị lệch style. Tailwind/shadcn có thể cân nhắc sau khi app đã ổn workflow.

Sub-app:

- Python Tkinter
- Dùng chung core parser/schema với backend nếu repo tổ chức được
- Gọi big LLM qua cùng provider config hoặc file config riêng đơn giản

Storage:

- File-based JSON/Markdown.
- Không dùng database server.
- Mọi write quan trọng nên atomic: ghi vào temp file, validate, rename.
- Nên có backup snapshot tự động trước mỗi pipeline run hoặc table-level save quan trọng, không tạo backup cho từng row write trong batch lớn.

## 5. Settings and Project Folder Layout

App nên có app-level settings ngoài project để user không phải nhập lại provider mỗi lần tạo project mới:

```text
~/.novel-studio/
  settings.json
```

App-level settings chứa API keys, default provider, default batch count, theme default. Project-level `settings.json` chỉ chứa override an toàn để share cùng project, ví dụ max sub-item tokens, target language, prompt behavior, hoặc batch override nếu user muốn.

Một project nên có cấu trúc như sau:

```text
NovelProject/
  project.json
  settings.json
  source/
    volume.01.json
  segment/
    volume.01.segment.json
  prompt/
    segment_source.md
    extract_glossary.md
    extract_relationship.md
    label_dialogue.md
    translate.md
    json_policy.md
  db/
    counters.json
    volume.01/
      draft_glossary.json
      glossary.json
      item_glossary.json
      segment_glossary.json
      relationships.json
      dialogue_labels.json
      translations.json
      polish_overrides.json
    volume.02/
      ...
    series_glossary.json
    series_relationships.json
  work/
    volume.01/
      segment_skeleton.json
      segment_flesh.json
      sub_items.json
      pipeline_state.json
      llm_jobs.json
      llm_results/
  export/
  backups/
  logs/
```

Ghi chú:

- `prompt/*.md` là prompt local, user edit trực tiếp được.
- App có thể ship default prompt templates, nhưng khi tạo project nên copy vào project để mỗi project tự giữ prompt version của nó.
- `work/` chứa artifact có thể rebuild.
- `db/counters.json` giữ file-based ID allocator cho các ID project-wide như `glossary_ID` và `relationship_ID`; mọi increment phải atomic.
- `db/volume.XX/` chứa dữ liệu theo từng volume. Không dùng một file phẳng cho draft glossary/translation nhiều volume vì dễ ghi đè và khó review.
- `db/series_glossary.json` và `db/series_relationships.json` là dữ liệu cross-volume đã được review.
- `backups/` giúp rollback thủ công khi merge sai.

## 6. Canonical Input Format

### Volume source file

File `source/volume.XX.json` nên là array:

```json
[
  {
    "chapter": "001",
    "name": "Chapter title",
    "content": "Full chapter content"
  }
]
```

### Segment file

File `segment/volume.XX.segment.json` nên là array:

```json
[
  {
    "chapter": "001",
    "name": "Chapter title",
    "segment": "001",
    "segment_ID": "v01_ch001_s001",
    "content": "Segment content"
  }
]
```

`segment` là ordinal trong chapter. `segment_ID` là ID canonical để tránh mơ hồ. Sub-app phải biết volume number trước khi export để tạo `vXX_chYYY_sZZZ`; nếu import format cũ hoặc format không có volume prefix, app chính có thể auto-generate/migrate `segment_ID` dựa trên filename `volume.XX.segment.json`.

## 7. ID Convention

ID phải stable, deterministic, dễ truy ngược.

```text
volume_ID       = v01
chapter_ID      = ch001
segment_ID      = v01_ch001_s001
item_ID         = v01_ch001_s001_nar_001
item_ID         = v01_ch001_s001_diag_001
sub_item_ID     = v01_ch001_s001_nar_001_sub_001
glossary_ID     = glo_000001
relationship_ID = rel_000001
translation_ID  = item_ID
```

Blueprint dùng ví dụ `001_01_nar_01`. MVP có thể giữ format đó nếu muốn, nhưng plan khuyến nghị format canonical có volume/chapter/segment rõ ràng để timeline sort dễ hơn và không bị nhầm `007_01` là chapter hay segment.

Project-wide IDs such as `glossary_ID` and `relationship_ID` should be allocated from `db/counters.json` with an atomic read-increment-write operation. If the implementation cannot guarantee a lock, use UUID-style IDs instead of counters.

## 8. Relationship Time Semantics

Đây là quyết định quan trọng nhất cho relationship canvas.

`time` trong relationship không phải duration. Nó là timestamp phát sinh một state mới.

Ví dụ:

- Chapter 1: Đông Sơn và Thúy Thúy là thầy trò.
- Không có timestamp mới cho cặp này tới chapter 100.
- Khi kéo timeline tới chapter 100, canvas vẫn render quan hệ thầy trò vì timestamp chapter 1 là state mới nhất không vượt quá cursor.

Nếu chapter 10 có state mới:

- Chapter 1: thầy trò.
- Chapter 10: kẻ thù.
- Cursor chapter 8: render thầy trò.
- Cursor chapter 15: render kẻ thù.

Canonical representation:

```json
{
  "relationship_ID": "rel_000001",
  "speaker": "glo_000007",
  "listener": "glo_000010",
  "type": "ally",
  "relationship": "teacher/student",
  "pronoun": "lão phu",
  "alias_pronoun": [],
  "time": {
    "volume": 1,
    "chapter": 1,
    "segment": 7,
    "key": "v01_ch001_s007"
  },
  "source_segment_ID": "v01_ch001_s007",
  "human_review": false,
  "conflict": false
}
```

Render rule:

1. Convert timeline cursor to comparable key: volume, chapter, segment.
2. For every directed pair `(speaker, listener)`, lấy relationship record mới nhất có `time <= cursor`.
3. Canvas edge giữa 2 character có thể là undirected summary, nhưng detail panel phải hiển thị cả hai hướng nếu có.
4. Nếu chỉ có một hướng, vẫn dựng edge.

Merge rule:

- Nếu new record giống previous record về `type`, `relationship`, `pronoun`, `alias_pronoun`: duplicate, discard hoặc mark merged vào previous.
- Nếu chỉ một phần giống, ví dụ type giống nhưng pronoun đổi, hoặc pronoun giống nhưng type đổi: mark conflict, cần human review.
- Nếu khác rõ ràng: giữ record mới như state change.
- Null không nên tự động thắng dữ liệu cũ. Null chỉ được coi là unknown, trừ khi user xác nhận overwrite.

Series relationship:

- Relationship là append-only theo timestamp.
- Với volume mới, nếu pair đã có trong series và state không đổi thì inherit.
- Nếu state đổi thì append timestamp mới.

## 9. Glossary Identity Model

Glossary là source of truth cho entity.

Relationship không được tạo character riêng. Relationship chỉ reference glossary entries có `type = "character"`.

Glossary schema nên có:

```json
{
  "glossary_ID": "glo_000001",
  "volume": 1,
  "source": "东山",
  "trans": "Đông Sơn",
  "type": "character",
  "alias": ["东山隐士"],
  "human_review": false,
  "link": ["glo_000004"],
  "item_ID": [],
  "segment_ID": [],
  "time": {
    "volume": 1
  }
}
```

Link semantics:

- `link` đại diện cho quan hệ cùng khái niệm giữa nhiều glossary entries.
- Link không thay thế translation glossary trong prompt dịch. Translate prompt vẫn dùng đúng glossary xuất hiện trong item.
- Link chủ yếu giúp relationship extraction, dialogue label và human editor hiểu rằng nhiều source forms có thể chỉ cùng một character/concept.
- Link chỉ nên áp dụng mạnh cho `character` trong MVP. Các type khác có thể hỗ trợ sau.

Merge semantics:

- Draft glossary được merge tự động chỉ ở mức exact match.
- Partial match không auto-merge trong MVP.
- Exact match gom alias và gắn `human_review`.
- User review xong mới commit vào `glossary.json`.
- Volume 2 trở đi inherit từ `series_glossary.json`; bản sửa mới sau review có quyền mạnh hơn bản cũ.

## 10. Text Processing Pipeline

### Step 0: Prepare Source bằng sub-app

Input:

- Người dùng paste text thủ công.
- Hoặc import TXT theo format:

```text
***Chapter_00***
Đây là tên chapter
**
Nội dung Chapter_00
***Chapter_01***
...
```

Output:

- `volume.XX.json`
- `volume.XX.segment.json`

Segmentation phải dùng big LLM, vì segment cần phù hợp ít nhất một trong ba điều kiện:

- Kết thúc sự kiện, timeskip, hoặc không ảnh hưởng sự kiện khác.
- Thay đổi POV.
- Kết thúc một đoạn hội thoại lớn, không ngắt thoại.

User có thể tự chia segment, nhưng sub-app phải cảnh báo rõ: chia sai segment sẽ làm relationship/dialogue extraction kém chính xác.

### Step 1: Import Source

- Copy source và segment vào project.
- Validate format.
- Build import manifest.

### Step 2: Skeleton Builder

- Với từng segment, mỗi non-empty paragraph là một item.
- Detect narration/dialogue.
- Gán `item_ID`.
- `segment_skeleton.json`: ordered list item IDs.
- `segment_flesh.json`: item text theo schema.

### Step 3: Sub-item Splitter

- Narration được split theo max token config, lùi về punctuation gần nhất.
- Dialogue không split dù dài.
- Sub-item chỉ dùng cho glossary extraction, không dùng cho relationship/translation.

### Step 4: Draft Glossary Extraction

- Small LLM.
- Input: prompt + JSON policy + sub-item.
- Output: draft glossary entries.
- Store: `db/volume.XX/draft_glossary.json`.

### Step 5A: Glossary Merge + Link

- Exact match merge draft glossary.
- Human review.
- Commit to `db/volume.XX/glossary.json`.

### Step 5B: Item Glossary Scanner

- After glossary commit, scan every item against committed glossary `source` and `alias`.
- Store item-level glossary matches in `db/volume.XX/item_glossary.json`.

### Step 5C: Segment Glossary Scanner

- Union item glossary per segment.
- Deduplicate repeated terms.
- Store segment-level glossary in `db/volume.XX/segment_glossary.json`.

### Step 6: Relationship + Pronoun Extraction

- Big LLM.
- Input: segment text + segment glossary character list + JSON policy.
- Output: directed relationships with pronoun.
- Store: `db/volume.XX/relationships.json`.
- Merge timeline duplicates/conflicts.

### Step 7: Relationship Canvas Review

- Render character graph.
- Timeline slider.
- User edits relationship/pronoun/conflict.

### Step 8: Label Dialogue

- Big LLM.
- Does not require relationship data.
- Input: segment text + segment glossary character list.
- Output: dialogue item speaker/listener.
- Store: `db/volume.XX/dialogue_labels.json`.

### Step 9: Translation

- Big LLM preferred.
- Input per item:
  - Translate prompt.
  - Item text.
  - Dialogue label if item is dialogue.
  - Glossary for item.
  - Pronoun context for speaker/listener. For dialogue items this is required context; value may be null only when no reviewed relationship/pronoun exists yet.
  - JSON output policy.
- Batch count controlled by user.
- Retry failed IDs.
- Store: `db/volume.XX/translations.json`.

### Step 10: Polish + Regenerate

- Rebuild chapter/volume text from skeleton + translations.
- User edits inline by item.
- Store edited text as polished override.

### Step 11: Series Update

- After human review, push reviewed glossary and relationship changes to series files.
- Volume 2+ compares against series before merge/extract where relevant.
- Proper names inherit from series by default.
- New reviewed edits have stronger priority than older series values.

### Step 12: Export

- Export TXT/MD/HTML/EPUB as supported.

## 11. Prompt System

Prompts are local Markdown files. Required MVP files:

```text
prompt/
  json_policy.md
  segment_source.md
  extract_glossary.md
  extract_relationship.md
  label_dialogue.md
  translate.md
```

Prompt template inputs should be explicit:

- `[TASK_PROMPT]`
- `[JSON_OUTPUT_POLICY]`
- `[SOURCE_TEXT]`
- `[SEGMENT_TEXT]`
- `[SUB_ITEM]`
- `[GLOSSARY_SEGMENT_CHARACTERS]`
- `[GLOSSARY_FOR_ITEM]`
- `[PRONOUN_CONTEXT]`
- `[DIALOGUE_LABEL]`
- `[SCHEMA]`

Prompt Studio is the human bridge:

- Left panel:
  - Task selector.
  - Scope selector: project/volume/chapter/segment/item/sub-item.
  - Prompt preview.
  - Copy button.
  - Run via API button.
- Right panel:
  - Result editor.
  - Validate button.
  - Save button.
  - Error list.

Manual and API modes must produce the same saved artifact.

Actual prompt template content is part of the plan, not left implicit. See `phase/04a_prompt_template_design.md` for the required default templates and the expected placeholders for `segment_source.md`, `extract_glossary.md`, `extract_relationship.md`, `label_dialogue.md`, `translate.md`, and `json_policy.md`.

## 12. API Surface Draft

MVP backend endpoints:

```text
GET    /api/health
GET    /api/projects
POST   /api/projects
GET    /api/projects/{project_id}
POST   /api/projects/{project_id}/open

POST   /api/projects/{project_id}/import/source
POST   /api/projects/{project_id}/import/segment
POST   /api/projects/{project_id}/validate

POST   /api/projects/{project_id}/pipeline/{volume}/skeleton
POST   /api/projects/{project_id}/pipeline/{volume}/subitems
POST   /api/projects/{project_id}/pipeline/{volume}/glossary/extract
POST   /api/projects/{project_id}/pipeline/{volume}/glossary/merge
POST   /api/projects/{project_id}/pipeline/{volume}/glossary/scan-items
POST   /api/projects/{project_id}/pipeline/{volume}/glossary/scan-segments
POST   /api/projects/{project_id}/pipeline/{volume}/relationships/extract
POST   /api/projects/{project_id}/pipeline/{volume}/dialogue-labels/extract
POST   /api/projects/{project_id}/pipeline/{volume}/translate
POST   /api/projects/{project_id}/pipeline/{volume}/regenerate
POST   /api/projects/{project_id}/pipeline/{volume}/series/update

GET    /api/projects/{project_id}/db/volumes/{volume}/{table}
PUT    /api/projects/{project_id}/db/volumes/{volume}/{table}
PATCH  /api/projects/{project_id}/db/volumes/{volume}/{table}/{id}
GET    /api/projects/{project_id}/db/series/{table}
PUT    /api/projects/{project_id}/db/series/{table}

GET    /api/projects/{project_id}/prompts
GET    /api/projects/{project_id}/prompts/{name}
PUT    /api/projects/{project_id}/prompts/{name}
POST   /api/projects/{project_id}/prompts/render
POST   /api/projects/{project_id}/prompts/validate-result
POST   /api/projects/{project_id}/prompts/save-result

GET    /api/projects/{project_id}/relationships/canvas?time_key=...&scope=series
GET    /api/projects/{project_id}/relationships/state?time_key=...&scope=series
PATCH  /api/projects/{project_id}/relationships/{id}

POST   /api/projects/{project_id}/export
POST   /api/projects/{project_id}/export/{volume}
```

Export request body should specify scope and format:

```json
{
  "volumes": [1, 2],
  "format": "md",
  "scope": "selected_volumes"
}
```

For a full-series export, use `scope = "series"` and omit `volumes` or pass all imported volumes explicitly.

Relationship canvas/state endpoints should aggregate `db/series_relationships.json` plus all imported `db/volume.XX/relationships.json` up to the requested `time_key` by default. A volume-only debug/filter mode can exist, but series-wide continuity is the default behavior.

API shape có thể đổi khi code, nhưng phải giữ principle: pipeline operation, database editing, prompt studio, canvas state là các boundary rõ.

## 13. Validation Rules

Validation cơ bản:

- JSON parse được.
- Required fields không trống.
- ID unique trong cùng table.
- Relationship speaker/listener tồn tại trong glossary và là character hoặc linked character.
- Dialogue label item_ID tồn tại và là dialogue.
- Translation `item_ID` tồn tại trong segment_flesh. App có thể accept `item_id` từ LLM/manual paste để tương thích prompt cũ, nhưng phải normalize về `item_ID` trước khi save.
- Segment order sortable.
- `time.key` match `source_segment_ID`.
- Manual paste result phải match schema trước khi save.

LLM output:

- Nếu API hỗ trợ structured output thì bật.
- Nếu không, dùng JSON guard nhẹ:
  - Extract JSON block.
  - Validate schema.
  - Nếu fail thì mark job failed và cho retry/manual correction.

## 14. Human Review Checkpoints

Human review là feature cốt lõi, không phải ngoại lệ.

Review points:

- Imported source/segment validation.
- Draft glossary merge candidates.
- Glossary link.
- Relationship conflicts.
- Dialogue labels with missing speaker/listener.
- Translation failed IDs.
- Polish center inline edits.
- Series glossary/relationship update before commit.

## 15. Implementation Phases

Các phase chi tiết nằm trong `phase/*.md`:

1. `phase/00_app_foundation.md`
2. `phase/01_source_preparer_sub_app.md`
3. `phase/02_project_manager_import_source.md`
4. `phase/03_skeleton_subitem_pipeline.md`
5. `phase/04_llm_provider_prompt_studio.md`
6. `phase/04a_prompt_template_design.md`
7. `phase/05_glossary_pipeline.md`
8. `phase/06_relationship_timeline_canvas.md`
9. `phase/07_dialogue_label_pipeline.md`
10. `phase/08_translation_pipeline.md`
11. `phase/08a_series_update.md`
12. `phase/09_polish_export.md`
13. `phase/10_database_editor.md`
14. `phase/11_config_packaging_polish.md`

## 16. Suggested MVP Milestone

MVP đáng gọi là dùng được khi có thể:

1. Tạo project.
2. Import one volume source + segment.
3. Build skeleton/sub-items.
4. Extract glossary bằng small LLM hoặc manual Prompt Studio.
5. Review/merge glossary.
6. Extract relationship + dialogue labels bằng big LLM hoặc manual Prompt Studio.
7. Render relationship canvas có timeline chapter/segment.
8. Translate items theo batch.
9. Rebuild và edit bản dịch.
10. Export TXT/Markdown.

EPUB, HTML đẹp, advanced database tools, theme polish có thể để sau MVP.

## 17. Open Decisions Không Block Phase 0

- Có cần EPUB trong MVP đầu tiên hay để MVP-late.
- Có cần import legacy segment format không có `segment_ID`. Plan khuyến nghị có auto-migration.
- Cách detect dialogue chính xác theo source language. MVP nên rule-based trước, cho user sửa sau.
- Có cần encryption API key local không. MVP có thể lưu app-level config local plaintext và ghi rõ cảnh báo.
