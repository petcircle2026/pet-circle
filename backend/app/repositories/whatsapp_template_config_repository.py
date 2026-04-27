"""
WhatsApp Template Config Repository — WhatsApp template management.

Manages WhatsApp template configurations and body text lookups.
"""

from sqlalchemy.orm import Session

from app.models.messaging.whatsapp_template_config import WhatsappTemplateConfig


class WhatsappTemplateConfigRepository:
    """Manages WhatsApp template configuration data."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_name(self, template_name: str) -> WhatsappTemplateConfig | None:
        """Find a template by name."""
        return (
            self.db.query(WhatsappTemplateConfig)
            .filter(WhatsappTemplateConfig.template_name == template_name)
            .first()
        )

    def get_body_text(self, template_name: str) -> str:
        """Get template body text by name, returns empty string if not found."""
        row = self.find_by_name(template_name)
        return row.body_text if row and row.body_text else ""
