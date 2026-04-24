"""Validates container image tags against configurable policies."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TagPolicy:
    """Rules that a valid image tag must satisfy."""

    allowed_patterns: List[str] = field(default_factory=list)
    blocked_patterns: List[str] = field(default_factory=list)
    block_latest: bool = True

    def is_valid(self) -> bool:
        """Return True when the policy itself is well-formed."""
        for pat in self.allowed_patterns + self.blocked_patterns:
            try:
                re.compile(pat)
            except re.error:
                return False
        return True


@dataclass
class ValidationResult:
    """Outcome of a single tag validation check."""

    tag: str
    passed: bool
    reason: Optional[str] = None


def validate_tag(tag: str, policy: TagPolicy) -> ValidationResult:
    """Check *tag* against *policy* and return a :class:`ValidationResult`."""

    if policy.block_latest and tag.lower() == "latest":
        return ValidationResult(tag=tag, passed=False, reason="'latest' tag is blocked by policy")

    for pattern in policy.blocked_patterns:
        if re.search(pattern, tag):
            return ValidationResult(
                tag=tag,
                passed=False,
                reason=f"tag matches blocked pattern '{pattern}'",
            )

    if policy.allowed_patterns:
        for pattern in policy.allowed_patterns:
            if re.search(pattern, tag):
                return ValidationResult(tag=tag, passed=True)
        return ValidationResult(
            tag=tag,
            passed=False,
            reason="tag does not match any allowed pattern",
        )

    return ValidationResult(tag=tag, passed=True)


class TagValidator:
    """Stateful validator that applies a :class:`TagPolicy` to image tags."""

    def __init__(self, policy: Optional[TagPolicy] = None) -> None:
        self._policy = policy or TagPolicy()

    @property
    def policy(self) -> TagPolicy:
        return self._policy

    def check(self, image: str) -> ValidationResult:
        """Validate the tag portion of *image* (``name:tag`` or bare tag)."""
        tag = image.split(":", 1)[-1] if ":" in image else image
        return validate_tag(tag, self._policy)

    def is_allowed(self, image: str) -> bool:
        """Convenience wrapper — return ``True`` when the tag passes."""
        return self.check(image).passed
