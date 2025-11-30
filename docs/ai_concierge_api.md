# AI Concierge API Documentation

## Overview

The AI Concierge API provides a chat interface for site visitors to interact with an AI assistant. It uses the Core AI Gateway to handle messages and can invoke tools for booking, FAQ lookup, and service information.

## Endpoint

### POST `/api/concierge/message`

Send a message to the AI concierge and receive a response.

#### Request

## Headers:

- `Content-Type: application/json`

## Body:

```json
{
  "message": "Привет! Какие услуги у вас есть?",
  "user_id": "optional-user-id",
  "context": {
    "page": "home",
    "lang": "ru"
  }
}
```

## Fields:

- `message` (required, string): The user's message (max 4000 characters)
- `user_id` (optional, string): Unique identifier for the user (used for rate limiting and context)
- `context` (optional, object): Additional context for the request
  - `page` (optional, string): Current page name
  - `lang` (optional, string): Language code (e.g., "ru", "en")

### Response

## Success (200):

```json
{
  "type": "assistant",
  "text": "Привет! У нас есть следующие услуги..."
}
```

Or with tool result:

```json
{
  "type": "tool_result",
  "tool": "get_services",
  "result": {
    "services": [...]
  }
}
```

## Validation Error (400):

```json
{
  "error": "message required"
}
```

## Rate Limit Exceeded (429):

```json
{
  "error": "rate_limit_exceeded"
}
```

## Server Error (500):

```json
{
  "error": "Internal server error message"
}
```

## Examples

### Basic Chat

```bash
curl -X POST http://localhost:5000/api/concierge/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Какие услуги вы предлагаете?"
  }'
```

### With Context

```bash
curl -X POST http://localhost:5000/api/concierge/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Когда доступны тренировки?",
    "user_id": "user-123",
    "context": {
      "page": "booking",
      "lang": "ru"
    }
  }'
```

## Rate Limiting

If `AI_GATEWAY_ENABLE_RATE_LIMIT` is enabled in configuration, rate limiting is applied per user. The rate limit defaults to 60 requests per 60 seconds.

Rate limiting is keyed by:
1. `user_id` (if provided)
2. `request.remote_addr` (if `user_id` is missing)
3. `'anon'` (if both are missing)

## Metrics

The endpoint increments the `mywave_concierge_requests_total` Prometheus counter for each request.

## Configuration

The concierge endpoint behavior can be configured via environment variables:

- `AI_GATEWAY_ENABLE_RATE_LIMIT`: Enable/disable rate limiting (default: `False`)
- `AI_GATEWAY_RATE_LIMIT_COUNT`: Maximum requests per window (default: `60`)
- `AI_GATEWAY_RATE_LIMIT_WINDOW`: Time window in seconds (default: `60`)
- `MYWAVE_AI_MODE`: AI Gateway mode (`mock` or `real`, default: `mock`)
- `MYWAVE_AI_SYSTEM_PROMPT`: System prompt for the AI (default: "You are a helpful assistant for MyWave.")

