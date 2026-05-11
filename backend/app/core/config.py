import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BASE_DIR.parent


def load_env_files() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return

    for path in [ROOT_DIR / ".env", BASE_DIR / ".env"]:
        if path.exists():
            load_dotenv(path, override=False)


load_env_files()


PLACEHOLDER_OPENAI_API_KEYS = {
    "replace_with_your_openai_api_key",
    "your-api-key",
    "your_api_key_here",
}


def env_value(name: str, default: str = "") -> str:
    value = os.getenv(name, default).strip()
    return value


def openai_api_key_from_env() -> str:
    api_key = env_value("OPENAI_API_KEY")
    if api_key in PLACEHOLDER_OPENAI_API_KEYS:
        return ""
    return api_key


class Settings:
    app_name = "AI Admin Agent MVP"
    database_path = Path(env_value("ADMIN_AGENT_DB", str(BASE_DIR / "admin_agent.db")))
    openai_api_key = openai_api_key_from_env()
    openai_model = env_value("OPENAI_MODEL", "gpt-5.5")
    use_openai_ai = env_value("USE_OPENAI_AI", "false").lower() == "true"
    email_provider = env_value("EMAIL_PROVIDER", "mock").lower() or "mock"
    smtp_host = env_value("SMTP_HOST")
    smtp_port = int(env_value("SMTP_PORT", "587") or "587")
    smtp_username = env_value("SMTP_USERNAME")
    smtp_password = env_value("SMTP_PASSWORD")
    sendgrid_api_key = env_value("SENDGRID_API_KEY")
    email_from_name = env_value("EMAIL_FROM_NAME", "Agent Concierge")
    email_from_address = env_value("EMAIL_FROM_ADDRESS")
    whatsapp_provider = env_value("WHATSAPP_PROVIDER", "mock").lower() or "mock"
    twilio_account_sid = env_value("TWILIO_ACCOUNT_SID")
    twilio_auth_token = env_value("TWILIO_AUTH_TOKEN")
    twilio_whatsapp_from = env_value("TWILIO_WHATSAPP_FROM")
    whatsapp_cloud_access_token = env_value("WHATSAPP_CLOUD_ACCESS_TOKEN")
    whatsapp_phone_number_id = env_value("WHATSAPP_PHONE_NUMBER_ID")
    whatsapp_business_account_id = env_value("WHATSAPP_BUSINESS_ACCOUNT_ID")


settings = Settings()
