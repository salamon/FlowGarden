from __future__ import annotations

import argparse
import math
import random
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

import glfw
import moderngl


SHADER_DIR = Path(__file__).with_name("shaders")
PALETTE_NAMES = ("Garden", "Tidepool", "Ember", "Sakura", "Mineral")
MAX_ROCKS = 8
HELP_LINES = (
    "FLOWGARDEN HELP",
    "",
    "SPACE       AUTO / ZEN MODE",
    "LEFT DRAG   COMB / MOVE ROCK",
    "RIGHT DRAG  SWIRL",
    "WHEEL       BRUSH SIZE",
    "R           RE-SEED",
    "P           NEXT PALETTE",
    "1-5         SELECT PALETTE",
    "S           ADD ROCK",
    "SHIFT S     CLEAR ROCKS",
    "F11         FULLSCREEN",
    "H           CLOSE HELP",
    "ESC         QUIT",
)

# Seven rows of five pixels keep the help self-contained and deterministic.
FONT_5X7 = {
    " ": ("00000",) * 7,
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00100", "01000", "10000", "00000", "00000"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
}


def build_help_bitmap(scale: int = 2, padding: int = 12) -> tuple[tuple[int, int], bytes]:
    """Rasterize the static help without fonts, assets, or UI dependencies."""
    glyph_width, glyph_height = 5, 7
    advance_x, advance_y = glyph_width + 1, glyph_height + 2
    text_width = max(len(line) for line in HELP_LINES) * advance_x - 1
    text_height = len(HELP_LINES) * advance_y - 2
    width = text_width * scale + padding * 2
    height = text_height * scale + padding * 2
    pixels = bytearray(width * height)

    for line_index, line in enumerate(HELP_LINES):
        for character_index, character in enumerate(line):
            glyph = FONT_5X7[character]
            origin_x = padding + character_index * advance_x * scale
            origin_y = padding + line_index * advance_y * scale
            for row_index, row in enumerate(glyph):
                for column_index, value in enumerate(row):
                    if value == "0":
                        continue
                    pixel_x = origin_x + column_index * scale
                    pixel_y = origin_y + row_index * scale
                    for offset_y in range(scale):
                        start = (pixel_y + offset_y) * width + pixel_x
                        pixels[start : start + scale] = b"\xff" * scale

    return (width, height), bytes(pixels)


@dataclass
class Rock:
    x: float
    y: float
    radius_x: float
    radius_y: float
    angle: float
    shape: float


