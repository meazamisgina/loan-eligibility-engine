import ingest


def test_package_is_importable() -> None:
    package_name = ingest.__name__
    assert package_name == "ingest"