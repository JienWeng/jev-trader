from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ValidationError

from .jev_policy import JevPolicy
from .models import Action, JevDecision, MarketState, Regime, Venue


class JevPolicyError(RuntimeError):
    """Raised when the TypeSafe response cannot safely become a decision."""


class JevApiResponse(BaseModel):
    model: str
    answers: dict[str, dict]


@dataclass(frozen=True)
class TypeSafeClient:
    api_key: str
    endpoint: str = "https://api.typesafe.ai/v1/systemone"
    model: str = "jev-latest"
    timeout_seconds: float = 2.0

    @classmethod
    def from_environment(cls) -> TypeSafeClient:
        key = os.environ.get("TYPESAFE_API_KEY")
        if not key:
            raise JevPolicyError("TYPESAFE_API_KEY is not configured")
        return cls(api_key=key)

    def evaluate(
        self, state: Mapping[str, object], questions: Mapping[str, object]
    ) -> JevApiResponse:
        body = json.dumps({"state": state, "model": self.model, "questions": questions}).encode()
        request = Request(
            self.endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise JevPolicyError("TypeSafe evaluation request failed") from exc
        try:
            return JevApiResponse.model_validate(payload)
        except ValidationError as exc:
            raise JevPolicyError("TypeSafe returned an invalid response envelope") from exc


def build_questions() -> dict[str, object]:
    return {
        "action": {
            "type": "choice",
            "instructions": "What strategy action should be taken now, after considering mean reversion and execution costs?",
            "criteria": {
                "no_trade": None,
                "open_long": None,
                "open_short": None,
                "reduce": None,
                "close": None,
            },
        },
        "regime": {
            "type": "choice",
            "instructions": "What market regime best describes this state?",
            "criteria": {"range": None, "trend": None, "volatile": None, "unknown": None},
        },
        "setup_quality": {
            "type": "score",
            "instructions": "How strong is the mean-reversion setup after considering divergence and order-book pressure?",
            "criteria": ["invalid", "weak", "acceptable", "strong", "exceptional"],
        },
        "execution_quality": {
            "type": "score",
            "instructions": "How executable is this opportunity after spread, depth, slippage, gas, and funding?",
            "criteria": ["poor", "limited", "acceptable", "good", "excellent"],
        },
        "risk_acceptable": {
            "type": "noul",
            "instructions": "Is this trade risk acceptable under the supplied state and hard policy constraints?",
        },
        "leverage": {
            "type": "choice",
            "instructions": "What leverage bucket is appropriate, if any?",
            "criteria": {"0x": None, "1x": None, "2x": None},
        },
    }


def _answer(response: JevApiResponse, key: str) -> dict:
    answer = response.answers.get(key)
    if not isinstance(answer, dict):
        raise JevPolicyError(f"missing Jev answer: {key}")
    return answer


def _score(answer: dict, key: str) -> float:
    value = answer.get("score")
    if not isinstance(value, (int, float)):
        raise JevPolicyError(f"invalid Jev score answer: {key}")
    return float(value) / 4.0


class TypeSafeJevPolicy(JevPolicy):
    """Translate Jev's typed answers into the internal strategy decision."""

    def __init__(self, client: TypeSafeClient):
        self.client = client

    def decide(self, state: MarketState) -> JevDecision:
        response = self.client.evaluate(
            state=state.model_dump(mode="json"),
            questions=build_questions(),
        )
        action_answer = _answer(response, "action")
        regime_answer = _answer(response, "regime")
        action_name = action_answer.get("choice")
        regime_name = regime_answer.get("choice")
        try:
            action = Action(action_name)
            regime = Regime(regime_name)
        except ValueError as exc:
            raise JevPolicyError("Jev selected an unknown action or regime") from exc

        action_probability = float(action_answer.get("probabilities", {}).get(action.value, 0.0))
        confidence = float(action_answer.get("confidence", 0.0))
        risk_probability = float(_answer(response, "risk_acceptable").get("noul", 0.0))
        leverage_name = _answer(response, "leverage").get("choice", "0x")
        leverage = float(str(leverage_name).removesuffix("x"))
        if risk_probability < 0.5:
            action = Action.NO_TRADE
            leverage = 0.0

        return JevDecision(
            action=action,
            venue=Venue.BINANCE if state.cex is not None else Venue.DEX,
            regime=regime,
            action_probability=action_probability,
            confidence=confidence,
            setup_score=_score(_answer(response, "setup_quality"), "setup_quality"),
            execution_score=_score(_answer(response, "execution_quality"), "execution_quality"),
            risk_score=risk_probability,
            expected_edge_bps=0.0,
            holding_period_seconds=0,
            requested_leverage=leverage,
            reason_codes=("typesafe_jev",),
        )
