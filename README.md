# FlowGarden

![FlowGarden composition](docs/assets/flowgarden.png)

FlowGarden is an offline, shader-driven fluid-art playground. Four colorful pigment fields flow across the screen and can be combed or swirled with the mouse, turning a real-time GPU process into a quiet, interactive visual instrument.

> [!IMPORTANT]
> FlowGarden is an artistic simulation, not a physics simulation. Its numerical passes are inspired by real-time incompressible-flow techniques, but they are deliberately tuned for visual behavior. The output must not be interpreted as a physically accurate model of fluids, viscosity, pigments, pressure, or material mixing.

The application has no accounts, telemetry, analytics, cloud services, advertisements, or automatic update checks. Once downloaded and installed, it runs entirely on the local computer. See [Privacy](PRIVACY.md) for the complete offline guarantee.

## Current status

FlowGarden is preparing its first public source release. Windows is the currently verified platform; standalone binaries will be added in a later GitHub release. The source already includes the complete interactive renderer and GPU pipeline.

## Highlights

- Real-time GPU rendering with Python, ModernGL, GLFW, and GLSL.
- Autonomous motion and a paused zen-garden interaction mode.
- Four stylized, immiscible-looking pigment fields with five color palettes.
- Multi-monitor fullscreen that stays active when another monitor receives focus.
- A deliberately small codebase designed to be read, modified, and forked.
- Fully offline execution with no data collection.

## Requirements

- Python 3.12 is recommended for running from source.
- A GPU and driver supporting OpenGL 4.3 or newer.
- Windows is currently tested. Other operating systems are not yet supported or verified.

macOS is not currently supported because FlowGarden requires OpenGL 4.3, while Apple's native OpenGL implementation exposes an older core profile.

## Run from source

Clone the repository, create a virtual environment, and install the project:

```powershell
git clone https://github.com/salamon/FlowGarden.git
cd FlowGarden
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m flowgarden
```

Installing dependencies can require an internet connection. Running FlowGarden does not.

For contributors who prefer Conda:

```powershell
conda env create -f environment.yml
conda activate flowgarden
python -m flowgarden
```

Start directly in fullscreen mode:

```powershell
python -m flowgarden --fullscreen
```

Reduce the simulation resolution on older GPUs or very high-resolution displays:

```powershell
python -m flowgarden --scale 0.4
```

## Controls

| Input | Action |
|---|---|
| `Space` | Toggle autonomous flow and zen-garden mode |
| Left-drag | Push and comb the pigment fields |
| Right-drag or hold | Create a local swirl |
| Mouse wheel | Adjust the brush radius |
| `R` | Re-seed and restart the composition |
| `P` | Cycle to the next color palette |
| `1`–`5` | Select Garden, Tidepool, Ember, Sakura, or Mineral directly |
| `F11` | Toggle fullscreen on the current monitor without auto-minimizing on focus loss |
| `Esc` | Quit |

## Color palettes

- **Garden**: the original jade, coral, amber, and violet identity.
- **Tidepool**: deep blue, cyan, seafoam, and warm sand.
- **Ember**: charcoal, crimson, orange, and gold.
- **Sakura**: indigo, magenta, pink, and pale blossom tones.
- **Mineral**: forest green, turquoise, ochre, and clay.

Changing palettes remaps the current pigment fields without resetting their motion. Press `P` to cycle or use `1`–`5` for direct selection.

## How it works

Python is responsible only for the window, input, GPU resources, and render-pass orchestration. Advection, procedural forcing, divergence, pressure relaxation, velocity projection, pigment-field transport, and final styling run in GLSL fragment shaders.

The implementation favors responsive and aesthetically interesting motion over physical correctness. For pass-by-pass details and the model's limitations, read [Architecture and artistic model](docs/architecture.md).

The initial palette can also be selected from the command line with `--palette 1-5`.

## Project structure

```text
FlowGarden/
|-- flowgarden/
|   |-- app.py          # Window, input, GPU resources, and pass orchestration
|   `-- shaders/        # Simulation and rendering passes
|-- docs/               # Public technical documentation and media
|-- environment.yml     # Optional Conda development environment
|-- pyproject.toml      # Package metadata and dependencies
`-- main.py             # Compatibility entry point
```

## Contributing and forks

FlowGarden intentionally has no runtime plugin manager or online extension marketplace. The MIT-licensed source and separate shader passes are meant to make experiments and forks straightforward. Contributions that preserve the offline, transparent, and artistically focused nature of the project are welcome; see [Contributing](CONTRIBUTING.md).

## License

FlowGarden is released under the [MIT License](LICENSE).

Academic and educational use can reference the project through [CITATION.cff](CITATION.cff).
