from typing import Callable, Optional
from pages.questionnaire_answer_page import questionnaire_answer_page
from nicegui import ui

def clear_and_render(content_container: ui.element, render_fn: Callable[[], None]):
    if not content_container:
        return
    content_container.clear()
    with content_container:
        render_fn()

@ui.page('/questionnaire/{questionnaire_id}/respond')
def respond_questionnaire_page(questionnaire_id: str):
    questionnaire_answer_page(questionnaire_id)
