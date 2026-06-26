from datetime import datetime, time as dt_time, date as DateType
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func
from typing import Dict, List, Any, Optional
from app.models import (
    Questionnaire, QuestionnaireSubmission, Answer, Question,
    QuestionOption, QuestionnaireItem
)

_CHYPS_V_CAPTIONS = {f"Q{i}" for i in range(1, 21)}


def compute_chyps_score(answers: List, questions: Dict) -> float:
    """Computes the CHYPS-V global score (items Q1–Q20 only, Likert 0–3).

    Uses option sort_order position as the Likert value (0=first, 3=last),
    or the explicit weight when non-zero. Ignores all non-CHYPS-V items.
    """
    total = 0.0
    for answer in answers:
        question = questions.get(answer.question_id)
        if not question or question.caption not in _CHYPS_V_CAPTIONS:
            continue
        if not answer.selected_options:
            continue
        sorted_opts = sorted(question.options or [], key=lambda o: (o.sort_order or 0, o.id))
        position_map = {opt.id: i for i, opt in enumerate(sorted_opts)}
        for opt_id in answer.selected_options:
            opt = next((o for o in sorted_opts if o.id == opt_id), None)
            if opt is None:
                continue
            weight = opt.weight or 0.0
            total += weight if weight else float(position_map.get(opt_id, 0))
    return total


