goto_url 'https://demo.dexi.io/sites/list_detail/'

extract 'title' 'h1'

select '.list-group' as @container

foreach '@container .list-group-item' as @item
  extract 'name' '@item'
  extract_attribute 'url' 'href' '@item'
  click '@item'
  extract 'description' 'h1'
  save_row
  history_back
end_foreach