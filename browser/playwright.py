from typing import List, Optional, Any
from playwright.async_api import async_playwright, ElementHandle, Page, Browser
from browser.interface import BrowserAutomation, Element

class PlaywrightElement(Element):
    """Playwright implementation of Element interface for tab-based navigation."""
    
    def __init__(self, handle: ElementHandle) -> None:
        self._handle = handle
        
    async def query(self, selector: str) -> Optional['Element']:
        handle = await self._handle.query_selector(selector)
        if handle:
            return PlaywrightElement(handle)
        return None
        
    async def query_all(self, selector: str) -> List['Element']:
        handles = await self._handle.query_selector_all(selector)
        return [PlaywrightElement(handle) for handle in handles]
    
    async def text_content(self) -> str:
        return await self._handle.text_content() or ""
        
    async def get_attribute(self, name: str) -> Optional[str]:
        return await self._handle.get_attribute(name)
        
    async def click(self) -> None:
        await self._handle.click()

class PlaywrightAutomation(BrowserAutomation):
    """
    Playwright implementation that uses tabs for navigation history.
    Each new URL opens in a new tab, and history navigation switches between tabs.
    This preserves page state when navigating back and forth.
    """
    
    def __init__(self) -> None:
        self._playwright = None
        self._browser = None
        self._context = None  # Browser context (window)
        self._tabs = []  # List of all tabs/pages
        self._current_tab_index = -1  # Index of current active tab
    
    @property
    def _current_page(self) -> Optional[Page]:
        """Get the currently active page/tab."""
        if 0 <= self._current_tab_index < len(self._tabs):
            return self._tabs[self._current_tab_index]
        return None
    
    async def launch(self, headless: bool = True) -> None:
        """Launch browser and initialize with a blank page/tab."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=headless)
        
        # Create a single browser context (window)
        self._context = await self._browser.new_context()
        
        # Create initial tab within the context
        initial_page = await self._context.new_page()
        await initial_page.goto("about:blank")
        self._tabs = [initial_page]
        self._current_tab_index = 0
    
    async def goto(self, url: str) -> None:
        """Navigate to URL by opening a new tab and closing any forward tabs."""
        # If we previously went back, truncate the tab list
        if self._current_tab_index < len(self._tabs) - 1:
            # Close any tabs that would be "ahead" in history
            for tab in self._tabs[self._current_tab_index + 1:]:
                await tab.close()
            # Remove closed tabs from our list
            self._tabs = self._tabs[:self._current_tab_index + 1]
        
        # Create a new tab and navigate to the URL
        new_page = await self._context.new_page()
        await new_page.goto(url, wait_until="domcontentloaded")
        
        # Add the new tab and make it current
        self._tabs.append(new_page)
        self._current_tab_index = len(self._tabs) - 1
    
    async def get_current_url(self) -> str:
        """Get the URL of the current page."""
        if not self._current_page:
            return ""
        return self._current_page.url
    
    async def query_selector(self, selector: str) -> Optional[Element]:
        """Find first element matching selector in current tab."""
        if not self._current_page:
            return None
            
        handle = await self._current_page.query_selector(selector)
        if handle:
            return PlaywrightElement(handle)
        return None
    
    async def query_selector_all(self, selector: str) -> List[Element]:
        """Find all elements matching selector in current tab."""
        if not self._current_page:
            return []
            
        handles = await self._current_page.query_selector_all(selector)
        return [PlaywrightElement(handle) for handle in handles]
    
    async def extract_text(self, element: Element) -> str:
        """Extract text content from element."""
        playwright_element = element
        return await playwright_element.text_content()
    
    async def extract_attribute(self, element: Element, attribute: str) -> Optional[str]:
        """Extract attribute value from element."""
        playwright_element = element
        return await playwright_element.get_attribute(attribute)
    
    async def click(self, element: Element) -> bool:
        playwright_element = element  # Type cast would be better here
        if not self._current_page:
            return False
            
        try:
            # Set up a navigation detector
            navigation_occurred = False
            async def on_navigation():
                nonlocal navigation_occurred
                navigation_occurred = True
            
            # Listen for navigation events
            self._current_page.on("framenavigated", lambda _: on_navigation())
            
            # Perform the click
            await playwright_element.click()
            
            # Short wait to detect if navigation happens
            await self._current_page.wait_for_timeout(500)
            
            # Check if navigation occurred
            if navigation_occurred:
                print("ERROR: Navigation detected after click. Use goto_href instead for navigation.")
                return False
                
            return True
        except Exception as e:
            # Click failed completely
            print(f"Click operation failed: {str(e)}")
            return False
            
    async def go_back(self) -> None:
        """Go back to previous tab."""
        if self._current_tab_index > 0:
            self._current_tab_index -= 1
            # Bring the tab into focus
            await self._current_page.bring_to_front()
    
    async def go_forward(self) -> None:
        """Go forward to next tab."""
        if self._current_tab_index < len(self._tabs) - 1:
            self._current_tab_index += 1
            # Bring the tab into focus
            await self._current_page.bring_to_front()
    
    async def cleanup(self) -> None:
        """Close all tabs and the browser."""
        # Close all tabs
        for tab in self._tabs:
            try:
                await tab.close()
            except:
                pass
        
        # Clear tab list
        self._tabs = []
        self._current_tab_index = -1
        
        # Close browser context
        if self._context:
            await self._context.close()
            self._context = None
        
        # Close browser
        if self._browser:
            await self._browser.close()
            self._browser = None
        
        # Stop playwright
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None