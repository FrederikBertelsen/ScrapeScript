goto_url 'https://example.com/'

extract 'title' 'h1'
set_field 'title' 'Title has been overwritten'
save_row

save_row

extract 'title' 'h1'
save_row
