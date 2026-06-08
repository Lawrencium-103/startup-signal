import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    apify_api_key: Optional[str] = None
    apollo_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    nvidia_api_key: Optional[str] = None

    smtp_host: str = "smtp-relay.sendinblue.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = ""
    email_to: str = ""

    producthunt_api_key: Optional[str] = None
    crunchbase_api_key: Optional[str] = None

    ai_provider: str = "openai"
    ai_model: str = "gpt-4o-mini"
    groq_model: str = "llama-3.3-70b-versatile"
    nvidia_model: str = "moonshotai/kimi-k2.6"

    @classmethod
    def from_env(cls):
        return cls(
            apify_api_key=os.getenv("APIFY_API_KEY"),
            apollo_api_key=os.getenv("APOLLO_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            groq_api_key=os.getenv("GROQ_API_KEY"),
            nvidia_api_key=os.getenv("NVIDIA_API_KEY"),
            smtp_host=os.getenv("SMTP_HOST", "smtp-relay.sendinblue.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            email_from=os.getenv("EMAIL_FROM", ""),
            email_to=os.getenv("EMAIL_TO", ""),
            producthunt_api_key=os.getenv("PRODUCTHUNT_API_KEY"),
            crunchbase_api_key=os.getenv("CRUNCHBASE_API_KEY"),
            ai_provider=os.getenv("AI_PROVIDER", "openai"),
            ai_model=os.getenv("AI_MODEL", "gpt-4o-mini"),
            groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            nvidia_model=os.getenv("NVIDIA_MODEL", "moonshotai/kimi-k2.6"),
        )
