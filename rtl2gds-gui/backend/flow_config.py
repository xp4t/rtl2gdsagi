from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class FlowCommand:
    """One externally configured stage command in an RTL-to-GDS flow."""

    stage: str
    program: str
    arguments: tuple[str, ...] = ()
    stage_number: int | None = None
    description: str = ""
    working_directory: str | None = None
    environment: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
        *,
        base_directory: Path | None = None,
    ) -> "FlowCommand":
        stage = value.get("stage")
        program = value.get("program")
        if not isinstance(stage, str) or not stage.strip():
            raise ValueError("Flow command 'stage' must be a non-empty string")
        if not isinstance(program, str) or not program.strip():
            raise ValueError("Flow command 'program' must be a non-empty string")

        arguments = value.get("arguments", ())
        if not isinstance(arguments, Sequence) or isinstance(arguments, (str, bytes)):
            raise ValueError("Flow command 'arguments' must be a list of strings")
        if not all(isinstance(argument, str) for argument in arguments):
            raise ValueError("Flow command 'arguments' must contain only strings")

        stage_number = value.get("stage_number", value.get("stageNumber"))
        if stage_number is not None and (
            not isinstance(stage_number, int) or isinstance(stage_number, bool) or stage_number < 1
        ):
            raise ValueError("Flow command 'stage_number' must be a positive integer")

        description = value.get("description", "")
        if not isinstance(description, str):
            raise ValueError("Flow command 'description' must be a string")

        working_directory = value.get("working_directory", value.get("workingDirectory"))
        if working_directory is not None and not isinstance(working_directory, str):
            raise ValueError("Flow command 'working_directory' must be a string")
        if working_directory and base_directory:
            directory_path = Path(working_directory)
            if not directory_path.is_absolute():
                working_directory = str((base_directory / directory_path).resolve())

        environment = value.get("environment", {})
        if not isinstance(environment, Mapping) or not all(
            isinstance(key, str) and isinstance(item, str)
            for key, item in environment.items()
        ):
            raise ValueError("Flow command 'environment' must map strings to strings")

        return cls(
            stage=stage.strip(),
            program=program.strip(),
            arguments=tuple(arguments),
            stage_number=stage_number,
            description=description.strip(),
            working_directory=working_directory,
            environment=dict(environment),
        )


@dataclass(frozen=True, slots=True)
class FlowConfiguration:
    """Validated process plan supplied to :class:`FlowRunner`."""

    commands: tuple[FlowCommand, ...] = ()
    total_stages: int = 14

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
        *,
        base_directory: Path | None = None,
    ) -> "FlowConfiguration":
        command_values = value.get("commands", ())
        if not isinstance(command_values, Sequence) or isinstance(command_values, (str, bytes)):
            raise ValueError("Flow configuration 'commands' must be a list")
        if not all(isinstance(command, Mapping) for command in command_values):
            raise ValueError("Each flow command must be an object")

        total_stages = value.get("total_stages", value.get("totalStages", 14))
        if (
            not isinstance(total_stages, int)
            or isinstance(total_stages, bool)
            or total_stages < 1
        ):
            raise ValueError("Flow configuration 'total_stages' must be a positive integer")

        commands = tuple(
            FlowCommand.from_mapping(command, base_directory=base_directory)
            for command in command_values
        )
        for command in commands:
            if command.stage_number is not None and command.stage_number > total_stages:
                raise ValueError(
                    f"Stage number {command.stage_number} exceeds total_stages {total_stages}"
                )
        return cls(commands=commands, total_stages=total_stages)


def load_flow_configuration(path: str | Path) -> FlowConfiguration:
    """Load a flow plan from JSON without introducing command knowledge into QML."""

    config_path = Path(path).expanduser().resolve()
    with config_path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, Mapping):
        raise ValueError("Flow configuration root must be an object")
    return FlowConfiguration.from_mapping(value, base_directory=config_path.parent)
