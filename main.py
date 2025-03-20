#!/usr/bin/env python3
import sys
import os
import argparse
from playwright_wrapper import PlaywrightWrapper
from scrapescript_parser import parse_file
from stack_machine import StackMachine

def main():
    parser = argparse.ArgumentParser(description='Parse and execute ScrapeScript files.')
    parser.add_argument('script_file', help='The ScrapeScript file (.c extension) to parse')
    parser.add_argument('-v', '--verbose', action='store_true', help='Print parsed steps')
    parser.add_argument('-l', '--headless', action='store_true', help='run in headless mode')
    
    args = parser.parse_args()
    
    # Validate file exists
    if not os.path.isfile(args.script_file):
        print(f"Error: File '{args.script_file}' not found.")
        sys.exit(1)
    
    try:
        execute_script(args)
        
    except Exception as e:
        print(f"Error executing script: {e}")
        sys.exit(1)


def execute_script(args: argparse.Namespace):
        try:
            steps = parse_file(args.script_file)
        except Exception as e:
            print(f"Error parsing script: {e}")
            sys.exit(1)
    
        if args.verbose:
            print(f"\nParsed {len(steps)} steps from '{args.script_file}':\n")
            for step in steps:
                print(f"    {step}")
            print()

        playwright = PlaywrightWrapper(args.headless, args.verbose)
        stack_machine = StackMachine(steps, playwright, args.verbose)

        data = stack_machine.execute_steps()
        print(data)
        playwright.close()
        print("Script execution completed.")
        # Future
        # stack_machine = StackMachine(steps, PlaywrightWrapper(verbose=verbose), verbose)
        # stack_machine.execute_steps()
    

if __name__ == '__main__':
    main()