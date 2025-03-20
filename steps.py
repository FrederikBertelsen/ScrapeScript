from step_type import StepType

from abc import ABC, abstractmethod
from playwright.sync_api import Page

class Step(ABC):
    def __init__(self, step_id: int, type: StepType, next_step_id: int = -1):
        self.id = step_id
        self.type = type
        self.next_step_id = next_step_id

    @abstractmethod
    def __str__(self):
        # return f'{self.id} {self.type.name}' + (f' -> {self.next_step_id}' if self.next_step_id != -1 else '')
        raise NotImplementedError
    
    @abstractmethod
    def execute_and_get_next_step(self, page: Page, row: dict) -> int:
        raise NotImplementedError
    
class GoToUrlStep(Step):
    def __init__(self, step_id: int, url: str, next_step_id: int = -1):
        super().__init__(step_id, StepType.GOTO_URL, next_step_id)
        self.url = url

    def __str__(self):
        return f'{self.id} {self.type.name} "{self.url}"' + (f' -> {self.next_step_id}' if self.next_step_id != -1 else '')
    
    def execute_and_get_next_step(self, page: Page, row: dict) -> int:
        page.goto(self.url)
        page.wait_for_load_state('networkidle')
        return self.next_step_id
        

class IfExistsStep(Step):
    def __init__(self, step_id: int, selector: str, next_step_id_true: int, next_step_id_false: int):
        super().__init__(step_id, StepType.IF_EXISTS)
        self.selector = selector
        self.next_step_id_true = next_step_id_true
        self.next_step_id_false = next_step_id_false

    def __str__(self):
        return f'{self.id} {self.type.name} "{self.selector}" ? {self.next_step_id_true} : {self.next_step_id_false}'
    
    def execute_and_get_next_step(self, page: Page, row: dict) -> int:
        if page.query_selector(self.selector):
            return self.next_step_id_true
        else:
            return self.next_step_id_false

class ExtractStep(Step):
    def __init__(self, step_id: int, selector: str, field: str, next_step_id: int = -1):
        super().__init__(step_id, StepType.EXTRACT, next_step_id)
        self.selector = selector
        self.field = field

    def __str__(self):
        return f'{self.id} {self.type.name} "{self.field}" "{self.selector}"' + (f' -> {self.next_step_id}' if self.next_step_id != -1 else '')

    def execute_and_get_next_step(self, page: Page, row: dict) -> int:
        element = page.query_selector(self.selector)
        if element:
            row[self.field] = element.inner_text()
        else:
            raise Exception(f'Element not found: {self.selector}')
        return self.next_step_id

class ClickStep(Step):
    def __init__(self, step_id: int, selector: str, next_step_id: int = -1):
        super().__init__(step_id, StepType.CLICK, next_step_id)
        self.selector = selector

    def __str__(self):
        return f'{self.id} {self.type.name} "{self.selector}"' + (f' -> {self.next_step_id}' if self.next_step_id != -1 else '')

    def execute_and_get_next_step(self, page: Page, row: dict) -> int:
        element = page.query_selector(self.selector)
        if not element:
            raise Exception(f'Element not found: {self.selector}')
        element.click()
        page.wait_for_load_state('networkidle')
        return self.next_step_id
    
# class ForeachStep(Step):
#     def __init__(self, step_id: int, selector: str, steps: list, next_step_id: int = -1):
#         super().__init__(step_id, StepType.FOREACH, next_step_id)
#         self.selector = selector
#         self.steps = steps

#     def __str__(self):
#         return f'{self.id} {self.type.name} {self.selector}'

class GotoLineStep(Step):
    def __init__(self, step_id: int, next_step_id: int):
        super().__init__(step_id, StepType.GOTO_LINE, next_step_id)

    def __str__(self):
        return f'{self.id} {self.type.name} {self.next_step_id}'
    
    def execute_and_get_next_step(self, page: Page, row: dict) -> int:
        return self.next_step_id
    
class LogStep(Step):
    def __init__(self, step_id: int, message: str, next_step_id: int = -1):
        super().__init__(step_id, StepType.LOG, next_step_id)
        self.message = message

    def __str__(self):
        return f'{self.id} {self.type.name} "{self.message}"' + (f' -> {self.next_step_id}' if self.next_step_id != -1 else '')

    def execute_and_get_next_step(self, page: Page, row: dict) -> int:
        print(self.message)
        return self.next_step_id

class SaveRowStep(Step):
    def __init__(self, step_id: int, next_step_id: int = -1):
        super().__init__(step_id, StepType.SAVE_ROW, next_step_id)

    def __str__(self):
        return f'{self.id} {self.type.name}' + (f' -> {self.next_step_id}' if self.next_step_id != -1 else '')
    
    def execute_and_get_next_step(self, page: Page, row: dict) -> int:
        return self.next_step_id
    
class EndStep(Step):
    def __init__(self, step_id: int):
        super().__init__(step_id, StepType.END)

    def __str__(self):
        return f'{self.id} {self.type.name}'
    
    def execute_and_get_next_step(self, page: Page, row: dict) -> int:
        raise Exception('Cannot execute end step')