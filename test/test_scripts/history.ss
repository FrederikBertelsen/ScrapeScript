goto_url 'https://example.com/'

extract 'title' 'h1'
save_row

goto_href 'a[href]'

extract 'title' 'h1'
save_row

history_back

extract 'title' 'h1'
save_row

history_forward

extract 'title' 'h1'
save_row

