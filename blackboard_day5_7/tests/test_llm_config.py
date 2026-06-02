from app.llm.config import LLMConfig, load_config, save_settings


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.delenv("ATLAS_CLOUD_BASE_URL", raising=False)
    monkeypatch.delenv("ATLAS_CLOUD_API_KEY", raising=False)
    monkeypatch.delenv("ATLAS_CLOUD_MODEL", raising=False)
    settings = tmp_path / "atlas_settings.json"

    cfg = save_settings(
        {
            "mode": "cloud",
            "cloud_base_url": "https://api.groq.com/openai/v1",
            "cloud_api_key": "gsk_secret_value_123456",
            "cloud_model": "llama-3.3-70b-versatile",
        },
        settings_path=settings,
    )
    assert cfg.mode == "cloud"
    assert cfg.cloud_configured is True

    reloaded = load_config(settings)
    assert reloaded.cloud_model == "llama-3.3-70b-versatile"
    assert reloaded.cloud_api_key == "gsk_secret_value_123456"


def test_blank_api_key_does_not_wipe_existing(tmp_path):
    settings = tmp_path / "atlas_settings.json"
    save_settings({"cloud_api_key": "keep-me", "cloud_base_url": "x", "cloud_model": "m"}, settings_path=settings)
    # second update without api key (UI editing other fields)
    cfg = save_settings({"cloud_model": "m2"}, settings_path=settings)
    assert cfg.cloud_api_key == "keep-me"
    assert cfg.cloud_model == "m2"


def test_public_dict_hides_api_key():
    cfg = LLMConfig(cloud_base_url="x", cloud_api_key="super-secret", cloud_model="m")
    public = cfg.public_dict()
    assert public["cloud_api_key"] == ""
    assert public["cloud_api_key_set"] is True
    assert public["cloud_configured"] is True
    assert "super-secret" not in str(public)


def test_invalid_mode_falls_back_to_hybrid(tmp_path):
    settings = tmp_path / "atlas_settings.json"
    save_settings({"mode": "nonsense"}, settings_path=settings)
    assert load_config(settings).mode == "hybrid"
