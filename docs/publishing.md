# Publish the prepared repository

Suggested name: **sr-inqly**  
Suggested description: **A Windows screen annotation workspace with drawing, highlighting, inline text and non-destructive screen captures.**  
Suggested topics: `windows`, `screen-annotation`, `drawing`, `productivity`, `pyside6`, `python`, `screen-capture`, `desktop-app`.

The source is prepared for `SachinRathnayaka/sr-inqly`. These instructions do not imply that a remote repository or release already exists.

## Repository

1. Create a new **public** GitHub repository named `sr-inqly`.
2. When using Git, leave GitHub's automatic README/license/gitignore creation unchecked because these files are already supplied.
3. Open a terminal in the prepared `sr-inqly` folder and run:

```powershell
git init -b main
git add .
git status --short
git commit -m "Prepare SR Inqly 2.0.4 public source repository"
git remote add origin https://github.com/SachinRathnayaka/sr-inqly.git
git push -u origin main
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

## Release 2.0.4

Create a release with tag `v2.0.4`, title **SR Inqly 2.0.4**, and the notes from `docs/release-notes-2.0.4.md`. Upload these as release assets from `dist/`:

| File | Purpose |
| --- | --- |
| `SR Inqly Setup 2.0.4.exe` | Per-user Windows installer |
| `SR-Inqly-2.0.4-Windows-Portable.zip` | Extract and run without installation |
| `SR-Inqly-2.0.4-Source.zip` | Organized source snapshot, documentation and assets |
| `SHA256SUMS-2.0.4.txt` | Checksums for these prepared assets |

Binaries belong in Releases, not in the source repository. If assets are rebuilt or signed, regenerate the checksums. Review applicable third-party distribution terms before a commercial release.
