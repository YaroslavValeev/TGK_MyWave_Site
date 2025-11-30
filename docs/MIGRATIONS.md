# Database Migrations Guide

## Overview

This project uses Alembic for database migrations. Alembic is a lightweight database migration tool for SQLAlchemy.

## Current Migrations

### Existing migrations:

- `e89ecaa2c591` - Add email to user table
- `b2f4a6c8d9e1` - Add unique constraint on booking date/time/phone
- `b2a005fd0c4b` - Add image model and blog post image relationship
- `30bb9011ac3c` - Create blog_post and chat_message tables
- `f3c72d1a9b4e` - Add participant and safari_booking tables (latest)

## Core Models with Migrations

### Participant Table

- `id` (Integer, Primary Key)
- `name` (String 128)
- `email` (String 256, Unique)
- `phone` (String 32, optional)
- `level` (String 64, optional)
- `route_id` (Integer, optional)
- `created_at` (DateTime)

### SafariBooking Table

- `id` (Integer, Primary Key)
- `participant_id` (Integer, Foreign Key → participant)
- `status` (String 32, default: 'pending')
- `start_date` (Date)
- `days` (Integer)
- `message` (Text, optional)
- `route_id` (Integer, optional)
- `created_at` (DateTime)

## Migration Commands

### Generate a new migration

```bash
flask db migrate -m "Description of changes"
```

### Apply pending migrations (upgrade)

```bash
flask db upgrade
```

### Rollback to previous version (downgrade)

```bash
flask db downgrade
```

### View migration history

```bash
flask db current  # Show current version
flask db history  # Show all versions
```

### Downgrade to specific version

```bash
flask db downgrade <revision>
```

## Adding New Models

When adding a new model to `app/database/models.py`:

1. **Create the model class** with proper SQLAlchemy definitions
2. **Generate migration**: `flask db migrate -m "Add <ModelName> model"`
3. **Review generated migration** in `migrations/versions/`
4. **Apply migration**: `flask db upgrade`
5. **Test upgrade/downgrade** locally

## Testing Migrations

Run unit tests to verify migration structure:

```bash
pytest tests/unit/test_migrations.py -v
```

This verifies:
- Migration files exist and are valid Python
- Upgrade/downgrade functions are properly defined
- Migration chain is valid
- Key models (Participant, SafariBooking) have migrations

## Troubleshooting

### Migration conflicts

If multiple migrations target the same revision, resolve by:
1. Check `down_revision` in conflicting files
2. Reorder migration files or rename them
3. Ensure linear chain: A → B → C

### Migration failed

```bash
# Rollback failed migration
flask db downgrade -1

# Check current version
flask db current

# Review migration file for errors
```

### Circular dependencies

Avoid circular foreign key constraints. Use nullable foreign keys or separate migrations if needed.

## Best Practices

1. **Always test migrations locally** before deploying
2. **Keep migrations small** - one logical change per migration
3. **Name migrations descriptively** - e.g., "Add Safari booking fields"
4. **Never edit applied migrations** - create a new migration instead
5. **Test both upgrade AND downgrade** on production-like data
6. **Document schema changes** in migration docstring

## Production Deployment

```bash
# On production server
flask db upgrade  # Apply pending migrations

# Monitor for errors:
# - Check application logs
# - Verify data integrity
# - Monitor database performance
```

## Migration Status

✅ **All core models have migrations**:
- User (email field)
- Booking (constraints)
- Image & BlogPost
- Participant & SafariBooking

Current database state can be verified with:

```bash
flask db current
```
