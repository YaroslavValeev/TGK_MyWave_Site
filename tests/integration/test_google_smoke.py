import json
import os

import pytest


def test_google_service_account_json_exists_and_valid():
	"""Smoke test: verify that the service account JSON file exists and can be parsed.

	This test is intended for CI integration job only. It will fail quickly with
	a helpful message if the secret wasn't provided or the JSON is invalid.
	"""
	path = os.path.join('instance', 'service_account.json')
	assert os.path.exists(path), f"Service account file not found at {path}. Ensure CI wrote it from secret."

	with open(path, 'r', encoding='utf-8') as f:
		try:
			data = json.load(f)
		except json.JSONDecodeError as e:
			pytest.fail(f"service_account.json is not valid JSON: {e}")

	# Basic sanity: must contain client_email and private_key
	assert 'client_email' in data and data.get('client_email'), 'service_account.json missing client_email'
	assert 'private_key' in data and data.get('private_key'), 'service_account.json missing private_key'
