"""
Point d'entrée du package log_analyzer (compatible avec uv run log-analyzer).
"""

from Storage.main import run_pipeline


def main() -> None:
    run_pipeline()


if __name__ == "__main__":
    main()
