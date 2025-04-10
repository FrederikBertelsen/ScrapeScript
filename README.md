> [!WARNING]  
> Disclaimer: Work in Progress.
> 
> ScrapeScript is currently in early development. Features and functionality are subject to change.

# ScrapeScript
ScrapeScript is a Domain Specific Language (DSL) designed to simplify web scraping tasks. It provides a concise, readable syntax that allows users to define data extraction workflows without writing complex code.

The core design principle of ScrapeScript is its browser independence. The language is deliberately decoupled from specific browser automation implementations, using a clean interface layer that allows it to work with any Python-compatible browser automation library. This means ScrapeScript can work with Playwright, Selenium, Puppeteer, BeautifulSoup, or any other automation tools that implement the required interface.

This modular approach ensures that as browser technologies evolve, ScrapeScript can adapt without requiring changes to scripts written in the language.

## Current TODO
1. Import data to execute from
   1. figure out syntax
   2. write code
2. implement BeautifulSoup4 (tab navigation simulation)
3. custom css: ":parent", ":text_contains()", etc.?
4. pipes (connecting ScrapeScripts together)?
   1. can we do realtime data feedthrough?
   2. figure out syntax for piping data between ScrapeScripts
   3. Can we maybe have muliple ScrapeScripts in the same file, with some pipe connecters somehow?
   4. paralellism?
   5. What would be the best way to implement this?
5. More steps?
   1. save current url to field step
6. fix bugs
   1. parser doesn't pass css selectors with ":nth-child(1)" in it. no : or num chars
   2. string does not parse numbers.
   3. string should not parse new-lines!

