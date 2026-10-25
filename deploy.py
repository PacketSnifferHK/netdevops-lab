"""Push the rendered configs to the live lab with NAPALM (merge + commit).

    python deploy.py --check     # dry run: show the diff, change nothing
    python deploy.py             # apply the changes

Run render_configs.py first so rendered/ is up to date.
"""
import argparse
from pathlib import Path

from nornir import InitNornir
from nornir.core.task import Task
from nornir_napalm.plugins.tasks import napalm_configure
from nornir_utils.plugins.functions import print_result

RENDERED = Path("rendered")


def push(task: Task, dry_run: bool):
    cfg = (RENDERED / f"{task.host.name}.cfg").read_text()
    # replace=False -> merge the service config into the running config.
    task.run(task=napalm_configure, configuration=cfg, replace=False, dry_run=dry_run)


def main() -> None:
    ap = argparse.ArgumentParser(description="Deploy configs to the lab")
    ap.add_argument("--check", action="store_true", help="dry run (diff only)")
    args = ap.parse_args()

    nr = InitNornir(config_file="config.yaml")
    result = nr.run(task=push, dry_run=args.check)
    print_result(result)

    if args.check:
        print("\n(dry run — nothing was changed. Drop --check to apply.)")


if __name__ == "__main__":
    main()
