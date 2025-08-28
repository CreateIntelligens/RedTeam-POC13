# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import os
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json

from pyrit.models import PromptRequestPiece, PromptRequestResponse
from pyrit.prompt_target.google.gemini_target import GeminiTarget
from pyrit.exceptions import PyritException, EmptyResponseException


@pytest.mark.asyncio
@patch("httpx.AsyncClient.request")
async def test_gemini_target_success(mock_request, patch_central_database):
    """Test successful Gemini API call"""
    # Mock response from Gemini API (wrapped as string representation of bytes)
    mock_response_data = {
        "candidates": [{
            "content": {
                "parts": [{"text": "Hello! How can I help you today?"}]
            }
        }]
    }
    
    # Simulate the wrapped response format that HTTPXAPITarget returns
    wrapped_response = f"b'{json.dumps(mock_response_data).replace(chr(39), chr(92) + chr(39))}'"
    
    mock_response = MagicMock()
    mock_response.content = wrapped_response.encode()
    mock_request.return_value = mock_response
    
    # Create request
    request_piece = PromptRequestPiece(
        role="user", 
        original_value="Hello", 
        converted_value="Hello"
    )
    prompt_request = PromptRequestResponse(request_pieces=[request_piece])
    
    # Create Gemini target
    target = GeminiTarget(api_key="test_key")
    
    # Send prompt
    response = await target.send_prompt_async(prompt_request=prompt_request)
    
    # Verify response
    assert response is not None
    assert len(response.request_pieces) > 0
    assert "Hello! How can I help you today?" in response.request_pieces[0].converted_value


@pytest.mark.asyncio  
@patch("httpx.AsyncClient.request")
async def test_gemini_target_api_error(mock_request, patch_central_database):
    """Test Gemini API error handling"""
    # Mock error response
    error_response_data = {
        "error": {
            "code": 403,
            "message": "API key invalid",
            "status": "PERMISSION_DENIED"
        }
    }
    
    wrapped_response = f"b'{json.dumps(error_response_data).replace(chr(39), chr(92) + chr(39))}'"
    mock_response = MagicMock()
    mock_response.content = wrapped_response.encode()
    mock_request.return_value = mock_response
    
    request_piece = PromptRequestPiece(
        role="user", 
        original_value="Hello", 
        converted_value="Hello"
    )
    prompt_request = PromptRequestResponse(request_pieces=[request_piece])
    
    target = GeminiTarget(api_key="invalid_key")
    
    # Should raise PyritException for API errors
    with pytest.raises(PyritException) as exc_info:
        await target.send_prompt_async(prompt_request=prompt_request)
    
    assert "API key invalid" in str(exc_info.value)


def test_gemini_target_initialization(patch_central_database):
    """Test Gemini target initialization"""
    target = GeminiTarget(api_key="test_key", model="gemini-1.5-flash")
    
    assert target.model == "gemini-1.5-flash"
    assert target.api_key_set is True
    assert target.headers["Content-Type"] == "application/json"


def test_gemini_target_no_api_key(patch_central_database):
    """Test that GeminiTarget raises error when no API key is provided"""
    # Temporarily remove the environment variable
    original_key = os.environ.pop("GEMINI_API_KEY", None)
    
    try:
        with pytest.raises(ValueError) as exc_info:
            GeminiTarget()
        
        assert "Gemini API key is required" in str(exc_info.value)
    finally:
        # Restore the original environment variable if it existed
        if original_key:
            os.environ["GEMINI_API_KEY"] = original_key


def test_gemini_target_format_request_data(patch_central_database):
    """Test request formatting for Gemini API"""
    target = GeminiTarget(api_key="test_key")
    formatted = target._format_request_data("Hello world")
    
    expected = {
        "contents": [{
            "parts": [{"text": "Hello world"}]
        }]
    }
    
    assert formatted == expected


