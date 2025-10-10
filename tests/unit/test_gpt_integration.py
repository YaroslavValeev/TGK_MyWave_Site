def test_ask_gpt(mocker):
    mock = mocker.patch('app.services.openai_service.ask', return_value='Тестовый ответ')
    from app.services.openai_service import ask
    result = ask('Привет!')
    assert result == 'Тестовый ответ'
    mock.assert_called_once() 