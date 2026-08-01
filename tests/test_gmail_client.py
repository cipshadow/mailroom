"""fetch_labelled_messages pagination: limit 0 must walk every page."""

from kindle_mailroom.core import gmail_client as gc


class _FakeExecute:
    def __init__(self, response):
        self._response = response

    def execute(self):
        return self._response


class _FakeMessages:
    """Serves labelled refs in pages of `page_size`, plus full messages."""

    def __init__(self, total, page_size):
        self._ids = [f"m{i}" for i in range(total)]
        self._page_size = page_size
        self.list_calls = []

    def list(self, userId, labelIds, maxResults, pageToken=None):
        self.list_calls.append({"maxResults": maxResults, "pageToken": pageToken})
        start = int(pageToken or 0)
        end = min(start + min(maxResults, self._page_size), len(self._ids))
        response = {"messages": [{"id": mid} for mid in self._ids[start:end]]}
        if end < len(self._ids):
            response["nextPageToken"] = str(end)
        return _FakeExecute(response)

    def get(self, userId, id, format):
        return _FakeExecute({
            "id": id,
            "threadId": f"t-{id}",
            "payload": {"headers": [
                {"name": "Subject", "value": f"Subject {id}"},
                {"name": "From", "value": "News <n@example.com>"},
            ]},
        })


class _FakeService:
    def __init__(self, messages):
        self._messages = messages

    def users(self):
        return self

    def messages(self):
        return self._messages

    def labels(self):
        return self

    def list(self, userId):
        return _FakeExecute({"labels": [{"id": "L1", "name": "Mailroom/Send next 📤"}]})


def test_limit_zero_pages_through_everything():
    fake = _FakeMessages(total=120, page_size=50)
    service = _FakeService(fake)
    messages = gc.fetch_labelled_messages(service, "Mailroom/Send next 📤",
                                          limit=0, unread_only=False)
    assert len(messages) == 120
    assert len(fake.list_calls) == 3  # 50 + 50 + 20
    assert messages[0].subject == "Subject m0"


def test_positive_limit_stops_early():
    fake = _FakeMessages(total=120, page_size=50)
    service = _FakeService(fake)
    messages = gc.fetch_labelled_messages(service, "Mailroom/Send next 📤",
                                          limit=60, unread_only=False)
    assert len(messages) == 60
    assert len(fake.list_calls) == 2  # 50, then 10 more — never over-fetches
    assert fake.list_calls[1]["maxResults"] == 10
