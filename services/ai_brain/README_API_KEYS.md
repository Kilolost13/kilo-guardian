# API Keys Configuration

## Brave Search API

The AI Brain uses Brave Search API for internet search capabilities.

### Setup

1. Sign up at https://brave.com/search/api/
2. Get your API key (format: BSAxxxxxxxxxxxxx...)
3. Add to Kubernetes deployment:

```bash
kubectl set env deployment/kilo-ai-brain -n kilo-guardian \
  BRAVE_API_KEY="YOUR_API_KEY_HERE"
```

### Security

- API key stored as Kubernetes Secret/EnvVar (never committed to git)
- Key accessed via os.environ.get("BRAVE_API_KEY") 
- No hardcoded secrets in source code
- .gitignore protects .env files

### Free Tier Limits

- 2,000 searches/month (~66/day)
- Rate limit errors handled gracefully
- Quota resets monthly

### Testing

Verify key is set:
kubectl exec -n kilo-guardian deployment/kilo-ai-brain -- env | grep BRAVE_API_KEY
