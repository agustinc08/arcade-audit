#!/usr/bin/python3
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


OPTIONS = (
    ("arcade", "BOTONERAS PRIMERO"),
    ("external", "JOYSTICKS PRIMERO"),
    ("cancel", "CANCELAR"),
)


def self_test() -> int:
    try:
        import pygame  # noqa: F401
    except Exception as exc:
        print(f"ERROR: pygame no disponible: {exc}", file=sys.stderr)
        return 1
    print("SELECTOR_SELF_TEST_OK")
    return 0


def choose(timeout: int, fullscreen: bool) -> int:
    os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    import pygame

    pygame.init()
    pygame.joystick.init()
    joysticks = []
    for index in range(pygame.joystick.get_count()):
        joystick = pygame.joystick.Joystick(index)
        joystick.init()
        joysticks.append(joystick)

    info = pygame.display.Info()
    width = max(960, info.current_w or 960)
    height = max(540, info.current_h or 540)
    flags = pygame.FULLSCREEN if fullscreen else pygame.NOFRAME
    screen = pygame.display.set_mode((width, height), flags)
    pygame.display.set_caption("Selector universal de controles")
    pygame.mouse.set_visible(False)

    title_font = pygame.font.Font(None, max(44, height // 14))
    option_font = pygame.font.Font(None, max(38, height // 18))
    help_font = pygame.font.Font(None, max(25, height // 30))
    clock = pygame.time.Clock()
    selected: int | None = None
    started = time.monotonic()
    axis_ready: dict[tuple[int, int], bool] = {}

    while True:
        if timeout > 0 and time.monotonic() - started >= timeout:
            print("timeout", file=sys.stderr)
            return 4

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 3
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_3, pygame.K_KP3):
                    print("cancel")
                    return 0
                if event.key in (pygame.K_1, pygame.K_KP1):
                    print("arcade")
                    return 0
                if event.key in (pygame.K_2, pygame.K_KP2):
                    print("external")
                    return 0
                if event.key in (pygame.K_UP, pygame.K_LEFT):
                    selected = 2 if selected is None else (selected - 1) % 3
                elif event.key in (pygame.K_DOWN, pygame.K_RIGHT, pygame.K_TAB):
                    selected = 0 if selected is None else (selected + 1) % 3
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) and selected is not None:
                    print(OPTIONS[selected][0])
                    return 0
            elif event.type == pygame.JOYHATMOTION:
                x, y = event.value
                if y > 0 or x < 0:
                    selected = 2 if selected is None else (selected - 1) % 3
                elif y < 0 or x > 0:
                    selected = 0 if selected is None else (selected + 1) % 3
            elif event.type == pygame.JOYAXISMOTION and event.axis in (0, 1):
                key = (event.instance_id, event.axis)
                if abs(event.value) < 0.35:
                    axis_ready[key] = True
                elif axis_ready.get(key, True):
                    axis_ready[key] = False
                    if event.value < 0:
                        selected = 2 if selected is None else (selected - 1) % 3
                    else:
                        selected = 0 if selected is None else (selected + 1) % 3
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button in (0, 1, 2, 3, 4, 5) and selected is not None:
                    print(OPTIONS[selected][0])
                    return 0

        screen.fill((9, 13, 22))
        title = title_font.render("¿CON QUÉ CONTROLES QUERÉS JUGAR?", True, (245, 247, 250))
        screen.blit(title, title.get_rect(center=(width // 2, height // 5)))

        top = height * 2 // 5
        box_w = min(width - 120, 920)
        box_h = max(65, height // 10)
        gap = max(18, height // 45)
        for index, (_, label) in enumerate(OPTIONS):
            rect = pygame.Rect((width - box_w) // 2, top + index * (box_h + gap), box_w, box_h)
            active = selected == index
            color = (25, 108, 170) if active else (31, 41, 55)
            border = (125, 211, 252) if active else (75, 85, 99)
            pygame.draw.rect(screen, color, rect, border_radius=12)
            pygame.draw.rect(screen, border, rect, width=3, border_radius=12)
            text = option_font.render(f"{index + 1}. {label}", True, (255, 255, 255))
            screen.blit(text, text.get_rect(center=rect.center))

        help_text = help_font.render(
            "Direcciones para elegir · botón de acción o Enter para confirmar",
            True,
            (174, 184, 198),
        )
        screen.blit(help_text, help_text.get_rect(center=(width // 2, height - height // 14)))
        pygame.display.flip()
        clock.tick(60)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--simulate", choices=("arcade", "external", "cancel"))
    parser.add_argument("--timeout", type=int, default=0)
    parser.add_argument("--windowed", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if args.simulate:
        print(args.simulate)
        return 0
    try:
        return choose(max(0, args.timeout), not args.windowed)
    except Exception as exc:
        print(f"selector_error: {exc}", file=sys.stderr)
        return 2
    finally:
        try:
            import pygame

            pygame.quit()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
