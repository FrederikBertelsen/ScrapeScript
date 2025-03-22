
import re

from step_type import StepType
from steps import *


def load_file(file) -> list[str]:
    with open(file) as f:
        content = f.readlines()
    return content

def parse_file(file_path: str) -> list[Step]:
    step_list = []
    step_id_incremental = 0

    lines = load_file(file_path)
    for line in lines:
        line = line.strip()
        if line == '':
            continue

        step_id_incremental += 1

        # First extract the step id and type
        match = re.match(r'^(\w+)(?: +(.*?)(?: +-> +(\d+))?)?$', line)
        if not match:
            print(f'Error parsing line: {line}')
            continue
        step_type_str = match.group(1)
        args = match.group(2) if match.group(2) else ""
        next_step_id = int(match.group(3)) if match.group(3) else -1

        try:
            step_type = StepType(step_type_str.upper())
        except ValueError:
            print(f"Unknown step type string: '{step_type_str}' on line: {step_id_incremental}")
            exit(1)
            continue

        match step_type:
            case StepType.GOTO_URL:
                match = re.match(r"'([^']+)'", args)
                if not match:
                    print(f'Error parsing GOTO_URL: {line}')
                    continue
                url = match.group(1).strip()
                goto_url_step = GoToUrlStep(step_id_incremental, url, next_step_id)
                step_list.append(goto_url_step)
                
            case StepType.IF_EXISTS:
                match = re.match(r"'([^']+)' +\? +(\d+) +: +(\d+)", args)
                if not match:
                    print(f'Error parsing IF_EXISTS: {line}')
                    continue
                selector = match.group(1).strip()
                next_step_id_true = int(match.group(2))
                next_step_id_false = int(match.group(3))
                if_exists_step = IfExistsStep(step_id_incremental, selector, next_step_id_true, next_step_id_false)
                step_list.append(if_exists_step)
                
            case StepType.EXTRACT:
                match = re.match(r"'([^']+)' +'([^']+)'", args)
                if not match:
                    print(f'Error parsing EXTRACT: {line}')
                    continue
                field_name = match.group(1).strip()
                selector = match.group(2).strip()
                extract_step = ExtractStep(step_id_incremental, selector, field_name, next_step_id)
                step_list.append(extract_step)
                
            case StepType.CLICK:
                match = re.match(r"'([^']+)'", args)
                if not match:
                    print(f'Error parsing CLICK: {line}')
                    continue
                selector = match.group(1).strip()
                click_step = ClickStep(step_id_incremental, selector, next_step_id)
                step_list.append(click_step)
                
            case StepType.SAVE_ROW:
                save_row_step = SaveRowStep(step_id_incremental, next_step_id)
                step_list.append(save_row_step)
                
            case StepType.GOTO_LINE:
                match = re.match(r'(\d+)', args)
                if not match:
                    print(f'Error parsing GOTO_LINE: {line}')
                    continue
                next_step_id = int(match.group(1))

                goto_line_step = GotoLineStep(step_id_incremental, next_step_id)
                step_list.append(goto_line_step)
                
            case StepType.LOG:
                match = re.match(r"'([^']+)'", args)
                if not match:
                    print(f'Error parsing LOG: {line}')
                    continue
                message = match.group(1).strip()
                log_step = LogStep(step_id_incremental, message, next_step_id)
                step_list.append(log_step)
                
            case StepType.END:
                end_step = EndStep(step_id_incremental)
                step_list.append(end_step)
                
            case _:
                print(f"Unknown step type: {step_type}")
            
        
    return step_list