class FlowGarden:
    """Thin window/input shell around an artistic GPU flow simulation."""

    def __init__(
        self,
        *,
        windowed: bool,
        scale: float,
        pressure_steps: int,
        palette: int = 0,
        hidden: bool = False,
    ) -> None:
        if not glfw.init():
            raise RuntimeError("GLFW could not initialize")

        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 1)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
        glfw.window_hint(glfw.DOUBLEBUFFER, glfw.TRUE)
        glfw.window_hint(glfw.AUTO_ICONIFY, glfw.FALSE)
        glfw.window_hint(glfw.FLOATING, glfw.FALSE)
        if hidden:
            glfw.window_hint(glfw.VISIBLE, glfw.FALSE)

        monitor = glfw.get_primary_monitor()
        mode = glfw.get_video_mode(monitor)
        if mode is None:
            glfw.terminate()
            raise RuntimeError("Could not read the primary monitor video mode")

        if windowed:
            width, height = min(1280, mode.size.width), min(720, mode.size.height)
            target_monitor = None
        else:
            width, height = mode.size.width, mode.size.height
            target_monitor = monitor

        self.window = glfw.create_window(width, height, "FlowGarden", target_monitor, None)
        if not self.window:
            glfw.terminate()
            raise RuntimeError("An OpenGL 4.1 context could not be created")

        glfw.make_context_current(self.window)
        if windowed and not hidden:
            glfw.set_window_pos(self.window, max(40, (mode.size.width - width) // 2), max(40, (mode.size.height - height) // 2))
        glfw.swap_interval(1)
        self.ctx = moderngl.create_context(require=410)
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.BLEND)

        self.pressure_steps = max(4, pressure_steps)
        self.auto_mode = True
        self.help_visible = False
        self.palette_index = palette % len(PALETTE_NAMES)
        self.brush_radius = 0.075
        self.mouse_uv = (0.5, 0.5)
        self.mouse_delta = [0.0, 0.0]
        self.left_down = False
        self.right_down = False
        self.seed = self._new_seed()
        self.rocks: list[Rock] = []
        self._rng = random.Random(secrets.randbits(64))
        self._dragged_rock: int | None = None
        self._rock_drag_offset = (0.0, 0.0)
        self._last_cursor: tuple[float, float] | None = None
        self._windowed_rect = (100, 100, min(1280, width), min(720, height))
        self._is_fullscreen = not windowed
        self._fullscreen_monitor = target_monitor

        sim_width = max(320, int(width * max(0.2, min(scale, 1.0))))
        sim_height = max(180, int(height * max(0.2, min(scale, 1.0))))
        self.sim_size = (sim_width, sim_height)

        self._build_programs()
        self._build_targets()
        self._build_help_texture()
        self._install_callbacks()
        self._update_window_title()
        self._reset_pigment()

    @staticmethod
    def _new_seed() -> float:
        return secrets.randbelow(1_000_000) / 1000.0

    @staticmethod
    def _shader(name: str) -> str:
        return (SHADER_DIR / name).read_text(encoding="utf-8")

    def _build_programs(self) -> None:
        vertex = self._shader("fullscreen.vert")
        fragment_names = {
            "init": "init.frag",
            "velocity": "velocity.frag",
            "divergence": "divergence.frag",
            "pressure": "pressure.frag",
            "project": "project.frag",
            "pigment": "pigment.frag",
            "render": "render.frag",
        }
        self.programs = {
            name: self.ctx.program(vertex_shader=vertex, fragment_shader=self._shader(filename))
            for name, filename in fragment_names.items()
        }
        texture_uniforms = {
            "velocity": ("u_velocity",),
            "divergence": ("u_velocity",),
            "pressure": ("u_pressure", "u_divergence"),
            "project": ("u_velocity", "u_pressure"),
            "pigment": ("u_pigment", "u_velocity"),
            "render": ("u_pigment", "u_velocity", "u_help_mask"),
        }
        for name, uniform_names in texture_uniforms.items():
            for unit, uniform_name in enumerate(uniform_names):
                self.programs[name][uniform_name].value = unit
        self.vaos = {name: self.ctx.vertex_array(program, []) for name, program in self.programs.items()}

    def _texture(self, components: int, dtype: str = "f2") -> moderngl.Texture:
        texture = self.ctx.texture(self.sim_size, components, dtype=dtype)
        texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        texture.repeat_x = False
        texture.repeat_y = False
        return texture

    def _build_targets(self) -> None:
        self.velocity = [self._texture(2), self._texture(2)]
        self.pigment = [self._texture(4), self._texture(4)]
        self.pressure = [self._texture(1), self._texture(1)]
        self.divergence = self._texture(1)

        self.velocity_fbo = [self.ctx.framebuffer([texture]) for texture in self.velocity]
        self.pigment_fbo = [self.ctx.framebuffer([texture]) for texture in self.pigment]
        self.pressure_fbo = [self.ctx.framebuffer([texture]) for texture in self.pressure]
        self.divergence_fbo = self.ctx.framebuffer([self.divergence])
        self.velocity_fbo[0].clear()
        self.velocity_fbo[1].clear()
        self.pressure_fbo[0].clear()
        self.pressure_fbo[1].clear()

    def _build_help_texture(self) -> None:
        size, pixels = build_help_bitmap()
        self.help_texture = self.ctx.texture(size, 1, data=pixels, dtype="f1")
        self.help_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.help_texture.repeat_x = False
        self.help_texture.repeat_y = False

    def _install_callbacks(self) -> None:
        glfw.set_key_callback(self.window, self._on_key)
        glfw.set_cursor_pos_callback(self.window, self._on_cursor)
        glfw.set_mouse_button_callback(self.window, self._on_button)
        glfw.set_scroll_callback(self.window, self._on_scroll)

    def _on_key(self, _window, key: int, _scancode: int, action: int, _mods: int) -> None:
        if action != glfw.PRESS:
            return
        if key == glfw.KEY_ESCAPE:
            glfw.set_window_should_close(self.window, True)
        elif key == glfw.KEY_SPACE:
            self.auto_mode = not self.auto_mode
            if not self.auto_mode:
                self._clear_motion()
        elif key == glfw.KEY_R:
            self._reseed()
        elif key == glfw.KEY_P:
            self._set_palette(self.palette_index + 1)
        elif key == glfw.KEY_S:
            if _mods & glfw.MOD_SHIFT:
                self._clear_rocks()
            else:
                self._add_random_rock()
        elif glfw.KEY_1 <= key <= glfw.KEY_5:
            self._set_palette(key - glfw.KEY_1)
        elif key == glfw.KEY_F11:
            self._toggle_fullscreen()
        elif key == glfw.KEY_H:
            self.help_visible = not self.help_visible

    def _update_window_title(self) -> None:
        rock_count = len(self.rocks)
        rock_suffix = "" if rock_count == 0 else f" - {rock_count} {'rock' if rock_count == 1 else 'rocks'}"
        glfw.set_window_title(
            self.window,
            f"FlowGarden - {PALETTE_NAMES[self.palette_index]}{rock_suffix}",
        )

    def _set_palette(self, palette: int) -> None:
        self.palette_index = palette % len(PALETTE_NAMES)
        self._update_window_title()

    def _reseed(self) -> None:
        self.seed = self._new_seed()
        self._clear_motion()
        self._reset_pigment()

    def _add_random_rock(self) -> None:
        if len(self.rocks) >= MAX_ROCKS:
            return

        aspect = self.sim_size[0] / self.sim_size[1]
        for _ in range(32):
            radius_y = self._rng.uniform(0.045, 0.085)
            radius_x = radius_y * self._rng.uniform(0.78, 1.42)
            margin_x = radius_x / aspect + 0.025
            margin_y = radius_y + 0.025
            candidate = Rock(
                x=self._rng.uniform(margin_x, 1.0 - margin_x),
                y=self._rng.uniform(margin_y, 1.0 - margin_y),
                radius_x=radius_x,
                radius_y=radius_y,
                angle=self._rng.uniform(-math.pi, math.pi),
                shape=self._rng.random(),
            )
            if all(
                math.hypot((candidate.x - rock.x) * aspect, candidate.y - rock.y)
                > max(candidate.radius_x, candidate.radius_y)
                + max(rock.radius_x, rock.radius_y)
                + 0.035
                for rock in self.rocks
            ):
                self.rocks.append(candidate)
                self._update_window_title()
                return

    def _clear_rocks(self) -> None:
        self.rocks.clear()
        self._dragged_rock = None
        self._update_window_title()

    def _rock_at(self, position: tuple[float, float]) -> int | None:
        aspect = self.sim_size[0] / self.sim_size[1]
        for index in range(len(self.rocks) - 1, -1, -1):
            rock = self.rocks[index]
            dx = (position[0] - rock.x) * aspect
            dy = position[1] - rock.y
            cosine = math.cos(rock.angle)
            sine = math.sin(rock.angle)
            local_x = cosine * dx + sine * dy
            local_y = -sine * dx + cosine * dy
            if (local_x / rock.radius_x) ** 2 + (local_y / rock.radius_y) ** 2 <= 1.3:
                return index
        return None

    def _rock_uniforms(self) -> dict[str, object]:
        rocks = [(rock.x, rock.y, rock.radius_x, rock.radius_y) for rock in self.rocks]
        metadata = [(rock.angle, rock.shape) for rock in self.rocks]
        rocks.extend([(0.0, 0.0, 0.01, 0.01)] * (MAX_ROCKS - len(rocks)))
        metadata.extend([(0.0, 0.0)] * (MAX_ROCKS - len(metadata)))
        return {
            "u_rock_count": len(self.rocks),
            "u_rocks": tuple(rocks),
            "u_rock_meta": tuple(metadata),
        }

    def _on_cursor(self, _window, x: float, y: float) -> None:
        width, height = glfw.get_window_size(self.window)
        if width <= 0 or height <= 0:
            return
        current = (x / width, 1.0 - y / height)
        if self._dragged_rock is not None:
            rock = self.rocks[self._dragged_rock]
            aspect = self.sim_size[0] / self.sim_size[1]
            margin_x = rock.radius_x / aspect
            rock.x = max(margin_x, min(1.0 - margin_x, current[0] + self._rock_drag_offset[0]))
            rock.y = max(rock.radius_y, min(1.0 - rock.radius_y, current[1] + self._rock_drag_offset[1]))
            self.mouse_uv = current
            self._last_cursor = current
            return
        if self._last_cursor is not None and (self.left_down or self.right_down):
            self.mouse_delta[0] += current[0] - self._last_cursor[0]
            self.mouse_delta[1] += current[1] - self._last_cursor[1]
        self.mouse_uv = current
        self._last_cursor = current

    def _on_button(self, _window, button: int, action: int, _mods: int) -> None:
        if button == glfw.MOUSE_BUTTON_LEFT:
            if action == glfw.PRESS:
                x, y = glfw.get_cursor_pos(self.window)
                self._on_cursor(self.window, x, y)
                rock_index = self._rock_at(self.mouse_uv)
                if rock_index is None:
                    self.left_down = True
                else:
                    rock = self.rocks[rock_index]
                    self._dragged_rock = rock_index
                    self._rock_drag_offset = (rock.x - self.mouse_uv[0], rock.y - self.mouse_uv[1])
                    self.left_down = False
            elif action == glfw.RELEASE:
                self.left_down = False
                self._dragged_rock = None
        elif button == glfw.MOUSE_BUTTON_RIGHT:
            self.right_down = action != glfw.RELEASE
        if action == glfw.PRESS and button != glfw.MOUSE_BUTTON_LEFT:
            x, y = glfw.get_cursor_pos(self.window)
            self._on_cursor(self.window, x, y)

    def _on_scroll(self, _window, _dx: float, dy: float) -> None:
        self.brush_radius = max(0.025, min(0.22, self.brush_radius * math.exp(dy * 0.12)))

    def _monitor_for_window(self):
        """Return the monitor containing the largest part of the window."""
        window_x, window_y = glfw.get_window_pos(self.window)
        window_width, window_height = glfw.get_window_size(self.window)
        window_center = (window_x + window_width * 0.5, window_y + window_height * 0.5)

        best_monitor = None
        best_overlap = -1
        best_distance = math.inf
        for monitor in glfw.get_monitors() or ():
            monitor_x, monitor_y, monitor_width, monitor_height = glfw.get_monitor_workarea(monitor)
            overlap_width = max(
                0,
                min(window_x + window_width, monitor_x + monitor_width) - max(window_x, monitor_x),
            )
            overlap_height = max(
                0,
                min(window_y + window_height, monitor_y + monitor_height) - max(window_y, monitor_y),
            )
            overlap = overlap_width * overlap_height
            center_x = monitor_x + monitor_width * 0.5
            center_y = monitor_y + monitor_height * 0.5
            distance = (window_center[0] - center_x) ** 2 + (window_center[1] - center_y) ** 2
            if overlap > best_overlap or (overlap == best_overlap and distance < best_distance):
                best_monitor = monitor
                best_overlap = overlap
                best_distance = distance

        return best_monitor or glfw.get_primary_monitor()

    def _toggle_fullscreen(self) -> None:
        if self._is_fullscreen:
            x, y, width, height = self._windowed_rect
            glfw.set_window_monitor(self.window, None, x, y, width, height, 0)
            self._fullscreen_monitor = None
        else:
            self._windowed_rect = (*glfw.get_window_pos(self.window), *glfw.get_window_size(self.window))
            monitor = self._monitor_for_window()
            mode = glfw.get_video_mode(monitor)
            if mode is None:
                return
            glfw.set_window_monitor(
                self.window, monitor, 0, 0, mode.size.width, mode.size.height, mode.refresh_rate
            )
            self._fullscreen_monitor = monitor
        self._is_fullscreen = not self._is_fullscreen

    def _clear_motion(self) -> None:
        self.velocity_fbo[0].clear()
        self.velocity_fbo[1].clear()
        self.pressure_fbo[0].clear()
        self.pressure_fbo[1].clear()

    def _set_uniforms(self, program: moderngl.Program, uniforms: dict[str, object]) -> None:
        for name, value in uniforms.items():
            if name in program:
                program[name].value = value

    def _draw(
        self,
        name: str,
        framebuffer: moderngl.Framebuffer | None,
        textures: tuple[moderngl.Texture, ...] = (),
        uniforms: dict[str, object] | None = None,
    ) -> None:
        if framebuffer is None:
            self.ctx.screen.use()
            width, height = glfw.get_framebuffer_size(self.window)
        else:
            framebuffer.use()
            width, height = framebuffer.size
        self.ctx.viewport = (0, 0, width, height)
        for unit, texture in enumerate(textures):
            texture.use(unit)
        program = self.programs[name]
        if uniforms:
            self._set_uniforms(program, uniforms)
        self.vaos[name].render(mode=moderngl.TRIANGLES, vertices=3)

    def _reset_pigment(self) -> None:
        uniforms = {"u_seed": self.seed, "u_aspect": self.sim_size[0] / self.sim_size[1]}
        self._draw("init", self.pigment_fbo[0], uniforms=uniforms)
        self._draw("init", self.pigment_fbo[1], uniforms=uniforms)

    @staticmethod
    def _swap(textures: list[moderngl.Texture], fbos: list[moderngl.Framebuffer]) -> None:
        textures.reverse()
        fbos.reverse()

    def _simulate(self, dt: float, elapsed: float) -> None:
        mouse_kind = 1 if self.left_down else (-1 if self.right_down else 0)
        rock_uniforms = self._rock_uniforms()
        common = {
            "u_dt": dt,
            "u_time": elapsed,
            "u_aspect": self.sim_size[0] / self.sim_size[1],
            "u_auto": int(self.auto_mode),
            "u_mouse": self.mouse_uv,
            "u_mouse_delta": tuple(self.mouse_delta),
            "u_mouse_kind": mouse_kind,
            "u_brush": self.brush_radius,
            "u_seed": self.seed,
            **rock_uniforms,
        }

        self._draw("velocity", self.velocity_fbo[1], (self.velocity[0],), common)
        self._swap(self.velocity, self.velocity_fbo)

        self._draw("divergence", self.divergence_fbo, (self.velocity[0],))
        self.pressure_fbo[0].clear()
        self.pressure_fbo[1].clear()
        for _ in range(self.pressure_steps):
            self._draw("pressure", self.pressure_fbo[1], (self.pressure[0], self.divergence))
            self._swap(self.pressure, self.pressure_fbo)

        self._draw(
            "project",
            self.velocity_fbo[1],
            (self.velocity[0], self.pressure[0]),
            {"u_aspect": common["u_aspect"], **rock_uniforms},
        )
        self._swap(self.velocity, self.velocity_fbo)

        self._draw("pigment", self.pigment_fbo[1], (self.pigment[0], self.velocity[0]), common)
        self._swap(self.pigment, self.pigment_fbo)
        self.mouse_delta[:] = (0.0, 0.0)

    def _render(self, elapsed: float, target: moderngl.Framebuffer | None = None) -> None:
        if target is None:
            view_width, view_height = glfw.get_framebuffer_size(self.window)
        else:
            view_width, view_height = target.size
        self._draw(
            "render",
            target,
            (self.pigment[0], self.velocity[0], self.help_texture),
            {
                "u_time": elapsed,
                "u_aspect": self.sim_size[0] / self.sim_size[1],
                "u_view_aspect": view_width / max(view_height, 1),
                "u_auto": int(self.auto_mode),
                "u_help": int(self.help_visible),
                "u_mouse": self.mouse_uv,
                "u_brush": self.brush_radius,
                "u_mouse_kind": int(self.left_down or self.right_down),
                "u_palette": self.palette_index,
                **self._rock_uniforms(),
            },
        )

    def run(self, frame_limit: int | None = None) -> None:
        started = previous = time.perf_counter()
        frame = 0
        verification_fbo = self.ctx.simple_framebuffer((8, 8), components=3) if frame_limit else None
        try:
            while not glfw.window_should_close(self.window):
                glfw.poll_events()
                now = time.perf_counter()
                dt = min(now - previous, 1.0 / 30.0)
                previous = now
                self._simulate(max(dt, 1.0 / 240.0), now - started)
                self._render(now - started)
                frame += 1
                if frame_limit is not None:
                    width, height = glfw.get_framebuffer_size(self.window)
                    if self.ctx.viewport != (0, 0, width, height):
                        raise RuntimeError("The screen viewport does not match the framebuffer")
                if frame_limit is not None and frame >= frame_limit:
                    self._render(now - started, verification_fbo)
                    center = verification_fbo.read(viewport=(4, 4, 1, 1), components=3, alignment=1)
                    if not any(center):
                        raise RuntimeError("The render pipeline produced an empty frame")
                glfw.swap_buffers(self.window)
                if frame_limit is not None and frame >= frame_limit:
                    break
                if frame_limit is not None and frame == 1:
                    self._add_random_rock()
                    self.auto_mode = False
                    self._on_key(self.window, glfw.KEY_H, 0, glfw.PRESS, 0)
                    self._clear_motion()
                    self.left_down = True
                    self.mouse_uv = (0.25, 0.25)
                    self.mouse_delta[:] = (0.012, 0.006)
        finally:
            glfw.destroy_window(self.window)
            glfw.terminate()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="An offline, artistic GPU flow garden")
    parser.add_argument("--fullscreen", action="store_true", help="start in fullscreen instead of a 1280x720 window")
    parser.add_argument(
        "--scale", type=float, default=0.55, help="simulation resolution relative to the screen (0.2-1.0)"
    )
    parser.add_argument("--pressure-steps", type=int, default=14, help="Jacobi pressure iterations per frame")
    parser.add_argument(
        "--palette",
        type=int,
        choices=range(1, len(PALETTE_NAMES) + 1),
        default=1,
        metavar="1-5",
        help="initial color palette (1: Garden, 2: Tidepool, 3: Ember, 4: Sakura, 5: Mineral)",
    )
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = FlowGarden(
        windowed=not args.fullscreen,
        scale=args.scale,
        pressure_steps=args.pressure_steps,
        palette=args.palette - 1,
        hidden=args.smoke_test,
    )
    app.run(frame_limit=2 if args.smoke_test else None)
    if args.smoke_test:
        print("FlowGarden smoke test passed")
