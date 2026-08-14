# Architecture and artistic model

FlowGarden is an interactive GPU artwork built from techniques commonly used in real-time fluid rendering. It is not a scientific fluid solver and does not attempt to reproduce a specific physical material.

## Design intent

The system is designed to produce continuous, controllable, visually coherent motion with a small and inspectable implementation. Parameters are selected by eye for responsiveness and composition rather than derived from physical units or experimental measurements.

Python and GLFW create the window and process input. ModernGL allocates textures and framebuffers and dispatches a full-screen triangle for each pass. All field updates and final shading execute in GLSL fragment shaders.

## GPU fields

The simulation maintains these screen-space textures:

| Field | Channels | Purpose |
|---|---:|---|
| Velocity | 2 | Stylized two-dimensional motion field |
| Pigment | 4 | Relative weights of the four artistic color regions |
| Pressure | 1 | Intermediate relaxation field used for projection |
| Divergence | 1 | Intermediate estimate of velocity divergence |

Velocity, pigment, and pressure use ping-pong texture pairs so each pass reads the previous state while writing the next state.

## Frame pipeline

Each displayed frame runs the following passes:

1. **Velocity update**: semi-Lagrangian backtracing transports the current velocity. A small neighbor blend adds smoothness. Autonomous mode adds a procedural flow field; mouse interaction adds directional or rotational impulses.
2. **Divergence estimate**: centered texture samples estimate the divergence of the velocity field.
3. **Pressure relaxation**: a configurable number of Jacobi-like iterations produces a pressure field.
4. **Velocity projection**: the pressure gradient is subtracted from velocity to reduce visible divergence.
5. **Pigment transport**: the four pigment weights are backtraced through the velocity field and sharpened to preserve distinct color regions.
6. **Artistic rendering**: pigment weights are mapped to a fixed palette and combined with boundary shading, procedural grain, rake-like contours, velocity highlights, and a vignette.

The render passes are ordered by `flowgarden/app.py`; individual equations and style decisions live in `flowgarden/shaders/`.

## Interaction

Autonomous mode continuously injects a procedural force. Switching to zen-garden mode clears existing motion and applies stronger damping, allowing mouse gestures to become the dominant influence:

- Left-drag adds motion along the gesture.
- Right-drag adds a local tangential field.
- The mouse wheel changes the spatial influence radius.

The state exists only in GPU memory for the lifetime of the process.

## Why this is not a physics simulation

FlowGarden borrows numerical ideas associated with incompressible flow, but it deliberately omits the model, calibration, and validation required for physical interpretation:

- Values have no physical units.
- The procedural force is an artistic vector field, not a modeled external force.
- The smoothing term is not a calibrated viscosity model.
- Pressure iterations use a small fixed budget selected for real-time appearance.
- Boundary handling is a visual damping rule rather than a validated material boundary condition.
- Pigment sharpening is a stylistic operation and does not model chemistry, diffusion, surface tension, or multiphase flow.
- The implementation makes no conservation, convergence, or accuracy guarantees.

As a result, images and motion produced by FlowGarden should be described as generative fluid art or an artistic flow simulation, never as a prediction of real fluid or pigment behavior.

## Performance controls

The `--scale` option controls simulation texture resolution relative to the display. Lower values trade spatial detail for speed and memory use. The `--pressure-steps` option changes the number of relaxation iterations; it is exposed primarily for development and performance experiments.

## Extension philosophy

The shader-per-pass structure is the extension surface. Forks can replace procedural forcing, pigment transport, palettes, or final rendering without requiring a plugin loader or network service. The official project keeps this surface source-based so that behavior stays transparent and auditable.
