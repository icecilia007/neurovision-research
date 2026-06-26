import csv
import json
import io
from typing import List, Dict, Any

EXPORT_FORMATS = [
    ('csv',  'CSV',          'Compatível com Excel e Google Sheets', 'table_chart'),
    ('xlsx', 'Excel (XLSX)', 'Arquivo Excel nativo com formatação',  'grid_on'),
    ('json', 'JSON',         'Formato estruturado para integração',   'data_object'),
]


class CustomExportService:
    def to_csv(self, rows: List[Dict], columns: List[str]) -> bytes:
        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=columns, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
        return out.getvalue().encode('utf-8-sig')

    def to_json(self, rows: List[Dict]) -> bytes:
        return json.dumps(rows, ensure_ascii=False, indent=2, default=str).encode('utf-8')

    def to_xlsx(self, rows: List[Dict], columns: List[str], labels: Dict[str, str]) -> bytes:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append([labels.get(c, c) for c in columns])
        for row in rows:
            ws.append([str(row.get(c, '') or '') for c in columns])
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()


custom_export_service = CustomExportService()
