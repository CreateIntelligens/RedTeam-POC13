# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import json
import logging
import os
from typing import Optional

import httpx
from pyrit.common import net_utility
from pyrit.exceptions import (
    EmptyResponseException,
    PyritException,
    handle_bad_request_exception,
    pyrit_target_retry,
)
from pyrit.models import PromptRequestPiece, PromptRequestResponse, construct_response_from_request
from pyrit.prompt_target.common.prompt_chat_target import PromptChatTarget
from pyrit.prompt_target.common.utils import limit_requests_per_minute

logger = logging.getLogger(__name__)


class GeminiTarget(PromptChatTarget):
    """
    A target for Google's Gemini API, supporting text generation through the Gemini models.
    
    This class extends PromptChatTarget to provide integration with Google's Gemini API,
    supporting models like gemini-1.5-flash, gemini-pro, etc.
    
    Args:
        api_key (str, Optional): The API key for Google AI. If not provided, 
                                will be read from the GEMINI_API_KEY environment variable.
        model (str): The model name to use. Defaults to "gemini-1.5-flash".
        temperature (float, Optional): Controls randomness in the output. Range: 0.0 to 2.0.
        max_output_tokens (int, Optional): Maximum number of tokens to generate.
        top_p (float, Optional): Controls diversity via nucleus sampling.
        top_k (int, Optional): Controls diversity via top-k sampling.
        **kwargs: Additional keyword arguments passed to PromptChatTarget.
    
    Raises:
        ValueError: If no API key is provided and GEMINI_API_KEY environment variable is not set.
    
    Example:
        >>> from pyrit.prompt_target import GeminiTarget
        >>> target = GeminiTarget(api_key="your_api_key")
        >>> # Use in orchestrator workflows
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: str = "gemini-1.5-flash",
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        **kwargs,
    ):
        """
        Initialize the Gemini target.
        """
        self._api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GEMINI_API_KEY")
        self._model = model
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens
        self._top_p = top_p
        self._top_k = top_k

        if not self._api_key:
            raise ValueError(
                "Gemini API key is required. Either pass it as 'api_key' parameter "
                "or set the 'GEMINI_API_KEY' environment variable."
            )

        # Construct the API endpoint URL (without API key in URL)
        self._endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent"
        
        # Set headers with proper authentication
        self._headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key
        }

        super().__init__(**kwargs)

        logger.info(f"GeminiTarget initialized with model: {self._model}")

    def _format_request_data(self, prompt: str) -> dict:
        """
        Format the request data for the Gemini API.
        
        Args:
            prompt (str): The input prompt text.
            
        Returns:
            dict: The formatted request payload for Gemini API.
        """
        request_data = {
            "contents": [{"parts": [{"text": prompt}]}]
        }

        # Add generation configuration if parameters are provided
        generation_config = {}
        if self._temperature is not None:
            generation_config["temperature"] = self._temperature
        if self._max_output_tokens is not None:
            generation_config["maxOutputTokens"] = self._max_output_tokens
        if self._top_p is not None:
            generation_config["topP"] = self._top_p
        if self._top_k is not None:
            generation_config["topK"] = self._top_k

        if generation_config:
            request_data["generationConfig"] = generation_config

        return request_data

    def _parse_gemini_response(self, response_content: str) -> str:
        """
        Parse the Gemini API response and extract the generated text.
        
        Args:
            response_content (str): Raw response content from the API.
            
        Returns:
            str: The extracted text response.
            
        Raises:
            PyritException: If the response cannot be parsed or contains errors.
        """
        try:
            # Handle the case where response is wrapped as a string representation of bytes
            if response_content.startswith("b'") and response_content.endswith("'"):
                # Remove b' and ' wrapper, then unescape
                json_str = response_content[2:-1]
                json_str = json_str.encode().decode('unicode_escape')
                response_content = json_str

            gemini_response = json.loads(response_content)

            # Handle error responses
            if "error" in gemini_response:
                error_info = gemini_response["error"]
                if isinstance(error_info, dict):
                    error_message = error_info.get("message", "Unknown error")
                    error_code = error_info.get("code", "Unknown")
                    error_status = error_info.get("status", "Unknown")
                    
                    logger.error(f"Gemini API error: {error_code} {error_status}: {error_message}")
                    raise PyritException(f"Gemini API error: {error_code} {error_status}: {error_message}")
                else:
                    # Handle case where error is just a string
                    logger.error(f"Gemini API error: {error_info}")
                    raise PyritException(f"Gemini API error: {error_info}")

            # Extract text from successful response
            if "candidates" in gemini_response and gemini_response["candidates"]:
                candidate = gemini_response["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if parts and "text" in parts[0]:
                        return parts[0]["text"].strip()
                    
            # If we reach here, the response structure was unexpected
            logger.error(f"Unexpected Gemini response structure: {gemini_response}")
            raise EmptyResponseException("Could not extract text from Gemini response")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            raise PyritException(f"Invalid JSON response from Gemini API: {e}")
        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected response format from Gemini: {e}")
            raise PyritException(f"Unexpected response format from Gemini API: {e}")
        except Exception as e:
            if isinstance(e, (PyritException, EmptyResponseException)):
                raise
            logger.error(f"Unexpected error parsing Gemini response: {e}")
            raise PyritException(f"Failed to parse Gemini response: {e}")

    def _build_gemini_prompt_from_conversation(self, conversation) -> str:
        """
        Build a single prompt string from the conversation history.
        
        For now, we'll concatenate all messages, but this could be enhanced
        to use Gemini's proper conversation format in the future.
        
        Args:
            conversation: List of PromptRequestResponse objects representing the conversation.
            
        Returns:
            str: The formatted prompt text.
        """
        prompt_parts = []
        for entry in conversation:
            for piece in entry.request_pieces:
                if piece.role == "system":
                    prompt_parts.append(f"System: {piece.converted_value}")
                elif piece.role == "user":
                    prompt_parts.append(f"User: {piece.converted_value}")
                elif piece.role == "assistant":
                    prompt_parts.append(f"Assistant: {piece.converted_value}")
                else:
                    prompt_parts.append(piece.converted_value)
        
        # If there's only one piece, return it directly (likely the current prompt)
        if len(prompt_parts) == 1:
            return prompt_parts[0].replace("User: ", "").replace("System: ", "").replace("Assistant: ", "")
        
        return "\n\n".join(prompt_parts)

    def _validate_request(self, *, prompt_request: PromptRequestResponse) -> None:
        """
        Validates the provided prompt request response.
        
        Args:
            prompt_request (PromptRequestResponse): The prompt request to validate.
            
        Raises:
            ValueError: If the request is invalid.
        """
        if not prompt_request.request_pieces:
            raise ValueError("PromptRequestResponse must contain at least one request piece")
            
        for piece in prompt_request.request_pieces:
            if piece.converted_value_data_type != "text":
                raise ValueError(f"GeminiTarget only supports text input. Received: {piece.converted_value_data_type}")

    def is_json_response_supported(self) -> bool:
        """
        Indicates whether this target supports JSON response format.
        
        Returns:
            bool: False, as Gemini API doesn't support structured JSON responses in this implementation.
        """
        return False

    @limit_requests_per_minute
    @pyrit_target_retry
    async def send_prompt_async(self, *, prompt_request: PromptRequestResponse) -> PromptRequestResponse:
        """
        Send a prompt to the Gemini API and return the response.
        
        Args:
            prompt_request (PromptRequestResponse): The prompt request to send.
            
        Returns:
            PromptRequestResponse: The response from the Gemini API.
            
        Raises:
            PyritException: If the request fails or the response cannot be processed.
        """
        try:
            self._validate_request(prompt_request=prompt_request)
            
            # Validate that we have exactly one request piece
            if not prompt_request.request_pieces or len(prompt_request.request_pieces) != 1:
                raise ValueError("GeminiTarget expects exactly one request piece")

            request_piece = prompt_request.request_pieces[0]
            
            # Get conversation history from memory
            conversation = self._memory.get_conversation(conversation_id=request_piece.conversation_id)
            conversation.append(prompt_request)
            
            # Build the prompt from conversation history
            prompt_text = self._build_gemini_prompt_from_conversation(conversation)

            logger.debug(f"Sending prompt to Gemini: {prompt_text[:100]}...")

            # Format the request data for Gemini API
            request_body = self._format_request_data(prompt_text)

            # Make HTTP request to Gemini API
            try:
                str_response: httpx.Response = await net_utility.make_request_and_raise_if_error_async(
                    endpoint_uri=self._endpoint,
                    method="POST",
                    headers=self._headers,
                    request_body=request_body,
                )
            except httpx.HTTPStatusError as StatusError:
                if StatusError.response.status_code == 400:
                    return handle_bad_request_exception(
                        response_text=StatusError.response.text,
                        request=request_piece,
                        error_code=StatusError.response.status_code,
                        is_content_filter=False,
                    )
                else:
                    raise

            # Parse the Gemini response
            parsed_text = self._parse_gemini_response(str_response.text)
            logger.debug(f"Gemini response: {parsed_text[:100]}...")
                
            # Construct response
            response = construct_response_from_request(request=request_piece, response_text_pieces=[parsed_text])
            return response

        except Exception as e:
            if isinstance(e, (PyritException, EmptyResponseException, ValueError)):
                raise
            logger.error(f"Unexpected error in GeminiTarget.send_prompt_async: {e}")
            raise PyritException(f"Failed to send prompt to Gemini: {e}")

    @property
    def model(self) -> str:
        """Get the model name being used."""
        return self._model

    @property
    def api_key_set(self) -> bool:
        """Check if API key is configured (without exposing the actual key)."""
        return bool(self._api_key)

    def __repr__(self) -> str:
        """String representation of the GeminiTarget."""
        return f"GeminiTarget(model='{self._model}', api_key_set={self.api_key_set})"