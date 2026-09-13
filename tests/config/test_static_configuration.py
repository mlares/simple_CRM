import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders

from simple_crm.config.settings import base


def test_static_configuration_uses_whitenoise_manifest_storage() -> None:
    assert base.MIDDLEWARE[1] == "whitenoise.middleware.WhiteNoiseMiddleware"
    assert (
        base.STORAGES["staticfiles"]["BACKEND"]
        == "simple_crm.config.static_storage.CrmStaticFilesStorage"
    )
    assert base.STATIC_ROOT.name == "staticfiles"
    assert (
        settings.STORAGES["staticfiles"]["BACKEND"]
        == "django.contrib.staticfiles.storage.StaticFilesStorage"
    )


def test_vendor_manifest_records_official_local_asset_contract() -> None:
    manifest_path = Path(settings.BASE_DIR) / "THIRD_PARTY_LICENSES/vendor-assets.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assets = {asset["name"]: asset for asset in manifest["assets"]}
    assert set(assets) == {"Bootstrap", "HTMX"}
    assert (
        assets["Bootstrap"]["version"],
        assets["Bootstrap"]["license"],
        assets["Bootstrap"]["license_header"],
    ) == ("5.3.8", "MIT", "The MIT License (MIT)")
    assert (
        assets["HTMX"]["version"],
        assets["HTMX"]["license"],
        assets["HTMX"]["license_header"],
    ) == ("2.0.10", "0BSD", "Zero-Clause BSD")
    for asset in assets.values():
        content_path = Path(settings.BASE_DIR) / asset["local_path"]
        license_path = Path(settings.BASE_DIR) / asset["license_path"]
        assert asset["status"] == "verified"
        assert f"@{asset['version']}" in asset["source_url"]
        assert content_path.is_file()
        assert license_path.is_file()
        assert hashlib.sha256(content_path.read_bytes()).hexdigest() == asset["sha256"]
        assert (
            hashlib.sha256(license_path.read_bytes()).hexdigest()
            == asset["license_sha256"]
        )
        assert license_path.read_text(encoding="utf-8").startswith(
            asset["license_header"]
        )

    assert finders.find("vendor/bootstrap/5.3.8/bootstrap.min.css")
    assert finders.find("vendor/htmx/2.0.10/htmx.min.js")
