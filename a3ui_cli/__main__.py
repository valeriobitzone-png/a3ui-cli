from __future__ import annotations

import argparse
import sys

from .render import load_and_render


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="a3ui_cli")
    commands = parser.add_subparsers(dest="command", required=True)
    render = commands.add_parser("render", help="render one surface JSON as text")
    render.add_argument("surface", help="path to a surface JSON object")
    args = parser.parse_args(argv)
    if args.command == "render":
        try:
            print(load_and_render(args.surface))
        except (OSError, ValueError) as error:
            print(f"reject: {error}", file=sys.stderr)
            return 1
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
