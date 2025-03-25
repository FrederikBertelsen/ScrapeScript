from typing import List, Optional, Any
from playwright.async_api import async_playwright, ElementHandle as PlaywrightElement
from playwright.async_api import Page as PlaywrightPage, Browser as PlaywrightBrowser

from browser.interface import BrowserAutomation, Browser, Page, Element

class PlaywrightElementAdapter(Element):
    """Adapter for Playwright ElementHandle."""
    
    def __init__(self, element: PlaywrightElement) -> None:
        self._element = element
    
    async def click(self) -> None:
        await self._element.click()
    
    async def text_content(self) -> str:
        return await self._element.text_content() or ""
    
    async def get_attribute(self, name: str) -> Optional[str]:
        return await self._element.get_attribute(name)
    
    async def query_selector(self, selector: str) -> Optional[Element]:
        element = await self._element.query_selector(selector)
        return PlaywrightElementAdapter(element) if element else None
    
    async def query_selector_all(self, selector: str) -> List[Element]:
        elements = await self._element.query_selector_all(selector)
        return [PlaywrightElementAdapter(e) for e in elements]

class PlaywrightPageAdapter(Page):
    """Adapter for Playwright Page."""
    
    def __init__(self, page: PlaywrightPage) -> None:
        self._page = page
    
    async def goto(self, url: str) -> None:
        await self._page.goto(url)
    
    async def query_selector(self, selector: str) -> Optional[Element]:
        element = await self._page.query_selector(selector)
        return PlaywrightElementAdapter(element) if element else None
    
    async def query_selector_all(self, selector: str) -> List[Element]:
        elements = await self._page.query_selector_all(selector)
        return [PlaywrightElementAdapter(e) for e in elements]
    
    async def go_back(self) -> None:
        await self._page.go_back()
    
    async def go_forward(self) -> None:
        await self._page.go_forward()

class PlaywrightBrowserAdapter(Browser):
    """Adapter for Playwright Browser."""
    
    def __init__(self, browser: PlaywrightBrowser) -> None:
        self._browser = browser
    
    async def new_page(self) -> Page:
        page = await self._browser.new_page()
        return PlaywrightPageAdapter(page)
    
    async def close(self) -> None:
        await self._browser.close()

class PlaywrightAutomation(BrowserAutomation):
    """Playwright implementation of browser automation."""
    
    def __init__(self) -> None:
        self._playwright = None
        self._browser = None
    
    async def launch(self, headless: bool = True) -> Browser:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=headless)
        return PlaywrightBrowserAdapter(self._browser)
    
    async def cleanup(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None