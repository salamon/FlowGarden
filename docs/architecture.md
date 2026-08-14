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

1. **Velocity update**: semi-Lagrangian backtracing transports the current velocity. A small neighbor blend adds smoothness. Autonomous mode adds a procedural flow field; mouse interaction adds directional or rotational impulses. Inward velocity near a rock is redirected and velocity inside it is cleared.
2. **Divergence estimate**: centered texture samples estimate the divergence of the velocity field.
3. **Pressure relaxation**: a configurable number of Jacobi-like iterations produces a pressure field.
4. **Velocity projection**: the pressure gradient is subtracted from velocity to reduce visible divergence, then rock constraints are applied again so projection cannot reintroduce motion inside an obstacle.
5. **Pigment transport**: the four pigment weights are backtraced through the velocity field and sharpened to preserve distinct color regions. Backtraces that land inside a rock are rejected.
6. **Artistic rendering**: pigment weights are mapped to one of five selectable palettes and combined with boundary shading, procedural grain, rake-like contours, velocity highlights, a vignette, and shaded rocks.

The render passes are ordered by `flowgarden/app.py`; individual equations and style decisions live in `flowgarden/shaders/`.

## Numerical model and artistic approximations

This section records the discrete operations implemented by the shaders. It is a description of the artwork's computation, not a derivation of a physical fluid model.

Let $\mathbf{x}=(x,y)$ be normalized texture coordinates, $\mathbf{h}=(1/W,1/H)$ one texel, $\mathbf{u}$ the two-channel velocity field, $p$ pressure, $d$ divergence, and $\mathbf{c}$ the four pigment weights. Texture lookups are bilinearly filtered. The frame time step is clamped to

$$
1/240 \leq \Delta t \leq 1/30.
$$

### Velocity transport and forcing

The velocity pass uses a semi-Lagrangian backtrace:

$$
\mathbf{x}_b = \operatorname{clamp}(\mathbf{x}-\Delta t\,\mathbf{u}^n(\mathbf{x}),\mathbf{h},1-\mathbf{h}),
\qquad
\widetilde{\mathbf{u}}=\mathbf{u}^n(\mathbf{x}_b).
$$

It then blends the transported value with its four axial neighbors. With $\alpha=\min(0.12,4\Delta t)$ and $\mathcal{N}$ denoting those samples,

$$
\mathbf{u}_a=(1-\alpha)\widetilde{\mathbf{u}}+\frac{\alpha}{4}\sum_{q\in\mathcal{N}}\mathbf{u}^n(q).
$$

Autonomous mode adds the analytic procedural field $\mathbf{f}(\mathbf{x},t)$ defined in [`velocity.frag`](../flowgarden/shaders/velocity.frag), then applies exponential damping:

$$
\mathbf{u}^{*}=(\mathbf{u}_a+0.055\,\Delta t\,\mathbf{f})e^{-0.34\Delta t}.
$$

Zen-garden mode injects no autonomous field and uses the stronger damping $\mathbf{u}^{*}=\mathbf{u}_a e^{-8\Delta t}$. Mouse impulses and rock constraints are applied afterward. Velocity is finally tapered near the canvas boundary and clamped component-wise to $[-1.2,1.2]$.

### Divergence and pressure projection

The divergence shader uses centered neighbor differences in grid-scaled coordinates:

$$
d_{i,j}=\frac{1}{2}\left[
(u^x_{i+1,j}-u^x_{i-1,j})+
(u^y_{i,j+1}-u^y_{i,j-1})
\right].
$$

Pressure is reset to zero each frame. A small fixed-budget Jacobi-like relaxation, 14 iterations by default, applies

$$
p^{k+1}_{i,j}=\frac{1}{4}\left(
p^k_{i-1,j}+p^k_{i+1,j}+p^k_{i,j-1}+p^k_{i,j+1}-d_{i,j}
\right).
$$

The projection pass subtracts the corresponding centered pressure difference:

$$
\mathbf{u}^{n+1}_{i,j}=\mathbf{u}^{*}_{i,j}
-\frac{1}{2}
\begin{pmatrix}
p_{i+1,j}-p_{i-1,j}\\
p_{i,j+1}-p_{i,j-1}
\end{pmatrix}.
$$

These operators intentionally omit a conversion to physical grid spacing. The projection is a visual divergence-reduction step and the fixed iteration count is not a convergence criterion.

### Pigment transport

Each pigment channel follows the projected velocity using the same backtrace. If the traced position lies inside a rock, the shader samples the current position instead. The sampled weights are sharpened and normalized:

