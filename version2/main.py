import asyncio
import argparse
import json
from typing import Dict, List, Any
from lexer import Lexer
from parser import Parser
from interpreter import Interpreter

async def run_script(script_path: str) -> List[Dict[str, Any]]:
    """Run a ScrapeScript from a file."""
    # Read the script file
    with open(script_path, 'r') as f:
        script_text: str = f.read()
    
    # Tokenize the script
    lexer = Lexer(script_text)
    tokens = lexer.tokenize()
    
    # Parse the tokens into an AST
    parser = Parser(tokens)
    ast = parser.parse()
    
    # Execute the AST
    interpreter = Interpreter(ast)
    results = await interpreter.execute()
    
    return results

def main() -> None:
    parser = argparse.ArgumentParser(description='ScrapeScript: A DSL for web scraping')
    parser.add_argument('script', help='Path to the ScrapeScript file')
    parser.add_argument('-o', '--output', help='Output file path (JSON format)')
    
    args = parser.parse_args()
    
    # Run the script
    results: List[Dict[str, Any]] = asyncio.run(run_script(args.script))
    
    # Print the results to stdout
    print(json.dumps(results, indent=2))
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {args.output}")

if __name__ == '__main__':
    main()