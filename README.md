# ScrapeScript
A DSL for web scrapping

## Example
```c
0 GOTO_URL "https://example.com"

1 IF_EXISTS "#title" ? 2 : 4
    2 EXTRACT "Title" "#title"
    3 CLICK "#next-button" -> 5
    4 EXTRACT "Title" "#alternative-title"

5 FOR ".item"
    6 EXTRACT "Element" CURRENT
    7 SAVE_ROW
8 GOTO 5

9 IF_EXISTS "#next-page" ? 10 : 13
    10 CLICK "#next-page"
    11 LOG "Going to next page!"
    12 GOTO 1
13 END
```