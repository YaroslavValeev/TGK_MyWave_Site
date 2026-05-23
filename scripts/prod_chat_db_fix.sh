#!/usr/bin/env bash
# Обратная совместимость: полный деплой чата и сайта.
exec bash "$(dirname "$0")/prod_deploy_site.sh" "$@"
