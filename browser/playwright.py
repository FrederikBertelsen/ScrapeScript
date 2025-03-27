from typing import List, Optional, Any
from playwright.async_api import async_playwright, ElementHandle, Page, Browser
from browser.interface import BrowserAutomation
from browser.selector import Selector

class PlaywrightAutomation(BrowserAutomation):
    """Playwright implementation of browser automation."""
    
    def __init__(self) -> None:
        self._playwright = None
        self._browser = None
        self._page = None
    
    async def launch(self, headless: bool = True) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=headless)
        self._page = await self._browser.new_page()
    
    async def _resolve_elements(self, selector: Selector) -> List[ElementHandle]:
        """Internal method to resolve elements based on Selector object."""
        # Base case: No parent - direct page query
        if selector.parent is None:
            if selector.css_selector is None:
                return []
            return await self._page.query_selector_all(selector.css_selector)
        
        # Recursive case: First resolve the parent elements
        parent_elements = await self._resolve_elements(selector.parent)
        if not parent_elements:
            return []
        
        # Get the specific parent element based on index
        parent_index = selector.parent.index if selector.parent.index is not None else 0
        if parent_index >= len(parent_elements):
            return []
        
        parent = parent_elements[parent_index]
        
        # If no css_selector, return the parent element itself
        if selector.css_selector is None:
            return [parent]
        
        # Query within the parent element
        return await parent.query_selector_all(selector.css_selector)
    
    async def _find_first_matching_elements(self, selectors: List[Selector]) -> List[ElementHandle]:
        """Try each selector in the list and return elements from the first one that works."""
        for selector in selectors:
            elements = await self._resolve_elements(selector)
            if elements:
                return elements
        return []
    
    async def goto(self, url: str) -> None:
        await self._page.goto(url)
    
    async def extract_text(self, selectors: List[Selector]) -> Optional[str]:
        elements = await self._find_first_matching_elements(selectors)
        if elements:
            return await elements[0].text_content()
        return None
    
    async def extract_texts(self, selectors: List[Selector]) -> List[str]:
        elements = await self._find_first_matching_elements(selectors)
        return [await element.text_content() for element in elements]
    
    async def extract_attribute(self, selectors: List[Selector], attribute: str) -> Optional[str]:
        elements = await self._find_first_matching_elements(selectors)
        if elements:
            return await elements[0].get_attribute(attribute)
        return None
    
    async def extract_attributes(self, selectors: List[Selector], attribute: str) -> List[str]:
        elements = await self._find_first_matching_elements(selectors)
        results = []
        for element in elements:
            attr_value = await element.get_attribute(attribute)
            if attr_value is not None:
                results.append(attr_value)
        return results
    
    async def click(self, selectors: List[Selector]) -> bool:
        elements = await self._find_first_matching_elements(selectors)
        if elements:
            # Create a promise for navigation that might happen
            async with self._page.expect_navigation(timeout=5000, wait_until="networkidle"):
                await elements[0].click()
            return True
        return False
    
    async def element_exists(self, selectors: List[Selector]) -> bool:
        return len(await self._find_first_matching_elements(selectors)) > 0
    
    async def get_elements_count(self, selectors: List[Selector]) -> int:
        elements = await self._find_first_matching_elements(selectors)
        return len(elements)
    
    async def go_back(self) -> None:
        await self._page.go_back()
    
    async def go_forward(self) -> None:
        await self._page.go_forward()
    
    async def cleanup(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None