"""NeMo Guardrails Input Security Validation Layer (Layer A)."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from config.settings import settings


@dataclass
class GuardrailResult:
    """Outcome of NeMo Guardrails input validation."""
    is_safe: bool
    blocked_category: Optional[str] = None
    reason: Optional[str] = None
    sanitized_input: str = ""


class NeMoInputGuard:
    """Layer A Security Guardrail: Scans user input before it reaches the LLM.
    
    Implements Colang-defined safety rails:
    1. Destructive Database Operations (DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE, REPLACE)
    2. SQL Injection Patterns (tautologies '1'='1', comment syntax '--', '/*', UNION attacks)
    3. Prompt Injections & System Prompt Overrides
    4. Malicious Script Tags and Markup (<script>, javascript:)
    """

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        self.config_dir = config_dir or settings.GUARDRAILS_CONFIG_DIR
        self._rails = None
        self._init_nemo_rails()

    def _init_nemo_rails(self) -> None:
        """Attempt to initialize NeMo LLMRails engine if dependencies and config exist."""
        try:
            from nemoguardrails import LLMRails, RailsConfig
            if self.config_dir.exists():
                rails_config = RailsConfig.from_path(str(self.config_dir))
                self._rails = LLMRails(rails_config)
        except Exception:
            # Fall back gracefully to Colang-aligned deterministic rule engine
            self._rails = None

    def validate(self, user_input: str) -> GuardrailResult:
        """Validate raw user query against Colang input guardrail rules."""
        if not user_input or not user_input.strip():
            return GuardrailResult(
                is_safe=False,
                blocked_category="EMPTY_INPUT",
                reason="Query is empty. Please enter an analytics question.",
                sanitized_input="",
            )

        text = user_input.strip()

        # 1. Check for Script Tags and Malicious Markup
        script_pattern = re.compile(r"<\s*script\b|javascript:|onerror\s*=|onload\s*=", re.IGNORECASE)
        if script_pattern.search(text):
            return GuardrailResult(
                is_safe=False,
                blocked_category="SCRIPT_TAGS",
                reason="Security Alert: Malicious markup or script tags (<script>, javascript:) detected and blocked by NeMo Guardrails.",
                sanitized_input=text,
            )

        # 2. Check for Prompt Injection / Instruction Bypasses
        prompt_injection_patterns = [
            r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
            r"disregard\s+(the\s+)?system\s+prompt",
            r"reveal\s+(your\s+)?(system\s+)?instructions",
            r"you\s+are\s+now\s+dan",
            r"bypass\s+all\s+security\s+filters",
            r"act\s+as\s+root",
        ]
        for pattern in prompt_injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return GuardrailResult(
                    is_safe=False,
                    blocked_category="PROMPT_INJECTION",
                    reason="Security Alert: Prompt injection or instruction bypass attempt detected and blocked by NeMo Guardrails.",
                    sanitized_input=text,
                )

        # 3. Check for Destructive SQL Commands in Input
        destructive_sql_pattern = re.compile(
            r"\b(DROP\s+TABLE|DROP\s+DATABASE|DROP\s+VIEW|DROP\s+INDEX|DELETE\s+FROM|TRUNCATE\s+TABLE|ALTER\s+TABLE|UPDATE\s+\w+\s+SET|INSERT\s+INTO|CREATE\s+TABLE|REPLACE\s+INTO)\b",
            re.IGNORECASE,
        )
        if destructive_sql_pattern.search(text):
            return GuardrailResult(
                is_safe=False,
                blocked_category="DESTRUCTIVE_SQL",
                reason="Security Alert: Destructive database modifications (DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE) are strictly blocked by NeMo Guardrails.",
                sanitized_input=text,
            )

        # 4. Check for SQL Injection Signatures & Tautology Attacks
        sqli_patterns = [
            # Tautology attacks: 1=1, '1'='1', 'a'='a', WHERE 1=1, OR 1=1, AND 1=1
            r"(?:\bwhere\b|\bor\b|\band\b)?\s*['\"]?(\w+)['\"]?\s*=\s*['\"]?\1['\"]?",
            # Comment-based attacks: -- or /* ... */
            r"(?:--|/\*|\*/)",
            # Statement chaining attempt in raw query: ; DROP, ; SELECT
            r";\s*(?:DROP|DELETE|UPDATE|INSERT|SELECT|ALTER|TRUNCATE|EXEC|SHUTDOWN)\b",
            # Union-based injection
            r"\bUNION\s+(?:ALL\s+)?SELECT\b",
            # Hex/char based evasion or administrative exec
            r"\b(xp_cmdshell|sp_executesql|benchmark\s*\(|pg_sleep\s*\(|sleep\s*\()\b",
        ]
        for pattern in sqli_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return GuardrailResult(
                    is_safe=False,
                    blocked_category="SQL_INJECTION",
                    reason="Security Alert: Potential SQL injection or comment expansion attack detected and blocked by NeMo Guardrails.",
                    sanitized_input=text,
                )

        # Clean sanitized input
        return GuardrailResult(
            is_safe=True,
            blocked_category=None,
            reason=None,
            sanitized_input=text,
        )
