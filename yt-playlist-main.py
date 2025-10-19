from ytplaylist import main


if __name__ == "__main__":
    # Keep working directory consistent with original script behaviour
    import os
    import sys

    os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
    # Ensure UTF-8 on Windows
    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore
        except Exception:
            pass

    main()