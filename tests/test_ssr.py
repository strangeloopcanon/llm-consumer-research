"""Tests for the ssr module."""

from __future__ import annotations

import numpy as np
import pytest

from ssr_service.ssr import likert_metrics


def test_likert_metrics():
    """Test the likert_metrics function."""
    pmf = np.array([0.1, 0.2, 0.3, 0.4])
    ratings = [1, 2, 3, 4]
    mean, top2 = likert_metrics(pmf, ratings)
    assert mean == 3.0
    assert top2 == 0.7
