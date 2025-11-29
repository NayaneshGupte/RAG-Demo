# LLM Provider Architecture Diagram

## Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     AgentService                                │
│  (Email Classification & Response Generation)                  │
│                                                                 │
│  - No direct LLM dependencies                                  │
│  - Uses LLMFactory for all LLM operations                       │
│  - Maintains backward compatible public API                     │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                      LLMFactory                                 │
│  (Central Hub for Provider Management)                          │
│                                                                 │
│  ✓ Provider Registry & Initialization                          │
│  ✓ Primary/Fallback Selection                                  │
│  ✓ Error Detection & Handling                                  │
│  ✓ Retry with Exponential Backoff                             │
│  ✓ Status Monitoring                                           │
│  ✓ Custom Provider Support                                     │
└─────────────────────────────────────────────────────────────────┘
         ↓                                ↓
    Primary Provider              Fallback Providers (if primary fails)
         ↓                                ↓
┌──────────────────┐         ┌──────────────────────────┐
│ GeminiProvider   │         │  ClaudeProvider          │
│                  │         │  (+ custom providers)    │
│ • Google API     │         │  • Anthropic API         │
│ • Model mgmt     │         │  • Model mgmt            │
│ • Error handling │         │  • Error handling        │
└──────────────────┘         └──────────────────────────┘
         ↓                                ↓
   External API                    External API
   google.generativeai            anthropic
```

## Request Flow with Error Handling

```
AgentService.should_process_email() / generate_response()
    │
    ├─→ llm_factory.generate_content(prompt)
    │
    ├─→ LLMFactory: Check current provider
    │
    ├─→ [Attempt 1] Call Primary Provider (Gemini)
    │
    ├─ Success? ──→ Return LLMResponse ✓
    │
    ├─ 429 Error? (Quota Exceeded)
    │   │
    │   ├─→ Retry with backoff (delay * 2^attempt)
    │   │
    │   └─ All retries failed?
    │       │
    │       ├─→ Switch to Fallback 1 (Claude)
    │       │
    │       ├─ Success? ──→ Return LLMResponse ✓
    │       │
    │       ├─ 429 Error?
    │       │   └─→ Retry with backoff
    │       │
    │       └─ Switch to Fallback 2, 3, ...
    │
    └─ Other Error? ──→ Raise Exception (No retry)
```

## Provider Initialization Flow

```
LLMFactory.__init__()
    │
    ├─→ Read config: LLM_PRIMARY_PROVIDER, LLM_FALLBACK_PROVIDERS
    │
    ├─→ Create Primary Provider
    │   ├─ Validate credentials
    │   ├─ Initialize if credentials valid
    │   └─ Set as current_provider if available
    │
    ├─→ Create Fallback Providers (in order)
    │   ├─ Provider 1 (Claude)
    │   │  ├─ Validate credentials
    │   │  └─ Initialize if credentials valid
    │   │
    │   ├─ Provider 2 (Custom)
    │   │  ├─ Validate credentials
    │   │  └─ Initialize if credentials valid
    │   │
    │   └─ ...more providers
    │
    └─→ If primary not available, use first available fallback
```

## Class Inheritance Hierarchy

```
LLMProvider (Abstract Base)
├── Methods:
│   ├─ generate_content(prompt, temperature, max_tokens) → LLMResponse
│   ├─ validate_credentials() → bool
│   ├─ is_available() → bool
│   └─ get_provider_name() → str
│
├── GeminiProvider
│   ├─ Imports: google.generativeai
│   └─ Uses: genai.GenerativeModel
│
├── ClaudeProvider
│   ├─ Imports: anthropic.Anthropic
│   └─ Uses: Anthropic client.messages.create()
│
└── CustomProvider (user-defined)
    ├─ Imports: your_api_client
    └─ Uses: your implementation
```

## Configuration Structure

```
.env File
│
├─ LLM_PRIMARY_PROVIDER ──→ Config.LLM_PRIMARY_PROVIDER
│  (e.g., "gemini")
│
├─ LLM_FALLBACK_PROVIDERS ──→ Config.LLM_FALLBACK_PROVIDERS
│  (e.g., "claude,custom")
│
├─ GOOGLE_API_KEY ──────────→ GeminiProvider
│  (passed to genai.configure)
│
├─ ANTHROPIC_API_KEY ───────→ ClaudeProvider
│  (passed to Anthropic client)
│
├─ LLM_TEMPERATURE ─────────→ generate_content(temperature=...)
│  (default: 0.0)
│
├─ LLM_MAX_TOKENS ──────────→ generate_content(max_tokens=...)
│  (default: 1024)
│
├─ LLM_RETRY_MAX_ATTEMPTS ──→ generate_content(max_retries=...)
│  (default: 5)
│
└─ LLM_RETRY_DELAY_SECONDS ─→ backoff_delay = delay * 2^attempt
   (default: 5 seconds)
