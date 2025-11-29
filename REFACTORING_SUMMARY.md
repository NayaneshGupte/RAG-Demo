# LLM Provider Refactoring - Summary

## Overview

The `agent_service.py` has been successfully refactored to make it completely agnostic to LLM implementations. The LLM logic has been abstracted away from the agent service and separated into individual provider classes with a factory pattern for managing them.

## What Changed

### Before (Tightly Coupled)
- `agent_service.py` directly imported and used `google.generativeai` and `anthropic`
- LLM selection logic was embedded in the agent service
- Fallback logic was scattered throughout the service
- Adding a new LLM required modifying `agent_service.py`
- Hard to test different providers

### After (Loosely Coupled)
- `agent_service.py` only uses `LLMFactory`
- All LLM-specific code is in provider classes
- Fallback logic is centralized in the factory
- Adding a new LLM requires only creating a new provider class
- Easy to test, swap, or mock providers

## New Architecture

### File Structure

```
app/services/llm_providers/
├── __init__.py                  # Module exports
├── base.py                      # LLMProvider abstract class
├── gemini_provider.py           # Google Gemini implementation
├── claude_provider.py           # Anthropic Claude implementation
└── factory.py                   # LLMFactory with retry & fallback logic
```

### Core Components

#### 1. **LLMProvider (base.py)**
Abstract base class defining the interface all providers must implement.

**Key Methods:**
- `generate_content()` - Generate text from a prompt
- `validate_credentials()` - Check if API keys are configured
- `is_available()` - Check if provider is ready to use
- `get_provider_name()` - Get provider identifier

**LLMResponse Wrapper:**
- Provides consistent interface across all providers
- Contains `text` and `model_name` attributes

#### 2. **GeminiProvider (gemini_provider.py)**
Concrete implementation for Google Gemini API.

**Features:**
- Automatic model initialization
- Configurable model name
- Generation config support (temperature, max_tokens)
- Proper error logging

#### 3. **ClaudeProvider (claude_provider.py)**
Concrete implementation for Anthropic Claude API.

**Features:**
- Automatic client initialization
- Support for claude-3-sonnet-20240229 (customizable)
- Message-based API integration
- Consistent response format with LLMResponse

#### 4. **LLMFactory (factory.py)**
Central factory managing provider lifecycle and fallback logic.

**Key Features:**
- **Provider Registry**: Maps provider names to classes
- **Automatic Initialization**: Loads all configured providers
- **Fallback Logic**: Automatically switches on errors
- **Retry with Backoff**: Exponential backoff for rate limits
- **Error Detection**: Identifies quota vs other errors
- **Status Monitoring**: Get real-time provider health
- **Custom Providers**: Extensible provider registration

**Error Handling Flow:**
1. Detect error type (quota vs other)
2. For quota errors: Apply exponential backoff and retry
3. After max retries or non-quota errors: Switch to fallback
4. Continue until success or all providers exhausted

### Configuration

All LLM settings are now in `app/config/__init__.py`:

```python
LLM_PRIMARY_PROVIDER = "gemini"              # Primary LLM
LLM_FALLBACK_PROVIDERS = ["claude"]          # Fallback list
LLM_TEMPERATURE = 0.0                        # Response randomness
LLM_MAX_TOKENS = 1024                        # Response length
LLM_RETRY_MAX_ATTEMPTS = 5                   # Rate limit retries
LLM_RETRY_DELAY_SECONDS = 5                  # Initial retry delay
```

**Configured via `.env` file:**
```bash
LLM_PRIMARY_PROVIDER=gemini
LLM_FALLBACK_PROVIDERS=claude
GOOGLE_API_KEY=...
ANTHROPIC_API_KEY=...
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=1024
LLM_RETRY_MAX_ATTEMPTS=5
LLM_RETRY_DELAY_SECONDS=5
```

## Refactored Methods in AgentService

### Before: Direct LLM Usage
```python
# Old code
self.model = genai.GenerativeModel(Config.CHAT_MODEL)
response = self._retry_with_backoff(self.model.generate_content, formatted_prompt)
```

### After: Factory Usage
```python
# New code
response = self.llm_factory.generate_content(
    prompt=formatted_prompt,
    temperature=Config.LLM_TEMPERATURE,
    max_tokens=Config.LLM_MAX_TOKENS,
    max_retries=Config.LLM_RETRY_MAX_ATTEMPTS,
    retry_delay=Config.LLM_RETRY_DELAY_SECONDS
)
```

### Removed Methods
- `_configure_genai()` - Replaced by provider initialization
- `_initialize_model()` - Replaced by LLMFactory
- `_initialize_alternative_model()` - Handled by factory fallback
- `_retry_with_backoff()` - Replaced by factory.generate_content()

### Modified Methods
- `__init__()` - Now initializes LLMFactory instead of direct LLM
- `should_process_email()` - Uses factory for classification
- `generate_response()` - Uses factory for response generation
- `run()` - Updated logging, no API key validation needed

## Adding a New LLM Provider

### Step 1: Create Provider Class

