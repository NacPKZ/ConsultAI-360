"""Run: python -m src.assistant.check_connection"""

from dotenv import load_dotenv

from .kpi import delivery, overview


def main():
    load_dotenv()
    for fn in (overview, delivery):
        print(fn.__name__, fn("medium"))


if __name__ == "__main__":
    main()
