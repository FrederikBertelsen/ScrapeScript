goto_url 'https://example.com'
extract 'title' 'h1'
extract 'description' 'p'
save_row
goto_url 'https://scryfall.com/'
extract 'title' 'h1'
extract 'description' '.homepage-news'
save_row
exit