```python
# app/services/llm_providers/new_provider.py
from app.services.llm_providers.base import LLMProvider, LLMResponse

class NewProvider(LLMProvider):
    def __init__(self, model_name: str = "default-model", api_key: str = None):
        super().__init__(model_name)
        self.api_key = api_key or os.getenv("NEW_API_KEY")
        self.client = None
        
        if self.validate_credentials():
            self._initialize_client()
    
    def validate_credentials(self) -> bool:
        return bool(self.api_key)
    
    def _initialize_client(self):
        # Initialize your API client
        self.client = YourAPIClient(api_key=self.api_key)
    
    def is_available(self) -> bool:
        if not self.validate_credentials():
            return False
        if self.client is None:
            self._initialize_client()
        return self.client is not None
    
    def generate_content(self, prompt: str, temperature: float = 0.0, max_tokens: int = 1024) -> LLMResponse:
        if not self.is_available():
            raise Exception("NewProvider not available")
        
        response_text = self.client.call_api(prompt, temperature, max_tokens)
        return LLMResponse(text=response_text, model_name=self.model_name)
```

### Step 2: Register Provider

```python
# In app startup or initialization
from app.services.llm_providers.factory import LLMFactory
from app.services.llm_providers.new_provider import NewProvider

LLMFactory.PROVIDER_REGISTRY["new_provider"] = NewProvider
```

### Step 3: Configure

```bash
LLM_PRIMARY_PROVIDER=new_provider
LLM_FALLBACK_PROVIDERS=gemini,claude
NEW_API_KEY=your-key-here
```

## Key Improvements

### 1. **Separation of Concerns**
- Agent logic is separate from LLM logic
- Each provider encapsulates its own implementation details
- Factory handles orchestration

### 2. **Extensibility**
- Add new providers without modifying existing code
- Provider registry pattern allows dynamic registration
- Custom providers can override default behavior

### 3. **Maintainability**
- Clearer code structure and responsibilities
- Easier to understand provider-specific code
- Simplified testing (can mock providers)

### 4. **Reliability**
- Automatic fallback to alternative providers
- Intelligent retry logic with exponential backoff
- Detailed error detection and logging

### 5. **Configurability**
- All settings in `.env` file
- Easy to swap providers without code changes
- Support for multiple providers simultaneously

### 6. **Monitoring**
- Real-time provider status via `get_provider_status()`
- Detailed logging of provider switches
- Error tracking per provider

## Backward Compatibility Notes

If you have existing code that directly uses `agent_service.py`:

**Old Usage:**
```python
agent = AgentService()
agent.process_emails()
```

**Still Works:**
```python
# No changes needed - public API is the same
agent = AgentService()
agent.process_emails()
```

The refactoring maintains backward compatibility for all public methods while improving internal architecture.

## Testing

### Test Individual Providers

```python
from app.services.llm_providers import GeminiProvider
from app.config import Config

provider = GeminiProvider()
if provider.is_available():
    response = provider.generate_content("Hello", temperature=0.0)
    print(response.text)
```

### Test Factory with Fallback

```python
from app.services.llm_providers import LLMFactory

factory = LLMFactory(primary_provider="gemini", fallback_providers=["claude"])
status = factory.get_provider_status()
print(status)

response = factory.generate_content("Hello")
print(response.text)
```

### Test Agent Service

```python
from app.services.agent_service import AgentService

agent = AgentService()  # Initializes with configured providers
agent.process_emails()
```

## Migration Checklist

- [x] Created LLMProvider abstract base class
- [x] Implemented GeminiProvider
- [x] Implemented ClaudeProvider
- [x] Created LLMFactory with retry and fallback
- [x] Added LLM config to Config class
- [x] Refactored AgentService to use factory
- [x] Created documentation (LLM_CONFIGURATION.md)
- [x] Created .env.example with LLM settings
- [x] Verified syntax and imports
- [ ] Run integration tests
- [ ] Deploy to production

## Files Changed/Created

### Created Files
- `app/services/llm_providers/base.py`
- `app/services/llm_providers/gemini_provider.py`
- `app/services/llm_providers/claude_provider.py`
- `app/services/llm_providers/factory.py`
- `app/services/llm_providers/__init__.py`
- `LLM_CONFIGURATION.md`
- `.env.example`

### Modified Files
- `app/services/agent_service.py`
- `app/config/__init__.py`

### Removed LLM-Specific Code
- Direct `google.generativeai` usage
- Direct `anthropic.Anthropic` usage
- Manual fallback logic
- Retry logic

## Benefits Summary

| Aspect | Before | After |
|--------|--------|-------|
| **LLM Coupling** | Tightly coupled | Loosely coupled |
| **Adding Provider** | Modify agent_service | Create new class |
| **Fallback Logic** | Scattered | Centralized |
| **Error Handling** | Manual | Automatic |
| **Testability** | Hard to mock | Easy to mock |
| **Configuration** | Hard-coded | .env-based |
| **Monitoring** | Limited | Detailed status |

## Next Steps

1. **Testing**: Run full test suite to ensure no regressions
2. **Deployment**: Update deployment scripts with new .env variables
3. **Documentation**: Update team on new provider pattern
4. **Monitoring**: Set up alerts for provider failures
5. **Optional**: Add more providers (OpenAI, Hugging Face, etc.)
