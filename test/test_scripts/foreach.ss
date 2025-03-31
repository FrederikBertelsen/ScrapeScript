goto_url "https://demo.dexi.io/sites/linklist_external/"

select '.list-group' as @container

foreach '@container .list-group-item' as @item
  extract 'text' '@item'
  extract_attribute 'url' 'href' '@item'
  save_row
end_foreach