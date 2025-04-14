> [!WARNING]  
> Disclaimer: Work in Progress.
> 
> ScrapeScript is currently in early development. Features and functionality are subject to change.

# ScrapeScript
ScrapeScript is a Domain Specific Language (DSL) designed to simplify web scraping tasks. It provides a concise, readable syntax that allows users to define data extraction workflows without writing complex code.

The core design principle of ScrapeScript is its browser independence. The language is deliberately decoupled from specific browser automation implementations, using a clean interface layer that allows it to work with any Python-compatible browser automation library. This means ScrapeScript can work with Playwright, Selenium, Puppeteer, BeautifulSoup, or any other automation tools that implement the required interface.

This modular approach ensures that as browser technologies evolve, ScrapeScript can adapt without requiring changes to scripts written in the language.
