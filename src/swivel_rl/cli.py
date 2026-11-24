from __future__ import annotations

import argparse
import json
import sys

from .app import SwivelApp
from .config import Config, load_config, save_config
from .ui import run_ui
from .win32_input import list_mouse_devices


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swivel-rl",
        description="Translate physical mouse movement into Rocket League camera swivel input.",
    )
    parser.add_argument("--config", help="Path to a JSON configuration file")
    parser.add_argument("--write-default", help="Write the default configuration to this path and exit")
    parser.add_argument("--list-devices", action="store_true", help="List raw input mouse devices and exit")
    parser.add_argument("--ui", action="store_true", help="Open the configuration and control window")
    parser.add_argument("--log-file", help="Append diagnostic logs to this file")
    parser.add_argument(
        "--backend",
        choices=("dry_run", "sendinput_keyboard"),
        help="Override the configured input backend",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.write_default:
        save_config(Config(), args.write_default)
        print(args.write_default)
        return 0

    if args.list_devices:
        for index, device in enumerate(list_mouse_devices()):
            print(f"{index}: handle={_handle_value(device['handle'])} path={device['path']}")
        return 0

    config = load_config(args.config)
    if args.backend:
        config.backend = args.backend
    if args.ui:
        return run_ui(config, args.config)
    return SwivelApp(config, log_file=args.log_file).run()


def _handle_value(value: object) -> int:
    return int(getattr(value, "value", value) or 0)


if __name__ == "__main__":
    sys.exit(main())
