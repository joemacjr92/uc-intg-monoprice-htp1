# Hosted BEQ catalogue

The Remote no longer downloads the upstream 39 MB catalogue JSON at startup.
A scheduled GitHub Actions workflow fetches the upstream database, validates
and transforms it, and publishes a compact static dataset to GitHub Pages.

The hosted layout is versioned:

- `beq/manifest.json` points to an immutable version directory.
- `beq/<version>/index.json` contains only the media ID, original title, author, year, audio types, and compact integer category offsets. Search matches the original title; the display name is constructed from title and author so different authors’ versions remain distinguishable. Category offsets avoid storing category labels redundantly on every entry.
- `beq/<version>/entries/<id>.json` contains only the filter data needed to
  apply that selected BEQ.
- `beq/filterless-entries.txt` and `beq/filterless-entries.json` are
  downloadable reports of upstream records with no filters. These records are
  excluded from the Remote browse/search index and are not published as entry
  payloads, because they cannot be applied to the HTP-1.

The integration verifies the index SHA-256 before using it and fetches an
individual entry only when selected. It keeps a bounded 12-entry in-memory
LRU cache. Browse and search never download filter payloads. The integration
does not prefetch the catalogue on connection.

## Publishing

The `Publish BEQ catalogue` workflow runs daily and can be started manually.
The `actions/configure-pages` step provisions/configures the Pages site for
GitHub Actions deployment. The workflow deploys generated static files; Pages
itself does not execute refresh logic.

The manifest is published with the immutable versioned data in the same Pages
deployment, so clients cannot combine an index and entry files from different
catalogue versions. A failed fetch, validation, or transform prevents deployment.

## Upstream data and attribution

The generated data is derived from the BEQCatalogue database and BEQ filter
records maintained by Matt Khan in:

- https://github.com/3ll3d00d/beqcatalogue
- https://github.com/3ll3d00d/beqfilters

Both upstream projects provide MIT license notices. The publishing workflow
copies those notices alongside the generated catalogue. The integration's
own source code remains under its existing MPL-2.0 license.
