"""Verification tests for multi-model simulation."""

import os
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
import numpy as np

from ssr_service.models import (
    ConceptInput,
    PersonaSpec,
    SimulationOptions,
    SimulationRequest,
)
from ssr_service.orchestrator import run_simulation

@pytest.mark.asyncio
@patch("ssr_service.llm.openai_client.AsyncOpenAI")
@patch("ssr_service.llm.anthropic_client.AsyncAnthropic")
@patch("ssr_service.llm.gemini_client.genai")
@patch("ssr_service.llm.perplexity_client.AsyncOpenAI")
@patch("ssr_service.ssr.embed_texts")
@patch("ssr_service.ssr.embed_text")
@patch("ssr_service.llm.openai_client.get_from_cache", return_value=None)
@patch("ssr_service.llm.anthropic_client.get_from_cache", return_value=None)
@patch("ssr_service.llm.gemini_client.get_from_cache", return_value=None)
@patch("ssr_service.llm.perplexity_client.get_from_cache", return_value=None)
async def test_multi_provider_simulation(
    mock_cache_perp, mock_cache_gem, mock_cache_anth, mock_cache_oa,
    mock_embed_single, mock_embed_multi,
    mock_perplexity, mock_gemini, mock_anthropic, mock_openai
):
    # Mock Embeddings
    mock_embed_multi.return_value = np.random.rand(5, 1536)
    mock_embed_single.return_value = np.random.rand(1536)
    
    # Mock OpenAI
    mock_openai_instance = mock_openai.return_value
    mock_openai_instance.chat.completions.create = AsyncMock()
    mock_openai_instance.chat.completions.create.return_value.choices[0].message.content = '{"rationale": "I like it because it is cool."}'
    
    # Mock Anthropic
    mock_anthropic_instance = mock_anthropic.return_value
    mock_anthropic_instance.messages.create = AsyncMock()
    mock_anthropic_instance.messages.create.return_value.content[0].text = '{"rationale": "It seems useful for my daily routine."}'
    
    # Mock Gemini
    mock_gemini_model = MagicMock()
    mock_gemini.GenerativeModel.return_value = mock_gemini_model
    mock_gemini_model.generate_content_async = AsyncMock()
    mock_gemini_model.generate_content_async.return_value.text = '{"rationale": "I would buy this if the price is right."}'
    
    # Mock Perplexity
    mock_perplexity_instance = mock_perplexity.return_value
    mock_perplexity_instance.chat.completions.create = AsyncMock()
    mock_perplexity_instance.chat.completions.create.return_value.choices[0].message.content = '{"rationale": "Based on reviews, this is a good product."}'

    # Set dummy API keys
    with patch.dict(os.environ, {
        "OPENAI_API_KEY": "dummy",
        "ANTHROPIC_API_KEY": "dummy",
        "GOOGLE_API_KEY": "dummy",
        "PERPLEXITY_API_KEY": "dummy"
    }):
        request = SimulationRequest(
            concept=ConceptInput(
                title="Test Product",
                text="A revolutionary new widget.",
                price="$10",
            ),
            personas=[
                PersonaSpec(name="Test Persona", weight=1.0)
            ],
            options=SimulationOptions(
                n=4, # 1 per provider
                providers=["openai", "anthropic", "gemini", "perplexity"]
            )
        )
        
        response = await run_simulation(request)
        
        assert len(response.personas[0].rationales) == 4
        # We expect 4 rationales, one from each mocked provider
