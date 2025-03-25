from typing import List, Optional, Any
from pyppeteer.element_handle import ElementHandle as PuppeteerElement
from pyppeteer.page import Page as PuppeteerPage
from pyppeteer.browser import Browser as PuppeteerBrowser

from browser.interface import BrowserAutomation, Browser, Page, Element

class PuppeteerElementAdapter(Element):
    """Adapter for Puppeteer ElementHandle."""
    
    def __init__(self, element: PuppeteerElement) -> None:
        self._element = element
    
    async def click(self) -> None:
        await self._element.click()
    
    async def text_content(self) -> str:
        try:
            # Use JSHandle.evaluate properly
            return await self._element.executionContext.evaluate('(element) => element.textContent || ""', self._element)
        except Exception as e:
            print(f"Error getting text content: {e}")
            return ""
    
    async def get_attribute(self, name: str) -> Optional[str]:
        try:
            # Use JSHandle.evaluate properly
            return await self._element.executionContext.evaluate(
                f'(element, name) => element.getAttribute(name)', 
                self._element, name
            )
        except Exception as e:
            print(f"Error getting attribute {name}: {e}")
            return None
    
    async def query_selector(self, selector: str) -> Optional[Element]:
        element = await self._element.querySelector(selector)
        return PuppeteerElementAdapter(element) if element else None
    
    async def query_selector_all(self, selector: str) -> List[Element]:
        elements = await self._element.querySelectorAll(selector)
        return [PuppeteerElementAdapter(e) for e in elements]

class PuppeteerPageAdapter(Page):
    """Adapter for Puppeteer Page."""
    
    def __init__(self, page: PuppeteerPage) -> None:
        self._page = page
    
    async def goto(self, url: str) -> None:
        await self._page.goto(url, {'timeout': 30000})

    async def query_selector(self, selector: str) -> Optional[Element]:
        element = await self._page.querySelector(selector)
        return PuppeteerElementAdapter(element) if element else None
    
    async def query_selector_all(self, selector: str) -> List[Element]:
        elements = await self._page.querySelectorAll(selector)
        return [PuppeteerElementAdapter(e) for e in elements]
    
    async def go_back(self) -> None:
        await self._page.goBack()
    
    async def go_forward(self) -> None:
        await self._page.goForward()

class PuppeteerBrowserAdapter(Browser):
    """Adapter for Puppeteer Browser."""
    
    def __init__(self, browser: PuppeteerBrowser) -> None:
        self._browser = browser
    
    async def new_page(self) -> Page:
        page = await self._browser.newPage()
        return PuppeteerPageAdapter(page)
    
    async def close(self) -> None:
        await self._browser.close()

class PuppeteerAutomation(BrowserAutomation):
    """Puppeteer implementation of browser automation."""
    
    def __init__(self) -> None:
        self._browser = None
        import pyppeteer
        self._pyppeteer = pyppeteer
    
    async def launch(self, headless: bool = True) -> Browser:
        self._browser = await self._pyppeteer.launch(
            headless=headless,
            args=['--disable-dev-shm-usage', '--no-sandbox'],
            handleSIGINT=False  # Prevent signal handling conflicts
        )
        return PuppeteerBrowserAdapter(self._browser)
    
    async def cleanup(self) -> None:
        # Don't try to close browser again if it was already closed
        # in the Browser.close() method
        self._browser = None