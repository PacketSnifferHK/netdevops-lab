"""Render each device's config from inventory data + the Jinja2 template.

This needs NO devices and NO lab running — it just turns the source-of-truth
(inventory/hosts.yaml) into real EOS config under rendered/. That makes it
perfect to run in CI as a fast "did I break the config?" check.

    python render_configs.py
"""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from nornir import InitNornir

RENDERED = Path("rendered")


def main() -> None:
    nr = InitNornir(config_file="config.yaml")
    env = Environment(
        loader=FileSystemLoader("templates/eos"),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("full_config.j2")

    RENDERED.mkdir(exist_ok=True)
    for name, host in nr.inventory.hosts.items():
        cfg = template.render(host_name=name, d=host.data)
        out = RENDERED / f"{name}.cfg"
        out.write_text(cfg)
        print(f"  rendered {out}")

    print(f"\nDone — {len(nr.inventory.hosts)} configs written to {RENDERED}/")


if __name__ == "__main__":
    main()
