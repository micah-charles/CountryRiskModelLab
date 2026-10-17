from __future__ import annotations
from pydantic import BaseModel, Field, field_validator

class Company(BaseModel):
    stock_code: str
    name_en: str
    industry: str
    china_demand_relevance: str
    @field_validator("stock_code")
    @classmethod
    def code(cls, value: str) -> str:
        value = str(value).zfill(5)
        if not value.isdigit() or len(value) != 5: raise ValueError("stock_code must be five digits")
        return value

class Evidence(BaseModel):
    stock_code: str; company_name: str; industry: str; financial_year: int
    report_title: str = ""; metric: str; value: float | None = None; unit: str = ""
    value_raw: str = ""; period_label_raw: str = ""; hkex_result_page_url: str = ""
    source_document_url: str = ""; local_pdf_path: str = ""; local_markdown_path: str = ""
    pdf_page: int | None = None; markdown_heading: str = ""; table_title_or_context: str = ""
    evidence_text: str = ""; evidence_text_start_char: int | None = None
    evidence_text_end_char: int | None = None; extraction_method: str = ""
    confidence: float = Field(ge=0, le=1); validation_status: str
    missing_reason: str = ""

