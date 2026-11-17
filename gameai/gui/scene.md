# Scene manager — `gameai/gui/scene.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** 🔄 đang làm  ·  **Task:** P6.3 (D-29)  ·  **Cập nhật:** 2026-11-17

## Mục đích
Chia GUI thành các màn (`Scene`) và chuyển màn bằng tên. Không chứa logic ván.

## Public API
```python
class Scene:
    name: str;  manager: SceneManager;  widgets: list[Widget]
    def on_enter(self, **kwargs) -> None       # gọi mỗi lần switch tới màn
    def handle_event(self, ev) -> bool         # chuột: phát cho widget từ trên xuống (widget vẽ sau nhận trước)
    def handle_key(self, key) -> None          # mặc định: Esc → "home"
    def update(self) -> None;  def draw(self, surf) -> None   # draw mặc định: nền + widget
class SceneManager:
    def __init__(self, surface);  scenes: dict[str, Scene];  current; current_name; running
    def add(self, scene);  def switch(self, name, **kw) -> Scene;  def quit(self)
    def handle_event(self, ev)                 # QUIT → quit(); KEYDOWN → current.handle_key; còn lại → current.handle_event
    def tick(self)                             # current.update() + current.draw(surface)
```

## Phụ thuộc
- Dùng: pygame, `gui/widgets.py`. Được dùng bởi: `gui/scenes.py`, `gui/play_scene.py`, `gui/pygame_app.py`.

## Thiết kế & quyết định (D-29)
- Scene được tạo một lần (giữ trạng thái, vd. lựa chọn ở Setup); `on_enter` dựng lại widget / ván mới.
- Esc theo màn: Home → thoát; Setup/Demo/Help → Home (mặc định của `Scene`); Play → đóng modal nếu mở, không thì thoát.

## Test
- `tests/test_gui_scenes.py`: chuyển màn bằng click nút và Esc.
