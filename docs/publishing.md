# Publish the prepared repository

Repository name: **SR-Inqly**

Suggested description: **A Windows screen annotation workspace with drawing, highlighting, inline text and non-destructive screen captures.**  
Suggested topics: `windows`, `screen-annotation`, `drawing`, `productivity`, `pyside6`, `python`, `screen-capture`, `desktop-app`.

The public repository is `SachinRathnayaka/SR-Inqly`. Version 2.1.2 is an audit and reliability release; publish its prepared assets after pushing the updated source. Preserve existing release tags. Version 2.1.2 should use a new `v2.1.2` tag.

## Repository

Open the existing **SR-Inqly** repository in GitHub Desktop, commit the updated source if needed and select **Push origin**. For an existing Git checkout:

```powershell
git status --short
git push origin main
```

Before `git add .`, verify that `.gitignore` is present. The prepared folder's `build/` and `dist/` output is ignored. Never commit signing credentials, private keys or private desktop screenshots.

For GitHub's browser upload, use the source ZIP and upload its contents so `README.md` is at the repository root. Avoid uploading the outer `sr-inqly` directory as a nested folder. Git's upload preserves dotfiles and folders more reliably.

## Repository settings

- Add the description and topics above.
- Set the default branch to `main`.
- Enable Issues and optionally private vulnerability reporting.
- The `Renderer checks` workflow runs after publishing; the prepared source has local checks but no remote CI success is claimed beforehand.
- Social preview: use `docs/images/banner.png` if GitHub accepts its size; crop/export a copy if the upload UI requests a different aspect ratio.
- Keep the custom **Source Available** license. Do not select an unrelated MIT/GPL license for original application code.

## Release 2.1.2

Create a release with tag `v2.1.2`, title **SR Inqly 2.1.2**, and the notes from `docs/release-notes-2.1.2.md`. Upload these as release assets from `dist/`:

| File | Purpose |
| --- | --- |
| `SR.Inqly.Setup.2.1.2.exe` | Per-user Windows installer |
| `SR-Inqly-2.1.2-Windows-Portable.zip` | Extract and run without installation |
| `SR-Inqly-2.1.2-Source.zip` | Organized source snapshot, documentation and assets |
| `SHA256SUMS-2.1.2.txt` | Checksums for these prepared assets |

Binaries belong in Releases, not in the source repository. If assets are rebuilt or signed, regenerate the checksums. Review applicable third-party distribution terms before a commercial release.

## Correct the existing 2.1.1 checksum

The public 2.1.1 portable ZIP differed from its SHA-256 entry during the October 7 audit. The installer and source entries matched. Replace only the old release checksum asset with a checksum generated from all three actual public download files; do not reuse a checksum from a differently compressed local ZIP. New 2.1.2 packaging verifies all assets before upload.
