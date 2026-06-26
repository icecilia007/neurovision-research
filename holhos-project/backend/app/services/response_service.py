from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.models import (
    QuestionnaireSubmission, Answer, Question, QuestionOption,
    Questionnaire, QuestionnaireItem
)
from app.schemas.response import SubmissionCreate, SubmissionValidationResponse


class ResponseService:

    def validate_submission(self, db: Session, submission_data: SubmissionCreate) -> SubmissionValidationResponse:
        errors = []
        warnings = []

        questionnaire = db.query(Questionnaire).filter(
            Questionnaire.id == submission_data.questionnaire_id
        ).first()

        if not questionnaire:
            errors.append(f"Questionário com ID {submission_data.questionnaire_id} não encontrado")
            return SubmissionValidationResponse(
                is_valid=False,
                message="Questionário não encontrado",
                total_questions=0,
                answered_questions=0,
                missing_questions=[],
                errors=errors
            )

        if not questionnaire.is_active:
            errors.append("Este questionário não está mais disponível para receber respostas")

        questionnaire_items = db.query(QuestionnaireItem).filter(
            QuestionnaireItem.questionnaire_id == submission_data.questionnaire_id,
            QuestionnaireItem.item_type.in_(["question", "term"])
        ).all()

        questionnaire_question_ids = {item.item_id for item in questionnaire_items}

        submission_question_ids = {answer.question_id for answer in submission_data.answers}

        invalid_questions = submission_question_ids - questionnaire_question_ids
        if invalid_questions:
            invalid_list = sorted(list(invalid_questions))
            errors.append(f"Perguntas inválidas encontradas (não pertencem a este questionário): {invalid_list}")

        valid_questions = db.query(Question).filter(
            Question.id.in_(questionnaire_question_ids)
        ).all()
        question_map = {q.id: q for q in valid_questions}

        # Answers submitted, keyed by question, to evaluate display conditions
        submitted_answer_map = {answer.question_id: answer for answer in submission_data.answers}

        def _condition_met(question: Question) -> bool:
            """A question with a display condition only applies when the trigger
            option was selected in the answer of the question it depends on."""
            depends_on_qid = getattr(question, 'depends_on_question_id', None)
            depends_on_oid = getattr(question, 'depends_on_option_id', None)
            if not depends_on_qid or not depends_on_oid:
                return True
            trigger_answer = submitted_answer_map.get(depends_on_qid)
            if not trigger_answer or not trigger_answer.selected_options:
                return False
            return depends_on_oid in trigger_answer.selected_options

        required_question_ids = {
            qid for qid in questionnaire_question_ids
            if question_map.get(qid)
            and getattr(question_map[qid], 'is_required', True)
            and _condition_met(question_map[qid])
        }
        total_questions = len(required_question_ids)

        missing_questions = required_question_ids - submission_question_ids
        answered_questions = len(submission_question_ids & required_question_ids)

        if missing_questions:
            missing_list = sorted(list(missing_questions))
            errors.append(
                f"É obrigatório responder TODAS as {total_questions} perguntas obrigatórias. Perguntas não respondidas: {missing_list}")

        for answer in submission_data.answers:
            if answer.question_id in questionnaire_question_ids:
                question = next((q for q in valid_questions if q.id == answer.question_id), None)
                if question and not _condition_met(question):
                    continue
                if question:
                    validation_result = self._validate_answer_for_question_type(db, question, answer)
                    if validation_result['errors']:
                        errors.extend(validation_result['errors'])
                    if validation_result['warnings']:
                        warnings.extend(validation_result['warnings'])

        is_valid = len(errors) == 0 and len(missing_questions) == 0

        if is_valid:
            message = "Todas as respostas estão válidas e completas"
        else:
            message = "Existem problemas que precisam ser corrigidos antes de enviar"

        return SubmissionValidationResponse(
            is_valid=is_valid,
            message=message,
            total_questions=total_questions,
            answered_questions=answered_questions,
            missing_questions=sorted(list(missing_questions)),
            errors=errors if errors else None,
            warnings=warnings if warnings else None
        )

    def _validate_answer_for_question_type(self, db: Session, question: Question, answer) -> Dict[str, List[str]]:
        errors = []
        warnings = []

        preview_source = question.title or question.text
        question_preview = preview_source[:30] + "..." if len(preview_source) > 30 else preview_source

        if question.question_type == "free_text":
            text_response = (answer.text_response or '').strip()
            is_required = getattr(question, 'is_required', True)

            if not text_response:
                if is_required:
                    errors.append(f"A pergunta '{question_preview}' requer uma resposta em texto")
            elif len(text_response) < 3:
                errors.append(f"A resposta para '{question_preview}' deve ter pelo menos 3 caracteres")

            if answer.selected_options:
                warnings.append(
                    f"As opções selecionadas para '{question_preview}' serão ignoradas (pergunta de texto livre)")

        elif question.question_type == "single":
            if not answer.selected_options or len(answer.selected_options) == 0:
                errors.append(f"É obrigatório selecionar uma opção para '{question_preview}'")
            elif len(answer.selected_options) > 1:
                errors.append(f"Para '{question_preview}', selecione apenas UMA opção")
            else:
                option_id = answer.selected_options[0]
                option_exists = db.query(QuestionOption).filter(
                    QuestionOption.id == option_id,
                    QuestionOption.question_id == question.id
                ).first()

                if not option_exists:
                    errors.append(f"A opção selecionada para '{question_preview}' não é válida")

        elif question.question_type == "multiple":
            if not answer.selected_options or len(answer.selected_options) == 0:
                errors.append(f"É obrigatório selecionar pelo menos uma opção para '{question_preview}'")
            else:
                existing_options = db.query(QuestionOption).filter(
                    QuestionOption.id.in_(answer.selected_options),
                    QuestionOption.question_id == question.id
                ).all()

                existing_option_ids = {opt.id for opt in existing_options}
                invalid_options = set(answer.selected_options) - existing_option_ids

                if invalid_options:
                    errors.append(f"Algumas opções selecionadas para '{question_preview}' não são válidas")

        return {"errors": errors, "warnings": warnings}

    def calculate_answer_score(self, question: Question, answer_data) -> float:
        if question.question_type == "free_text":
            return 0.0

        if not answer_data.selected_options:
            return 0.0

        selected_option_ids = answer_data.selected_options
        all_options = sorted(question.options or [], key=lambda o: (o.sort_order or 0, o.id))
        option_map = {opt.id: opt for opt in all_options}
        selected_options = [option_map[oid] for oid in selected_option_ids if oid in option_map]

        if question.question_type == "single":
            if not selected_options:
                return 0.0
            opt = selected_options[0]
            # Use explicit weight when configured (non-zero); otherwise derive
            # the Likert value from the option's position (sort_order - 1).
            if opt.weight:
                return float(opt.weight)
            position = all_options.index(opt)
            return float(position)

        elif question.question_type == "multiple":
            score = 0.0
            for opt in selected_options:
                if opt.weight:
                    score += float(opt.weight)
                else:
                    score += float(all_options.index(opt))
            return score

        return 0.0

    def submit_questionnaire_response(self, db: Session, submission_data: SubmissionCreate) -> QuestionnaireSubmission:
        db_submission = QuestionnaireSubmission(
            questionnaire_id=submission_data.questionnaire_id,
            total_score=0.0
        )

        db.add(db_submission)
        db.commit()
        db.refresh(db_submission)

        total_score = 0.0

        answered_question_ids = set()

        for answer_data in submission_data.answers:
            question = db.query(Question).filter(Question.id == answer_data.question_id).first()
            if not question:
                continue

            answered_question_ids.add(question.id)

            normalized_text_response = answer_data.text_response
            if question.question_type == "free_text":
                text_value = (answer_data.text_response or '').strip()
                if not text_value and not getattr(question, 'is_required', True):
                    normalized_text_response = "N/A"
                else:
                    normalized_text_response = text_value or None

            answer_score = self.calculate_answer_score(question, answer_data)
            total_score += answer_score

            db_answer = Answer(
                submission_id=db_submission.id,
                question_id=answer_data.question_id,
                selected_options=answer_data.selected_options,
                text_response=normalized_text_response,
                score=answer_score
            )
            db.add(db_answer)

        questionnaire_items = db.query(QuestionnaireItem).filter(
            QuestionnaireItem.questionnaire_id == submission_data.questionnaire_id,
            QuestionnaireItem.item_type.in_(["question", "term"])
        ).all()
        questionnaire_question_ids = [item.item_id for item in questionnaire_items]

        optional_free_text_questions = db.query(Question).filter(
            Question.id.in_(questionnaire_question_ids),
            Question.question_type == "free_text",
            Question.is_required.is_(False)
        ).all()

        for question in optional_free_text_questions:
            if question.id in answered_question_ids:
                continue

            db_answer = Answer(
                submission_id=db_submission.id,
                question_id=question.id,
                selected_options=[],
                text_response="N/A",
                score=0.0
            )
            db.add(db_answer)

        db_submission.total_score = total_score
        db.commit()
        db.refresh(db_submission)

        return db_submission

    def get_submission_by_id(self, db: Session, submission_id: int) -> QuestionnaireSubmission:
        submission = db.query(QuestionnaireSubmission).filter(
            QuestionnaireSubmission.id == submission_id
        ).first()

        if not submission:
            raise ValueError("Submissão não encontrada")

        return submission

    def delete_submission(self, db: Session, submission_id: int) -> bool:
        submission = db.query(QuestionnaireSubmission).filter(
            QuestionnaireSubmission.id == submission_id
        ).first()

        if not submission:
            raise ValueError("Submissão não encontrada")

        db.delete(submission)
        db.commit()
        return True

    def list_submissions_by_questionnaire(self, db: Session, questionnaire_id: int) -> List[QuestionnaireSubmission]:
        return db.query(QuestionnaireSubmission).filter(
            QuestionnaireSubmission.questionnaire_id == questionnaire_id
        ).order_by(QuestionnaireSubmission.submitted_at.desc()).all()

    def get_submission_statistics(self, db: Session, questionnaire_id: int) -> Dict[str, Any]:
        submissions = self.list_submissions_by_questionnaire(db, questionnaire_id)

        if not submissions:
            return {
                "total_submissions": 0,
                "average_score": 0.0,
                "max_score": 0.0,
                "min_score": 0.0,
                "submission_rate": 0.0
            }

        scores = [s.total_score for s in submissions]

        return {
            "total_submissions": len(submissions),
            "average_score": round(sum(scores) / len(scores), 2),
            "max_score": max(scores),
            "min_score": min(scores),
            "median_score": round(sorted(scores)[len(scores) // 2], 2) if scores else 0.0,
            "latest_submission": submissions[0].submitted_at.isoformat() if submissions else None
        }

    def get_answers_by_question(self, db: Session, questionnaire_id: int, question_id: int) -> List[Answer]:
        return db.query(Answer).join(QuestionnaireSubmission).filter(
            QuestionnaireSubmission.questionnaire_id == questionnaire_id,
            Answer.question_id == question_id
        ).all()
