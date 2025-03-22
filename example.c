goto_url 'https://scryfall.com/search?q=%28type%3Acreature+type%3Alegendary%29+%28game%3Apaper%29+%28color%3AG%29&unique=cards&as=grid&order=name'
extract 'text' '.search-info > p:nth-child(1) > strong:nth-child(1)'
save_row
if_exists 'div.search-controls:nth-child(1) > div:nth-child(1) > div:nth-child(2) > a:nth-child(4)' ? 5 : 7
click 'div.search-controls:nth-child(1) > div:nth-child(1) > div:nth-child(2) > a:nth-child(4)'
goto_line 2
end



extract 'Title' 'h1'
save_row
if_exists 'input.homepage-form-field' ? 7 : 5
LOG 'Search form NOT found'
END
LOG 'Search form found'
CLICK 'p.homepage-links > a'
EXTRACT 'Name' 'h1.visuallyhidden'
SAVE_ROW
END

