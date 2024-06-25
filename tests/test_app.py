def test_app_hello_world_success(sapinvoices_client):
    response = sapinvoices_client.get("/")
    assert response.status_code == 200  # noqa: PLR2004
    assert b"Hello, World! WORKSPACE=test" in response.data
