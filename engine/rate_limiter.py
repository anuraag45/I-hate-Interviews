import asyncio
import enum
import time
from typing import Dict, Optional, Tuple

class CircuitState(enum.Enum):
    CLOSED = "CLOSED"       # Normal operation
    OPEN = "OPEN"           # Failing, requests blocked
    HALF_OPEN = "HALF_OPEN" # Probing recovery with a single test request

class ProviderCircuitBreaker:
    def __init__(self, provider_name: str, failure_threshold: int = 3, recovery_timeout: float = 15.0):
        self.provider_name = provider_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_state_change = time.time()
        self._lock = asyncio.Lock()

    async def can_execute(self) -> bool:
        """Determines if a request can be dispatched to this provider."""
        async with self._lock:
            now = time.time()
            if self.state == CircuitState.OPEN:
                if now - self.last_state_change >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.last_state_change = now
                    print(f"[CircuitBreaker] {self.provider_name} entering HALF_OPEN probe state.")
                    return True
                return False
            return True

    async def record_success(self):
        """Records a successful response and resets failure counters."""
        async with self._lock:
            self.failure_count = 0
            if self.state != CircuitState.CLOSED:
                self.state = CircuitState.CLOSED
                self.last_state_change = time.time()
                print(f"[CircuitBreaker] {self.provider_name} recovered. Circuit is now CLOSED.")

    async def record_failure(self):
        """Records an API error or timeout and trips the circuit if threshold is reached."""
        async with self._lock:
            self.failure_count += 1
            now = time.time()
            if self.state == CircuitState.HALF_OPEN or self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.last_state_change = now
                print(f"[CircuitBreaker] {self.provider_name} TRIPPED -> OPEN (Failures: {self.failure_count}). Cooldown: {self.recovery_timeout}s")

class TokenBucketRateLimiter:
    def __init__(self, requests_per_minute: float = 30.0, burst_capacity: float = 5.0):
        self.capacity = burst_capacity
        self.tokens = burst_capacity
        self.refill_rate = requests_per_minute / 60.0 # Tokens per second
        self.last_refill = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens_needed: float = 1.0) -> bool:
        """Attempts to acquire tokens without blocking."""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

            if self.tokens >= tokens_needed:
                self.tokens -= tokens_needed
                return True
            return False

class RateLimitingManager:
    """Central registry of per-provider rate limiters and circuit breakers."""
    def __init__(self):
        self.circuit_breakers: Dict[str, ProviderCircuitBreaker] = {
            "gemini": ProviderCircuitBreaker("gemini", failure_threshold=3, recovery_timeout=10.0),
            "groq": ProviderCircuitBreaker("groq", failure_threshold=3, recovery_timeout=15.0),
            "openai": ProviderCircuitBreaker("openai", failure_threshold=3, recovery_timeout=20.0),
            "deepgram": ProviderCircuitBreaker("deepgram", failure_threshold=3, recovery_timeout=15.0),
        }
        self.rate_limiters: Dict[str, TokenBucketRateLimiter] = {
            "gemini": TokenBucketRateLimiter(requests_per_minute=60.0, burst_capacity=10.0),
            "groq": TokenBucketRateLimiter(requests_per_minute=30.0, burst_capacity=5.0),
            "openai": TokenBucketRateLimiter(requests_per_minute=30.0, burst_capacity=5.0),
            "deepgram": TokenBucketRateLimiter(requests_per_minute=120.0, burst_capacity=20.0),
        }
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_requests = 0

    def get_circuit_breaker(self, provider: str) -> ProviderCircuitBreaker:
        return self.circuit_breakers.setdefault(provider.lower(), ProviderCircuitBreaker(provider))

    def get_rate_limiter(self, provider: str) -> TokenBucketRateLimiter:
        return self.rate_limiters.setdefault(provider.lower(), TokenBucketRateLimiter())

    def record_token_usage(self, input_tokens: int, output_tokens: int):
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_requests += 1

    def get_usage_metrics(self) -> dict:
        # Approximate blended cost calculation ($0.10/1M input, $0.40/1M output for Gemini 2.0 Flash)
        est_cost = (self.total_input_tokens * 0.0000001) + (self.total_output_tokens * 0.0000004)
        return {
            "requests": self.total_requests,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "estimated_cost_usd": round(est_cost, 5)
        }
