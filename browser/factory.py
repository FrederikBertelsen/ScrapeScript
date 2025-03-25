from typing import Dict, Type
from browser.interface import BrowserAutomation
from browser.playwright import PlaywrightAutomation

class BrowserFactory:
    """Factory for creating browser automation instances."""
    
    _implementations: Dict[str, Type[BrowserAutomation]] = {
        "playwright": PlaywrightAutomation
    }
    
    @classmethod
    def create(cls, implementation: str = "playwright") -> BrowserAutomation:
        """Create a browser automation instance."""
        if implementation not in cls._implementations:
            supported = ", ".join(cls._implementations.keys())
            raise ValueError(f"Unsupported browser implementation: {implementation}. "
                             f"Supported implementations: {supported}")
        
        return cls._implementations[implementation]()
    
    @classmethod
    def register(cls, name: str, implementation: Type[BrowserAutomation]) -> None:
        """Register a new browser automation implementation."""
        cls._implementations[name] = implementation