$$
\widehat{c}_m=\max(c_m,10^{-5})^{1.035},
\qquad
c'_m=\frac{\widehat{c}_m}{\sum_{r=1}^{4}\widehat{c}_r}.
$$

Normalization keeps the four channels interpretable as relative palette weights. The exponent deliberately counteracts numerical blending and is not a material-mixing law.

### Implicit rocks

For a rock centered at $\mathbf{x}_c$, the fragment position is aspect-corrected and rotated into local coordinates. Its signed boundary estimate is

$$
\rho(\mathbf{x})=
\left\|
\frac{R(-\phi)\left((a(x-x_c),y-y_c)\right)}
{(r_x,r_y)I(\theta)}
\right\|-1,
$$

where $a$ is the canvas aspect ratio and the procedural silhouette perturbation is

$$
I(\theta)=1+0.065\sin(3\theta+2\pi s)+0.035\sin(5\theta-3\pi s/2).
$$

Velocity is cleared where $\rho<0$. Within a narrow exterior band, only inward motion is redirected using the approximate ellipse normal. This constraint is repeated after projection so the pressure pass cannot restore motion inside the rock. No momentum is transferred to the rock.

## Interaction

Autonomous mode continuously injects a procedural force. Switching to zen-garden mode clears existing motion and applies stronger damping, allowing mouse gestures to become the dominant influence:

- Left-drag adds motion along the gesture.
- Right-drag adds a local tangential field.
- The mouse wheel changes the spatial influence radius.

The state exists only in GPU memory for the lifetime of the process.

Re-seeding creates a new procedural starting arrangement and clears the velocity and pressure fields. Palette changes affect only the final color mapping, so they can be made without interrupting the current motion.

The on-screen help is a static 5×7 bitmap generated in memory by the Python host and composited as a translucent panel in the final shader. It does not load a system font, UI toolkit, or external asset.

Fullscreen uses the selected monitor's current video mode with GLFW auto-iconification disabled. This keeps the composition fullscreen on a secondary monitor when another application receives focus on the primary monitor. The window is not floating or always-on-top.

## Rocks and obstacle response

Up to eight rocks are stored as a small CPU-side list and sent to the relevant shaders as uniform arrays. Each rock is a rotated ellipse with a procedural boundary perturbation, producing varied positions, sizes, orientations, and silhouettes without meshes or asset files.

The velocity and projection passes clear motion inside a rock and reflect the inward component within a narrow boundary band. Pigment advection rejects samples whose backtraced position falls inside a rock. The render pass draws a compact shaded stone and shadow from the same implicit shape, so interaction, collision, and appearance remain aligned.

Left-dragging performs a CPU-side hit test against the ellipse and updates its center. When no rock is hit, the same gesture continues to comb the pigment fields. This deliberately avoids a separate editing mode or tool system.

## Why this is not a physics simulation

FlowGarden borrows numerical ideas associated with incompressible flow, but it deliberately omits the model, calibration, and validation required for physical interpretation:

| Operation | Numerical or artistic choice | Consequence |
|---|---|---|
| Velocity advection | Semi-Lagrangian backtrace | Stable and smooth for interactive use, but numerically dissipative |
| Neighbor blend | Fixed screen-space smoothing | Improves visual continuity but is not calibrated viscosity |
| Autonomous forcing | Analytic, time-varying vector field | Directs the composition rather than representing a measured force |
| Pressure projection | Grid-scaled differences and a small fixed Jacobi budget | Reduces visible divergence without convergence or accuracy guarantees |
| Canvas boundaries | Tapering and component clearing | Contains the artwork but is not a validated material boundary condition |
| Pigment sharpening | Nonlinear channel adjustment and normalization | Preserves color regions but does not model chemistry, diffusion, surface tension, or multiphase flow |
| Rock response | Local clearing and redirection | Suggests collision without a solid-fluid coupling model or momentum transfer |

Field values and coefficients have no calibrated physical units and are selected by eye; wall-clock seconds only parameterize the animation. The implementation makes no conservation, convergence, stability-range, or accuracy guarantees.

As a result, images and motion produced by FlowGarden should be described as generative fluid art or an artistic flow simulation, never as a prediction of real fluid or pigment behavior.

## Performance controls

The `--scale` option controls simulation texture resolution relative to the display. Lower values trade spatial detail for speed and memory use. The `--pressure-steps` option changes the number of relaxation iterations; it is exposed primarily for development and performance experiments.

## Extension philosophy

The shader-per-pass structure is the extension surface. Forks can replace procedural forcing, pigment transport, palettes, or final rendering without requiring a plugin loader or network service. The official project keeps this surface source-based so that behavior stays transparent and auditable.
