# AI Tools for Site Concierge

## Overview

The AI concierge can use various tools to help users with bookings, FAQ lookup, and service information. All tools are validated using JSON schemas before execution.

## Available Tools

### 1. get_services

Get a list of available services/projects with optional filtering.

**Schema:**
```json
{
  "type": "object",
  "properties": {
    "city": {"type": ["string", "null"]},
    "tags": {
      "type": "array",
      "items": {"type": "string"}
    }
  },
  "additionalProperties": false
}
```

**Example Payload:**
```json
{
  "city": null,
  "tags": ["обучение", "интенсив"]
}
```

**Response:**
```json
{
  "services": [
    {
      "slug": "wsc",
      "title": "Wake School Camp",
      "description": "Интенсивный курс обучения...",
      "image": "images/projects/wsc/cover.webp",
      "detail": true,
      "tags": ["обучение", "интенсив", "лето"]
    }
  ]
}
```

### 2. get_available_slots

Get available time slots for a specific service and date.

**Schema:**
```json
{
  "type": "object",
  "properties": {
    "service_id": {"type": "string"},
    "date": {"type": "string", "format": "date"}
  },
  "required": ["service_id", "date"],
  "additionalProperties": false
}
```

**Example Payload:**
```json
{
  "service_id": "wsc",
  "date": "2025-10-01"
}
```

**Response:**
```json
{
  "service_id": "wsc",
  "date": "2025-10-01",
  "slots": [
    {
      "time": "09:00",
      "available": 2,
      "max": 4,
      "booked": 2
    },
    {
      "time": "11:00",
      "available": 4,
      "max": 4,
      "booked": 0
    }
  ]
}
```

### 3. create_booking

Create a booking for a service.

**Schema:**
```json
{
  "type": "object",
  "properties": {
    "service_id": {"type": "string"},
    "date": {"type": "string", "format": "date"},
    "slot": {"type": "string"},
    "name": {"type": "string"},
    "phone": {"type": "string"},
    "email": {"type": ["string", "null"], "format": "email"}
  },
  "required": ["service_id", "date", "slot", "name", "phone"],
  "additionalProperties": false
}
```

**Example Payload:**
```json
{
  "service_id": "wsc",
  "date": "2025-10-01",
  "slot": "11:00",
  "name": "Иван Иванов",
  "phone": "+79123456789",
  "email": "ivan@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "confirm_text": "Запись успешно создана!",
  "service_id": "wsc",
  "email": "ivan@example.com"
}
```

### 4. get_faq_answer

Search FAQ and knowledge base for an answer to a question.

**Schema:**
```json
{
  "type": "object",
  "properties": {
    "question": {"type": "string"}
  },
  "required": ["question"],
  "additionalProperties": false
}
```

**Example Payload:**
```json
{
  "question": "Какова стоимость тренировок?"
}
```

**Response:**
```json
{
  "question": "Какова стоимость тренировок?",
  "answer": "Стоимость тренировок зависит от выбранного пакета...",
  "source": "static_faq"
}
```

**Response Sources:**
- `static_faq`: Answer found in static FAQ file
- `fallback`: Generic fallback response
- `not_found`: No answer found
- `error`: Error occurred during search

## Validation

All tool inputs are validated against their schemas before execution. Validation failures:
1. Increment the `mywave_ai_gateway_tool_validation_failures_total` Prometheus counter
2. Return an error response with `type: "error"` and `error: "invalid_payload"`

**Example Validation Error Response:**
```json
{
  "type": "error",
  "error": "invalid_payload",
  "tool": "create_booking",
  "message": "'service_id' is a required property"
}
```

## Tool Registration

Tools are registered automatically on application startup via `app.ai.register_tools.register_default_tools()`. The registration process:
1. Imports the gateway instance
2. Defines tool adapter functions
3. Registers each tool with its schema using `ToolDefinition`
4. Logs success or failure

## Error Handling

Tool execution errors are caught and returned as:
```json
{
  "type": "tool_error",
  "tool": "tool_name",
  "error": "Error message"
}
```

Validation errors are returned as:
```json
{
  "type": "error",
  "error": "invalid_payload",
  "tool": "tool_name",
  "message": "Validation error details"
}
```

## Metrics

Tool usage is tracked via Prometheus metrics:
- `mywave_ai_gateway_tool_calls_total`: Total tool call requests
- `mywave_ai_gateway_tool_results_total`: Successful tool executions
- `mywave_ai_gateway_tool_validation_failures_total`: Validation failures

### 5. get_showcase_itinerary (v1)

Return the itinerary/program for a Safari or Challenge showcase.

**Schema:** `ai.tools.showcase.itinerary.v1`
```json
{
  "$id": "ai.tools.showcase.itinerary.v1",
  "type": "object",
  "properties": {
    "showcase_id": {"type": "string", "minLength": 3, "maxLength": 64},
    "date": {"type": ["string", "null"], "pattern": "^\\d{1,2}$"}
  },
  "required": ["showcase_id"],
  "additionalProperties": false
}
```

**Example Payload:**
```json
{
  "showcase_id": "wakesurf_safari",
  "date": null
}
```

**Response:**
```json
{
  "showcase_id": "wakesurf_safari",
  "itinerary": [
    {"day": 1, "title": "Самара — welcome day", "description": "Трансфер, знакомство"}
  ]
}
```

### 6. get_challenge_leaderboard (v1)

Return leaderboard entries for a challenge-style showcase.

**Schema:** `ai.tools.showcase.leaderboard.v1`
```json
{
  "$id": "ai.tools.showcase.leaderboard.v1",
  "type": "object",
  "properties": {
    "showcase_id": {"type": "string"},
    "limit": {"type": "integer", "minimum": 1, "maximum": 50}
  },
  "required": ["showcase_id"],
  "additionalProperties": false
}
```

**Response:**
```json
{
  "showcase_id": "sochi_camp",
  "entries": [
    {"rider": "Анна С.", "score": 95}
  ]
}
```

### 7. join_challenge (v1)

Register a participant in a challenge leaderboard or Safari waitlist.

**Schema:** `ai.tools.showcase.join_challenge.v1`
```json
{
  "$id": "ai.tools.showcase.join_challenge.v1",
  "type": "object",
  "properties": {
    "showcase_id": {"type": "string"},
    "name": {"type": "string", "minLength": 2},
    "city": {"type": ["string", "null"]},
    "experience_level": {"type": ["string", "null"]},
    "channel": {"type": ["string", "null"]}
  },
  "required": ["showcase_id", "name"],
  "additionalProperties": false
}
```

**Response:**
```json
{
  "ok": true,
  "showcase_id": "sochi_camp",
  "participant": {
    "name": "Иван", "city": "Москва", "experience_level": "intermediate"
  }
}
```

> ℹ️ Версионирование: при изменении структуры добавляйте новую схему `...v2` и сохраняйте обработчики для предыдущих версий в шлюзе AI, чтобы не ломать интеграции.

