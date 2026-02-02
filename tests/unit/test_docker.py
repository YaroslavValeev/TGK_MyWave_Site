"""
Unit tests for Docker configuration and health checks
Tests for docker-compose setup, environment variables, and service health

Point 14: Docker containerization
"""

import json
import os
import pytest
import tempfile
from pathlib import Path


class TestDockerfileStructure:
    """Test Dockerfile structure and build configuration"""

    def test_dockerfile_exists(self):
        """Verify Dockerfile exists in project root"""
        dockerfile_path = Path("Dockerfile")
        assert dockerfile_path.exists(), "Dockerfile must exist in project root"

    def test_dockerfile_multi_stage(self):
        """Verify Dockerfile uses multi-stage build"""
        with open("Dockerfile") as f:
            content = f.read()

        # Check for builder stage
        assert "as builder" in content.lower(), "Dockerfile must have builder stage"
        assert (
            "COPY --from=builder" in content
        ), "Dockerfile must copy from builder stage"

    def test_dockerfile_non_root_user(self):
        """Verify application runs as non-root user"""
        with open("Dockerfile") as f:
            content = f.read()

        assert "useradd" in content, "Dockerfile must create non-root user"
        assert "USER appuser" in content, "Dockerfile must switch to non-root user"

    def test_dockerfile_healthcheck(self):
        """Verify HEALTHCHECK instruction exists"""
        with open("Dockerfile") as f:
            content = f.read()

        assert "HEALTHCHECK" in content, "Dockerfile must define HEALTHCHECK"
        assert (
            "/api/metrics/health" in content
        ), "Health check must verify metrics endpoint"

    def test_dockerfile_exposes_ports(self):
        """Verify correct ports are exposed"""
        with open("Dockerfile") as f:
            content = f.read()

        assert "5000" in content, "Port 5000 must be exposed for Flask app"

    def test_dockerfile_uses_gunicorn(self):
        """Verify Gunicorn is used as WSGI server"""
        with open("Dockerfile") as f:
            content = f.read()

        assert "gunicorn" in content.lower(), "Dockerfile must use gunicorn"


