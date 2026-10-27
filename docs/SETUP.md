# SETUP — Claude Code trên VS Code cho BTL

## 1. Một lần duy nhất

0. **Cài file cấu hình** (`.claude/`, `.vscode/` đang nằm trong `_setup/`). Terminal tại thư mục `btl`:
   ```powershell
   powershell -ExecutionPolicy Bypass -File _setup\install-config.ps1
   ```
   Thấy `OK - config installed` → xóa thư mục `_setup`.
1. **Mở đúng thư mục gốc:** VS Code → File → Open Folder → `...\tri tue nhan tao\btl`.
   Claude Code đọc `CLAUDE.md` và `.claude/` từ thư mục gốc của workspace — mở thư mục cha thì cấu hình không có tác dụng.
2. **Cài extension gợi ý:** VS Code sẽ hỏi cài các extension trong `.vscode/extensions.json` (Claude Code, Python, Ruff) → Install.
3. **Tạo môi trường Python** (terminal trong VS Code, PowerShell):
   ```powershell
   py -3.11 -m venv .venv        # hoặc py -3.12
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   git init
   ```
   Nếu PowerShell chặn Activate: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
   Ctrl+Shift+P → "Python: Select Interpreter" → chọn `.venv`.
4. **Trust workspace:** lần đầu mở Claude Code trong thư mục này, chọn trust — các rule `allow` trong `.claude/settings.json` chỉ có hiệu lực sau khi trust.
5. **Cấu hình extension (User settings, `Ctrl+,` → Extensions → Claude Code):**
   - `Initial Permission Mode`: `default` (Manual). Chuyển mode ngay trong ô chat khi cần (xem §2).
   - `Use Ctrl Enter To Send`: bật nếu hay viết prompt nhiều dòng.
   - `Use Python Environment`: để bật (mặc định) → Claude chạy lệnh trong `.venv`.
6. **Kiểm tra:** trong ô chat Claude gõ `/` — phải thấy `/next-task`, `/wrap-up`. Hỏi "Đọc PROGRESS.md và cho biết task tiếp theo" để chắc CLAUDE.md đã được nạp.

## 2. Quy trình mỗi task

| Bước | Làm gì |
|---|---|
| 1 | **Mở conversation mới** cho mỗi task (context sạch; trạng thái đã nằm trong PROGRESS.md). |
| 2 | Task thuật toán (P2, P3, P8) hoặc đầu phase: chuyển **Plan mode**, gõ `/next-task P3.1` → đọc kế hoạch, sửa nếu cần → chấp nhận. |
| 3 | Khi thực thi: **Accept edits** để Claude sửa file không hỏi từng lần (pytest/ruff/git commit đã được allow sẵn). |
| 4 | Xem diff + đọc file `.md` của module → tự hỏi "mình giải thích được chưa?". |
| 5 | Dừng giữa chừng hoặc xong task: `/wrap-up`. |

Model: dùng model mạnh nhất có trong gói (`/model`) cho P2, P3, P8; GUI/plot/báo cáo dùng model nhanh hơn được.

## 3. Thành viên mới vào nhóm

1. Clone repo, làm lại §1.
2. Đọc `PLAN.md` §2–§4, nhận task trong `PROGRESS.md` (điền Owner).
3. Chỉ sửa module của mình; muốn đổi interface → ghi `docs/DECISIONS.md` và báo nhóm.
4. Commit cả `.claude/settings.json`, `.claude/skills/`, `.claude/agents/` để mọi người dùng cùng cấu hình. Rule cá nhân để trong `.claude/settings.local.json` (đã gitignore).

## 4. Các file cấu hình đã có

| File | Vai trò |
|---|---|
| `CLAUDE.md` | Quy tắc dự án, thứ tự đọc file, lệnh, style |
| `.claude/settings.json` | Quyền: tự chạy pytest/ruff/gameai/git commit; hỏi khi pip install/push; cấm sửa `results/raw`, `rm -rf` |
| `.claude/skills/next-task/` | `/next-task [ID]` — làm 1 task trọn quy trình |
| `.claude/skills/wrap-up/` | `/wrap-up` — chốt tiến độ cuối phiên |
| `.claude/agents/spec-reviewer.md` | Reviewer độc lập (chỉ đọc) kiểm acceptance criteria + đồng bộ `.md` |
| `.vscode/settings.json` | Interpreter `.venv`, pytest, ruff format on save |