class ReportService:
    @staticmethod
    def get_full_report(db: Session, questionnaire_id: int) -> Dict[str, Any]:
        questionnaire = db.query(Questionnaire).filter(
            Questionnaire.id == questionnaire_id
        ).first()
        
        if not questionnaire:
            raise ValueError("Questionário não encontrado")
        
        submissions = db.query(QuestionnaireSubmission).filter(
            QuestionnaireSubmission.questionnaire_id == questionnaire_id
        ).order_by(QuestionnaireSubmission.submitted_at.desc()).all()
        
        total_submissions = len(submissions)
        
        submission_ids = [s.id for s in submissions]
        
        all_answers = db.query(Answer).filter(
            Answer.submission_id.in_(submission_ids)
        ).all()
        
        all_question_ids = list(set(a.question_id for a in all_answers))
        all_questions = {q.id: q for q in db.query(Question).filter(Question.id.in_(all_question_ids)).all()} if all_question_ids else {}
        
        all_option_ids = []
        for q in all_questions.values():
            if q.options:
                all_option_ids.extend([opt.id for opt in q.options])
        all_options = {opt.id: opt for opt in db.query(QuestionOption).filter(QuestionOption.id.in_(all_option_ids)).all()} if all_option_ids else {}
        
        for q in all_questions.values():
            q._options_cache = {opt.id: opt for opt in (q.options or [])}

        answers_by_submission_pre = {}
        for a in all_answers:
            answers_by_submission_pre.setdefault(a.submission_id, []).append(a)

        chyps_scores: Dict[int, float] = {
            s.id: compute_chyps_score(
                answers_by_submission_pre.get(s.id, []), all_questions
            )
            for s in submissions
        }
        avg_score = (
            sum(s.total_score for s in submissions) / total_submissions
            if total_submissions > 0 else 0.0
        )

        total_correct = 0
        total_incorrect = 0
        
        for answer in all_answers:
            question = all_questions.get(answer.question_id)
            if not question or question.question_type == "free_text":
                continue
            
            correct_option_ids = {opt.id for opt in question._options_cache.values() if opt.is_correct}
            selected_option_ids = set(answer.selected_options) if answer.selected_options else set()
            
            if question.question_type == "single":
                if len(selected_option_ids) == 1 and selected_option_ids.issubset(correct_option_ids):
                    total_correct += 1
                else:
                    total_incorrect += 1
            elif question.question_type == "multiple":
                if selected_option_ids == correct_option_ids:
                    total_correct += 1
                else:
                    total_incorrect += 1
        
        question_stats = []
        questionnaire_items = db.query(QuestionnaireItem).filter(
            QuestionnaireItem.questionnaire_id == questionnaire_id,
            QuestionnaireItem.item_type.in_(["question", "term"])
        ).order_by(QuestionnaireItem.sort_order).all()
        
        for item in questionnaire_items:
            question = all_questions.get(item.item_id)
            if not question:
                continue
            
            answers = [a for a in all_answers if a.question_id == question.id]
            total_answers = len(answers)
            
            correct_count = 0
            total_question_score = 0
            scores_for_question = []
            accuracy = 0.0
            error_rate = 0.0
            
            if question.question_type != "free_text":
                correct_option_ids = {opt.id for opt in question._options_cache.values() if opt.is_correct}
                
                for answer in answers:
                    selected_option_ids = set(answer.selected_options) if answer.selected_options else set()
                    total_question_score += answer.score
                    scores_for_question.append(answer.score)
                    
                    if question.question_type == "single":
                        if len(selected_option_ids) == 1 and selected_option_ids.issubset(correct_option_ids):
                            correct_count += 1
                    elif question.question_type == "multiple":
                        if selected_option_ids == correct_option_ids:
                            correct_count += 1
                
                accuracy = (correct_count / total_answers * 100) if total_answers > 0 else 0
                error_rate = ((total_answers - correct_count) / total_answers * 100) if total_answers > 0 else 0

            option_distribution = {}
            if question.question_type in ["single", "multiple"]:
                for answer in answers:
                    if answer.selected_options:
                        for option_id in answer.selected_options:
                            option_distribution[option_id] = option_distribution.get(option_id, 0) + 1
            
            option_details = {}
            for option_id, count in option_distribution.items():
                option = all_options.get(option_id)
                if option:
                    percentage = (count / total_answers * 100) if total_answers > 0 else 0
                    option_details[option_id] = {
                        "text": option.text,
                        "count": count,
                        "percentage": round(percentage, 1),
                        "is_correct": option.is_correct,
                        "weight": option.weight
                    }
            
            avg_question_score = total_question_score / total_answers if total_answers > 0 else 0
            
            display_text = question.title or question.text
            question_stats.append({
                "question_id": question.id,
                "question_text": display_text,
                "question_title": question.title,
                "question_body": question.text if question.title else None,
                "question_type": question.question_type,
                "total_answers": total_answers,
                "correct_answers": correct_count,
                "accuracy_percentage": round(accuracy, 2),
                "error_rate": round(error_rate, 2),
                "weight": question.weight,
                "avg_score": round(avg_question_score, 2),
                "min_score": round(min(scores_for_question), 2) if scores_for_question else 0,
                "max_score": round(max(scores_for_question), 2) if scores_for_question else 0,
                "option_details": option_details
            })
        
        anonymous_submissions = []
        for submission in submissions:
            submission_id = submission.id
            total_score = submission.total_score
            chyps_score = chyps_scores.get(submission_id, 0.0)
            submitted_at = submission.submitted_at.isoformat()
            
            submission_answers = []
            sub_answers = answers_by_submission_pre.get(submission_id, [])
            
            for answer in sub_answers:
                question = all_questions.get(answer.question_id)
                if not question:
                    continue
                
                selected_option_texts = []
                if answer.selected_options and question.question_type in ["single", "multiple"]:
                    for opt_id in answer.selected_options:
                        opt = all_options.get(opt_id)
                        if opt:
                            selected_option_texts.append(opt.text)
                
                display_text = question.title or question.text
                submission_answers.append({
                    "id": answer.id,
                    "question_id": answer.question_id,
                    "question_text": display_text,
                    "question_title": question.title,
                    "question_body": question.text if question.title else None,
                    "question_type": question.question_type,
                    "caption": question.caption,
                    "selected_options": answer.selected_options,
                    "selected_option_texts": selected_option_texts,
                    "text_response": answer.text_response,
                    "score": answer.score,
                    "question_weight": question.weight
                })
            
            anonymous_submissions.append({
                "submission_id": submission_id,
                "total_score": total_score,
                "chyps_score": round(chyps_score, 2),
                "submitted_at": submitted_at,
                "answers": submission_answers
            })
        
        return {
            "questionnaire": {
                "id": questionnaire.id,
                "title": questionnaire.title,
                "description": questionnaire.description,
                "question_order": questionnaire.question_order,
                "created_by": questionnaire.creator_id,
                "created_at": questionnaire.created_at.isoformat(),
                "active": questionnaire.is_active
            },
            "general_stats": {
                "total_submissions": total_submissions,
                "average_score": round(avg_score, 2),
                "total_correct": total_correct,
                "total_incorrect": total_incorrect,
                "completion_rate": 100.0
            },
            "question_statistics": question_stats,
            "anonymous_submissions": anonymous_submissions
        }

    @staticmethod
    def get_summary_report(db: Session, questionnaire_id: int) -> Dict[str, Any]:
        """
        Retorna resumo do relatório com os campos esperados pelo frontend:
        - total_submissions
        - average_score
        - max_score  
        - min_score
        """
        submissions = db.query(QuestionnaireSubmission).filter(
            QuestionnaireSubmission.questionnaire_id == questionnaire_id
        ).all()

        if not submissions:
            return {
                "total_submissions": 0,
                "average_score": 0.0,
                "max_score": 0.0,
                "min_score": 0.0
            }

        scores = [float(s.total_score) for s in submissions if s.total_score is not None]

        if not scores:
            return {
                "total_submissions": len(submissions),
                "average_score": 0.0,
                "max_score": 0.0,
                "min_score": 0.0
            }

        average_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
        
        return {
            "total_submissions": len(submissions),
            "average_score": round(average_score, 2),
            "max_score": round(max_score, 2),
            "min_score": round(min_score, 2)
        }


    @staticmethod
    def custom_export(
        db: Session,
        questionnaire_id: int,
        question_ids: List[int],
        meta_fields: List[str],
        date_from: Optional[DateType],
        date_to: Optional[DateType],
    ) -> Dict[str, Any]:
        """Filtra submissions no banco e devolve dados wide-format para exportação."""
        questionnaire = db.query(Questionnaire).filter(
            Questionnaire.id == questionnaire_id
        ).first()
        if not questionnaire:
            raise ValueError("Questionário não encontrado")

        # ── 1. Filtrar submissions por data (no banco) ─────────────────
        query = db.query(QuestionnaireSubmission).filter(
            QuestionnaireSubmission.questionnaire_id == questionnaire_id
        )
        if date_from:
            query = query.filter(
                QuestionnaireSubmission.submitted_at >= datetime.combine(date_from, dt_time.min)
            )
        if date_to:
            query = query.filter(
                QuestionnaireSubmission.submitted_at <= datetime.combine(date_to, dt_time.max)
            )
        submissions = query.order_by(QuestionnaireSubmission.submitted_at.desc()).all()

        if not submissions:
            return {"column_keys": [], "column_labels": {}, "rows": [], "total": 0}

        # ── 2. Buscar respostas apenas das submissões filtradas ─────────
        submission_ids = [s.id for s in submissions]
        answer_query = db.query(Answer).filter(Answer.submission_id.in_(submission_ids))
        if question_ids:
            answer_query = answer_query.filter(Answer.question_id.in_(question_ids))
        all_answers = answer_query.all()

        # ── 3. Carregar questões e opções ─────────────────────────────
        needed_q_ids = list({a.question_id for a in all_answers})
        questions: Dict[int, Any] = {}
        if needed_q_ids:
            for q in db.query(Question).filter(Question.id.in_(needed_q_ids)).all():
                questions[q.id] = q

        all_option_ids = [opt.id for q in questions.values() for opt in (q.options or [])]
        options: Dict[int, Any] = {}
        if all_option_ids:
            for opt in db.query(QuestionOption).filter(QuestionOption.id.in_(all_option_ids)).all():
                options[opt.id] = opt

        # ── 4. Ordenar questões conforme o questionário ────────────────
        ordered_items = db.query(QuestionnaireItem).filter(
            QuestionnaireItem.questionnaire_id == questionnaire_id,
            QuestionnaireItem.item_type.in_(["question", "term"]),
        ).order_by(QuestionnaireItem.sort_order).all()

        ordered_questions = []
        seen: set = set()
        q_id_set = set(question_ids) if question_ids else None
        for item in ordered_items:
            q = questions.get(item.item_id)
            if q and q.id not in seen:
                if q_id_set is None or q.id in q_id_set:
                    seen.add(q.id)
                    ordered_questions.append(q)

        # ── 5. Definir colunas ────────────────────────────────────────
        _meta_labels = {
            "submission_id": "ID da Submissão",
            "submitted_at":  "Data de Envio",
            "total_score":   "Pontuação Total",
            "chyps_score":   "Escore CHYPS-V (Q1–Q20)",
        }
        # chyps_score is always included regardless of meta_fields selection
        effective_meta = list(meta_fields)
        if "chyps_score" not in effective_meta:
            effective_meta = effective_meta + ["chyps_score"]

        column_keys: List[str] = [f for f in effective_meta if f in _meta_labels]
        column_labels: Dict[str, str] = {k: _meta_labels[k] for k in column_keys}

        for q in ordered_questions:
            key = f"q_{q.id}"
            cap = q.caption or ""
            text = (q.title or q.text or "")[:70]
            column_keys.append(key)
            column_labels[key] = f"{cap}: {text}" if cap else text

        # ── 6. Indexar respostas por submissão ────────────────────────
        answers_by_sub_list: Dict[int, List] = {}
        answers_by_sub: Dict[int, Dict[int, Any]] = {}
        for a in all_answers:
            answers_by_sub_list.setdefault(a.submission_id, []).append(a)
            answers_by_sub.setdefault(a.submission_id, {})[a.question_id] = a

        chyps_by_sub: Dict[int, float] = {
            s.id: compute_chyps_score(answers_by_sub_list.get(s.id, []), questions)
            for s in submissions
        }

        # ── 7. Montar linhas ──────────────────────────────────────────
        rows: List[Dict] = []
        for sub in submissions:
            row: Dict = {}
            if "submission_id" in effective_meta:
                row["submission_id"] = sub.id
            if "submitted_at" in effective_meta:
                row["submitted_at"] = sub.submitted_at.isoformat()
            if "total_score" in effective_meta:
                row["total_score"] = sub.total_score
            row["chyps_score"] = round(chyps_by_sub.get(sub.id, 0.0), 2)

            sub_answers = answers_by_sub.get(sub.id, {})
            for q in ordered_questions:
                key = f"q_{q.id}"
                ans = sub_answers.get(q.id)
                if not ans:
                    row[key] = ""
                    continue
                if ans.text_response:
                    row[key] = ans.text_response
                elif ans.selected_options and q.question_type in ("single", "multiple"):
                    texts = [options[oid].text for oid in ans.selected_options if oid in options]
                    row[key] = "|".join(texts)
                else:
                    row[key] = ""

            rows.append(row)

        return {
            "column_keys":   column_keys,
            "column_labels": column_labels,
            "rows":          rows,
            "total":         len(rows),
        }

    @staticmethod
    def get_question_analysis(db: Session, questionnaire_id: int, question_id: int) -> Dict[str, Any]:
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise ValueError("Pergunta não encontrada")

        item_exists = db.query(QuestionnaireItem).filter(
            QuestionnaireItem.questionnaire_id == questionnaire_id,
            QuestionnaireItem.item_id == question_id,
            QuestionnaireItem.item_type.in_(["question", "term"])
        ).first()

        if not item_exists:
            raise ValueError("Pergunta não pertence a este questionário")

        answers = db.query(Answer).join(QuestionnaireSubmission).filter(
            Answer.question_id == question_id,
            QuestionnaireSubmission.questionnaire_id == questionnaire_id
        ).all()

        analysis = {
            "question": {
                "id": question.id,
                "text": question.title or question.text,
                "title": question.title,
                "body": question.text if question.title else None,
                "type": question.question_type,
                "weight": question.weight
            },
            "response_count": len(answers),
            "average_score": round(sum(a.score for a in answers) / len(answers), 2) if answers else 0,
            "correct_responses": sum(1 for a in answers if a.score > 0),
            "accuracy_rate": round((sum(1 for a in answers if a.score > 0) / len(answers)) * 100, 2) if answers else 0
        }

        if question.question_type in ["single", "multiple"]:
            option_stats = {}
            for answer in answers:
                if answer.selected_options:
                    for option_id in answer.selected_options:
                        option_stats[option_id] = option_stats.get(option_id, 0) + 1

            options = db.query(QuestionOption).filter(
                QuestionOption.question_id == question_id
            ).all()

            option_analysis = []
            for option in options:
                count = option_stats.get(option.id, 0)
                percentage = (count / len(answers) * 100) if answers else 0

                option_analysis.append({
                    "option_id": option.id,
                    "text": option.text,
                    "selection_count": count,
                    "selection_percentage": round(percentage, 2),
                    "is_correct": option.is_correct,
                    "weight": option.weight
                })

            analysis["option_analysis"] = option_analysis

        elif question.question_type == "free_text":
            text_responses = [
                {
                    "response_preview": (answer.text_response[:100] + "...") if len(
                        answer.text_response or "") > 100 else answer.text_response,
                    "character_count": len(answer.text_response or ""),
                    "score": answer.score
                }
                for answer in answers if answer.text_response
            ]

            analysis["text_analysis"] = {
                "total_text_responses": len(text_responses),
                "average_length": round(sum(resp["character_count"] for resp in text_responses) / len(text_responses),
                                        1) if text_responses else 0,
                "sample_responses": text_responses[:5]
            }

        return analysis

report_service = ReportService()
