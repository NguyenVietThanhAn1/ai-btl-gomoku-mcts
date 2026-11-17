"""Scene manager GUI P6.3: mỗi màn là một `Scene`; `SceneManager` giữ màn hiện tại, chuyển màn."""

from __future__ import annotations

from typing import Any

import pygame

from gameai.gui import anim
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

    def update(self, dt: float = 0.0) -> None:
        """Gọi mỗi frame trước `draw` (`dt` giây); mặc định cập nhật tween của widget."""
        for w in self.widgets:
            w.update(dt)

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
        self._fade_from: pygame.Surface | None = None  # frame cũ khi chuyển màn (crossfade)
        self._fade: anim.Tween | None = None

    def add(self, scene: Scene) -> None:
        self.scenes[scene.name] = scene

    def switch(self, name: str, **kwargs: Any) -> Scene:
        scene = self.scenes[name]
        if self.current is not None and anim.ENABLED:
            self._fade_from = self.surface.copy()
            self._fade = anim.Tween(255.0, 0.0, anim.SCENE)
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

    def tick(self, dt: float = 1 / 30) -> None:
        """Một frame: update(dt) + vẽ màn hiện tại (+ frame cũ mờ dần khi vừa chuyển màn)."""
        if self.current is None:
            return
        self.current.update(dt)
        self.current.draw(self.surface)
        if self._fade is not None and self._fade_from is not None:
            self._fade.update(dt)
            if self._fade.done:
                self._fade = self._fade_from = None
            else:
                self._fade_from.set_alpha(int(self._fade.value))
                self.surface.blit(self._fade_from, (0, 0))
