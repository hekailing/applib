# coding: utf8

render = {
    'engine': 'jinja2',
    'template_path': 'templates'
}


fieldfmt = {
    'money': '^\d{1,%d}(\.\d{1,%d})?$',  # % (ndigit_int, ndigit_decimal)
    'datetime': '^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$',
    'date': '^\d{4}-\d\d-\d\d$',
    'username': '^\w+$',
    'password': '^[0-9a-z]{64}$',
    'phone': '^\d{11}$',
    'postcode': '^\d{6}$',
    'ip': '^\d{1,3}(.\d{1,3}){3}(:\d{2,5})?$'
}
