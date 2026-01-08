data_schema
  'url' as $url
  'category'
  'name' as $product_name
end_schema

if is_empty '$product_name'
  log 'No name found: $url'
  exit
end_if

set_field 'category' '$category'
set_field 'product_name' '$product_name'
set_field 'url' 'https://www.elgiganten.dk$url'

goto_url 'https://www.elgiganten.dk$url'

extract 'title' 'div.ProductPageHeader h1'
extract_attribute 'price' 'data-primary-price' 'div[data-primary-price]'

extract_attribute_list 'images' 'src' 'button > img'

save_row
