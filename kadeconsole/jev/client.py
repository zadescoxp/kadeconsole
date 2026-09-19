"""
jev/client.py — TypeSafe AI (Jev) client wrapper.

Wraps the typesafe-sdk TypeSafeClient with:
  - Graceful degradation when TYPESAFE_API_KEY is absent
  - SQLite-backed caching keyed on (ticker, timeframe, data_hash)
  - A clean call interface for verdicts, ratings, and narratives

Jev uses structured output — it returns typed values (Score, Choice)
not free-form text. See verdicts.py / ratings.py for the question schemas.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from kadeconsole.cache.store import CacheStore

try:
    from typesafe_sdk import TypeSafeClient, Choice, Score
    _JEV_AVAILABLE = True
except ImportError:
    _JEV_AVAILABLE = False
    TypeSafeClient = None  # type: ignore[assignment,misc]
    Choice = None          # type: ignore[assignment,misc]
    Score = None           # type: ignore[assignment,misc]


class JevClient:
    """
    Thin wrapper around TypeSafeClient with caching and graceful degradation.

    If typesafe-sdk is not installed, or TYPESAFE_API_KEY is not set,
    all methods return None — callers must handle this gracefully.
    """

    def __init__(self, api_key: str, cache: "CacheStore") -> None:
        self.api_key = api_key
        self.cache = cache
        self._available = _JEV_AVAILABLE and bool(api_key)
        self._client: Optional[Any] = None

    @property
    def available(self) -> bool:
        """Return True if Jev is configured and the SDK is installed."""
        return self._available

    def call(
        self,
        state: dict[str, Any],
        questions: dict[str, Any],
        ticker: str,
        timeframe: str,
        cache_tag: str,
    ) -> Optional[dict[str, Any]]:
        """
        Execute a Jev system_one() call with caching.

        Args:
            state:     The program state dict passed to Jev.
            questions: Dict of Jev question objects (Choice/Score).
            ticker:    Used for cache keying.
            timeframe: Used for cache keying.
            cache_tag: Short string identifying the call type (e.g. "verdict").

        Returns:
            Dict of raw Jev response, or None if unavailable.
        """
        if not self._available:
            return None

        # Build cache key from state fingerprint
        fingerprint = self._fingerprint(state, cache_tag)
        cached = self.cache.get_jev(f"{ticker}:{cache_tag}", timeframe, fingerprint)
        if cached is not None:
            return cached

        # Make the API call
        try:
            result = self._do_call(state, questions)
            if result is not None:
                self.cache.set_jev(f"{ticker}:{cache_tag}", timeframe, fingerprint, result)
            return result
        except Exception:  # noqa: BLE001
            return None

    def _do_call(
        self,
        state: dict[str, Any],
        questions: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """Execute the actual TypeSafe API call."""
        if not _JEV_AVAILABLE:
            return None
        import os
        if self.api_key:
            os.environ["TYPESAFE_API_KEY"] = self.api_key
        try:
            with TypeSafeClient() as client:
                response = client.system_one(state=state, questions=questions)
                return self._serialize_response(response)
        except Exception as exc:  # noqa: BLE001
            # Surface a shortened error message — don't fully swallow
            import sys
            print(f"  [Jev] API error: {exc}", file=sys.stderr)
            return None

    @staticmethod
    def _serialize_response(response: Any) -> dict[str, Any]:
        """
        Convert a TypeSafe SystemOneResponse to a plain dict.

        SDK shape:
          response.answers: dict[str, ScoreAnswer | ChoiceAnswer | NoulAnswer]
          ScoreAnswer: .type='score', .score (float 0-1), .confidence, .probabilities
          ChoiceAnswer: .type='choice', .choice (str), .confidence, .probabilities
        """
        result: dict[str, Any] = {"scores": {}, "choices": {}}

        answers = getattr(response, "answers", {}) or {}
        for key, answer in answers.items():
            ans_type = getattr(answer, "type", None)
            if ans_type == "score":
                result["scores"][key] = float(getattr(answer, "score", 0.0))
            elif ans_type == "choice":
                result["choices"][key] = {
                    "choice": getattr(answer, "choice", ""),
                    "confidence": float(getattr(answer, "confidence", 0.0)),
                }

        return result

    @staticmethod
    def _fingerprint(state: dict, tag: str) -> str:
        """Short hash of state dict for cache keying."""
        raw = json.dumps(state, sort_keys=True, default=str) + tag
        return hashlib.sha256(raw.encode()).hexdigest()[:12]
