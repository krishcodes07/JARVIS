# Adding New Providers

JARVIS uses a **protocol pattern** where one protocol implementation handles many providers.

## No-Code Method (JSON Only)

If your provider uses an OpenAI-compatible API (most do), just add an entry to `config/providers.json`:

```json
{
  "name": "your_provider",
  "display_name": "Your Provider",
  "protocol": "openai",
  "base_url": "https://api.yourprovider.com/v1",
  "api_key_env": "YOUR_PROVIDER_API_KEY",
  "default_model": "your-model-id",
  "supports": ["text", "streaming", "tools"]
}
```

Then add your API key to `.env`:

```env
YOUR_PROVIDER_API_KEY=your_key_here
```

That's it! No code changes needed.

## Custom Protocol

If your provider has a unique API format, create a new protocol:

1. Create `src/jarvis/providers/protocols/your_protocol.py`
2. Subclass `BaseProvider` and implement `generate()`, `stream()`, and `embed()`
3. Add the protocol to `ProviderManager._create_protocol()`
4. Register providers using `"protocol": "your_protocol"` in providers.json
