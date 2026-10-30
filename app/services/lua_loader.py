"""Reads the Lua scripts that Redis runs atomically."""

from pathlib import Path

# The folder that holds all the .lua files, next to this file.
LUA_FOLDER = Path(__file__).parent / "lua"


def load_lua_script(script_name: str) -> str:
    """Return the text of `lua/<script_name>.lua`."""
    return (LUA_FOLDER / f"{script_name}.lua").read_text()
