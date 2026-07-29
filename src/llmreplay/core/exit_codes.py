"""Stable process exit codes (SPEC / DESIGN error model)."""

from enum import IntEnum


class ExitCode(IntEnum):
    """Machine-stable exit codes. Printed by name on stderr footers."""

    SUCCESS = 0
    STATIC_MISMATCH = 1
    CASSETTE_MISSING = 2
    LIVE_OR_UPSTREAM_ERROR = 3
    TEST_STACK_UNHEALTHY = 4
    SCHEMA_OR_REPAIR_REQUIRED = 5
    HOOK_OR_POLICY_DIVERGENCE = 6
    SECRET_SCRUB_OR_LIMIT = 7
    NETWORK_DENIED = 8
    ROUTE_OR_PROTOCOL = 9


EXIT_CODE_HELP: dict[ExitCode, str] = {
    ExitCode.SUCCESS: "Success",
    ExitCode.STATIC_MISMATCH: "Static mismatch — run `llmreplay why`",
    ExitCode.CASSETTE_MISSING: "Cassette/step missing — run `llmreplay record`",
    ExitCode.LIVE_OR_UPSTREAM_ERROR: "Live/upstream error — check CCR/Ollama",
    ExitCode.TEST_STACK_UNHEALTHY: "Test-stack unhealthy — `llmreplay test-stack up`",
    ExitCode.SCHEMA_OR_REPAIR_REQUIRED: "Schema/migrate/repair required",
    ExitCode.HOOK_OR_POLICY_DIVERGENCE: "Hook digest or policy divergence",
    ExitCode.SECRET_SCRUB_OR_LIMIT: "Secret/scrub/limit violation",
    ExitCode.NETWORK_DENIED: "Network denied in strict/ci profile",
    ExitCode.ROUTE_OR_PROTOCOL: "Route denied or protocol violation",
}
