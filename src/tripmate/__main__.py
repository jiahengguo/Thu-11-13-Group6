"""Offline B01 inspection and contract-example validation."""
import argparse
import json
from pathlib import Path

from tripmate.contracts import ContractError, SCHEMA_NAMES, validate
from tripmate.orchestrator import build_agents


def main() -> None:
    parser = argparse.ArgumentParser(description="TripMate AI B01 framework")
    parser.add_argument("--validate-examples", type=Path, metavar="DIRECTORY")
    args = parser.parse_args()
    if args.validate_examples:
        examples = sorted(args.validate_examples.glob("*.json"))
        if not examples:
            parser.error("No JSON examples found")
        for path in examples:
            name = path.name.split(".")[0]
            try:
                validate(name, json.loads(path.read_text()))
            except (ContractError, ValueError) as error:
                parser.exit(1, f"FAIL {path.name}: {error}\n")
            print(f"PASS {path.name}")
        print(f"Validated {len(examples)} examples. Business feasibility was not evaluated.")
        return
    print("TripMate AI | B01 framework | STUB mode | no LLM/database/web execution")
    for agent in build_agents().values():
        print(f"{agent.agent_id}: {agent.owner}")
    print("Contracts: " + ", ".join(SCHEMA_NAMES))


if __name__ == "__main__":
    main()
