from typing import List, Optional, Any
from playwright.async_api import async_playwright, ElementHandle, Page, Browser
from browser.interface import BrowserAutomation, Element

class PlaywrightElement(Element):
    """Playwright implementation of Element interface."""
    
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
    
    # These methods are implementation details, not part of the Element interface
    async def text_content(self) -> str:
        return await self._handle.text_content() or ""
        
    async def get_attribute(self, name: str) -> Optional[str]:
        return await self._handle.get_attribute(name)
        
    async def click(self) -> None:
        await self._handle.click()

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
    
    async def goto(self, url: str) -> None:
        await self._page.goto(url)
    
    async def query_selector(self, selector: str) -> Optional[Element]:
        handle = await self._page.query_selector(selector)
        if handle:
            return PlaywrightElement(handle)
        return None
    
    async def query_selector_all(self, selector: str) -> List[Element]:
        handles = await self._page.query_selector_all(selector)
        return [PlaywrightElement(handle) for handle in handles]
    
    async def extract_text(self, element: Element) -> str:
        playwright_element = element  # Type cast would be better here
        return await playwright_element.text_content()
    
    async def extract_attribute(self, element: Element, attribute: str) -> Optional[str]:
        playwright_element = element  # Type cast would be better here
        return await playwright_element.get_attribute(attribute)
    
    async def click(self, element: Element) -> bool:
        playwright_element = element  # Type cast would be better here
        try:
            async with self._page.expect_navigation(timeout=5000, wait_until="networkidle"):
                await playwright_element.click()
            return True
        except:
            return False
    
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