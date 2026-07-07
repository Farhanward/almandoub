# المندوب AlMandoub

المندوب موظف محادثات محلي لرسائل واتساب/تيليجرام: يصنف intent، يعقم البريد والجوال، يستخرج رقم الطلب، ثم يقرر هل يرد آلياً أو يصعد لموظف بشري أو ينشئ/يعدل طلباً.

## آلية العمل

1. `download` يجلب Bitext Customer Support من Hugging Face.
2. `train` يبني Naive Bayes محلياً على intent/category.
3. `handle` يعقم الرسالة، يستخرج entities، يتنبأ بالintent، ثم يحدد action.
4. `batch/stress` يقيسان الدقة والانهيار.

## تشغيل سريع

```powershell
python -m almandoub.cli download --limit 12000
python -m almandoub.cli train
python -m almandoub.cli handle --message "where is my order ORD-1234?"
python -m almandoub.cli batch
```

## بيانات الاختبار

المصدر: Hugging Face `bitext/Bitext-customer-support-llm-chatbot-training-dataset`، ويحتوي 26,872 زوج سؤال/جواب و27 intent و10 categories.

## آخر نتائج

- الاختبارات الذاتية: 3/3 ناجحة.
- بيانات الإنترنت: 12,000 رسالة من Bitext، غطت 13 intent في أول عينة محملة.
- التدريب: 12,000 سجل، 1,619 ميزة.
- Benchmark: 12,000 معالجة، Accuracy=99.84%، 0 أخطاء، escalations=1,283، p99=0.211ms.
- Stress: 36,000 معالجة، Accuracy=99.84%، 0 أخطاء، p99=0.224ms، peak memory=1.21MB.

## تحسينات إنتاجية 2026-07-04

- القرار لا يكتفي بالتصنيف؛ يدمج الثقة والغضب والintent لاختيار `REPLY/ESCALATE/CREATE_OR_UPDATE_ORDER`.
- الرسائل تعقم البريد والجوال قبل الرد أو التصعيد، وتستخرج أرقام الطلبات من الصيغ الشائعة.
- النموذج محلي بالكامل ويحفظ رد intent الأكثر شيوعاً من بيانات التدريب لاستخدامه كقالب رد أولي.

## التشغيل المؤسسي (Enterprise) — v1.0.0

- **خدمة محادثات HTTP**: `python -m almandoub.cli serve` → `POST /api/handle {"message"}` يعيد `action/intent/confidence/safe_message/response`.
- **النموذج يحمل مرة واحدة** عند الإقلاع (`ALMANDOUB_MODEL`، افتراضي `models\almandoub_intent_model.json`).
- **ضمانة**: البريد والجوال يعقمان في `safe_message` قبل أي معالجة أو تسجيل.
- **نقاط فحص**: `/api/health` (مفتوح) · `/api/version` · `/api/metrics`.
- **تهيئة عبر البيئة**: متغيرات `ALMANDOUB_*` — انظر `docs/OPERATIONS.md`.
- **مصادقة**: `ALMANDOUB_API_KEY` → ترويسة `X-API-Key`. **سجلات JSON**: `logs\almandoub.service.jsonl`.
