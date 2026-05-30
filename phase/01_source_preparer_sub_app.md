# Phase 01 - Source Preparer Sub-App

## Goal

Tạo sub-app chạy riêng bằng Tkinter để chuẩn hóa source novel thành `volume.XX.json` và `volume.XX.segment.json` trước khi import vào app chính.

Sub-app này đơn giản hơn app chính, nhưng cực kỳ quan trọng vì segment sai sẽ kéo theo relationship/dialogue extraction sai.

## Input Modes

Before export, user must choose `volume_number` (for example `1`). Sub-app uses that value for filenames and canonical `segment_ID`.

1. Manual paste:
   - User paste raw chapter text vào textbox.
   - User nhập chapter name/number nếu cần.

2. TXT import:

```text
***Chapter_00***
Đây là tên chapter
**
Nội dung Chapter_00
***Chapter_01***
...
```

Parser rule:

- `***Chapter_XX***` bắt đầu chapter.
- Dòng ngay sau là chapter name.
- Dòng `**` phân cách name và content.
- Content kéo dài tới marker chapter tiếp theo.

## Output Formats

`volume.XX.json`:

```json
[
  {
    "chapter": "001",
    "name": "Chapter title",
    "content": "Full chapter content"
  }
]
```

`volume.XX.segment.json`:

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

## Segmentation Rules

Segment phải dùng big LLM khi auto-split.

Một segment hợp lệ nên kết thúc tại ít nhất một điều kiện:

- Kết thúc một event, timeskip, hoặc điểm không ảnh hưởng event khác.
- Thay đổi POV.
- Kết thúc một đoạn hội thoại lớn, không ngắt giữa thoại.

User có thể tự split, merge, reorder segment. Khi manual edit, sub-app phải hiển thị warning:

```text
Segment boundaries affect relationship extraction, dialogue labels, pronouns, and translation context.
Avoid cutting in the middle of a dialogue or event.
```

## UI Draft

Window layout:

- Top toolbar:
  - Volume Number input
  - Open TXT
  - Paste Mode
  - Load Config
  - Save Volume
  - Save Segments
- Left panel:
  - Chapter list
- Center panel:
  - Source chapter text
- Right panel:
  - Segment list
  - Segment editor
- Bottom bar:
  - Auto Segment with Big LLM
  - Split Here
  - Merge Selected
  - Validate
  - Export

UI language: English.

## LLM Integration

Sub-app config fallback order:

1. Read app-level `~/.novel-studio/settings.json` if it exists and use the `big_llm` section.
2. If not found, let user load a local config JSON from the sub-app UI.
3. If neither exists, let user enter base URL/API key/model manually in the UI.
4. Never require a project folder just to run the sub-app.

OpenAI-compatible config shape:

```json
{
  "base_url": "https://api.openai.com/v1",
  "api_key": "",
  "model": "",
  "batch_count": 1
}
```

Auto segmentation prompt nên đọc từ `prompt/segment_source.md` nếu có, hoặc có default built-in.

## Validation

- Chapter number không trùng.
- Volume number được nhập và khớp filename export.
- Chapter content không rỗng.
- Segment content không rỗng.
- Mỗi segment có `segment_ID` dạng `vXX_chYYY_sZZZ`.
- Segment order đúng trong chapter.
- Tổng content segment nên gần khớp content chapter. MVP có thể normalize whitespace rồi so sánh.

## Acceptance Criteria

- Import được TXT đúng format.
- Export được `volume.XX.json`.
- Auto hoặc manual tạo được `volume.XX.segment.json`.
- Validate báo lỗi rõ khi thiếu chapter, thiếu content, duplicate segment_ID.
- Segment_ID deterministic theo volume/chapter/segment.
- Export filename và `segment_ID` dùng cùng volume number.

## Notes for Implementer

- Không cần canvas trong sub-app.
- Không cần database editor.
- Không cần polish giao diện nặng.
- Ưu tiên ổn định parser và output schema.