def test_gemini_target_format_request_with_parameters(patch_central_database):
    """Test request formatting with generation parameters"""
    target = GeminiTarget(
        api_key="test_key", 
        temperature=0.7, 
        max_output_tokens=1000,
        top_p=0.8,
        top_k=40
    )
    
    formatted = target._format_request_data("Hello world")
    
    assert "generationConfig" in formatted
    config = formatted["generationConfig"]
    assert config["temperature"] == 0.7
    assert config["maxOutputTokens"] == 1000
    assert config["topP"] == 0.8
    assert config["topK"] == 40


def test_gemini_response_parsing_success(patch_central_database):
    """Test response parsing from Gemini API"""
    target = GeminiTarget(api_key="test_key")
    
    response_data = {
        "candidates": [{
            "content": {
                "parts": [{"text": "This is a response"}]
            }
        }]
    }
    
    # Test both regular JSON and wrapped format
    json_response = json.dumps(response_data)
    parsed = target._parse_gemini_response(json_response)
    assert parsed == "This is a response"
    
    # Test wrapped format (as returned by HTTPXAPITarget)
    wrapped_response = f"b'{json_response.replace(chr(39), chr(92) + chr(39))}'"
    parsed = target._parse_gemini_response(wrapped_response)
    assert parsed == "This is a response"


def test_gemini_response_parsing_error(patch_central_database):
    """Test response parsing with malformed data"""
    target = GeminiTarget(api_key="test_key")
    
    # Test invalid JSON
    with pytest.raises(PyritException) as exc_info:
        target._parse_gemini_response("invalid json")
    assert "Invalid JSON response" in str(exc_info.value)
    
    # Test missing required fields
    response_data = {"error": "something went wrong"}
    json_response = json.dumps(response_data)
    
    with pytest.raises(PyritException) as exc_info:
        target._parse_gemini_response(json_response)
    assert "something went wrong" in str(exc_info.value)


def test_gemini_target_properties(patch_central_database):
    """Test GeminiTarget properties"""
    target = GeminiTarget(api_key="test_key", model="gemini-1.5-flash")
    
    assert target.model == "gemini-1.5-flash"
    assert target.api_key_set is True
    
    # Test string representation
    repr_str = repr(target)
    assert "GeminiTarget" in repr_str
    assert "gemini-1.5-flash" in repr_str
    assert "api_key_set=True" in repr_str


@pytest.mark.asyncio
async def test_gemini_target_validation_errors(patch_central_database):
    """Test various validation errors"""
    target = GeminiTarget(api_key="test_key")
    
    # Test empty request pieces
    empty_request = PromptRequestResponse(request_pieces=[])
    with pytest.raises(ValueError) as exc_info:
        await target.send_prompt_async(prompt_request=empty_request)
    assert "exactly one request piece" in str(exc_info.value)
    
    # Test multiple request pieces
    multi_request = PromptRequestResponse(request_pieces=[
        PromptRequestPiece(role="user", original_value="test1", converted_value="test1"),
        PromptRequestPiece(role="user", original_value="test2", converted_value="test2")
    ])
    with pytest.raises(ValueError) as exc_info:
        await target.send_prompt_async(prompt_request=multi_request)
    assert "exactly one request piece" in str(exc_info.value)
    
    # Test empty prompt text
    empty_prompt_request = PromptRequestResponse(request_pieces=[
        PromptRequestPiece(role="user", original_value="", converted_value="")
    ])
    with pytest.raises(ValueError) as exc_info:
        await target.send_prompt_async(prompt_request=empty_prompt_request)
    assert "non-empty string" in str(exc_info.value)


@pytest.mark.asyncio
async def test_gemini_target_empty_response(patch_central_database):
    """Test handling of empty response from API"""
    target = GeminiTarget(api_key="test_key")
    
    # Mock a response with empty candidates
    response_data = {"candidates": []}
    json_response = json.dumps(response_data)
    
    with pytest.raises(EmptyResponseException) as exc_info:
        target._parse_gemini_response(json_response)
    assert "Could not extract text" in str(exc_info.value)