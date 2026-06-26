from datetime import date as DateType
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ValidityFilter(BaseModel):
    caption: str
    accepted_option_ids: List[int]


class FilterParams(BaseModel):
    diagnosis: Optional[List[str]] = None
    medication: Optional[List[str]] = None
    birth_year: Optional[Dict[str, Optional[int]]] = None  # {"min": 1990, "max": 2000}
    validity: Optional[ValidityFilter] = None

    def to_filter_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        if self.diagnosis:
            d["diagnosis"] = self.diagnosis
        if self.medication:
            d["medication"] = self.medication
        if self.birth_year:
            d["birth_year"] = self.birth_year
        if self.validity:
            d["validity"] = {
                "caption": self.validity.caption,
                "accepted_option_ids": self.validity.accepted_option_ids,
            }
        return d


class CrosstabRequest(BaseModel):
    row_variable: str
    col_variable: str
    filters: Optional[FilterParams] = None


class TextResponseQuery(BaseModel):
    question_id: int
    search: Optional[str] = None
    page: int = 1
    page_size: int = 10
    filters: Optional[FilterParams] = None


class CustomExportRequest(BaseModel):
    question_ids: List[int] = []
    meta_fields: List[str] = ["submission_id", "submitted_at", "total_score"]
    date_from: Optional[DateType] = None
    date_to: Optional[DateType] = None
    format: str = "csv"
