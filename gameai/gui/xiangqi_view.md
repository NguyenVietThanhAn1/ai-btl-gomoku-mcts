# View cờ tướng — `gameai/gui/xiangqi_view.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** 🟡 đang làm (P6.2, chờ đo thời gian + D-37)  ·  **Task:** P6.2 (D-28, D-37)  ·  **Cập nhật:** 2026-11-25

## Mục đích
`GameView` cho `Xiangqi`: bàn 9×10 giao điểm như bàn thật (sông ngắt đường dọc, chéo cung, dấu chữ thập
pháo/tốt, chữ 楚河 漢界, viền đôi), quân đĩa gỗ viền đôi chữ Hán (Đỏ/Đen chữ khác nhau), input 2 bước
(chọn quân → ô đích), nước cuối, quầng tướng bị chiếu, xoay bàn khi người cầm Đen. Overlay N/W/N của MCTS
**không** vẽ trên bàn cờ tướng (✂ PLAN P6.2).

## Public API
```python
class XiangqiView(GameView):
    def __init__(self, rect: pygame.Rect, flipped: bool = False)   # flipped = Đen ở dưới
    cell: int            # khoảng cách 2 giao điểm (BOARD_RECT 672 px → 59)
    margin: int          # giao điểm biên → mép vùng gỗ = cell//2 + EDGE_PAD (16) → 45
    origin               # tọa độ màn hình của giao điểm (cột 0, hàng 0) màn hình
    selected: int | None # ô quân đang chọn (máy trạng thái input)
    # hình học
    def screen_cr(sq) -> (col, row)       # cột/hàng màn hình, hàng 0 ở trên
    def sq_at(col, row) -> int            # nghịch đảo screen_cr
    def sq_center(sq) -> (x, y)           # tâm giao điểm
    def pos_to_sq(pos) -> int | None      # giao điểm gần nhất nếu |dx|,|dy| ≤ cell/2; None ngoài bàn
    def board_rect() -> Rect              # vùng gỗ có lưới (không gồm khung/nhãn)
    def piece_radius() -> float           # (cell − 6) / 2
    def border_offsets() -> (inner, outer)  # giao điểm biên → viền trong / viền ngoài của viền đôi
    def col_label(col) -> "a".."i"; def row_label(row) -> "0".."9"   # nhãn ICCS, xoay theo flipped
    # input (D-28)
    def hit_test(pos, game) -> Move | None   # xem "Máy trạng thái chọn quân"
    def preview(pos, game) -> Move | None    # nước nếu click ở pos; KHÔNG đổi selected
    def highlights(game) -> list[Move]       # nước hợp lệ của quân đang chọn ([] nếu chưa chọn / hết ván)
    def reset_input() -> None                # selected = None (undo, đổi lượt…)
    # lời văn
    def move_label(move) -> str              # ICCS, vd "h2e2"
    def side_name(p) -> "Đỏ" | "Đen"
    def side_symbol(p) -> "●" | "○"          # PlayScene thay bằng side_dot trong lịch sử
    def side_dot(p, d) -> Surface            # đĩa trơn đỏ / đen (chấm lịch sử)
    def avatar(p, d) -> Surface              # quân tướng 帥 / 將 (avatar thẻ người chơi)
    def status_text(game) -> "Đỏ đang bị chiếu" | "Đen đang bị chiếu" | None   # None khi hết ván
    def end_reason(game) -> str | None       # = end_reason(game) bên dưới
    # vẽ
    def draw(surf, game, last, overlay_info, opts) -> None   # bỏ qua overlay_info/opts
    def draw_piece(surf, sq, piece, alpha=255) -> None       # alpha < 255: mờ, không bóng
    def draw_ghost(surf, move, player) -> None   # quân ở ô đi (theo bàn của lần draw trước) mờ ở ô đích
    def static_layer(theme=None) -> Surface      # bóng + khung + gỗ + lưới + viền đôi + sông + nhãn; cache theo (theme, flipped)
    def piece_sprite(piece) -> Surface           # sprite cache, đường kính cell − 6
def piece_char(piece) -> str            # 帥仕相傌俥炮兵 (Đỏ, piece > 0) / 將士象馬車砲卒 (Đen)
def end_reason(game: Xiangqi) -> str | None
    # "Chiếu bí" | "Bí nước" (bên tới lượt hết nước = thua) | "Hòa — lặp thế 3 lần"
    # | "Hòa — đạt giới hạn N nước" (N = game.max_plies) | None khi chưa hết ván
ALL_CHARS: str                          # 14 chữ quân + 楚河漢界 (font đóng gói phải có đủ)
```
- Đăng ký `VIEWS["xiangqi"]` khi import (`make_view` import sẵn module này). Factory mặc định `flipped=False`.
- Font chữ Hán: `view.get_cjk_font(size)` — file đóng gói `assets/fonts/NotoSerifTC-Bold-xq.otf` → font CJK hệ thống
  → `None`. Khi `None`: quân ghi chữ Việt (Tướng, Sĩ, Tượng, Mã, Xe, Pháo, Tốt), không vẽ chữ sông.

