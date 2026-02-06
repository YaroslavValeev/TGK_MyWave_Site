def test_create_user(mocker):
    mock = mocker.patch("app.services.user_service.save_user", return_value=True)
    from app.services.user_service import create_user

    result = create_user(
        {"username": "test", "email": "test@mail.com", "password": "1234"}
    )
    assert result["success"]
    mock.assert_called_once()
