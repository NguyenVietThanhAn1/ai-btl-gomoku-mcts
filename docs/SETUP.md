# SETUP — cài đặt cho thành viên BTL

Luật dự án: [AGENTS.md](../AGENTS.md) (dùng chung cho mọi công cụ). §A bắt buộc cho mọi người; sau đó làm §B **hoặc** §C tùy công cụ.

## A. Chung (mọi công cụ)

1. **Clone** và mở đúng thư mục gốc repo (VS Code → File → Open Folder → thư mục vừa clone):
   ```powershell
   git clone https://github.com/NguyenVietThanhAn1/ai-btl-gomoku-mcts.git
   cd ai-btl-gomoku-mcts
   git switch develop
   git config pull.rebase true
   ```
   `pull.rebase true` cho người gõ tay `git pull`; agent đồng bộ bằng `git fetch origin` + `git rebase origin/develop` (AGENTS.md).
   Agent đọc `AGENTS.md` / `CLAUDE.md` từ thư mục gốc workspace — mở thư mục cha thì luật không được nạp.
2. **Tạo môi trường Python** (PowerShell, Python 3.11+):
   ```powershell
   py -3.11 -m venv .venv        # hoặc py -3.12
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```
   Nếu PowerShell chặn Activate: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
3. **Chọn interpreter:** Ctrl+Shift+P → "Python: Select Interpreter" → `.venv` (`.vscode/settings.json` đã trỏ sẵn, cấu hình pytest + ruff format on save).
4. **Extension:** VS Code gợi ý theo `.vscode/extensions.json` → cài **Python** và **Ruff** (Claude Code chỉ cần nếu làm §B).
5. **Kiểm tra:**
   ```powershell
   python -m pytest -q          # phải xanh
   python -m ruff check .       # phải sạch
   ```
6. **Nhận task:** đọc `PLAN.md` §2–§4, chọn task trong `PROGRESS.md`, điền Owner, viết vào khối "Đang ở đâu" của mình. Quy trình: [docs/WORKFLOW.md](WORKFLOW.md); review: [docs/REVIEW.md](REVIEW.md).

## B. Nếu dùng Claude Code

1. **Trust workspace** lần đầu mở Claude Code trong thư mục — rule `allow` trong `.claude/settings.json` chỉ có hiệu lực sau khi trust.
2. **Cấu hình extension** (User settings, `Ctrl+,` → Extensions → Claude Code):
   - `Initial Permission Mode`: `default` (Manual). Chuyển mode trong ô chat khi cần.
   - `Use Python Environment`: bật (mặc định) → Claude chạy lệnh trong `.venv`.
   - `Use Ctrl Enter To Send`: tùy thích.
3. **Kiểm tra:** gõ `/` trong ô chat — phải thấy `/next-task`, `/wrap-up`. Hỏi "Đọc PROGRESS.md và cho biết task tiếp theo" để chắc `CLAUDE.md` (→ `@AGENTS.md`) đã được nạp.
4. **Mỗi task:**

   | Bước | Làm gì |
   |---|---|
   | 1 | **Conversation mới** cho mỗi task (trạng thái đã nằm trong PROGRESS.md). |
   | 2 | Task thuật toán hoặc đầu phase: **Plan mode**, gõ `/next-task <ID>` → duyệt kế hoạch. |
   | 3 | Khi thực thi: **Accept edits** (pytest/ruff/git commit đã allow sẵn). |
   | 4 | Xem diff + đọc `.md` của module. |
   | 5 | Dừng giữa chừng hoặc xong: `/wrap-up`. |

5. **Model:** model mạnh nhất trong gói (`/model`) cho task thuật toán (P2, P3, P8); GUI/plot/báo cáo dùng model nhanh hơn được.
6. **File cấu hình** (commit chung; rule cá nhân để `.claude/settings.local.json`, đã gitignore):

   | File | Vai trò |
   |---|---|
   | `CLAUDE.md` | `@AGENTS.md` + ghi chú riêng Claude Code |
   | `.claude/settings.json` | Permission: tự chạy pytest/ruff/gameai/git commit; hỏi khi pip install/push; cấm sửa `results/raw`, `rm -rf`, `git reset --hard`, `git push --force` |
   | `.claude/skills/next-task/` | `/next-task [ID]` = WORKFLOW §1 |
   | `.claude/skills/wrap-up/` | `/wrap-up` = WORKFLOW §2 |
   | `.claude/agents/spec-reviewer.md` | Subagent review = REVIEW.md |

## C. Nếu dùng agent khác (Codex, Cursor, Copilot, Gemini…) hoặc code tay

1. **Luật:** agent tự đọc `AGENTS.md` ở gốc repo (Codex, Cursor, Copilot đọc mặc định). **Gemini CLI** cần thêm `.gemini/settings.json`:
   ```json
   { "context": { "fileName": "AGENTS.md" } }
   ```
   Agent không tự đọc thì dán câu đầu tiên: "Đọc AGENTS.md và làm theo".
2. **Agent khác không bị chặn bằng permission như Claude Code** → tự để ý mục "Lệnh nguy hiểm" trong `AGENTS.md` (không `rm -rf`, `git reset --hard`, `git push --force`, sửa `results/raw/`; hỏi trước khi cài gói mới / push). Nên để agent ở chế độ hỏi trước khi chạy lệnh.
3. **Giao task:** "Làm task `<ID>` theo docs/WORKFLOW.md". Dừng phiên: "Wrap-up theo docs/WORKFLOW.md mục 2".
4. **Review:** mở phiên/agent mới: "Review task `<ID>` theo docs/REVIEW.md".
5. Code tay: làm theo đúng checklist trong `docs/WORKFLOW.md`.
