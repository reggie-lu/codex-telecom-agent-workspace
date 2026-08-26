from collections.abc import Callable

import httpx2
import pytest
from openai import APITimeoutError, AuthenticationError, InternalServerError, RateLimitError
from openai.types.chat import ChatCompletion

from telecom_agent.adapters.sambanova.current_plan_answers import (
    SambaNovaCurrentPlanAnswerGenerator,
    SambaNovaSettings,
)
from telecom_agent.domain.plans import GroundedCurrentPlanFacts
from telecom_agent.ports.messages import AnswerGenerationUnavailableError

FACTS = GroundedCurrentPlanFacts(
    plan_name="Synthetic KDDI 5G 20GB",
    data_allowance="20 GB",
    recurring_charge="JPY 4,500",
    effective_date="August 1, 2026",
)
ANSWER = (
    "You have Synthetic KDDI 5G 20GB with 20 GB of domestic data. "
    "Its monthly recurring charge is JPY 4,500. "
    "It has been effective since August 1, 2026."
)


def completion(content: str | None) -> ChatCompletion:
    return ChatCompletion.model_validate(
        {
            "id": "completion-1",
            "object": "chat.completion",
            "created": 0,
            "model": "MiniMax-M3",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
        }
    )


def settings() -> SambaNovaSettings:
    return SambaNovaSettings(
        base_url="https://api.sambanova.ai/v1",
        model="MiniMax-M3",
        api_key="test-key",
        timeout_seconds=30.0,
    )


def test_generator_configures_openai_client_without_sdk_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_options: list[dict[str, object]] = []

    class FakeCompletions:
        def create(self, **_kwargs: object) -> ChatCompletion:
            return completion(ANSWER)

    class FakeChat:
        completions = FakeCompletions()

    class FakeOpenAI:
        chat = FakeChat()

        def __init__(self, **kwargs: object) -> None:
            client_options.append(kwargs)

    monkeypatch.setattr(
        "telecom_agent.adapters.sambanova.current_plan_answers.OpenAI",
        FakeOpenAI,
    )

    generator = SambaNovaCurrentPlanAnswerGenerator(settings())

    assert generator.generate(question="What is my plan?", facts=FACTS) == ANSWER
    assert client_options == [
        {
            "base_url": "https://api.sambanova.ai/v1",
            "api_key": "test-key",
            "timeout": 30.0,
            "max_retries": 0,
        }
    ]


def test_generator_sends_only_question_and_canonical_facts() -> None:
    calls: list[dict[str, object]] = []

    def create_completion(**kwargs: object) -> ChatCompletion:
        calls.append(kwargs)
        return completion(ANSWER)

    generator = SambaNovaCurrentPlanAnswerGenerator(
        settings(),
        completion_create=create_completion,
    )

    result = generator.generate(question="What is my current plan?", facts=FACTS)

    assert result == ANSWER
    assert len(calls) == 1
    call = calls[0]
    assert call["model"] == "MiniMax-M3"
    assert call["temperature"] == 0
    messages = call["messages"]
    prompt_text = str(messages)
    assert "What is my current plan?" in prompt_text
    assert "Synthetic KDDI 5G 20GB" in prompt_text
    assert "20 GB" in prompt_text
    assert "JPY 4,500" in prompt_text
    assert "August 1, 2026" in prompt_text
    assert "10000000-0000-0000-0000-000000000001" not in prompt_text


@pytest.mark.parametrize(
    "failure_factory",
    [
        lambda request: APITimeoutError(request=request),
        lambda request: RateLimitError(
            "rate limited",
            response=httpx2.Response(429, request=request),
            body=None,
        ),
        lambda request: InternalServerError(
            "server unavailable",
            response=httpx2.Response(503, request=request),
            body=None,
        ),
    ],
)
def test_generator_retries_one_transient_failure_then_succeeds(
    failure_factory: Callable[[httpx2.Request], Exception],
) -> None:
    request = httpx2.Request("POST", "https://api.sambanova.ai/v1/chat/completions")
    outcomes: list[Exception | ChatCompletion] = [failure_factory(request), completion(ANSWER)]
    calls = 0

    def create_completion(**_kwargs: object) -> ChatCompletion:
        nonlocal calls
        calls += 1
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    generator = SambaNovaCurrentPlanAnswerGenerator(
        settings(),
        completion_create=create_completion,
    )

    assert generator.generate(question="What is my plan?", facts=FACTS) == ANSWER
    assert calls == 2


@pytest.mark.parametrize(
    "failure_factory",
    [
        lambda request: APITimeoutError(request=request),
        lambda request: AuthenticationError(
            "invalid API key",
            response=httpx2.Response(401, request=request),
            body=None,
        ),
    ],
)
def test_generator_returns_terminal_failure_with_bounded_retry(
    failure_factory: Callable[[httpx2.Request], Exception],
) -> None:
    request = httpx2.Request("POST", "https://api.sambanova.ai/v1/chat/completions")
    calls = 0

    def create_completion(**_kwargs: object) -> ChatCompletion:
        nonlocal calls
        calls += 1
        raise failure_factory(request)

    generator = SambaNovaCurrentPlanAnswerGenerator(
        settings(),
        completion_create=create_completion,
    )

    with pytest.raises(AnswerGenerationUnavailableError):
        generator.generate(question="What is my plan?", facts=FACTS)

    expected_calls = 2 if isinstance(failure_factory(request), APITimeoutError) else 1
    assert calls == expected_calls


@pytest.mark.parametrize("content", [None, "", "   "])
def test_generator_rejects_missing_completion_content(content: str | None) -> None:
    generator = SambaNovaCurrentPlanAnswerGenerator(
        settings(),
        completion_create=lambda **_kwargs: completion(content),
    )

    with pytest.raises(AnswerGenerationUnavailableError):
        generator.generate(question="What is my plan?", facts=FACTS)
