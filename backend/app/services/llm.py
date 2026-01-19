"""LLM service for bot intelligence using Ollama.

This module provides functions to generate intelligent bot responses
using a local Ollama instance with Llama 3.2.
"""

import logging
import os
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

# Ollama configuration - can be overridden by environment variables
OLLAMA_BASE_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "30.0"))


@dataclass
class LLMResponse:
    """Response from the LLM."""

    text: str
    success: bool
    error: str | None = None


@dataclass
class BotSubmissionResult:
    """Result from a bot's LLM-generated submission."""

    tiles: list[str]
    reaction: str | None = None  # Optional chat message if the bot is proud of its answer


async def generate_completion(prompt: str, timeout: float = OLLAMA_TIMEOUT) -> LLMResponse:
    """Generate a completion from Ollama.

    Args:
        prompt: The prompt to send to the model.
        timeout: Request timeout in seconds.

    Returns:
        LLMResponse with the generated text or error.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.9,  # Creative responses
                        "num_predict": 100,  # Limit response length
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            return LLMResponse(text=data.get("response", "").strip(), success=True)
    except httpx.TimeoutException:
        logger.warning("Ollama request timed out")
        return LLMResponse(text="", success=False, error="timeout")
    except httpx.HTTPStatusError as e:
        logger.warning(f"Ollama HTTP error: {e.response.status_code}")
        return LLMResponse(text="", success=False, error=f"http_{e.response.status_code}")
    except httpx.ConnectError:
        logger.debug("Ollama not available (connection refused)")
        return LLMResponse(text="", success=False, error="connection_refused")
    except Exception as e:
        logger.warning(f"Ollama error: {e}")
        return LLMResponse(text="", success=False, error=str(e))


async def check_ollama_health() -> bool:
    """Check if Ollama is running and responsive."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            return response.status_code == 200
    except Exception:
        return False


async def generate_bot_submission(prompt_text: str, available_tiles: list[str]) -> BotSubmissionResult | None:
    """Generate a bot's submission using LLM intelligence.

    Args:
        prompt_text: The game prompt to respond to.
        available_tiles: List of word tiles the bot has available.

    Returns:
        BotSubmissionResult with tiles and optional reaction, or None if LLM unavailable.
    """
    if not available_tiles:
        return None

    tiles_str = ", ".join(f'"{tile}"' for tile in available_tiles)

    llm_prompt = f"""You are playing a party game called "Random Quotes" where you must create \
funny or clever answers using word tiles cut from magazines.

PROMPT: "{prompt_text}"

YOUR AVAILABLE TILES: [{tiles_str}]

RULES:
- Pick 1-5 tiles from your available tiles to form your answer
- Arrange them in an order that makes a funny, clever, or absurd response to the prompt
- You MUST only use tiles from your available tiles list (exact spelling)
- Humor, creativity, and unexpected answers win!

Respond in this exact format:
TILES: word1, word2, word3
RATING: [1-5 stars, where 5 means you think this answer is hilarious]
REACTION: [If 4-5 stars, write a SHORT excited comment about your answer, max 10 words. Otherwise write "none"]

Example response:
TILES: cheese, explosion, why
RATING: 5
REACTION: This one's a winner!"""

    response = await generate_completion(llm_prompt)

    if not response.success or not response.text:
        return None

    # Parse the structured response
    lines = response.text.strip().split("\n")
    tiles_line = None
    rating = 0
    reaction = None

    for line in lines:
        line = line.strip()
        if line.upper().startswith("TILES:"):
            tiles_line = line[6:].strip()
        elif line.upper().startswith("RATING:"):
            rating_text = line[7:].strip()
            # Extract number from rating (handles "5", "5 stars", "5/5", etc.)
            for char in rating_text:
                if char.isdigit():
                    rating = int(char)
                    break
        elif line.upper().startswith("REACTION:"):
            reaction_text = line[9:].strip()
            if reaction_text.lower() not in ("none", "n/a", "-", ""):
                reaction = reaction_text

    if not tiles_line:
        # Fallback: try to parse the whole response as comma-separated tiles
        tiles_line = response.text.strip().split("\n")[0]

    # Parse tiles
    selected_tiles = []
    response_parts = [part.strip().strip('"').strip("'").lower() for part in tiles_line.split(",")]

    # Create lowercase mapping for matching
    tile_map = {tile.lower(): tile for tile in available_tiles}

    for part in response_parts:
        if part in tile_map and tile_map[part] not in selected_tiles:
            selected_tiles.append(tile_map[part])
            if len(selected_tiles) >= 5:
                break

    # Return None if we couldn't parse any valid tiles
    if not selected_tiles:
        return None

    # Only include reaction if rating was 4 or higher
    final_reaction = reaction if rating >= 4 else None

    return BotSubmissionResult(tiles=selected_tiles, reaction=final_reaction)


async def generate_bot_judgment(prompt_text: str, submissions: dict[str, list[str]]) -> str | None:
    """Generate a bot judge's winner selection using LLM intelligence.

    Args:
        prompt_text: The game prompt that was answered.
        submissions: Dict mapping player_id to their list of tiles used.

    Returns:
        The player_id of the chosen winner, or None if LLM unavailable.
    """
    if not submissions:
        return None

    # Format submissions for the prompt
    submissions_text = ""
    player_ids = list(submissions.keys())
    for i, (player_id, tiles) in enumerate(submissions.items(), 1):
        answer = " ".join(tiles)
        submissions_text += f'{i}. "{answer}"\n'

    llm_prompt = f"""You are judging a party game called "Random Quotes" where players \
create funny answers using word tiles.

PROMPT: "{prompt_text}"

SUBMISSIONS:
{submissions_text}
Pick the funniest, most clever, or most creative answer. Consider:
- Humor and wit
- Unexpected or absurd combinations
- How well it answers the prompt (even if silly)

Respond with ONLY the number of your choice (1, 2, 3, etc.). Nothing else."""

    response = await generate_completion(llm_prompt)

    if not response.success or not response.text:
        return None

    # Parse the response - extract the number
    try:
        # Try to find a number in the response
        choice_text = response.text.strip()
        # Handle responses like "1", "1.", "Answer 1", etc.
        for char in choice_text:
            if char.isdigit():
                choice = int(char)
                if 1 <= choice <= len(player_ids):
                    return player_ids[choice - 1]
                break
    except (ValueError, IndexError):
        pass

    return None


async def ensure_model_loaded() -> bool:
    """Ensure the Ollama model is loaded and ready.

    This pulls the model if it's not available.
    Returns True if model is ready, False otherwise.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Check if model exists
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if response.status_code != 200:
                return False

            data = response.json()
            models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]

            if OLLAMA_MODEL not in models and f"{OLLAMA_MODEL}:latest" not in [
                m.get("name", "") for m in data.get("models", [])
            ]:
                # Model not found, try to pull it
                logger.info(f"Pulling Ollama model: {OLLAMA_MODEL}")
                pull_response = await client.post(
                    f"{OLLAMA_BASE_URL}/api/pull",
                    json={"name": OLLAMA_MODEL},
                    timeout=300.0,  # Model download can take a while
                )
                return pull_response.status_code == 200

            return True
    except Exception as e:
        logger.warning(f"Failed to ensure model loaded: {e}")
        return False
