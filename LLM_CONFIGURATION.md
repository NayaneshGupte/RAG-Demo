# LLM Provider Configuration Guide

This guide explains how to configure and use the pluggable LLM providers in the RAG Demo application.

## Overview

The application now uses an abstract LLM provider system that allows you to:
- Use different LLM providers (Gemini, Claude, or custom providers)
- Automatically fallback to alternative providers on quota/rate limit errors
- Configure primary and fallback providers via environment variables
- Add new LLM providers with minimal code changes

## Architecture

### Components

1. **LLMProvider (Base Class)**: Abstract interface that all LLM providers must implement
2. **GeminiProvider**: Google Gemini implementation
3. **ClaudeProvider**: Anthropic Claude implementation
4. **LLMFactory**: Factory class that manages provider initialization, selection, and fallback logic

### Data Flow

```
AgentService
    ↓
LLMFactory (with retry & fallback logic)
    ↓
Primary Provider (e.g., Gemini)
    ↓
Fallback Provider (e.g., Claude) [on quota error]
    ↓
LLMResponse
```

## Environment Variables

Add these to your `.env` file to configure LLM providers:

```bash
# Primary LLM Provider (default: gemini)
# Options: "gemini", "claude", or custom provider name
LLM_PRIMARY_PROVIDER=gemini

# Fallback Providers (comma-separated, default: claude)
# Tried in order when primary provider fails
LLM_FALLBACK_PROVIDERS=claude

# API Keys
GOOGLE_API_KEY=your-google-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# LLM Generation Settings
LLM_TEMPERATURE=0.0              # Response creativity (0.0-1.0)
LLM_MAX_TOKENS=1024             # Maximum response length
LLM_RETRY_MAX_ATTEMPTS=5        # Max retries for rate limits
LLM_RETRY_DELAY_SECONDS=5       # Initial retry delay (exponential backoff)
```

## Configuration Examples

### Example 1: Gemini as Primary, Claude as Fallback

```bash
LLM_PRIMARY_PROVIDER=gemini
LLM_FALLBACK_PROVIDERS=claude
GOOGLE_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here
```

### Example 2: Claude as Primary, Gemini as Fallback

```bash
LLM_PRIMARY_PROVIDER=claude
LLM_FALLBACK_PROVIDERS=gemini
ANTHROPIC_API_KEY=your-key-here
GOOGLE_API_KEY=your-key-here
```

### Example 3: Multiple Fallbacks

```bash
LLM_PRIMARY_PROVIDER=gemini
LLM_FALLBACK_PROVIDERS=claude,custom_provider
GOOGLE_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here
```

## How It Works

### Normal Flow

1. Application starts and initializes LLMFactory
2. Primary provider is validated and loaded
3. All fallback providers are pre-loaded
4. Requests are sent to the current provider

### On Rate Limit Error

1. Request fails with 429 or "Quota exceeded" error
2. Factory automatically switches to the first available fallback provider
3. Request is retried with exponential backoff
4. If fallback also hits rate limit, continues to next fallback
5. If all providers exhausted, raises exception

### On Other Errors

1. Request fails with non-rate-limit error
2. Exception is logged and raised to caller
3. Application can implement its own error handling

## Adding a New LLM Provider

### Step 1: Create Provider Class

```python
# app/services/llm_providers/my_provider.py
from app.services.llm_providers.base import LLMProvider, LLMResponse
import logging

logger = logging.getLogger(__name__)

class MyProvider(LLMProvider):
    def __init__(self, model_name: str = "my-model", api_key: str = None):
        super().__init__(model_name)
        self.api_key = api_key or os.getenv("MY_API_KEY")
        self.client = None
        
        if self.validate_credentials():
            self._initialize_client()
    
    def validate_credentials(self) -> bool:
        return bool(self.api_key)
    
    def _initialize_client(self):
        # Initialize your API client here
        pass
    
    def is_available(self) -> bool:
        if not self.validate_credentials():
            return False
        if self.client is None:
            self._initialize_client()
        return self.client is not None
    
    def generate_content(self, prompt: str, temperature: float = 0.0, max_tokens: int = 1024) -> LLMResponse:
        if self.client is None:
            if not self.is_available():
                raise Exception("MyProvider is not available")
        
        try:
            # Call your API and get response
            response_text = self.client.call_api(prompt, temperature, max_tokens)
            return LLMResponse(text=response_text, model_name=self.model_name)
        except Exception as e:
            logger.error(f"Error generating content with MyProvider: {e}")
            raise
```

