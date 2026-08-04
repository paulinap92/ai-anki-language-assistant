from src.anki.client import AnkiClient


class FakeAnkiClient(AnkiClient):
    def __init__(self):
        super().__init__("http://localhost:8765", "Default")
        self.calls = []

    def _invoke(self, action, params=None):
        self.calls.append((action, params or {}))
        if action == "findNotes":
            return [1, 2]
        if action == "notesInfo":
            return [
                {
                    "noteId": 1,
                    "modelName": "AI Vocabulary Light Card",
                    "tags": [],
                    "fields": {
                        "Word": {"value": "dar cuenta de"},
                        "Example": {"value": "El informe da cuenta de los avances."},
                    },
                },
                {
                    "noteId": 2,
                    "modelName": "Basic",
                    "tags": [],
                    "fields": {
                        "Front": {"value": "aunar"},
                        "Back": {"value": "połączyć"},
                    },
                },
            ]
        raise AssertionError(action)


def test_list_notes_for_conversation_reads_selected_deck_without_changing_active_deck():
    client = FakeAnkiClient()

    notes = client.list_notes_for_conversation('Spanish::C1')

    assert [note["word"] for note in notes] == ["dar cuenta de", "aunar"]
    assert client.deck_name == "Default"
    assert client.calls[0] == (
        "findNotes",
        {"query": 'deck:"Spanish::C1"'},
    )
