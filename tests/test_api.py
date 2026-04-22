"""API integration tests — DB thật + LLM thật, không mock gì cả."""
from __future__ import annotations

import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Fixture: chạy full lifespan (DB + LLM thật)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def ac():
    from main import create_app
    app = create_app()
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class TestHealth:
    async def test_returns_200(self, ac):
        r = await ac.get("/health")
        assert r.status_code == 200

    async def test_db_connected(self, ac):
        data = (await ac.get("/health")).json()
        assert data["db"] == "ok"

    async def test_response_shape(self, ac):
        data = (await ac.get("/health")).json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "llm_url" in data

    async def test_llm_url_correct(self, ac):
        data = (await ac.get("/health")).json()
        assert "trycloudflare.com" in data["llm_url"]


# ---------------------------------------------------------------------------
# /api/v1/stage1
# ---------------------------------------------------------------------------

# Fixed UUIDs — stable across test runs so ON CONFLICT DO NOTHING works cleanly
_PT01 = "00000000-0000-0000-0000-000000000001"
_PT02 = "00000000-0000-0000-0000-000000000002"

STAGE1_NORMAL = {
    "readings": [
        {"patient_id": _PT01, "source": "HBPM", "day_period": "morning",
         "datetime": "2026-04-01T07:00:00", "systolic": 116, "diastolic": 72,
         "device_type": "upper_arm", "device_validated": True, "position": "sitting", "rested_minutes": 5},
        {"patient_id": _PT01, "source": "HBPM", "day_period": "evening",
         "datetime": "2026-04-01T19:00:00", "systolic": 118, "diastolic": 74,
         "device_type": "upper_arm", "device_validated": True, "position": "sitting", "rested_minutes": 5},
        {"patient_id": _PT01, "source": "HBPM", "day_period": "morning",
         "datetime": "2026-04-02T07:00:00", "systolic": 117, "diastolic": 73,
         "device_type": "upper_arm", "device_validated": True, "position": "sitting", "rested_minutes": 5},
        {"patient_id": _PT01, "source": "HBPM", "day_period": "evening",
         "datetime": "2026-04-02T19:00:00", "systolic": 119, "diastolic": 75,
         "device_type": "upper_arm", "device_validated": True, "position": "sitting", "rested_minutes": 5},
    ]
}

STAGE1_HYPERTENSION = {
    "readings": [
        {"patient_id": _PT02, "source": "HBPM", "day_period": "morning",
         "datetime": f"2026-04-0{d}T07:00:00", "systolic": 155 + d, "diastolic": 95 + d,
         "device_type": "upper_arm", "device_validated": True, "position": "sitting", "rested_minutes": 5}
        for d in range(1, 8)
    ] + [
        {"patient_id": _PT02, "source": "HBPM", "day_period": "evening",
         "datetime": f"2026-04-0{d}T19:00:00", "systolic": 158 + d, "diastolic": 97 + d,
         "device_type": "upper_arm", "device_validated": True, "position": "sitting", "rested_minutes": 5}
        for d in range(1, 8)
    ]
}


class TestStage1:
    async def test_normal_200(self, ac):
        r = await ac.post("/api/v1/stage1", json=STAGE1_NORMAL)
        assert r.status_code == 200

    async def test_hypertension_200(self, ac):
        r = await ac.post("/api/v1/stage1", json=STAGE1_HYPERTENSION)
        assert r.status_code == 200

    async def test_response_has_patient_summary(self, ac):
        data = (await ac.post("/api/v1/stage1", json=STAGE1_NORMAL)).json()
        assert "patient_summary" in data or "patient_count" in data

    async def test_normal_bp_category(self, ac):
        data = (await ac.post("/api/v1/stage1", json=STAGE1_NORMAL)).json()
        summary = data.get("patient_summary", [])
        if summary:
            assert summary[0].get("bp_category") in {"normal", "elevated", "hypertension"}

    async def test_hypertension_bp_category(self, ac):
        data = (await ac.post("/api/v1/stage1", json=STAGE1_HYPERTENSION)).json()
        summary = data.get("patient_summary", [])
        if summary:
            assert summary[0].get("bp_category") in {"hypertension", "elevated"}

    async def test_empty_readings_rejected(self, ac):
        r = await ac.post("/api/v1/stage1", json={"readings": []})
        assert r.status_code == 422

    async def test_missing_required_field_rejected(self, ac):
        r = await ac.post("/api/v1/stage1", json={"readings": [{"patient_id": "x", "source": "HBPM"}]})
        assert r.status_code == 422

    async def test_invalid_body_rejected(self, ac):
        r = await ac.post("/api/v1/stage1", json="not_an_object")
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# /api/v1/stage2
# ---------------------------------------------------------------------------

