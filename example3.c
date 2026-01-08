goto_url 'https://scryfall.com/search?q=color%3DWB+%28game%3Apaper%29+ab&unique=cards&as=grid&order=name'

select 'div.card-grid-inner' as @container

foreach '@container .card-grid-item-card' as @card
  extract_attribute 'url' 'href' '@card'
  extract 'name' '@card span.card-grid-item-invisible-label'
  extract_attribute 'image' 'src' '@card img'
  goto_href '@card'
  extract 'type' '.card-text-oracle'
  history_back
  save_row
end_foreach

