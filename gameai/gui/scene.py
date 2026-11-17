"""Scene manager GUI P6.3: mỗi màn là một `Scene`; `SceneManager` giữ màn hiện tại, chuyển màn."""

from __future__ import annotations

from typing import Any

import pygame

from gameai.gui.widgets import Widget, current_theme


class Scene:
    """Một màn. Lớp con dựng `self.widgets` trong `on_enter`; sự kiện đi qua widget trên → dưới."""

    name = "scene"

    def __init__(self, manager: SceneManager) -> None:
        self.manager = manager
        self.widgets: list[Widget] = []

    def on_enter(self, **kwargs: Any) -> None:
        """Gọi mỗi lần chuyển tới màn này (tham số từ `SceneManager.switch`)."""

    def handle_event(self, ev: pygame.event.Event) -> bool:
        """Phát sự kiện cho widget (widget vẽ sau = nằm trên → nhận trước)."""
        for w in reversed(self.widgets):
            if w.handle_event(ev):
                return True
        return False

    def handle_key(self, key: int) -> None:
        """Phím mặc định: Esc → Home."""
        if key == pygame.K_ESCAPE:
            self.manager.switch("home")

    def update(self) -> None:
        """Gọi mỗi frame trước `draw`."""

    def draw(self, surf: pygame.Surface) -> None:
        surf.fill(current_theme().bg)
        for w in self.widgets:
            w.draw(surf)


class SceneManager:
    """Giữ các scene theo tên; `switch(name, **kw)` đổi màn và gọi `on_enter(**kw)`."""

    def __init__(self, surface: pygame.Surface) -> None:
        self.surface = surface
        self.scenes: dict[str, Scene] = {}
        self.current: Scene | None = None
        self.running = True

    def add(self, scene: Scene) -> None:
        self.scenes[scene.name] = scene

    def switch(self, name: str, **kwargs: Any) -> Scene:
        scene = self.scenes[name]
        self.current = scene
        scene.on_enter(**kwargs)
        return scene

    @property
    def current_name(self) -> str | None:
        return None if self.current is None else self.current.name

    def quit(self) -> None:
        self.running = False

    def handle_event(self, ev: pygame.event.Event) -> None:
        if ev.type == pygame.QUIT:
            self.quit()
        elif self.current is None:
            return
        elif ev.type == pygame.KEYDOWN:
            self.current.handle_key(ev.key)
        else:
            self.current.handle_event(ev)

    def tick(self) -> None:
        """Một frame: update + vẽ màn hiện tại."""
        if self.current is not None:
            self.current.update()
            self.current.draw(self.surface)