```

## Error Handling Decision Tree

```
Exception in generate_content()
    │
    ├─ "429" in str(e) OR "Quota exceeded" in str(e)?
    │  ├─ YES: Is quota error
    │  │   ├─ Retry < max_retries?
    │  │   │  ├─ YES: Sleep and retry
    │  │   │  └─ NO: Try fallback
    │  │   └─ Fallback available?
    │  │      ├─ YES: Switch and retry
    │  │      └─ NO: Raise exception
    │  │
    │  └─ NO: Is other error type
    │      └─ Try fallback immediately
    │         ├─ YES: Switch and retry
    │         └─ NO: Raise exception
    │
    └─ All options exhausted? ──→ Raise "All providers exhausted"
```

## File Organization

```
app/
├── services/
│   ├── llm_providers/                    ← NEW LLM abstraction layer
│   │   ├── __init__.py                   ← Module exports
│   │   ├── base.py                       ← LLMProvider abstract class
│   │   ├── gemini_provider.py            ← Gemini implementation
│   │   ├── claude_provider.py            ← Claude implementation
│   │   ├── factory.py                    ← LLMFactory with fallback
│   │   └── [custom_provider.py]          ← User-defined providers
│   │
│   ├── agent_service.py                  ← REFACTORED (now LLM-agnostic)
│   ├── vector_store_service.py
│   ├── gmail_service.py
│   ├── database_service.py
│   └── [other services]
│
├── config/
│   └── __init__.py                       ← Updated with LLM settings
│
├── utils/
├── templates/
└── static/
```

## Provider Status Monitoring

```
LLMFactory.get_provider_status() returns:
{
    "current_provider": "GeminiProvider",
    "primary": {
        "name": "gemini",
        "available": true
    },
    "fallbacks": [
        {
            "name": "claude",
            "available": true
        },
        {
            "name": "custom_provider",
            "available": false
        }
    ]
}
```

## Sequence Diagram: Normal Request

```
AgentService            LLMFactory         GeminiProvider    Google API
    │                      │                    │                 │
    ├─generate_content────→│                    │                 │
    │   (prompt, config)   │                    │                 │
    │                      ├─validate primary──→│                 │
    │                      │                    ├─check API key──→│
    │                      │                    │                 │
    │                      │    ✓ valid         │                 │
    │                      │←───────────────────┤                 │
    │                      │                    │                 │
    │                      ├─generate_content──→│                 │
    │                      │   (prompt, params) ├─API call───────→│
    │                      │                    │                 │
    │                      │                    │    response     │
    │                      │                    │←────────────────┤
    │                      │                    │                 │
    │    LLMResponse       │
    │←──────────LLMResponse────────────────────┤
    │  (text, model_name)  │
    │                      │
    └─ Continue processing
```

## Sequence Diagram: Fallback on Rate Limit

```
AgentService            LLMFactory         Gemini          Claude
    │                      │                 │               │
    ├─generate_content────→│                 │               │
    │   (prompt, config)   │                 │               │
    │                      ├─[Attempt 1]    │               │
    │                      ├─generate──────→│               │
    │                      │                 │               │
    │                      │      ✗ 429      │               │
    │                      │←────────────────┤               │
    │                      │  "Quota exceeded"
    │                      │                 │               │
    │                      ├─Detect 429 error               │
    │                      ├─[Attempt 2-5: Retry with backoff]
    │                      │  (delays: 5s, 10s, 20s, 40s)  │
    │                      │                 │               │
    │                      │      ✗ 429      │               │
    │                      │←────────────────┤               │
    │                      │                 │               │
    │                      ├─All retries failed             │
    │                      ├─Switch to Claude               │
    │                      │                 │               │
    │                      ├─generate──────────────────────→│
    │                      │                 │               │
    │                      │                 │    ✓ response
    │                      │                 │←──────────────┤
    │                      │                 │               │
    │    LLMResponse       │
    │←──────────LLMResponse────────────────────────────────→│
    │  (text, model_name)  │
    │                      │
    └─ Continue processing
```

## Configuration Examples

### Example 1: Gemini → Claude
```
LLM_PRIMARY_PROVIDER=gemini
LLM_FALLBACK_PROVIDERS=claude
GOOGLE_API_KEY=gsk_...
ANTHROPIC_API_KEY=sk_...
```

### Example 2: Multiple Fallbacks
```
LLM_PRIMARY_PROVIDER=gemini
LLM_FALLBACK_PROVIDERS=claude,openai_provider,custom_provider
GOOGLE_API_KEY=gsk_...
ANTHROPIC_API_KEY=sk_...
OPENAI_API_KEY=sk-...
```

### Example 3: Production Redundancy
```
LLM_PRIMARY_PROVIDER=claude
LLM_FALLBACK_PROVIDERS=gemini,custom_llm
ANTHROPIC_API_KEY=sk_...
GOOGLE_API_KEY=gsk_...
CUSTOM_LLM_KEY=...
LLM_RETRY_MAX_ATTEMPTS=10
LLM_RETRY_DELAY_SECONDS=10
```
