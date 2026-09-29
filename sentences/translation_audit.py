"""Track which English/Traditional Chinese sentence pairs were reviewed."""

import hashlib
import json


REVIEW_FIELDS = ("type", "prompt_zh", "question_en", "answer_en", "answer_zh")


def fingerprint(card):
    payload = {field: card.get(field, "") for field in REVIEW_FIELDS}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def pending_reviews(cards, ledger):
    reviewed = ledger.get("cards", {}) if ledger.get("schema_version") == 1 else {}
    return [card for card in cards if reviewed.get(card["id"]) != fingerprint(card)]


def require_reviewed(cards, ledger):
    pending = pending_reviews(cards, ledger)
    if pending:
        raise ValueError(f"Translation review pending for {len(pending)} card(s), first: {pending[0]['id']}")


def build_request(cards, ledger):
    return {
        "schema_version": 1,
        "cards": [{"id": card["id"], "fingerprint": fingerprint(card),
                   **{field: card.get(field, "") for field in REVIEW_FIELDS}}
                  for card in pending_reviews(cards, ledger)],
    }


def approve_reviews(cards, ledger, response):
    if not isinstance(response.get("reviews"), list):
        raise ValueError("Audit response requires a reviews list")
    by_id = {card["id"]: card for card in cards}
    reviewed = dict(ledger.get("cards", {}))
    seen = set()
    for entry in response["reviews"]:
        card_id = entry.get("id")
        if card_id in seen or card_id not in by_id:
            raise ValueError(f"Unknown or duplicate audit card: {card_id}")
        seen.add(card_id)
        if entry.get("approved") is not True:
            raise ValueError(f"Audit card is not approved: {card_id}")
        if entry.get("fingerprint") != fingerprint(by_id[card_id]):
            raise ValueError(f"Audit fingerprint is stale: {card_id}")
        reviewed[card_id] = entry["fingerprint"]
    return {"schema_version": 1, "cards": reviewed}
