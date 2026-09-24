# AI Passport Content Repository

This repository is the public, versioned content origin for AI Passport.
GitHub Pages serves the parent-facing landing page, `themes.json` publishes
available learning themes, and each theme keeps its metadata and assets under
`themes/<theme-id>/`. Versioned courses live under `courses/v<version>/`.
The v2 catalogue supplies a SHA-256 digest for each course. The device needs
to validate that digest before presenting downloaded content; device-side
remote loading is a separate firmware feature from publishing the JSON files.
`device-catalog.json` is the compact device-facing projection of `themes.json`;
both must carry identical course paths and digests for each theme.

No database or server runtime is required. Git versioning is the source of
truth; JSON files form the device content contract.

## Browser firmware updates

`firmware/release.json` is the allow-listed release contract used by the
Device Center. Each safe update lists only bootloader, partition-table, and
application segments, including their ESP32-C3 offsets and SHA-256 digests.
It deliberately omits NVS, so saved Wi-Fi credentials are retained.

Before opening the serial port, the Device Center verifies each downloaded
segment in the browser. It writes only the offsets declared by the selected
release. A future factory-reset package must be a separate, clearly labelled,
second-confirmation flow; the safe-update path must never select it.

The repository initially carries a checked firmware release. Continuous
firmware publication belongs to the firmware repository: once build and image
verification pass, its release workflow can update this manifest using a
repository-scoped deployment credential.
