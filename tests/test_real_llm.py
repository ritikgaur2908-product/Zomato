"""Test real LLM API call with GroqClient."""

from llm.client import GroqClient


def test_real_groq_client_call():
    """Test that the real Groq API call works with configured API key."""
    client = GroqClient()
    
    # Simple test message to verify API connectivity
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say 'Hello' in one word."}
    ]
    
    response = client.complete(messages)
    
    # Verify we got a response
    assert response is not None
    assert len(response) > 0
    print(f"LLM Response: {response}")
