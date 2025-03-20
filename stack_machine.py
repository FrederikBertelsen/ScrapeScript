from time import sleep
from typing import List
from playwright_wrapper import PlaywrightWrapper
from steps import *


class StackMachine:
    def __init__(self, step_list: list[Step], playwrightWrapper: PlaywrightWrapper, verbose: bool = False):
        self.playwright = playwrightWrapper
        self.page = self.playwright.page
        self.verbose = verbose

        self.steps_by_id: dict[int, Step] = {}
        for step in step_list:
            self.steps_by_id[step.id] = step
    
    def execute_steps(self) -> List[dict]:
        if self.verbose:
            print()

        data = []
        current_row = {}

        current_step = self.steps_by_id[1]
        while current_step.type != StepType.END:
            if self.verbose:
                print(f"Executing: {current_step}")

            if current_step.type == StepType.SAVE_ROW:
                data.append(current_row)
                current_row = {}

            next_step_id = current_step.execute_and_get_next_step(self.page, current_row)

            if next_step_id == -1:
                next_step_id = current_step.id + 1
                current_step = self.steps_by_id[next_step_id]
                while current_step is None and next_step_id <= 1000:
                    next_step_id += 1
                    current_step = self.steps_by_id[next_step_id]
                if next_step_id > 1000:
                    raise Exception("No next step found. Out of step_id bounds")
                
            else:
                current_step = self.steps_by_id[next_step_id]

            if current_step is None:
                raise Exception(f"Step {next_step_id} not found in memory")
            
            # sleep(1)
        
        if self.verbose:
            print()

        return data