from typing import Callable, Optional
from nicegui import ui

class SortableColumn(ui.element, component='sortable_column.js'):
    def __init__(self, *, on_change: Optional[Callable] = None, group: str = None) -> None:
        super().__init__()
        self.on('item-drop', self._handle_drop)
        self._on_change = on_change
        self._classes.append('nicegui-column')
        self._props['group'] = group if group else 'default'

    def _handle_drop(self, e) -> None:
        if self._on_change:
            self._on_change(e)

    def update_position(self, element_id: int, new_place: int):
        element = self.client.elements[element_id]
        self.default_slot.children.remove(element)
        self.default_slot.children.insert(new_place, element)
        self.update()