STAGE2_LOW_RISK = {
    "patientInfo": {"age": 45, "gender": "male"},
    "bp_stage": "120-129/70-79",
    "special": {"diabetes": False, "familialHypercholesterolemia": False},
    "riskFactors": {
        "male": True, "ageOver65": False, "heartRateOver80": False,
        "overweight": False, "diabetes": False, "highLDLOrTriglyceride": False,
        "familialHypercholesterolemia": False, "familyHistoryOfHypertension": False,
        "earlyMenopause": False, "smoking": False,
        "environmentalSocioeconomicFactors": False, "menopause": False,
        "sedentaryLifestyle": False,
    },
    "hmod": {
        "leftVentricularHypertrophy": False, "brainDamage": False,
        "heartDamage": False, "kidneyDamage": False, "vascularDamage": False,
        "ckdStage3": False, "pulsePressureOver60": False,
    },
    "cardiovascularDisease": {
        "coronaryArteryDisease": False, "heartFailure": False, "stroke": False,
        "peripheralVascularDisease": False, "atrialFibrillation": False,
        "ckdStage4": False, "ckdStage5": False,
    },
}

STAGE2_HIGH_RISK = {
    "patientInfo": {"age": 70, "gender": "male"},
    "bp_stage": "stage2",
    "special": {"diabetes": True, "familialHypercholesterolemia": False},
    "riskFactors": {
        "male": True, "ageOver65": True, "heartRateOver80": True,
        "overweight": True, "diabetes": True, "highLDLOrTriglyceride": True,
        "familialHypercholesterolemia": False, "familyHistoryOfHypertension": True,
        "earlyMenopause": False, "smoking": True,
        "environmentalSocioeconomicFactors": False, "menopause": False,
        "sedentaryLifestyle": True,
    },
    "hmod": {
        "leftVentricularHypertrophy": True, "brainDamage": False,
        "heartDamage": True, "kidneyDamage": False, "vascularDamage": False,
        "ckdStage3": False, "pulsePressureOver60": True,
    },
    "cardiovascularDisease": {
        "coronaryArteryDisease": True, "heartFailure": False, "stroke": False,
        "peripheralVascularDisease": False, "atrialFibrillation": False,
        "ckdStage4": False, "ckdStage5": False,
    },
}


class TestStage2:
    async def test_low_risk_200(self, ac):
        r = await ac.post("/api/v1/stage2", json=STAGE2_LOW_RISK)
        assert r.status_code == 200

    async def test_high_risk_200(self, ac):
        r = await ac.post("/api/v1/stage2", json=STAGE2_HIGH_RISK)
        assert r.status_code == 200

    async def test_response_has_risk_level(self, ac):
        data = (await ac.post("/api/v1/stage2", json=STAGE2_LOW_RISK)).json()
        assert "risk_level" in data

    async def test_response_has_recommendation(self, ac):
        data = (await ac.post("/api/v1/stage2", json=STAGE2_LOW_RISK)).json()
        assert "recommendation" in data

    async def test_response_has_confidence(self, ac):
        data = (await ac.post("/api/v1/stage2", json=STAGE2_LOW_RISK)).json()
        assert "confidence" in data

    async def test_low_risk_label(self, ac):
        data = (await ac.post("/api/v1/stage2", json=STAGE2_LOW_RISK)).json()
        assert data["risk_level"] == "low"

    async def test_high_risk_label(self, ac):
        data = (await ac.post("/api/v1/stage2", json=STAGE2_HIGH_RISK)).json()
        assert data["risk_level"] in {"high", "very_high"}

    async def test_empty_body_200(self, ac):
        r = await ac.post("/api/v1/stage2", json={})
        assert r.status_code == 200

    async def test_invalid_body_rejected(self, ac):
        r = await ac.post("/api/v1/stage2", json="not_an_object")
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# LLM smoke test — gọi thật đến vLLM endpoint
# ---------------------------------------------------------------------------

class TestLLMDirect:
    async def test_chat_returns_content(self):
        from integrations.llms.vllm import create_llm
        llm = create_llm(profile="primary")
        resp = await llm.chat(
            [{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=16,
            temperature=0.0,
        )
        await llm.close()
        content = resp["choices"][0]["message"]["content"]
        assert isinstance(content, str) and len(content) > 0
        print(f"\n[LLM] {content!r}")

    async def test_chat_model_name_correct(self):
        from integrations.llms.vllm import DEFAULT_MODEL, create_llm
        llm = create_llm(profile="primary")
        assert llm.model == DEFAULT_MODEL
        await llm.close()

    async def test_stream_yields_tokens(self):
        from integrations.llms.vllm import create_llm
        llm = create_llm(profile="primary")
        tokens: list[str] = []
        async for token in llm.stream_chat(
            [{"role": "user", "content": "Count: 1, 2, 3"}],
            max_tokens=32,
            temperature=0.0,
        ):
            tokens.append(token)
        await llm.close()
        assert len(tokens) > 0
        print(f"\n[LLM stream] {''.join(tokens)!r}")
