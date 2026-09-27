from jev_trader.models import MarketState, OrderBookLevel, OrderBookSnapshot, Venue
from jev_trader.typesafe_policy import JevApiResponse, TypeSafeJevPolicy, build_questions


class FakeClient:
    def evaluate(self, state, questions):
        assert state["symbol"] == "BTCUSDT"
        assert questions["action"]["type"] == "choice"
        return JevApiResponse(
            model="jev-test",
            answers={
                "action": {
                    "type": "choice",
                    "choice": "open_long",
                    "probabilities": {"no_trade": 0.1, "open_long": 0.8},
                    "confidence": 0.9,
                },
                "regime": {"type": "choice", "choice": "range"},
                "setup_quality": {"type": "score", "score": 3, "confidence": 0.8},
                "execution_quality": {"type": "score", "score": 4, "confidence": 0.9},
                "risk_acceptable": {"type": "noul", "noul": 0.95},
                "leverage": {"type": "choice", "choice": "1x"},
            },
        )


def market_state():
    return MarketState(
        symbol="BTCUSDT",
        timestamp_ms=1,
        cex=OrderBookSnapshot(
            venue=Venue.BINANCE,
            symbol="BTCUSDT",
            sequence=1,
            timestamp_ms=1,
            bids=(OrderBookLevel(price=100, quantity=1),),
            asks=(OrderBookLevel(price=101, quantity=1),),
        ),
        estimated_fee_bps=4,
        estimated_slippage_bps=2,
        estimated_gas_bps=0,
        data_age_ms=10,
    )


def test_questions_use_typed_jev_primitives():
    questions = build_questions()
    assert questions["action"]["type"] == "choice"
    assert questions["setup_quality"]["type"] == "score"
    assert questions["risk_acceptable"]["type"] == "noul"


def test_policy_maps_typed_response_to_decision():
    decision = TypeSafeJevPolicy(FakeClient()).decide(market_state())
    assert decision.action == "open_long"
    assert decision.regime == "range"
    assert decision.action_probability == 0.8
    assert decision.setup_score == 0.75
    assert decision.requested_leverage == 1


def test_risk_noul_overrides_trade_action():
    class UnsafeClient(FakeClient):
        def evaluate(self, state, questions):
            response = super().evaluate(state, questions)
            response.answers["risk_acceptable"]["noul"] = 0.2
            return response

    decision = TypeSafeJevPolicy(UnsafeClient()).decide(market_state())
    assert decision.action == "no_trade"
    assert decision.requested_leverage == 0
