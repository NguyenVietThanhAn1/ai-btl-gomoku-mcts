# Font đóng gói — Be Vietnam Pro

- Họ font: **Be Vietnam Pro** (Regular, Medium, SemiBold, Bold) — hỗ trợ đầy đủ tiếng Việt có dấu.
- Tác giả: The Be Vietnam Pro Project Authors (https://github.com/bettergui/BeVietnamPro).
- License: **SIL Open Font License 1.1** — xem `OFL.txt` cùng thư mục (được phép đóng gói, phân phối kèm phần mềm;
  không bán riêng font; giữ nguyên file license).
- Nguồn tải: https://github.com/google/fonts/tree/main/ofl/bevietnampro (file `BeVietnamPro-*.ttf`, `OFL.txt`),
  tải ngày 2026-11-17.
- Dùng bởi: `gameai/gui/view.py::get_font` (fallback Segoe UI → Arial nếu thiếu file). Quyết định: D-29 (phiên 3).

# Font đóng gói — Noto Serif TC Bold (bản cắt, chữ Hán trên quân cờ tướng, P6.2)

- File: `NotoSerifTC-Bold-xq.otf` (7 408 byte, CFF/OTF) — **chỉ 18 chữ**: `帥仕相俥傌炮兵` (Đỏ), `將士象馬車砲卒` (Đen),
  `楚河漢界` (chữ trên sông). Dùng TC (chữ phồn thể) vì bộ chữ quân cờ truyền thống là phồn thể; bản gốc đủ cả 18 chữ.
- Tác giả: Adobe / Google (Noto CJK). License: **SIL Open Font License 1.1** — `OFL-NotoSerifTC.txt` (file `LICENSE`
  của thư mục `Serif/` trong repo). Bản cắt là "Modified Version" theo OFL: không dùng Reserved Font Name cho tên
  bán riêng; ở đây chỉ đóng gói kèm phần mềm.
- Nguồn tải: https://github.com/notofonts/noto-cjk/raw/main/Serif/SubsetOTF/TC/NotoSerifTC-Bold.otf
  (Version 2.003, 8 253 304 byte, sha256 `3ca2b329…a5768d`) và https://github.com/notofonts/noto-cjk/raw/main/Serif/LICENSE,
  tải ngày 2026-11-23.
- Lệnh cắt (chạy một lần; fonttools có sẵn trong venv vì matplotlib phụ thuộc — **không** thêm vào requirements):
  ```
  python -m fontTools.subset NotoSerifTC-Bold.otf --text="帥仕相俥傌炮兵將士象馬車砲卒楚河漢界" \
      --layout-features="" --no-hinting --output-file=gameai/gui/assets/fonts/NotoSerifTC-Bold-xq.otf
  ```
  Thêm chữ mới → cắt lại từ file gốc với `--text` mới (test `tests/test_gui_xiangqi.py` kiểm mọi chữ có glyph).
- Dùng bởi: `gameai/gui/view.py::get_cjk_font` (thiếu file → font CJK hệ thống Microsoft YaHei → SimHei → SimSun →
  chữ Việt viết tắt trên quân). Quyết định: D-37 (P6.2).