### Step 2: Register Provider

```python
# In your initialization code or app startup
from app.services.llm_providers.factory import LLMFactory
from my_provider import MyProvider

LLMFactory.PROVIDER_REGISTRY["my_provider"] = MyProvider
```

### Step 3: Use in Configuration

```bash
LLM_PRIMARY_PROVIDER=my_provider
LLM_FALLBACK_PROVIDERS=gemini,claude
MY_API_KEY=your-api-key
```

## Monitoring Provider Status

Get status of all providers:

```python
from app.services.llm_providers.factory import LLMFactory
from app.config import Config

factory = LLMFactory()
status = factory.get_provider_status()

print(status)
# Output:
# {
#     "current_provider": "GeminiProvider",
#     "primary": {"name": "gemini", "available": True},
#     "fallbacks": [
#         {"name": "claude", "available": True}
#     ]
# }
```

## Best Practices

1. **Always configure at least 2 providers**: Primary + 1 fallback for high availability
2. **Use appropriate temperature**: 0.0 for consistency, higher for creativity
3. **Set reasonable token limits**: Based on your expected response length
4. **Monitor logs**: Check logs to see when fallbacks are triggered
5. **Test provider availability**: Before deploying, verify all API keys work
6. **Update retry settings**: Adjust based on your rate limit thresholds

## Troubleshooting

### "No LLM provider available" Error

**Cause**: All providers failed initialization
**Solution**: 
- Check API keys are set correctly
- Verify API key format matches provider requirements
- Check network connectivity

### Frequent Fallback Switching

**Cause**: Primary provider hitting rate limits
**Solution**:
- Increase `LLM_RETRY_DELAY_SECONDS`
- Add more providers to fallback list
- Implement request queuing in your application

### "Max retries exceeded" Error

**Cause**: All retry attempts and fallbacks exhausted
**Solution**:
- Increase `LLM_RETRY_MAX_ATTEMPTS`
- Implement application-level retry logic
- Consider caching responses

## File Structure

```
app/
├── services/
│   ├── llm_providers/
│   │   ├── __init__.py
│   │   ├── base.py              # LLMProvider abstract class
│   │   ├── gemini_provider.py   # Gemini implementation
│   │   ├── claude_provider.py   # Claude implementation
│   │   ├── factory.py           # LLMFactory with fallback logic
│   │   └── my_provider.py       # [Your custom provider]
│   ├── agent_service.py         # Uses LLMFactory (no LLM-specific code)
│   └── [other services]
├── config/
│   └── __init__.py              # LLM config in Config class
└── [rest of app]
```

## Migration from Old Code

If upgrading from the previous implementation:

1. **Remove LLM-specific imports** from agent_service.py
2. **Replace direct LLM calls** with `self.llm_factory.generate_content()`
3. **Update environment variables** to use new LLM config format
4. **Test all providers** before deploying to production
5. **Update deployment scripts** to set new LLM environment variables

## Examples

### Get Current Provider Status

```python
from app.services.agent_service import AgentService

agent = AgentService()
status = agent.llm_factory.get_provider_status()
print(f"Using provider: {status['current_provider']}")
```

### Programmatically Switch Provider

```python
# This happens automatically, but you can also do it manually:
from app.services.llm_providers.factory import LLMFactory

factory = LLMFactory()
# Factory will automatically use primary or fallback based on availability
response = factory.generate_content("Your prompt here")
```

## Support

For issues with specific LLM providers:

- **Gemini**: Check [Google AI Studio](https://aistudio.google.com)
- **Claude**: Check [Anthropic Console](https://console.anthropic.com)
- **Custom Providers**: Ensure LLMProvider abstract methods are implemented
