from app.privacy.outbound_guard import REDACTION, has_pii, scrub_outbound


def test_scrubs_email_phone_and_id():
    text = "联系我 zhang.san@example.com 或 13812345678，身份证 11010119900307123X。"
    scrubbed, flags = scrub_outbound(text)
    assert "example.com" not in scrubbed
    assert "13812345678" not in scrubbed
    assert "11010119900307123X" not in scrubbed
    assert scrubbed.count(REDACTION) >= 3
    assert flags.get("email") == 1
    assert flags.get("phone") == 1
    assert flags.get("national_id") == 1


def test_scrubs_api_keys_and_credentials():
    text = "use sk-abcdef0123456789ABCD and password: hunter2 and token=xyz123abc"
    scrubbed, flags = scrub_outbound(text)
    assert "sk-abcdef0123456789ABCD" not in scrubbed
    assert "hunter2" not in scrubbed
    assert flags.get("api_key", 0) >= 1
    assert flags.get("credential", 0) >= 1


def test_clean_text_is_untouched():
    text = "请解释一下哈希表的时间复杂度和冲突处理方式。"
    scrubbed, flags = scrub_outbound(text)
    assert scrubbed == text
    assert flags == {}
    assert has_pii(text) is False


def test_empty_input():
    assert scrub_outbound("") == ("", {})
