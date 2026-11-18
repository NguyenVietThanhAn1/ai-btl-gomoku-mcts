@AGENTS.md

# Riêng cho Claude Code

Mọi luật dự án nằm ở `AGENTS.md` (import ở trên) — không ghi luật ở đây (D-31). File này chỉ mô tả tiện ích Claude Code bọc quanh các quy trình chung:

- `/next-task [ID]` = làm theo `docs/WORKFLOW.md` §1 (Làm task).
- `/wrap-up` = làm theo `docs/WORKFLOW.md` §2 (Kết thúc phiên).
- Bước tự kiểm trong WORKFLOW: gọi subagent `spec-reviewer` với task ID (nó làm theo `docs/REVIEW.md`).
- `.claude/settings.json` ép một phần luật "Lệnh nguy hiểm" của AGENTS.md bằng permission (allow/ask/deny). Settings chỉ là lớp bảo vệ thêm; luật gốc vẫn là AGENTS.md. Rule cá nhân để trong `.claude/settings.local.json` (gitignore).
