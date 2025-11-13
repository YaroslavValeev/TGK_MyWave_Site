import json
from app.ai.core_gateway import CoreAIGateway, MockOpenAIClient, ToolDefinition


def test_mock_gateway_basic_reply():
    client = MockOpenAIClient()
    gw = CoreAIGateway(client, system_prompt='test')
    resp = gw.handle_message('hello world')
    assert resp['type'] == 'assistant'
    assert 'hello world' in resp['text']


def test_tool_registration_and_call():
    client = MockOpenAIClient()
    gw = CoreAIGateway(client, system_prompt='test')

    def sample_tool(payload):
        return {'ok': True, 'payload': payload}

    tool = ToolDefinition(name='sample', description='sample tool')
    gw.register_tool(tool, sample_tool)

    # Trigger the mock client to request a tool call
    call_msg = '__call_tool__:sample:' + json.dumps({'x': 1})
    resp = gw.handle_message(call_msg)
    assert resp['type'] == 'tool_result'
    assert resp['tool'] == 'sample'
    assert resp['result']['ok'] is True
    assert resp['result']['payload']['x'] == 1


def test_unknown_tool_results_in_error():
    client = MockOpenAIClient()
    gw = CoreAIGateway(client, system_prompt='test')
    call_msg = '__call_tool__:nope:{}'.format('{}')
    resp = gw.handle_message(call_msg)
    assert resp['type'] == 'tool_error' or resp.get('error') is not None
