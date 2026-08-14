from __future__ import annotations

import argparse
import math
import time
from pathlib import Path

import glfw
import moderngl


SHADER_DIR = Path(__file__).with_name("shaders")


class FlowGarden:
    """Thin window/input shell around an artistic GPU flow simulation."""

    def __init__(self, *, windowed: bool, scale: float, pressure_steps: int, hidden: bool = False) -> None:
        if not glfw.init():
            raise RuntimeError("GLFW could not initialize")

        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.DOUBLEBUFFER, glfw.TRUE)
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
            raise RuntimeError("An OpenGL 4.3 context could not be created")

        glfw.make_context_current(self.window)
        if windowed and not hidden:
            glfw.set_window_pos(self.window, max(40, (mode.size.width - width) // 2), max(40, (mode.size.height - height) // 2))
        glfw.swap_interval(1)
        self.ctx = moderngl.create_context(require=430)
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.BLEND)

        self.pressure_steps = max(4, pressure_steps)
        self.auto_mode = True
        self.brush_radius = 0.075
        self.mouse_uv = (0.5, 0.5)
        self.mouse_delta = [0.0, 0.0]
        self.left_down = False
        self.right_down = False
        self.seed = time.time() % 1000.0
        self._last_cursor: tuple[float, float] | None = None
        self._windowed_rect = (100, 100, min(1280, width), min(720, height))
        self._is_fullscreen = not windowed
        self._fullscreen_monitor = target_monitor

        sim_width = max(320, int(width * max(0.2, min(scale, 1.0))))
        sim_height = max(180, int(height * max(0.2, min(scale, 1.0))))
        self.sim_size = (sim_width, sim_height)

        self._build_programs()
        self._build_targets()
        self._install_callbacks()
        self._reset_pigment()

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
            self.seed = (self.seed + 137.17) % 1000.0
            self._clear_motion()
            self._reset_pigment()
        elif key == glfw.KEY_F11:
            self._toggle_fullscreen()

    def _on_cursor(self, _window, x: float, y: float) -> None:
        width, height = glfw.get_window_size(self.window)
        if width <= 0 or height <= 0:
            return
        current = (x / width, 1.0 - y / height)
        if self._last_cursor is not None and (self.left_down or self.right_down):
            self.mouse_delta[0] += current[0] - self._last_cursor[0]
            self.mouse_delta[1] += current[1] - self._last_cursor[1]
        self.mouse_uv = current
        self._last_cursor = current

    def _on_button(self, _window, button: int, action: int, _mods: int) -> None:
        down = action != glfw.RELEASE
        if button == glfw.MOUSE_BUTTON_LEFT:
            self.left_down = down
        elif button == glfw.MOUSE_BUTTON_RIGHT:
            self.right_down = down
        if down:
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
        }

        self._draw("velocity", self.velocity_fbo[1], (self.velocity[0],), common)
        self._swap(self.velocity, self.velocity_fbo)

        self._draw("divergence", self.divergence_fbo, (self.velocity[0],))
        self.pressure_fbo[0].clear()
        self.pressure_fbo[1].clear()
        for _ in range(self.pressure_steps):
            self._draw("pressure", self.pressure_fbo[1], (self.pressure[0], self.divergence))
            self._swap(self.pressure, self.pressure_fbo)

        self._draw("project", self.velocity_fbo[1], (self.velocity[0], self.pressure[0]))
        self._swap(self.velocity, self.velocity_fbo)

        self._draw("pigment", self.pigment_fbo[1], (self.pigment[0], self.velocity[0]), common)
        self._swap(self.pigment, self.pigment_fbo)
        self.mouse_delta[:] = (0.0, 0.0)

    def _render(self, elapsed: float, target: moderngl.Framebuffer | None = None) -> None:
        width, height = target.size if target is not None else glfw.get_framebuffer_size(self.window)
        self._draw(
            "render",
            target,
            (self.pigment[0], self.velocity[0]),
            {
                "u_time": elapsed,
                "u_aspect": width / max(1, height),
                "u_auto": int(self.auto_mode),
                "u_mouse": self.mouse_uv,
                "u_brush": self.brush_radius,
                "u_mouse_kind": int(self.left_down or self.right_down),
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
                    self.auto_mode = False
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
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = FlowGarden(
        windowed=not args.fullscreen,
        scale=args.scale,
        pressure_steps=args.pressure_steps,
        hidden=args.smoke_test,
    )
    app.run(frame_limit=2 if args.smoke_test else None)
    if args.smoke_test:
        print("FlowGarden smoke test passed")
