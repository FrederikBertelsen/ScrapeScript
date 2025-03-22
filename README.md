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
8 GOTO_LINE 5

9 IF_EXISTS "#next-page" ? 10 : 13
    10 CLICK "#next-page"
    11 LOG "Going to next page!"
    12 GOTO_LINE 1
13 END
```

# ScrapeScript Step Syntax

## Step Types

### GOTO_URL
Navigates to a URL
`GOTO_URL "url" [-> next_step_id]`

### IF_EXISTS
Conditional branching based on element existence
`IF_EXISTS "selector" ? true_step_id : false_step_id`

### EXTRACT
Extracts data from an element and assigns to a field
`EXTRACT "FieldName" "selector" [-> next_step_id]`

### CLICK
Clicks on an element
`CLICK "selector" [-> next_step_id]`

### SAVE_ROW
Saves current data as a row
`SAVE_ROW [-> next_step_id]`

### GOTO_LINE
Jumps to another step
`GOTO_LINE step_id`

### LOG
Prints a message
`LOG "message" [-> next_step_id]`

### END
Terminates execution
`END`

## General Syntax Rules

- Each line starts with a numeric step ID
- Use `->` to explicitly specify the next step (optional for most steps)
- Indentation indicates nested steps (such as within IF_EXISTS or FOR blocks)
- Double quotes `"` are used for string literals
- Steps execute sequentially unless redirected by conditional logic or explicit next step IDs