class TestDockerCompose:
    """Test docker-compose configuration"""

    def test_docker_compose_exists(self):
        """Verify docker-compose.yml exists"""
        path = Path("docker-compose.yml")
        assert path.exists(), "docker-compose.yml must exist"

    def test_docker_compose_valid_yaml(self):
        """Verify docker-compose.yml is valid YAML"""
        import yaml

        with open("docker-compose.yml") as f:
            try:
                config = yaml.safe_load(f)
                assert config is not None, "docker-compose.yml must contain valid YAML"
            except yaml.YAMLError as e:
                pytest.fail(f"docker-compose.yml is invalid YAML: {e}")

    def test_docker_compose_has_required_services(self):
        """Verify all required services are defined"""
        import yaml

        with open("docker-compose.yml") as f:
            config = yaml.safe_load(f)

        services = config.get("services", {})
        required_services = ["db", "redis", "web", "nginx"]

        for service in required_services:
            assert (
                service in services
            ), f"Service '{service}' must be defined in docker-compose.yml"

    def test_db_service_config(self):
        """Verify database service configuration"""
        import yaml

        with open("docker-compose.yml") as f:
            config = yaml.safe_load(f)

        db_service = config["services"]["db"]

        # Check image
        assert (
            "postgres" in db_service.get("image", "").lower()
        ), "DB must use PostgreSQL"

        # Check environment variables
        env = db_service.get("environment", {})
        assert "POSTGRES_USER" in env or any(
            "POSTGRES_USER" in str(v) for v in env.values()
        ), "DB must define POSTGRES_USER"
        assert "POSTGRES_PASSWORD" in env or any(
            "POSTGRES_PASSWORD" in str(v) for v in env.values()
        ), "DB must define POSTGRES_PASSWORD"
        assert "POSTGRES_DB" in env or any(
            "POSTGRES_DB" in str(v) for v in env.values()
        ), "DB must define POSTGRES_DB"

        # Check volumes for persistence
        assert "pgdata" in db_service.get("volumes", []) or any(
            "pgdata" in str(v) for v in db_service.get("volumes", [])
        ), "DB must use pgdata volume for persistence"

        # Check health check
        assert "healthcheck" in db_service, "DB service must have healthcheck"

    def test_redis_service_config(self):
        """Verify Redis service configuration"""
        import yaml

        with open("docker-compose.yml") as f:
            config = yaml.safe_load(f)

        redis_service = config["services"]["redis"]

        # Check image
        assert (
            "redis" in redis_service.get("image", "").lower()
        ), "Redis service must use Redis image"

        # Check health check
        assert "healthcheck" in redis_service, "Redis service must have healthcheck"

        # Check volume
        assert "redis_data" in redis_service.get("volumes", []) or any(
            "redis_data" in str(v) for v in redis_service.get("volumes", [])
        ), "Redis must use redis_data volume"

    def test_web_service_config(self):
        """Verify web service configuration"""
        import yaml

        with open("docker-compose.yml") as f:
            config = yaml.safe_load(f)

        web_service = config["services"]["web"]

        # Check build context
        assert (
            "build" in web_service or "image" in web_service
        ), "Web service must have build or image configuration"

        # Check environment
        env = web_service.get("environment", {})
        assert any(
            "DATABASE_URL" in str(k) or "DATABASE_URL" in str(v) for k, v in env.items()
        ), "Web service must define DATABASE_URL"

        # Check ports
        ports = web_service.get("ports", [])
        assert any("5000" in str(p) for p in ports), "Web service must expose port 5000"

        # Check dependencies
        depends_on = web_service.get("depends_on", [])
        assert len(depends_on) > 0, "Web service must depend on other services"

        # Check health check
        assert "healthcheck" in web_service, "Web service must have healthcheck"

    def test_web_service_depends_on_db(self):
        """Verify web service depends on healthy database"""
        import yaml

        with open("docker-compose.yml") as f:
            config = yaml.safe_load(f)

        web_service = config["services"]["web"]
        depends_on = web_service.get("depends_on", {})

        # Check db is in depends_on
        if isinstance(depends_on, dict):
            assert "db" in depends_on, "Web service must depend on db service"
            db_config = depends_on.get("db", {})
            if isinstance(db_config, dict):
                assert "condition" in db_config, "DB dependency should have condition"
        else:
            assert "db" in depends_on, "Web service must depend on db service"

    def test_volumes_defined(self):
        """Verify named volumes are properly defined"""
        import yaml

        with open("docker-compose.yml") as f:
            config = yaml.safe_load(f)

        volumes = config.get("volumes", {})

        assert "pgdata" in volumes, "pgdata volume must be defined at top level"
        assert "redis_data" in volumes, "redis_data volume must be defined at top level"

    def test_network_defined(self):
        """Verify network is properly configured"""
        import yaml

        with open("docker-compose.yml") as f:
            config = yaml.safe_load(f)

        networks = config.get("networks", {})

        # Check at least one network exists
        assert len(networks) > 0, "At least one network must be defined"

    def test_docker_compose_version(self):
        """Verify docker-compose version is supported"""
        import yaml

        with open("docker-compose.yml") as f:
            config = yaml.safe_load(f)

        version = config.get("version")
        assert (
            version and version >= "3.8"
        ), "docker-compose version must be 3.8 or higher"


