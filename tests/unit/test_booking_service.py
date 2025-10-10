def test_create_booking_success(mocker):
    mocker.patch('app.services.booking_service.save_to_db', return_value=True)
    from app.services.booking_service import create_booking
    result = create_booking({'name': 'Иван', 'date': '2024-07-01'})
    assert result['success'] 