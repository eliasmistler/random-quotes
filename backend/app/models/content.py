"""Game content configuration model for loading from YAML."""

from pathlib import Path

import yaml
from pydantic import BaseModel


class GameContentConfig(BaseModel):
    """Configuration for game prompts and word tiles."""

    prompts: list[str]
    words: list[str]


def load_game_content(path: Path | None = None) -> GameContentConfig:
    """Load game content configuration from a YAML file."""
    if path is None:
        path = Path(__file__).parent.parent / "game_config.yaml"

    with open(path) as f:
        data = yaml.safe_load(f)

    return GameContentConfig.model_validate(data)
