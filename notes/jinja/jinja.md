# Jinja Tutorial

Jinja is a **text templating engine**: you write templates with placeholders and logic, then **render** them by passing a context (a dict).

## Getting Started

```bash
pip install jinja2
```

Example program

```python
from jinja2 import Template

tpl = Template("Hello {{ user }}! You have {{ messages|length }} messages.")
print(tpl.render(user="Alice", messages=["a", "b", "c"]))
```

- `{{ ... }}`: expressions / variables

- `{% ... %}`: statements (loops / ifs)

- `{# ... #}`: comments

## Syntax

### Variables & filters

```jinja
{{ username }}
{{ price | round(2) }}
{{ items | join(", ") }}
{{ user.name | default("anonymous") }}
```

- Filters pipe values through functions. Built-ins: `join`, `length`, `upper`, `lower`, `replace`, `safe`, `escape`, `default`, `sort`, `unique`, `map`, `select`, etc.

### Control flow

```jinja
{% if items %}
  You have {{ items|length }} items.
{% else %}
  No items.
{% endif %}

{% for i, item in enumerate(items) %}
  {{ i }}: {{ item }}
{% endfor %}
```

Loop helpers:

```jinja
{{ loop.index0 }} {{ loop.first }} {{ loop.last }}
```

### Tests

```jinja
{% if x is even %}even{% endif %}
{% if s is string %}string{% endif %}
```

### Macros (reusable pieces)

```jinja
{% macro badge(text, kind="info") -%}
<span class="badge badge-{{ kind }}">{{ text }}</span>
{%- endmacro %}

{{ badge("New!") }}
```

### Includes & inheritance (DRY)

**base.html**

```jinja
<!doctype html>
<title>{% block title %}App{% endblock %}</title>
<body>
  <header>{% block header %}{% endblock %}</header>
  <main>{% block content %}{% endblock %}</main>
</body>
```

**page.html**

```jinja
{% extends "base.html" %}
{% block title %}Home · {{ super() }}{% endblock %}
{% block content %}
  {% include "partials/message.html" %}
{% endblock %}
```

### Whitespace control (quick, practical)

- Default: Jinja keeps your newlines.
- Add `-` to trim whitespace near a tag:

  - `{%- ... %}` trims **before** the tag (left).
  - `{% ... -%}` trims **after** the tag (right).
- Handy loop pattern (no blank lines):

```jinja
{% for x in items -%}
{{ x }}
{%- endfor %}
```

- Env-wide knobs:

```python
Environment(trim_blocks=True, lstrip_blocks=True)
```

Use these for consistent files, then sprinkle `-` where needed.

## Environment

```python
```

## Minimal end-to-end example

**templates/email.txt**

```jinja
Subject: Welcome, {{ user.name }}!

Hi {{ user.name }},

{% if offers %}
Here are your offers:
{% for o in offers -%}
- {{ o.name }}: {{ o.price | round(2) }}
{%- endfor %}
{% else %}
No offers today.
{% endif %}

-- {{ app_name }}
```

**render.py**

```python
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pathlib import Path

env = Environment(
    loader=FileSystemLoader("templates"),
    undefined=StrictUndefined,
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)
env.globals["app_name"] = "ShopCo"

tpl = env.get_template("email.txt")
out = tpl.render(
    user={"name": "Alice"},
    offers=[{"name": "Widget", "price": 19.995}, {"name": "Gadget", "price": 9.5}],
)
Path("out_email.txt").write_text(out)
print(out)
```
