from __future__ import annotations

from .model import IntentModel
from .text import extract_entities, sanitize


ORDER_INTENTS = {"place_order", "cancel_order", "change_order", "track_order", "check_order_status"}
ESCALATE_INTENTS = {"complaint", "refund", "payment_issue", "get_refund", "recover_password"}


def decide(message: str, model: IntentModel, *, confidence_threshold: float = 0.55) -> dict:
    clean, redactions = sanitize(message)
    entities = extract_entities(message)
    prediction = model.predict(clean)
    intent = prediction["intent"]
    action = "REPLY"
    if prediction["confidence"] < confidence_threshold or entities["is_angry"]:
        action = "ESCALATE"
    elif intent in ORDER_INTENTS:
        action = "CREATE_OR_UPDATE_ORDER"
    elif intent in ESCALATE_INTENTS:
        action = "ESCALATE"
    response = prediction["response"] or "تم استلام طلبك، سأساعدك خطوة بخطوة."
    if action == "ESCALATE":
        response = "وصلتني رسالتك. سأحوّلها لموظف بشري مع ملخص آمن بدون بيانات حساسة."
    return {
        "action": action,
        "intent": intent,
        "category": prediction["category"],
        "confidence": prediction["confidence"],
        "safe_message": clean,
        "entities": entities,
        "redactions": redactions,
        "response": response,
    }

