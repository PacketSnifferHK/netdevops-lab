"""Pull the running config off every device and save it under backups/.

    python backup.py

Handy on its own, and the first half of drift detection: diff these
backups against rendered/ to see if anyone changed a device by hand.
"""
from pathlib import Path

from nornir import InitNornir
from nornir.core.task import Task
from nornir_napalm.plugins.tasks import napalm_get

BACKUPS = Path("backups")


def backup(task: Task):
    r = task.run(task=napalm_get, getters=["config"])
    running = r.result["config"]["running"]
    (BACKUPS / f"{task.host.name}.cfg").write_text(running)


def main() -> None:
    BACKUPS.mkdir(exist_ok=True)
    nr = InitNornir(config_file="config.yaml")
    nr.run(task=backup)
    print(f"Running configs saved to {BACKUPS}/")


if __name__ == "__main__":
    main()
