import argparse
import os
from pathlib import Path

from .bot import SupplyReleaseBot


def main():
    parser = argparse.ArgumentParser(description="Supply Release Bot")
    parser.add_argument("--config", type=str, default=os.path.join(Path(__file__).parent, "config.json"), help="Path to config file")
    args = parser.parse_args()

    bot = SupplyReleaseBot(args.config)
    bot.run()

if __name__ == "__main__":
    main()
