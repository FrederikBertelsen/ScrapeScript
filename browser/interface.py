from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Tuple
from browser.selector import Selector

class Element(ABC):
    """Interface for a DOM element that can be queried."""
    
    @abstractmethod
    async def query(self, selector: str) -> Optional['Element']:
        """Find the first child element matching the selector."""
        pass
        
    @abstractmethod
    async def query_all(self, selector: str) -> List['Element']:
        """Find all child elements matching the selector."""
        pass

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
    async def get_current_url(self) -> str:
        """Get the current page URL."""
        pass
    
    @abstractmethod
    async def query_selector(self, selector: str) -> Optional[Element]:
        """Find the first element matching the selector."""
        pass
    
    @abstractmethod
    async def query_selector_all(self, selector: str) -> List[Element]:
        """Find all elements matching the selector."""
        pass
    
    @abstractmethod
    async def extract_text(self, element: Element) -> str:
        """Extract text content from an element."""
        pass
    
    @abstractmethod
    async def extract_attribute(self, element: Element, attribute: str) -> Optional[str]:
        """Extract attribute value from an element."""
        pass
    
    @abstractmethod
    async def click(self, element: Element) -> bool:
        """Click on an element. Returns True if successful."""
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