## Tọa độ & xoay bàn
- Ô `sq = rank * 9 + file` (như `games/xiangqi.py`): file a–i = 0–8, rank 0 = hàng Đỏ, 9 = hàng Đen.
- Không xoay (`flipped=False`, Đỏ ở dưới): `(col, row) = (file, 9 − rank)` → a0 ở góc dưới-trái.
- Xoay (`flipped=True`, Đen ở dưới): `(col, row) = (8 − file, rank)` → a0 ở góc trên-phải.
- Nhãn luôn là tọa độ ICCS thật của giao điểm: cột dưới bàn (a…i hoặc i…a), hàng bên trái (9…0 hoặc 0…9),
  nên khớp `move_label` trong lịch sử dù bàn xoay.
- Lề: viền trong của viền đôi cách giao điểm biên `piece_radius() + 6` px, viền ngoài thêm 5 px; vùng gỗ thêm
  `EDGE_PAD` → quân hàng 0/9, cột a/i không đè viền. `cell = min((avail_w − 32) // 9, (avail_h − 32) // 10)`
  với `avail = cạnh rect − 26 (nhãn) − 20 (khung)`.

## Máy trạng thái chọn quân (`hit_test`)
| Trạng thái | Click vào | Kết quả |
|---|---|---|
| bất kỳ | ngoài bàn, hoặc ván đã hết | `selected = None`, trả `None` |
| chưa chọn | quân của bên tới lượt | `selected = ô đó`, trả `None` |
| chưa chọn | ô khác | giữ `None`, trả `None` |
| đã chọn S | đích hợp lệ của S (gồm ô ăn quân) | trả `Move = S*90 + ô`, `selected = None` |
| đã chọn S | chính S | bỏ chọn (`None`) |
| đã chọn S | quân mình khác | đổi chọn sang quân đó |
| đã chọn S | ô khác (không hợp lệ) | bỏ chọn |

Nước hợp lệ lấy từ `game.legal_moves()` (lọc theo ô đi), nên không cho đi nước tự chiếu.

## Quy ước đánh dấu (phân biệt bằng hình dạng)
| Dấu | Hình | Màu | Lớp |
|---|---|---|---|
| Quân đang chọn | đĩa tô mờ d = cell + 8 (alpha 90), lộ vành quanh quân | `t.accent` | **dưới** quân |
| Ô đích trống | chấm tròn đặc d = max(10, cell/4) | `t.accent` alpha 200 | trên quân |
| Ô ăn quân | vòng tròn quanh quân (d = cell − 4, nét 5) | `t.accent` alpha 200 | trên quân |
| Nước cuối | khung 4 góc vuông cạnh cell − 2, nét 3, ở **cả ô đi và ô đến** | `t.last_move` | trên quân |
| Tướng bị chiếu | quầng + vòng đỏ (`CHECK_GLOW`) | đỏ | dưới quân |
| Tướng bị chiếu **và** đang được chọn | bỏ quầng tô, vòng đỏ nét 3 d = cell + 16 (ngoài đĩa chọn) | đỏ | dưới quân |

Ô ăn quân trùng ô đến của nước cuối (thường gặp: ăn lại) vẫn đọc được vì vòng tròn ≠ khung góc vuông.
Thứ tự vẽ: lớp tĩnh → quầng chiếu → đĩa chọn → quân → khung nước cuối → vòng/chấm đích.
Quầng chiếu và đĩa chọn chồng cùng vùng sẽ trộn thành nâu, nên khi chọn chính tướng bị chiếu thì
vòng đỏ được đẩy ra ngoài đĩa thay vì chỉ đổi thứ tự vẽ.

## Phụ thuộc
- Dùng: `gui/view.py` (`GameView`, `get_font`, `get_cjk_font`, `register_view`), `gui/render.py`
  (sprite khử răng cưa, cache), `gui/widgets.py` (theme, `draw_text`), `games/xiangqi.py` (`board`, `legal_moves`,
  `in_check`, `winner`, `ply`, `max_plies`, `move_to_iccs`), `gui/controller.py` (`MoveInfo`).
- Được dùng bởi: `gui/play_scene.py` qua `make_view` (scene đặt `flipped` khi người duy nhất cầm Đen, hiện
  `status_text` ở dòng trạng thái và `end_reason` trong modal), `gui/screenshots.py` (`xq_*`).

## Thiết kế & quyết định
- Chỉ dùng API công khai của `Xiangqi`; `end_reason` suy lý do hòa: `ply < max_plies` ⇒ lặp thế (D-22: lặp lần 3
  ưu tiên; nếu cả hai xảy ra đúng ply giới hạn thì ghi giới hạn nước).
- Lớp tĩnh vẽ đường kẻ ở 4× rồi `smoothscale` (khử răng cưa); cache theo `(theme.name, flipped)`.
- Font cắt còn 18 chữ (OFL, xem `assets/fonts/README.md`) để repo nhẹ.

## Test
- `tests/test_gui_xiangqi_view.py`: khứ hồi 90 giao điểm (thường + xoay), nhãn khi xoay, lề viền đôi, chọn / bỏ
  chọn / đổi chọn / đi / preview không đổi trạng thái, ô ăn quân trùng ô đến nước cuối, đĩa chọn dưới quân,
  font đủ glyph, font dự phòng chữ Việt, `end_reason` (chiếu bí, bí nước, lặp thế, giới hạn nước), `status_text`.

## Hạn chế / TODO
- Chưa có animation đi quân (k-in-row có `anim_move`); overlay MCTS không vẽ trên bàn.
