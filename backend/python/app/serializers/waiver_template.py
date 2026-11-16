from app.models.enum import BucketVisibility
from app.models.waiver_template import WaiverTemplate, WaiverTemplateRead
from app.services.interfaces.storage_service import IStorageService


def waiver_template_read(template: WaiverTemplate, storage: IStorageService) -> WaiverTemplateRead:
    return WaiverTemplateRead.model_validate(
        {
            **template.model_dump(),
            "document_url": storage.url_for(template.document_key, BucketVisibility.PUBLIC),
        }
    )
