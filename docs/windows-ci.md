# Windows checks

The Windows workflow runs on pull requests, pushes to Main and manual dispatch.
It installs requirements with Python 3.11, runs the selected tests, builds from
AgeOfDuck.spec, and checks every spec-declared resource against its source bytes.
The resulting onedir package is kept as an Actions artifact for seven days.

The initial test list is explicit: bundle integrity, screen placement, HUD
regions, civilisation coverage and the technology-tree catalog. These use
resources already published in the repository. Full unittest discovery also
finds tests requiring unpublished screenshots or private profile captures and
is deliberately not used. Add the provider tests after synthetic fixtures are
merged, and updater/packaging regression tests after their respective changes.

For a local build, run:

```bat
python -m unittest -v test_bundle test_screen_placement test_hud_regions test_civ_coverage test_techtree_catalog
python -m PyInstaller --noconfirm --clean AgeOfDuck.spec
python scripts/check_bundle.py dist/AgeOfDuck
```

These checks do not launch the application or the game, compile the Inno Setup
installer, validate focus behaviour in a match, sign a release or publish one.
Before releasing, manually test the downloaded package and installer on Windows.
Fork pull requests may require a maintainer to approve the Actions run.
