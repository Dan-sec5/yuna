from .voice import hablar, escuchar
from .cli import main as cli_main
from .agent_cli import main as agent_main
from .avatar import main as avatar_main

__all__ = ["hablar", "escuchar", "cli_main", "agent_main", "avatar_main"]
