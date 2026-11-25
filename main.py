import os
from pathlib import Path
import sys
import zipfile

from view import App


def prepare_tk():
    source = Path(sys.base_prefix) / "tcl"
    target = Path(__file__).resolve().parent / "venv" / "tcl-runtime"
    for library, variable, marker in (
        ("tcl", "TCL_LIBRARY", "init.tcl"),
        ("tk", "TK_LIBRARY", "tk.tcl"),
    ):
        archives = sorted(source.glob(f"lib{library}*.zip"))
        if os.name != "nt" or variable in os.environ or not archives:
            continue
        folder = target / f"{library}_library"
        if not (folder / marker).exists():
            with zipfile.ZipFile(archives[-1]) as archive:
                archive.extractall(target)
        os.environ[variable] = str(folder)


def main():
    prepare_tk()
    App().run()


if __name__ == "__main__":
    main()
