import logging

from aiogram.filters.state import StatesGroup, State
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const


logger = logging.getLogger(__name__)

# ======================================================================================================
# Settings dialog's states

class ErrorsSG(StatesGroup):
    service_unavailable = State()



# ======================================================================================================
# 'Service unavailable' window

service_unavailable_error_window = Window(
    Const("<b>Service unavailable. Please try later.</b>"),
    state=ErrorsSG.service_unavailable,
)


def get_dialog() -> Dialog:
    dialog = Dialog(
                service_unavailable_error_window
            )
    return dialog
