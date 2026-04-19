#!/usr/bin/env python3
"""Seed the Default deck with 10 sample flashcards via AnkiConnect."""

from einki._anki_client import AnkiClient

CARDS = [
    ("What is the capital of France?", "Paris"),
    ("What is the chemical symbol for water?", "H₂O"),
    ("Who wrote 'Hamlet'?", "William Shakespeare"),
    ("What is the speed of light?", "Approx. 3 x 10^8 m/s"),
    ("What planet is known as the Red Planet?", "Mars"),
    ("What is the powerhouse of the cell?", "The mitochondria"),
    ("In what year did World War II end?", "1945"),
    ("What is the square root of 144?", "12"),
    ("What gas do plants absorb from the atmosphere?", "Carbon dioxide (CO₂)"),
    ("Who painted the Mona Lisa?", "Leonardo da Vinci"),
]


def main() -> None:
    """Add sample notes to the Default deck."""
    client = AnkiClient()

    for front, back in CARDS:
        client._invoke(  # noqa: SLF001
            "addNote",
            note={
                "deckName": "Default",
                "modelName": "Basic",
                "fields": {"Front": front, "Back": back},
                "options": {"allowDuplicate": True},
            },
        )
        print(f"Added: {front}")

    print(f"\nDone — added {len(CARDS)} cards to Default deck.")
    print(f"Total cards: {client.count_cards('Default')}")


if __name__ == "__main__":
    main()
