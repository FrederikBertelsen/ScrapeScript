0 GOTO_URL "https://example.com"

1 IF_EXISTS "body > #title" ? 2 : 4
    2 EXTRACT "Title" "body > #title"
    3 CLICK "#next-button" -> 5
    4 EXTRACT "Title" "#alternative-title"

5 IF_EXISTS "#next-page" ? 6 : 9
    6 CLICK "#next-page"
    7 LOG "Going to next page!"
    8 GOTO 1
9 END