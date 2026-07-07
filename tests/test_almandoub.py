from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from almandoub.agent import decide
from almandoub.batch import evaluate
from almandoub.model import IntentModel, train


class AlMandoubTests(unittest.TestCase):
    def test_train_and_handle_message(self):
        with tempfile.TemporaryDirectory(dir="C:/Projects") as tmp:
            data = Path(tmp) / "data.jsonl"
            model_path = Path(tmp) / "model.json"
            rows = [
                {"instruction": "where is my order ORD-1234", "intent": "track_order", "category": "ORDER", "response": "Track it from your account."},
                {"instruction": "cancel my order please", "intent": "cancel_order", "category": "ORDER", "response": "Open your order page to cancel."},
                {"instruction": "how can i reset my password", "intent": "recover_password", "category": "ACCOUNT", "response": "Use password reset."},
                {"instruction": "how do i contact support", "intent": "contact_customer_service", "category": "CONTACT", "response": "Use the contact form."},
            ]
            data.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            info = train(data, model_path)
            self.assertEqual(info["intents"], 4)
            model = IntentModel.load(model_path)
            result = decide("please track order ORD-1234", model)
            self.assertEqual(result["action"], "CREATE_OR_UPDATE_ORDER")
            self.assertIn("ORD", result["safe_message"])

    def test_sanitizes_contact_and_escalates_angry_message(self):
        with tempfile.TemporaryDirectory(dir="C:/Projects") as tmp:
            data = Path(tmp) / "data.jsonl"
            model_path = Path(tmp) / "model.json"
            data.write_text(
                '{"instruction":"contact support","intent":"contact_customer_service","category":"CONTACT","response":"Contact us."}\n'
                '{"instruction":"track order","intent":"track_order","category":"ORDER","response":"Track order."}\n',
                encoding="utf-8",
            )
            train(data, model_path)
            model = IntentModel.load(model_path)
            result = decide("I am angry, call me 0551234567", model)
            self.assertEqual(result["action"], "ESCALATE")
            self.assertNotIn("0551234567", result["safe_message"])

    def test_batch_fixture(self):
        with tempfile.TemporaryDirectory(dir="C:/Projects") as tmp:
            data = Path(tmp) / "data.jsonl"
            model_path = Path(tmp) / "model.json"
            rows = [
                {"instruction": "track order now", "intent": "track_order", "category": "ORDER", "response": "Track order."},
                {"instruction": "contact support", "intent": "contact_customer_service", "category": "CONTACT", "response": "Contact us."},
            ]
            data.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            train(data, model_path)
            summary = evaluate(data, model_path)
            self.assertEqual(summary["errors"], 0)


if __name__ == "__main__":
    unittest.main()

