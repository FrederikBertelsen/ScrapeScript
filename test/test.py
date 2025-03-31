import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import run_script

class ScriptTester:
    def __init__(self, test_cases_file='test_cases.json'):
        # Load test cases from JSON
        test_path = Path(__file__).parent / test_cases_file
        with open(test_path, 'r') as f:
            self.test_cases = json.load(f)
        
        self.passed = 0
        self.failed = 0
        
    def compare_results(self, expected, actual):
        """Compare results field by field and return list of errors"""
        errors = []
        
        if len(expected) != len(actual):
            return [f"Expected {len(expected)} items but got {len(actual)} items"]
        
        for i, (exp_item, act_item) in enumerate(zip(expected, actual)):
            # Check if all expected fields exist in actual result
            for key in exp_item:
                if key not in act_item:
                    errors.append(f"Item {i}: Missing field '{key}'")
                elif exp_item[key] != act_item[key]:
                    errors.append(f"Item {i}: Field '{key}' mismatch "
                                 f"(expected: '{exp_item[key]}', actual: '{act_item[key]}')")
                    
        return errors
    
    async def run_tests(self):
        """Run all tests and print results"""
        print(f"Running {len(self.test_cases)} tests...\n")
        
        start_time_total = time.time()
        
        for i, test_case in enumerate(self.test_cases):
            script = test_case['script']
            expected = test_case['expected']
            script_name = Path(script).name.split('.')[0]
                        
            start_time = time.time()
            try:
                results = await run_script(script, headless=True)
                errors = self.compare_results(expected, results)
                
                test_duration = time.time() - start_time
                
                if errors:
                    self.failed += 1
                    print(f"❌ FAILED: {script_name} ({test_duration:.2f}s)\n")
                    for error in errors:
                        print(f"  • {error}")
                    print(f"  Expected: {json.dumps(expected)}")
                    print(f"  Actual:   {json.dumps(results)}")
                else:
                    self.passed += 1
                    print(f"✅ PASSED: {script_name} ({test_duration:.2f}s)")
                    
            except Exception as e:
                test_duration = time.time() - start_time
                self.failed += 1
                print(f"❌ ERROR: {script_name} ({test_duration:.2f}s) - {str(e)}\n")
                        
        total_duration = time.time() - start_time_total
        
        # Print summary
        print(f"\nSummary: {self.passed} passed, {self.failed} failed (total time: {total_duration:.2f}s)")
        return self.failed == 0

if __name__ == "__main__":
    tester = ScriptTester()
    success = asyncio.run(tester.run_tests())
    sys.exit(0 if success else 1)