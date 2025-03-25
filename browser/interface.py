from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Any, Dict

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Any, Dict

class Element(ABC):
    """Interface for interacting with web page elements."""
    
    @abstractmethod
    async def click(self) -> None:
        """Click on this element."""
        pass
    
    @abstractmethod
    async def text_content(self) -> str:
        """Get the text content of this element."""
        pass
    
    @abstractmethod
    async def get_attribute(self, name: str) -> Optional[str]:
        """Get the value of an attribute on this element."""
        pass
    
    @abstractmethod
    async def query_selector(self, selector: str) -> Optional['Element']:
        """Query for a child element matching the selector."""
        pass
    
    @abstractmethod
    async def query_selector_all(self, selector: str) -> List['Element']:
        """Query for all child elements matching the selector."""
        pass

class Page(ABC):
    """Interface for interacting with web pages."""
    
    @abstractmethod
    async def goto(self, url: str) -> None:
        """Navigate to the specified URL."""
        pass
    
    @abstractmethod
    async def wait_for_load_state(self, state: str) -> None:
        """Wait for the page to reach the specified load state."""
        pass
    
    @abstractmethod
    async def query_selector(self, selector: str) -> Optional[Element]:
        """Query for an element matching the selector."""
        pass
    
    @abstractmethod
    async def query_selector_all(self, selector: str) -> List[Element]:
        """Query for all elements matching the selector."""
        pass
    
    @abstractmethod
    async def go_back(self) -> None:
        """Navigate back in browser history."""
        pass
    
    @abstractmethod
    async def go_forward(self) -> None:
        """Navigate forward in browser history."""
        pass

class Browser(ABC):
    """Interface for browser automation."""
    
    @abstractmethod
    async def new_page(self) -> Page:
        """Create a new browser page."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the browser."""
        pass

class BrowserAutomation(ABC):
    """Interface for browser automation libraries."""
    
    @abstractmethod
    async def launch(self, headless: bool = True) -> Browser:
        """Launch a browser instance."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass