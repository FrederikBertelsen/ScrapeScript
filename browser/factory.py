from typing import Dict, Type
from browser.interface import BrowserAutomation
from browser.playwright import PlaywrightAutomation

# Import the new Puppeteer implementation
try:
    from browser.puppeteer import PuppeteerAutomation
    PUPPETEER_AVAILABLE = True
except ImportError:
    PUPPETEER_AVAILABLE = False

class BrowserFactory:
    """Factory for creating browser automation instances."""
    
    _implementations: Dict[str, Type[BrowserAutomation]] = {
        "playwright": PlaywrightAutomation
    }
    
    # Register Puppeteer implementation if available
    if PUPPETEER_AVAILABLE:
        _implementations["puppeteer"] = PuppeteerAutomation
    
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