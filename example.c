goto_url 'https://www.elgiganten.dk/computer-kontor/computere'

foreach 'ul.grid-flow-row-dense > li' as @phone
  extract_attribute 'url' 'href' '@phone a[href]'
  extract 'name' '@phone h2'
  set_field 'category' 'Computers'
  save_row
end_foreach