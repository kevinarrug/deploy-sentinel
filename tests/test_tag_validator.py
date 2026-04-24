"""Tests for deploy_sentinel.tag_validator."""

import pytest

from deploy_sentinel.tag_validator import (
    TagPolicy,
    TagValidator,
    ValidationResult,
    validate_tag,
)


# ---------------------------------------------------------------------------
# TagPolicy.is_valid
# ---------------------------------------------------------------------------

class TestTagPolicyIsValid:
    def test_empty_policy_is_valid(self):
        assert TagPolicy().is_valid() is True

    def test_valid_regex_patterns_are_valid(self):
        policy = TagPolicy(allowed_patterns=[r"^v\d+\.\d+"], blocked_patterns=[r"dev"])
        assert policy.is_valid() is True

    def test_invalid_regex_makes_policy_invalid(self):
        policy = TagPolicy(allowed_patterns=[r"[unclosed"])
        assert policy.is_valid() is False


# ---------------------------------------------------------------------------
# validate_tag
# ---------------------------------------------------------------------------

class TestValidateTag:
    def test_latest_blocked_by_default(self):
        result = validate_tag("latest", TagPolicy())
        assert result.passed is False
        assert "latest" in result.reason

    def test_latest_allowed_when_flag_off(self):
        result = validate_tag("latest", TagPolicy(block_latest=False))
        assert result.passed is True

    def test_blocked_pattern_rejects_tag(self):
        policy = TagPolicy(blocked_patterns=[r"dev"], block_latest=False)
        result = validate_tag("1.2.3-dev", policy)
        assert result.passed is False
        assert "dev" in result.reason

    def test_allowed_pattern_accepts_matching_tag(self):
        policy = TagPolicy(allowed_patterns=[r"^v\d+"], block_latest=False)
        result = validate_tag("v3.1.0", policy)
        assert result.passed is True

    def test_allowed_pattern_rejects_non_matching_tag(self):
        policy = TagPolicy(allowed_patterns=[r"^v\d+"], block_latest=False)
        result = validate_tag("release-3", policy)
        assert result.passed is False
        assert "allowed pattern" in result.reason

    def test_no_patterns_passes_any_non_latest_tag(self):
        result = validate_tag("stable", TagPolicy(block_latest=False))
        assert result.passed is True

    def test_result_stores_tag(self):
        result = validate_tag("1.0.0", TagPolicy(block_latest=False))
        assert result.tag == "1.0.0"


# ---------------------------------------------------------------------------
# TagValidator
# ---------------------------------------------------------------------------

@pytest.fixture()
def validator():
    policy = TagPolicy(allowed_patterns=[r"^v\d+\.\d+\.\d+$"], block_latest=True)
    return TagValidator(policy)


class TestTagValidator:
    def test_is_allowed_true_for_semver(self, validator):
        assert validator.is_allowed("myapp:v1.2.3") is True

    def test_is_allowed_false_for_latest(self, validator):
        assert validator.is_allowed("myapp:latest") is False

    def test_is_allowed_false_for_non_matching_tag(self, validator):
        assert validator.is_allowed("myapp:edge") is False

    def test_check_returns_validation_result(self, validator):
        result = validator.check("myapp:v2.0.0")
        assert isinstance(result, ValidationResult)
        assert result.passed is True

    def test_bare_tag_without_image_name(self, validator):
        assert validator.is_allowed("v1.0.0") is True

    def test_default_policy_used_when_none_provided(self):
        v = TagValidator()
        assert v.policy.block_latest is True
        assert v.is_allowed("latest") is False
