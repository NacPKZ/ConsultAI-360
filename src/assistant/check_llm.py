
from .llm import analyse_business


def main():
    scenarios = ("low", "medium", "critical")

    for scenario in scenarios:
        print("\n" + "=" * 60)
        print(f"SCENARIO : {scenario.upper()}")
        print("=" * 60)

        resultat = analyse_business(scenario)

        print(f"\nMODE : {resultat['mode']}")
        print("\nANALYSE :\n")
        print(resultat["reponse"])


if __name__ == "__main__":
    main()
