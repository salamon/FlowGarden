# Privacy

FlowGarden is an offline desktop application. Privacy is an architectural constraint, not an optional setting.

## What FlowGarden does not do

The application:

- does not make network requests;
- does not collect telemetry, analytics, diagnostics, or crash reports;
- does not create identifiers, profiles, accounts, or login sessions;
- does not upload images, interaction data, hardware information, or settings;
- does not display advertisements;
- does not check for or install updates automatically; and
- does not depend on a remote service to run.

Mouse and keyboard input are processed in memory to control the current composition. The current version does not persist interaction history.

## Installation and updates

Downloading FlowGarden from GitHub or downloading its Python dependencies requires network access. Those are distribution and development activities, not application runtime behavior.

Updates are manual. FlowGarden will never contact GitHub or another server to determine whether a new version exists.

## Contributions

Changes that introduce networking, telemetry, remote configuration, authentication, advertising, or automatic update checks are outside the project's intended scope and will not be accepted into the official repository.
