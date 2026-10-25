"""Ask the network questions in plain English.

A small local-LLM assistant (Ollama + Instructor) that:
  1. turns your question into a single read-only 'show' command + target device,
  2. runs it against the live lab (read-only — non-'show' commands are refused),
  3. explains the output back to you in plain English.

    python ai/ask_network.py "is OSPF up between the cores?"
    python ai/ask_network.py "what VLANs are on acc1?"

Needs Ollama running with a model pulled (default: gemma3:4b).
This reuses the exact pattern from my ai-car-dealer project: a local model
forced into structured output with Instructor/Pydantic.
"""
import sys
import yaml
from pydantic import BaseModel, Field
from openai import OpenAI
import instructor
from napalm import get_network_driver

MODEL = "gemma3:4b"
HOSTS = yaml.safe_load(open("inventory/hosts.yaml"))
DEFAULTS = yaml.safe_load(open("inventory/defaults.yaml"))
DEVICES = list(HOSTS)

# Structured client (command selection) + plain client (explanation).
_openai = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
structured = instructor.from_openai(_openai, mode=instructor.Mode.JSON)


class NetQuery(BaseModel):
    device: str = Field(description=f"the device to query, one of: {DEVICES}")
    command: str = Field(description="ONE read-only Arista EOS 'show' command that answers the question")


def run_show(device: str, command: str) -> str:
    if device not in HOSTS:
        raise ValueError(f"unknown device '{device}'")
    if not command.strip().lower().startswith("show"):
        raise ValueError(f"refusing non-read-only command: '{command}'")
    h = HOSTS[device]
    drv = get_network_driver("eos")
    dev = drv(
        hostname=h["hostname"],
        username=DEFAULTS["username"],
        password=DEFAULTS["password"],
        optional_args={"transport": "https"},
    )
    dev.open()
    try:
        return dev.cli([command])[command]
    finally:
        dev.close()


def ask(question: str) -> None:
    plan = structured.chat.completions.create(
        model=MODEL,
        response_model=NetQuery,
        messages=[
            {
                "role": "system",
                "content": (
                    "You help operate an Arista EOS lab with devices "
                    f"{DEVICES}. core1/core2 are L3 (OSPF, SVIs); acc1/acc2 are "
                    "L2 access switches. Pick ONE device and ONE read-only "
                    "'show' command that best answers the question."
                ),
            },
            {"role": "user", "content": question},
        ],
    )
    print(f"\n→ running '{plan.command}' on {plan.device}\n")
    output = run_show(plan.device, plan.command)

    summary = _openai.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a network engineer. Explain this device output "
                "clearly and briefly to answer the user's question. Call out anything "
                "that looks wrong.",
            },
            {"role": "user", "content": f"Question: {question}\n\nOutput:\n{output}"},
        ],
    )
    print(summary.choices[0].message.content)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python ai/ask_network.py "your question about the network"')
        sys.exit(1)
    ask(" ".join(sys.argv[1:]))
