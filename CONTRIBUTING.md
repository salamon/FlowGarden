# Contributing to FlowGarden

Thank you for considering a contribution. FlowGarden is a small, offline, artistic graphics project. Clear experiments and focused improvements are preferred over platform or product complexity.

## Project principles

Contributions to the official repository should preserve these constraints:

- The application runs entirely offline after installation.
- There is no telemetry, analytics, advertising, authentication, or cloud dependency.
- The interface remains immediate and understandable to a non-technical user.
- The rendering pipeline remains readable and useful for graphics experimentation.
- Visual behavior takes priority over claims of physical accuracy.
- New third-party dependencies need a clear technical justification.

FlowGarden does not maintain a runtime plugin API. Experimental features and alternative artistic directions are welcome as forks, and focused improvements can be proposed through pull requests.

## Development setup

Python 3.12 and a GPU supporting OpenGL 4.1 or newer are recommended. Windows is the currently verified development platform; Linux and macOS contributions should describe the tested OS, hardware, and driver.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Run the application:

```powershell
python -m flowgarden
```

Run the built-in GPU smoke test:

```powershell
python -m flowgarden --smoke-test
```

The smoke test requires a working OpenGL context and display environment, even though its window is hidden.

## Proposing a change

Before opening a large pull request, start a GitHub issue describing the visual or technical goal. Keep pull requests focused, explain changes to the render pipeline, and include before-and-after images when visual output changes.

If a contribution changes a numerical pass, document whether it affects stability, performance, appearance, or all three. Do not describe a result as physically accurate without an appropriate model and validation.

By contributing, you agree that your contribution is licensed under the project's MIT License.
