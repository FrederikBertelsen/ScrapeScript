
import re

from step_type import StepType
from steps import *


def load_file(file) -> list[str]:
    with open(file) as f:
        content = f.readlines()
    return content

def parse_file(file) -> list[Step]:
    step_list = []

    lines = load_file(file)
    for line in lines:
        line = line.strip()
        if line == '':
            continue

        # First extract the step id and type
        match = re.match(r'^(\d+) +([A-Z_]+)(?: +(.*?)(?: +-> +(\d+))?)?$', line)
        if not match:
            print(f'Error parsing line: {line}')
            continue
        step_id = int(match.group(1))
        step_type_str = match.group(2)
        args = match.group(3) if match.group(3) else ""
        next_step_id = int(match.group(4)) if match.group(4) else -1

        try:
            step_type = StepType(step_type_str)
        except ValueError:
            print(f"Unknown step type string: {step_type_str}")
            continue

        match step_type:
            case StepType.GOTO_URL:
                match = re.match(r'"([^"]+)"', args)
                if not match:
                    print(f'Error parsing GOTO_URL: {line}')
                    continue
                url = match.group(1).strip()
                goto_url_step = GoToUrlStep(step_id, url, next_step_id)
                step_list.append(goto_url_step)
                
            case StepType.IF_EXISTS:
                match = re.match(r'"([^"]+)" +\? +(\d+) +: +(\d+)', args)
                if not match:
                    print(f'Error parsing IF_EXISTS: {line}')
                    continue
                selector = match.group(1).strip()
                next_step_id_true = int(match.group(2))
                next_step_id_false = int(match.group(3))
                if_exists_step = IfExistsStep(step_id, selector, next_step_id_true, next_step_id_false)
                step_list.append(if_exists_step)
                
            case StepType.EXTRACT:
                match = re.match(r'"([^"]+)" +"([^"]+)"', args)
                if not match:
                    print(f'Error parsing EXTRACT: {line}')
                    continue
                field_name = match.group(1).strip()
                selector = match.group(2).strip()
                extract_step = ExtractStep(step_id, selector, field_name, next_step_id)
                step_list.append(extract_step)
                
            case StepType.CLICK:
                match = re.match(r'"([^"]+)"', args)
                if not match:
                    print(f'Error parsing CLICK: {line}')
                    continue
                selector = match.group(1).strip()
                click_step = ClickStep(step_id, selector, next_step_id)
                step_list.append(click_step)
                
            case StepType.SAVE_ROW:
                save_row_step = SaveRowStep(step_id, next_step_id)
                step_list.append(save_row_step)
                
            case StepType.GOTO:
                match = re.match(r'(\d+)', args)
                if not match:
                    print(f'Error parsing GOTO: {line}')
                    continue
                next_step_id = int(match.group(1))

                goto_step = GotoStep(step_id, next_step_id)
                step_list.append(goto_step)
                
            case StepType.LOG:
                match = re.match(r'"([^"]+)"', args)
                if not match:
                    print(f'Error parsing LOG: {line}')
                    continue
                message = match.group(1).strip()
                log_step = LogStep(step_id, message, next_step_id)
                step_list.append(log_step)
                
            case StepType.END:
                end_step = EndStep(step_id)
                step_list.append(end_step)
                
            case _:
                print(f"Unknown step type: {step_type}")
        
    return step_list
    
if __name__ == '__main__':
    steps = parse_file('example.c')

    for step in steps:
        print(step)
