import unicodedata
import unittest


USER_ID = "test-user-0001"
USERNAME = "Test User"


def valid_event(event_id, created_at, event_key="shared-key"):
    return {
        "schemaVersion": "1.2",
        "eventId": event_id,
        "eventKey": event_key,
        "userId": USER_ID,
        "username": USERNAME,
        "observedAt": "2026-08-11T10:26:51.215Z",
        "createdAt": created_at,
        "source": "qa",
        "topic": "双指针",
        "problem": {"title": "三数之和", "source": "Hot100", "url": ""},
        "evidence": "用户请求讲解三数之和。",
        "outcome": "consulted",
        "tags": ["排序", "双指针", "去重"],
        "confidence": "high",
    }


def is_valid_event(event):
    return (
        event.get("schemaVersion") == "1.2"
        and event.get("userId") == USER_ID
        and event.get("username") == USERNAME
        and bool(event.get("eventId"))
        and bool(event.get("eventKey"))
        and bool(event.get("createdAt"))
    )


def deduplicate_events(events):
    kept_by_key = {}
    diagnostics = []
    for event in sorted(
        (event for event in events if is_valid_event(event)),
        key=lambda event: event["createdAt"],
    ):
        event_key = event["eventKey"]
        if event_key in kept_by_key:
            if "duplicate_event_key" not in diagnostics:
                diagnostics.append("duplicate_event_key")
            continue
        kept_by_key[event_key] = event
    return list(kept_by_key.values()), diagnostics


def rebuild_snapshot(events):
    kept, _ = deduplicate_events(events)
    source_event_keys = [event["eventKey"] for event in kept]
    head_event_id = kept[-1]["eventId"] if kept else None
    current_topic = kept[-1]["topic"] if kept else None
    return {
        "schemaVersion": "1.2",
        "userId": USER_ID,
        "username": USERNAME,
        "generatedAt": "2026-08-11T10:28:00Z",
        "headEventId": head_event_id,
        "sourceEventKeys": source_event_keys,
        "currentTopic": current_topic,
        "topicMastery": {},
        "weaknesses": [],
        "pendingProblemIds": [],
    }


def is_complete_snapshot(snapshot, expected_event_keys):
    return (
        snapshot.get("schemaVersion") == "1.2"
        and snapshot.get("userId") == USER_ID
        and snapshot.get("username") == USERNAME
        and set(snapshot.get("sourceEventKeys", [])) == expected_event_keys
    )


def select_or_rebuild_snapshot(events, snapshots):
    kept, _ = deduplicate_events(events)
    expected_event_keys = {event["eventKey"] for event in kept}
    complete = [
        snapshot
        for snapshot in snapshots
        if is_complete_snapshot(snapshot, expected_event_keys)
    ]
    if complete:
        return max(complete, key=lambda snapshot: snapshot["generatedAt"])
    return rebuild_snapshot(kept)


def normalize_name(raw_name):
    """Names are only normalised mechanically: NFKC plus surrounding whitespace."""
    if not isinstance(raw_name, str):
        return ""
    return unicodedata.normalize("NFKC", raw_name).strip()


def resolve_name_key(raw_name, registrations):
    """Return the single active userId for a name, or stop on ambiguity."""
    name_key = normalize_name(raw_name)
    if not name_key:
        return "invalid_display_name"
    matches = [
        registration
        for registration in registrations
        if normalize_name(registration.get("username")) == name_key
        and registration.get("status") == "active"
    ]
    if len(matches) == 1:
        return matches[0]["userId"]
    if not matches:
        return "user_not_found"
    return "username_conflict"


class AppendOnlyProfileModelTests(unittest.TestCase):
    def test_duplicate_event_key_keeps_only_the_earliest_valid_event(self):
        events = [
            valid_event("e-late", "2026-08-11T10:27:00Z"),
            valid_event("e-early", "2026-08-11T10:26:00Z"),
        ]
        kept, diagnostics = deduplicate_events(events)
        self.assertEqual(["e-early"], [event["eventId"] for event in kept])
        self.assertEqual(["duplicate_event_key"], diagnostics)

    def test_distinct_event_keys_are_both_kept(self):
        events = [
            valid_event("e-one", "2026-08-11T10:26:00Z", "key-one"),
            valid_event("e-two", "2026-08-11T10:27:00Z", "key-two"),
        ]
        kept, diagnostics = deduplicate_events(events)
        self.assertEqual(["e-one", "e-two"], [event["eventId"] for event in kept])
        self.assertEqual([], diagnostics)

    def test_incomplete_snapshot_is_rebuilt_from_all_verified_events(self):
        event_a = valid_event("e-a", "2026-08-11T10:26:00Z", "key-a")
        event_b = valid_event("e-b", "2026-08-11T10:27:00Z", "key-b")
        snapshot_only_for_a = {
            "schemaVersion": "1.2",
            "userId": USER_ID,
            "username": USERNAME,
            "generatedAt": "2026-08-11T10:26:01Z",
            "headEventId": "e-a",
            "sourceEventKeys": ["key-a"],
            "currentTopic": "双指针",
            "topicMastery": {},
            "weaknesses": [],
            "pendingProblemIds": [],
        }
        rebuilt = select_or_rebuild_snapshot([event_a, event_b], [snapshot_only_for_a])
        self.assertEqual({"key-a", "key-b"}, set(rebuilt["sourceEventKeys"]))
        self.assertEqual("e-b", rebuilt["headEventId"])

    def test_invalid_identity_event_is_not_used_for_snapshot(self):
        valid = valid_event("e-valid", "2026-08-11T10:26:00Z", "key-valid")
        invalid = valid_event("e-invalid", "2026-08-11T10:27:00Z", "key-invalid")
        invalid["username"] = "其他用户"
        rebuilt = select_or_rebuild_snapshot([valid, invalid], [])
        self.assertEqual(["key-valid"], rebuilt["sourceEventKeys"])

    def test_duplicate_active_username_is_reported_as_conflict(self):
        registrations = [
            {"userId": USER_ID, "username": USERNAME, "status": "active"},
            {"userId": "different-user", "username": USERNAME, "status": "active"},
        ]
        self.assertEqual("username_conflict", resolve_name_key(USERNAME, registrations))

    def test_name_normalization_is_only_nfkc_and_trim(self):
        self.assertEqual("Ada", normalize_name("  Ａda  "))
        self.assertEqual("Ada", normalize_name("Ada"))
        self.assertEqual("", normalize_name("   "))
        self.assertEqual("", normalize_name(None))

    def test_name_resolution_is_idempotent_across_normalized_forms(self):
        registrations = [{"userId": USER_ID, "username": "乔炳源", "status": "active"}]
        self.assertEqual(USER_ID, resolve_name_key("乔炳源", registrations))
        self.assertEqual(USER_ID, resolve_name_key(" 乔炳源 ", registrations))

    def test_distinct_names_resolve_to_distinct_users(self):
        registrations = [
            {"userId": USER_ID, "username": "张三", "status": "active"},
            {"userId": "different-user", "username": "李四", "status": "active"},
        ]
        self.assertEqual(USER_ID, resolve_name_key("张三", registrations))
        self.assertEqual("different-user", resolve_name_key("李四", registrations))

    def test_unknown_and_blank_names_stop_resolution(self):
        registrations = [{"userId": USER_ID, "username": USERNAME, "status": "active"}]
        self.assertEqual("user_not_found", resolve_name_key("陌生人", registrations))
        self.assertEqual("invalid_display_name", resolve_name_key("", registrations))


if __name__ == "__main__":
    unittest.main()
