import asyncio
from enum import Enum
from typing import Any, Callable


class CircuitState(str, Enum):
    CLOSED = "CLOSED"  # Normal operation: LLM calls pass through
    OPEN = "OPEN"  # Tripped: Bypass LLMs, return degraded static analysis
    HALF_OPEN = "HALF_OPEN"  # Probing recovery


class AgentCircuitBreaker:
    """
    Stage 2 Architecture: Agent Circuit Breaker (CIRCUIT_BREAKER).
    Wraps LLM agent execution with timeout guards (90s) and failure thresholds.
    If an external LLM endpoint hangs, throttles (429), or errors, the circuit trips to OPEN,
    immediately routing the review through deterministic static-analysis fallback mode.
    Guarantees that PR reviews never block the CI/CD pipeline and prevents runaway LLM costs.
    """

    def __init__(
        self,
        name: str = "agent_circuit_breaker",
        failure_threshold: int = 3,
        recovery_timeout_seconds: float = 60.0,
        execution_timeout_seconds: float = 90.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.execution_timeout_seconds = execution_timeout_seconds

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_state_change = asyncio.get_event_loop().time()
        self.total_trips = 0

    async def call(
        self,
        func: Callable[..., Any],
        fallback_func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Executes func with circuit breaker protection and automatic fallback routing."""
        now = asyncio.get_event_loop().time()

        # If OPEN, check if recovery window has elapsed to probe HALF_OPEN
        if self.state == CircuitState.OPEN:
            if now - self.last_state_change > self.recovery_timeout_seconds:
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = now
            else:
                # Still OPEN: Immediately invoke fallback without calling LLM
                return await self._execute_fallback(fallback_func, *args, **kwargs)

        try:
            # Execute with per-agent execution timeout guard
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.execution_timeout_seconds,
            )
            # On success, reset failures if HALF_OPEN or CLOSED
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.last_state_change = asyncio.get_event_loop().time()
            return result

        except Exception as ex:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold or self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.total_trips += 1
                self.last_state_change = asyncio.get_event_loop().time()

            return await self._execute_fallback(fallback_func, *args, **kwargs)

    async def _execute_fallback(
        self, fallback_func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Executes fallback logic (e.g. degraded mode with static-analysis only)."""
        if asyncio.iscoroutinefunction(fallback_func):
            return await fallback_func(*args, **kwargs)
        return fallback_func(*args, **kwargs)

    def get_metrics(self) -> dict[str, Any]:
        """Telemetry metrics for Prometheus and Grafana Circuit Dashboard."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "total_trips": self.total_trips,
        }
