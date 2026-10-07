# Feedback and contributions

Bug reports, clear reproduction steps and feature suggestions are welcome. Search existing issues before opening a new one. Include your SR Inqly version, Windows version, monitor resolution and scaling settings. Remove personal details from screenshots and logs.

Original SR Inqly code is distributed under the custom Source Available license in [LICENSE](LICENSE). Publishing modified builds, rebranded releases or derivative distributions requires prior written permission from Sachin Rathnayaka. Contact the developer before proposing a code contribution or distributing a modified version. Feedback does not change these permissions.

For authorized development, use Python 3.13, install `requirements-dev.txt`, and run `python scripts/run_checks.py --headless`. Native UI checks can be run locally with `python scripts/run_checks.py --all`; they use your Windows desktop, focus and clipboard. Preserve desktop input release, tool-toggle behavior, text-cache correctness and Fetcher undo semantics.
