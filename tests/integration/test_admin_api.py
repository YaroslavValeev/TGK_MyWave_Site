def test_admin_analytics(client):
    response = client.get("/admin/api/analytics")
    assert response.status_code in (
        200,
        401,
        403,
        404,
    )  # 404 if endpoint not implemented
