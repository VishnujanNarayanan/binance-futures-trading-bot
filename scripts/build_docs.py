"""Generate the static API documentation published to GitHub Pages.

GitHub Pages serves files; it cannot run FastAPI. So the OpenAPI schema is dumped at
build time and rendered by a standalone Swagger UI, giving a documentation page that
is instant and never sleeps, while live calls still go to the deployed service.

    python scripts/build_docs.py [output_dir]
"""
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "trading_bot"))

from api import app

API_URL = os.getenv("TRADING_BOT_PUBLIC_URL", "https://binance-futures-bot-api.onrender.com")

INDEX = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Binance Futures Trading Bot &mdash; API</title>
<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui.css">
<style>
  body {{ margin: 0; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }}
  .banner {{
    background: #0b1020; color: #e8ecf5; padding: 20px 24px;
    border-bottom: 3px solid #f0b90b;
  }}
  .banner h1 {{ margin: 0 0 6px; font-size: 20px; }}
  .banner p {{ margin: 6px 0 0; font-size: 14px; line-height: 1.55; color: #b9c2d6; }}
  .banner a {{ color: #f0b90b; }}
  .banner code {{
    background: #1b2338; padding: 1px 6px; border-radius: 4px; font-size: 13px;
  }}
  .note {{ border-left: 3px solid #f0b90b; padding-left: 12px; margin-top: 14px; }}
</style>
</head>
<body>
<div class="banner">
  <h1>Binance Futures Testnet Trading Bot &mdash; REST API</h1>
  <p>
    This page is static and always available.
    <strong>Try it out</strong> sends real requests to
    <a href="{api_url}">{api_url}</a>.
  </p>
  <div class="note">
    <p>
      <strong>Reads are open.</strong> <code>/health</code>, <code>/positions</code> and
      the order history need no key.
    </p>
    <p>
      <strong>Placing or closing an order needs a key.</strong> Use
      <strong>Authorize</strong> and supply <code>X-API-Key</code>. Without one those
      endpoints return <code>401</code>.
    </p>
    <p>
      The API is on a free instance that sleeps after about 15 minutes idle. The first
      request after that takes roughly 45 seconds while it wakes &mdash; it is starting,
      not broken.
    </p>
  </div>
  <p><a href="https://github.com/VishnujanNarayanan/binance-futures-trading-bot">Source on GitHub</a></p>
</div>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui-bundle.js" crossorigin></script>
<script>
  window.ui = SwaggerUIBundle({{
    url: "./openapi.json",
    dom_id: "#swagger-ui",
    deepLinking: true,
    tryItOutEnabled: true,
    presets: [SwaggerUIBundle.presets.apis],
    layout: "BaseLayout",
  }});
</script>
</body>
</html>
"""


def build(out_dir):
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    schema = app.openapi()
    # Point Try-it-out at the deployed service. Without this Swagger UI resolves
    # relative to github.io, where no API exists.
    schema["servers"] = [{"url": API_URL, "description": "Live testnet deployment"}]

    (out / "openapi.json").write_text(json.dumps(schema, indent=2))
    (out / "index.html").write_text(INDEX.format(api_url=API_URL))
    # Stop Pages running the output through Jekyll.
    (out / ".nojekyll").write_text("")

    print(f"built {out}/index.html and {out}/openapi.json -> {API_URL}")
    return out


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "site")
