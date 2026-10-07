# Publish the prepared repository

Repository name: **SR-Inqly**

Suggested description: **A Windows screen annotation workspace with drawing, highlighting, inline text and non-destructive screen captures.**  
Suggested topics: `windows`, `screen-annotation`, `drawing`, `productivity`, `pyside6`, `python`, `screen-capture`, `desktop-app`.

The public repository is `SachinRathnayaka/SR-Inqly`. Version 2.1.1 is a new feature release; publish its prepared assets after pushing the updated source. Preserve the existing 2.0.4 release.

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

## Release 2.1.1

Create a release with tag `v2.1.1`, title **SR Inqly 2.1.1**, and the notes from `docs/release-notes-2.1.1.md`. Upload these as release assets from `dist/`:

| File | Purpose |
| --- | --- |
| `SR.Inqly.Setup.2.1.1.exe` | Per-user Windows installer |
| `SR-Inqly-2.1.1-Windows-Portable.zip` | Extract and run without installation |
| `SR-Inqly-2.1.1-Source.zip` | Organized source snapshot, documentation and assets |
| `SHA256SUMS-2.1.1.txt` | Checksums for these prepared assets |

Binaries belong in Releases, not in the source repository. If assets are rebuilt or signed, regenerate the checksums. Review applicable third-party distribution terms before a commercial release.
