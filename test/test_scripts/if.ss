goto_url 'https://example.com/'

if exists 'h1'
    extract 'title' 'h1'
else
    set_field 'title' 'Title not found'
end_if
save_row

if exists 'not found one'
    set_field 'status' 'not found one'
else_if exists 'h1'
    set_field 'status' 'Title found'
else
    set_field 'status' 'Else hit'
end_if
save_row

if exists 'not found one'
    set_field 'status' 'not found one'
else_if exists 'not found two'
    set_field 'status' 'not found two'
else
    set_field 'status' 'Else hit'
end_if
save_row