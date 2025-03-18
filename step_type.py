from enum import Enum

class StepType(Enum):
    GOTO_URL = "GOTO_URL"
    IF_EXISTS = "IF_EXISTS"
    EXTRACT = "EXTRACT"
    CLICK = "CLICK"
    # FOREACH = "FOREACH"
    SAVE_ROW = "SAVE_ROW"
    GOTO = "GOTO"
    LOG = "LOG"
    END = "END"