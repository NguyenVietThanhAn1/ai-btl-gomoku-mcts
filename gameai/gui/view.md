# GameView — `gameai/gui/view.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P6.1 (D-28)  ·  **Cập nhật:** 2026-11-17

## Mục đích
Lớp view chung cho mọi game trong GUI (vẽ bàn + chuyển click thành nước đi), registry view theo
`GameSpec.kind`, font hỗ trợ tiếng Việt.

## Public API
```python
def get_font(size: int, bold: bool = False) -> pygame.font.Font  # Segoe UI → Arial → font mặc định; có cache
@dataclass class OverlayOpts: show: bool = True; show_wn: bool = False

class GameView(ABC):
    rect: pygame.Rect                                       # vùng bàn
    def draw(self, surf, game, last: MoveInfo | None, overlay_info: MoveInfo | None, opts) -> None  # abstract
    def hit_test(self, pos, game) -> Move | None            # abstract: 1 click → nước hoàn chỉnh hoặc None
    def reset_input(self) -> None                           # xóa chọn dở; mặc định không làm gì
    def highlights(self, game) -> list[Move]                # ô cần tô do input; mặc định []
    def move_label(self, move) -> str                       # abstract

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
- Font: tương đương `SysFont("segoeui,arial")` nhưng viết tường minh — `pygame.font.match_font` theo thứ tự `FONT_NAMES = ("segoeui", "arial")` rồi `Font(path)`; không tìm thấy → `Font(None)` (mặc định). Đúng dấu tiếng Việt trên Windows.

## Test
- `tests/test_gui_controller.py`: render chuỗi có dấu ("Đang nghĩ…", "Hòa") trên Surface headless; khi máy có Segoe UI/Arial thì ảnh render trùng byte với font đó (không rơi về mặc định); app vẽ được.

## Hạn chế / TODO
- Font mặc định của pygame (khi máy không có Segoe UI/Arial) có thể thiếu một số ký tự có dấu.
