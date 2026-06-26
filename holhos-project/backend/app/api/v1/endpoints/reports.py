import csv
import io
import json
import re

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, JSONResponse

from app.dependencies import ReportServiceDep, DatabaseDep
from app.schemas.analytics import CustomExportRequest

router = APIRouter()


@router.get("/questionnaires/{questionnaire_id}/full-report")
def get_full_report(
        questionnaire_id: int,
        db: DatabaseDep,
        report_service: ReportServiceDep
):
    try:
        return report_service.get_full_report(db, questionnaire_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/questionnaires/{questionnaire_id}/summary")
def get_summary_report(
        questionnaire_id: int,
        db: DatabaseDep,
        report_service: ReportServiceDep
):
    try:
        return report_service.get_summary_report(db, questionnaire_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/questionnaires/{questionnaire_id}/export")
def export_report(
    questionnaire_id: int,
    db: DatabaseDep,
    report_service: ReportServiceDep,
    format: str = Query("csv", regex="^(csv|json)$")
):
    try:
        report_data = report_service.get_full_report(db, questionnaire_id)
        q = report_data["questionnaire"]
        q_id = q["id"]
        q_created = q["created_at"]

        records = []
        for sub in report_data["anonymous_submissions"]:
            sub_id = sub["submission_id"]
            total = sub["total_score"]
            chyps = sub.get("chyps_score", 0.0)
            ts = sub["submitted_at"]
            for ans in sub["answers"]:
                rec = {
                    "questionnaire_id": q_id,
                    "questionnaire_created_at": q_created,
                    "submission_id": sub_id,
                    "total_score": total,
                    "chyps_score": chyps,
                    "submitted_at": ts,
                    "answer_id": ans["id"],
                    "question_id": ans["question_id"],
                    "question_weight": ans["question_weight"],
                    "question_text": ans["question_text"],
                    "selected_option_ids": ans.get("selected_options", []),
                    "selected_option_texts": ans.get("selected_option_texts", []),
                    "text_response": ans.get("text_response") or "",
                    "answer_score": ans["score"]
                }
                records.append(rec)

        if format == "csv":
            output = io.StringIO()
            submissions = report_data["anonymous_submissions"]

            all_questions = {}
            for sub in submissions:
                for ans in sub["answers"]:
                    if ans.get("caption"):
                        col_key = ans["caption"]
                    else:
                        col_key = f"q{ans['question_id']}_{slugify(ans['question_text'])}"
                    all_questions[col_key] = ans["question_text"]

            base_columns = [
                "questionnaire_id", "questionnaire_created_at",
                "submission_id", "total_score", "chyps_score", "submitted_at"
            ]
            question_columns = list(all_questions.keys())
            header = base_columns + question_columns
            writer = csv.DictWriter(output, fieldnames=header)
            writer.writeheader()

            for sub in submissions:
                row = {
                    "questionnaire_id": q_id,
                    "questionnaire_created_at": q_created,
                    "submission_id": sub["submission_id"],
                    "total_score": sub["total_score"],
                    "chyps_score": sub.get("chyps_score", 0.0),
                    "submitted_at": sub["submitted_at"]
                }
                for ans in sub["answers"]:
                    if ans.get("caption"):
                        col_key = ans["caption"]
                    else:
                        col_key = f"q{ans['question_id']}_{slugify(ans['question_text'])}"

                    if ans["text_response"]:
                        row[col_key] = ans["text_response"]
                    elif ans["selected_option_texts"]:
                        row[col_key] = "|".join(ans["selected_option_texts"])
                    else:
                        row[col_key] = ""

                for col in question_columns:
                    row.setdefault(col, "")

                writer.writerow(row)

            csv_content = output.getvalue()
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=questionnaire_{questionnaire_id}_report.csv"}
            )
        if format == "json":
            json_data = {
                "questionnaire": {
                    "id": q["id"],
                    "title": q["title"],
                    "description": q.get("description", ""),
                    "created_at": q["created_at"],
                    "created_by": q.get("created_by"),
                    "active": q.get("active", True)
                },
                "submissions": []
            }

            for sub in report_data["anonymous_submissions"]:
                sub_obj = {
                    "submission_id": sub["submission_id"],
                    "total_score": sub["total_score"],
                    "chyps_score": sub.get("chyps_score", 0.0),
                    "submitted_at": sub["submitted_at"],
                    "answers": []
                }
                for ans in sub["answers"]:
                    if ans.get("caption"):
                        col_key = ans["caption"]
                    else:
                        col_key = f"q{ans['question_id']}_{slugify(ans['question_text'])}"

                    sub_obj["answers"].append({
                        "answer_id": ans["id"],
                        "question_id": ans["question_id"],
                        "caption": col_key,
                        "question_title": ans.get("question_title"),
                        "selected_option_ids": ans.get("selected_options", []),
                        "selected_option_texts": ans.get("selected_option_texts", []),
                        "text_response": ans.get("text_response") or "",
                        "score": ans.get("score", 0)
                    })
                json_data["submissions"].append(sub_obj)

            return JSONResponse({"success": True, "data": json_data})


    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/questionnaires/{questionnaire_id}/analytics")
def get_analytics(
        questionnaire_id: int,
        db: DatabaseDep,
        report_service: ReportServiceDep
):
    try:
        report_data = report_service.get_full_report(db, questionnaire_id)

        submissions = report_data['anonymous_submissions']
        scores = [s['total_score'] for s in submissions]

        if not scores:
            return {"message": "Nenhuma resposta encontrada"}

        top_scores = sorted(scores, reverse=True)[:5]

        analytics = {
            "score_distribution": {
                "min": min(scores),
                "max": max(scores),
                "mean": sum(scores) / len(scores),
                "median": sorted(scores)[len(scores) // 2] if scores else 0,
                "std_deviation": round((sum((x - sum(scores) / len(scores)) ** 2 for x in scores) / len(scores)) ** 0.5,
                                       2)
            },
            "top_scores": top_scores,
            "difficult_questions": sorted(
                [q for q in report_data['question_statistics'] if q['total_answers'] > 0],
                key=lambda x: x['accuracy_percentage']
            )[:5],
            "performance_distribution": {
                "excellent": len([s for s in scores if s >= max(scores) * 0.8]) if scores else 0,
                "good": len([s for s in scores if max(scores) * 0.6 <= s < max(scores) * 0.8]) if scores else 0,
                "average": len([s for s in scores if max(scores) * 0.4 <= s < max(scores) * 0.6]) if scores else 0,
                "poor": len([s for s in scores if s < max(scores) * 0.4]) if scores else 0
            }
        }

        return analytics

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/questionnaires/{questionnaire_id}/questions/{question_id}/analysis")
def get_question_analysis(
        questionnaire_id: int,
        question_id: int,
        db: DatabaseDep,
        report_service: ReportServiceDep
):
    try:
        return report_service.get_question_analysis(db, questionnaire_id, question_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/questionnaires/{questionnaire_id}/custom-export")
def custom_export(
    questionnaire_id: int,
    body: CustomExportRequest,
    db: DatabaseDep,
    report_service: ReportServiceDep,
):
    if body.format not in ("csv", "xlsx", "json"):
        raise HTTPException(status_code=400, detail="Formato inválido. Use: csv, xlsx, json")

    try:
        data = report_service.custom_export(
            db,
            questionnaire_id,
            question_ids=body.question_ids,
            meta_fields=body.meta_fields,
            date_from=body.date_from,
            date_to=body.date_to,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if not data["rows"]:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma submissão encontrada com os filtros aplicados",
        )

    col_keys   = data["column_keys"]
    col_labels = data["column_labels"]
    rows       = data["rows"]
    fname      = f"exportacao_{questionnaire_id}"

    if body.format == "csv":
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=col_keys, extrasaction="ignore")
        writer.writerow({k: col_labels[k] for k in col_keys})   # header with labels
        writer.writerows(rows)
        return Response(
            content=out.getvalue().encode("utf-8-sig"),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{fname}.csv"'},
        )

    if body.format == "xlsx":
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append([col_labels[k] for k in col_keys])
        for row in rows:
            ws.append([str(row.get(k, "") or "") for k in col_keys])
        buf = io.BytesIO()
        wb.save(buf)
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{fname}.xlsx"'},
        )

    if body.format == "json":
        labeled_rows = [{col_labels[k]: row.get(k, "") for k in col_keys} for row in rows]
        return Response(
            content=json.dumps(labeled_rows, ensure_ascii=False, indent=2, default=str).encode("utf-8"),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{fname}.json"'},
        )


def slugify(text: str, length: int = 5) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text[:length]