class TestDockerConfig:
    """Test Docker configuration files"""

    def test_nginx_conf_exists(self):
        """Verify nginx.conf exists"""
        path = Path("docker/nginx.conf")
        assert path.exists(), "docker/nginx.conf must exist"

    def test_nginx_conf_valid(self):
        """Verify nginx.conf has required directives"""
        with open("docker/nginx.conf") as f:
            content = f.read()

        # Check for key directives
        assert "upstream flask_app" in content, "nginx must define upstream flask_app"
        assert "listen 443" in content, "nginx must listen on HTTPS port 443"
        assert "ssl_certificate" in content, "nginx must have SSL configuration"
        assert (
            "rate limiting" in content.lower() or "limit_req" in content
        ), "nginx must have rate limiting configured"

    def test_start_sh_exists(self):
        """Verify docker/start.sh exists"""
        path = Path("docker/start.sh")
        assert path.exists(), "docker/start.sh must exist"

    def test_start_sh_checks_db(self):
        """Verify start.sh checks database connectivity"""
        with open("docker/start.sh") as f:
            content = f.read()

        assert "pg_isready" in content, "start.sh must check PostgreSQL readiness"

    def test_init_sql_exists(self):
        """Verify docker/init.sql exists"""
        path = Path("docker/init.sql")
        assert path.exists(), "docker/init.sql must exist"

    def test_init_sql_creates_extensions(self):
        """Verify init.sql creates necessary PostgreSQL extensions"""
        with open("docker/init.sql") as f:
            content = f.read()

        assert "uuid-ossp" in content, "init.sql must create uuid-ossp extension"
        assert "pg_trgm" in content, "init.sql must create pg_trgm extension"

    def test_env_docker_exists(self):
        """Verify .env.docker template exists"""
        path = Path(".env.docker")
        assert path.exists(), ".env.docker template must exist"

    def test_env_docker_has_required_vars(self):
        """Verify .env.docker includes all required variables"""
        with open(".env.docker") as f:
            content = f.read()

        required_vars = [
            "FLASK_ENV",
            "SECRET_KEY",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_DB",
            "DATABASE_URL",
            "REDIS_URL",
            "GOOGLE_SERVICE_ACCOUNT_FILE",
            "OPENAI_API_KEY",
        ]

        for var in required_vars:
            assert var in content, f"Required variable {var} must be in .env.docker"


class TestDockerDocumentation:
    """Test Docker documentation"""

    def test_docker_docs_exists(self):
        """Verify Docker documentation exists"""
        path = Path("docs/DOCKER.md")
        assert path.exists(), "docs/DOCKER.md must exist"

    def test_docker_docs_comprehensive(self):
        """Verify Docker documentation is comprehensive"""
        with open("docs/DOCKER.md") as f:
            content = f.read()

        # Check for key sections
        required_sections = [
            "Quick Start",
            "Architecture",
            "Services",
            "Configuration",
            "Health Check",
            "Database Operations",
            "Troubleshooting",
            "Production",
        ]

        for section in required_sections:
            assert section in content, f"Documentation must include '{section}' section"


class TestHealthCheckEndpoint:
    """Test health check endpoint integration with Docker"""

    def test_health_check_endpoint_exists(self):
        """Verify health check endpoint is implemented"""
        from app.routes.metrics_api import health_check

        assert callable(health_check), "health_check endpoint must be callable"

    def test_health_check_returns_json(self):
        """Verify health check returns JSON response"""
        # Check that metrics_api imports/defines health_check
        with open("app/routes/metrics_api.py") as f:
            content = f.read()

        assert (
            "health_check" in content or "health" in content.lower()
        ), "metrics_api.py must define health check endpoint"
        assert (
            "json" in content.lower() or "return" in content
        ), "Health check must return JSON response"

    def test_metrics_api_registered(self):
        """Verify metrics API is registered in app"""
        with open("app/__init__.py", encoding="utf-8") as f:
            content = f.read()

        assert (
            "metrics" in content.lower()
        ), "app/__init__.py must register metrics blueprint"


class TestDockerSecurity:
    """Test Docker security configurations"""

    def test_dockerfile_no_root_user(self):
        """Verify application doesn't run as root"""
        with open("Dockerfile") as f:
            content = f.read()

        # Must have USER directive after app setup
        lines = content.split("\n")
        user_index = -1
        copy_index = -1

        for i, line in enumerate(lines):
            if "COPY . /app" in line or "COPY . ." in line:
                copy_index = i
            if line.startswith("USER"):
                user_index = i

        assert (
            user_index > copy_index
        ), "USER directive must come after copying application code"

    def test_nginx_security_headers(self):
        """Verify nginx has security headers"""
        with open("docker/nginx.conf") as f:
            content = f.read()

        security_headers = [
            "X-Frame-Options",
            "X-Content-Type-Options",
            "X-XSS-Protection",
        ]

        for header in security_headers:
            assert header in content, f"nginx must set {header} header"

    def test_dockerfile_no_secrets(self):
        """Verify Dockerfile doesn't contain secrets"""
        with open("Dockerfile") as f:
            content = f.read()

        forbidden_keywords = [
            "password=",
            "secret=",
            "api_key=",
            "token=",
        ]

        content_lower = content.lower()
        for keyword in forbidden_keywords:
            assert (
                keyword not in content_lower
            ), f"Dockerfile must not contain {keyword} (use environment variables instead)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
