"""Server event serialization tests."""

import json

from langchain_core.messages import HumanMessage

from thetable.server.events import event_to_dict


def test_event_to_dict_serializes_nested_human_message():
    event = {
        "event": "on_chain_start",
        "data": {
            "input": {
                "messages": [HumanMessage(content="hello", name="alice")],
            }
        },
    }

    result = event_to_dict(event)
    dumped = json.dumps(result)

    assert "HumanMessage" in dumped
    assert "hello" in dumped
