# Project Goal: Novel Translation Studio

Novel Translation Studio là một ứng dụng offline, một người dùng, dùng để hỗ trợ dịch tiểu thuyết dài kỳ theo hướng bán tự động, có kiểm soát chặt chẽ glossary, quan hệ nhân vật, đại từ xưng hô, dialogue label và bản dịch theo từng đơn vị văn bản nhỏ.

## Core Goal

Mục tiêu cốt lõi của dự án là tạo ra một workflow dịch tiểu thuyết đáng tin cậy hơn cách đưa nguyên chương cho LLM dịch. Ứng dụng phải chia văn bản thành skeleton, item và sub-item có ID ổn định; trích xuất và review glossary; theo dõi quan hệ nhân vật theo timeline; gắn speaker/listener cho thoại; rồi dịch từng item bằng prompt có đủ ngữ cảnh cần thiết.

## User Goal

Người dùng có thể:

- Chuẩn hóa source novel thành volume và segment rõ ràng.
- Kiểm soát glossary thay vì để AI tự dịch tên riêng/thuật ngữ tùy tiện.
- Theo dõi relationship và pronoun thay đổi theo thời gian trong truyện.
- Dùng manual copy/paste với chat LLM hoặc gọi API tự động.
- Review, sửa, polish và export bản dịch cuối cùng.

## Product Goal

Ứng dụng phải hoạt động như một studio dịch offline:

- File-based, dễ backup và share nguyên project folder.
- Không cần realtime collaboration.
- Dùng Python/FastAPI cho backend.
- Dùng React + React Flow cho frontend và relationship canvas.
- Dùng OpenAI-compatible providers cho cả small LLM và big LLM.
- Lưu prompt trong `prompt/*.md` để người dùng tự sửa.

## MVP Success Criteria

MVP được xem là đạt mục tiêu khi người dùng có thể:

1. Tạo project.
2. Import source volume và segment file.
3. Build skeleton, item và sub-item.
4. Extract, review, merge và link glossary.
5. Extract relationship/pronoun và xem trên canvas timeline.
6. Label dialogue bằng speaker/listener.
7. Translate item theo batch bằng API hoặc manual Prompt Studio.
8. Polish bản dịch theo từng item.
9. Export TXT/Markdown từ bản dịch đã polish.

## Non-Goal

Dự án này không nhằm tạo một công cụ dịch tự động hoàn toàn không cần người review. Con người vẫn là người kiểm soát glossary, relationship, prompt, bản dịch và kết quả cuối cùng.

For implementation details, see `master_plan.md`. For AI coding rules, see `Agent.md`.
