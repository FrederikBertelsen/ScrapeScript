from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict, Tuple
from browser.selector import Selector

class BrowserAutomation(ABC):
    """Interface for browser automation libraries."""
    
    @abstractmethod
    async def launch(self, headless: bool = True) -> None:
        """Launch a browser instance."""
        pass
    
    @abstractmethod
    async def goto(self, url: str) -> None:
        """Navigate to the specified URL."""
        pass
    
    @abstractmethod
    async def extract_text(self, selectors: List[Selector]) -> Optional[str]:
        """Extract text content from the first element matching any of the selectors."""
        pass
    
    @abstractmethod
    async def extract_texts(self, selectors: List[Selector]) -> List[str]:
        """Extract text content from all elements matching the first working selector."""
        pass
    
    @abstractmethod
    async def extract_attribute(self, selectors: List[Selector], attribute: str) -> Optional[str]:
        """Extract attribute value from the first element matching any of the selectors."""
        pass
    
    @abstractmethod
    async def extract_attributes(self, selectors: List[Selector], attribute: str) -> List[str]:
        """Extract attribute values from all elements matching the first working selector."""
        pass
    
    @abstractmethod
    async def click(self, selectors: List[Selector]) -> bool:
        """Click on the first element matching any of the selectors. Returns True if successful."""
        pass
    
    @abstractmethod
    async def element_exists(self, selectors: List[Selector]) -> bool:
        """Check if at least one element exists matching any of the selectors."""
        pass
    
    @abstractmethod
    async def get_elements_count(self, selectors: List[Selector]) -> int:
        """Get the count of elements matching the first working selector."""
        pass
    
    @abstractmethod
    async def go_back(self) -> None:
        """Navigate back in browser history."""
        pass
    
    @abstractmethod
    async def go_forward(self) -> None:
        """Navigate forward in browser history."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass