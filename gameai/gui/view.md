# GameView — `gameai/gui/view.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P6.1 (D-28), P6.3 (D-29)  ·  **Cập nhật:** 2026-11-17

## Mục đích
Lớp view chung cho mọi game trong GUI (vẽ bàn + chuyển click thành nước đi), registry view theo
`GameSpec.kind`, font hỗ trợ tiếng Việt.

## Public API
```python
def get_font(size, bold=False, weight=None) -> Font  # Be Vietnam Pro đóng gói → Segoe UI → Arial; có cache
FONT_DIR = gui/assets/fonts;  def font_path(weight) -> Path | None   # weight: regular/medium/semibold/bold
@dataclass class OverlayOpts: show: bool = True; show_wn: bool = False

class GameView(ABC):
    rect: pygame.Rect                                       # vùng bàn
    def draw(self, surf, game, last: MoveInfo | None, overlay_info: MoveInfo | None, opts) -> None  # abstract
    def hit_test(self, pos, game) -> Move | None            # abstract: 1 click → nước hoàn chỉnh hoặc None
    def reset_input(self) -> None                           # xóa chọn dở; mặc định không làm gì
    def highlights(self, game) -> list[Move]                # ô cần tô do input; mặc định []
    def move_label(self, move) -> str                       # abstract
    # P6.3 — hook có mặc định (view cờ tướng không bắt buộc cài):
    def preview(self, pos, game) -> Move | None             # nước nếu click ở pos (hover); KHÔNG đổi trạng thái input; mặc định None
    def draw_ghost(self, surf, move, player) -> None        # quân mờ; mặc định không vẽ
    def winning_cells(self, game, last) -> list[Move]       # đường thắng; mặc định []

VIEWS: dict[str, Callable[[GameSpec, Rect], GameView]]
def register_view(kind, factory) -> None
def make_view(spec: GameSpec, rect) -> GameView             # KeyError nếu kind chưa có view
```

## Phụ thuộc
- Dùng: pygame, `agents/registry.py` (`GameSpec`), `core/game.py`, `gui/controller.py` (`MoveInfo`).
- Được dùng bởi: `gui/kinrow_view.py`, `gui/pygame_app.py`; (P6.2) view cờ tướng.

## Thiết kế & quyết định (D-28)
- **Input là máy trạng thái nằm trong view.** App gọi `hit_test` mỗi click; view trả `Move` chỉ khi đủ
  thông tin. K-in-row: 1 click = 1 nước (không trạng thái). Cờ tướng (P6.2): click 1 chọn quân → lưu trạng
  thái, trả None, `highlights` trả các nước hợp lệ; click 2 vào ô đích → trả `Move`; click chỗ khác → đổi /
  bỏ chọn. App gọi `reset_input()` khi ván mới hoặc không phải lượt người. Controller không phải đổi.
- `make_view` import `gui/kinrow_view.py` để đăng ký; view mới gọi `register_view(kind, factory)` khi import.
- Font cache (`lru_cache`) bị xóa khi `pygame.quit()` (đăng ký lại `register_quit` mỗi chu kỳ init vì pygame bỏ
  danh sách sau mỗi lần quit) — font cũ sau quit gây access violation.
- **Font (D-29 phiên 3):** ưu tiên Be Vietnam Pro đóng gói (`assets/fonts`, SIL OFL 1.1, xem
  `assets/fonts/README.md`) để hình giống nhau trên mọi máy; thiếu file → fallback hệ thống như P6.1.
- Font hệ thống (fallback): tương đương `SysFont("segoeui,arial")` nhưng viết tường minh — `pygame.font.match_font` theo thứ tự `FONT_NAMES = ("segoeui", "arial")` rồi `Font(path)`; không tìm thấy → `Font(None)` (mặc định). Đúng dấu tiếng Việt trên Windows.

## Test
- `tests/test_gui_controller.py`: render chuỗi có dấu ("Đang nghĩ…", "Hòa") trên Surface headless; khi máy có Segoe UI/Arial thì ảnh render trùng byte với font đó (không rơi về mặc định); app vẽ được.

## Hạn chế / TODO
- Font mặc định của pygame (khi máy không có Segoe UI/Arial) có thể thiếu một số ký tự có dấu.
