import sys

if len(sys.argv) > 1:
    from .cli import main
    sys.exit(main(sys.argv[1:]))
else:
    from .gui import main
    sys.exit(main())
