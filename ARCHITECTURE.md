# AI Passport Content Repository

This repository is the public, versioned content origin for AI Passport.
GitHub Pages serves the parent-facing landing page, `themes.json` publishes
available learning themes, and each theme keeps its metadata and assets under
`themes/<theme-id>/`. Device firmware retains a small offline starter lesson
and only loads verified remote content when a network connection is available.

No database or server runtime is required. Git versioning is the source of
truth; JSON files form the device content contract.
