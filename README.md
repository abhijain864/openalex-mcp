# OpenAlex MCP Server

A small [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that lets
Claude (or any MCP client) search scholarly papers and authors via the
[OpenAlex](https://openalex.org) REST API.

OpenAlex is a free, fully open catalog of ~250M scholarly works — a clean, legal
alternative to scraping Google Scholar. **No API key required**, no rate-limit
arms race, no CAPTCHAs. It just returns JSON.

## Tools

| Tool | Description |
|------|-------------|
| `search_works` | Search papers by free text. Supports `year_from` / `year_to`, `open_access_only`, and `sort_by_citations`. |
| `get_work` | Fetch one work by OpenAlex ID (e.g. `W2741809807`) or DOI. Includes the reconstructed abstract. |
| `search_authors` | Find authors by name — affiliation, works/citation counts, top fields. |
| `get_author_works` | List an author's works (most-cited first) by OpenAlex author ID. |

## Requirements

- Python 3.10+
- [`mcp`](https://pypi.org/project/mcp/) and [`httpx`](https://pypi.org/project/httpx/) (see `requirements.txt`)

## Install

```bash
git clone https://github.com/abhijain864/openalex-mcp.git
cd openalex-mcp
pip install -r requirements.txt
```

### Optional: polite pool

OpenAlex offers a faster "polite pool" if you identify yourself with an email.
Set the `OPENALEX_MAILTO` environment variable to opt in (recommended but not
required):

```bash
export OPENALEX_MAILTO="you@example.com"
```

## Connecting to Claude

### Claude Code (CLI)

Run this once to register the server at user scope (available in every project):

```bash
claude mcp add --scope user openalex \
  --env OPENALEX_MAILTO=you@example.com \
  -- python /absolute/path/to/openalex-mcp/openalex_server.py
```

> On Windows, use the full path to `python.exe` and the script, e.g.
> `python C:\Users\you\openalex-mcp\openalex_server.py`.

Verify it's connected:

```bash
claude mcp list
```

Then just ask Claude things like *"find the most-cited open-access papers on
diffusion models since 2023."* The tools appear as `mcp__openalex__search_works`,
`mcp__openalex__get_work`, etc.

#### Or edit the config directly

Add an entry under `mcpServers` in `~/.claude.json`:

```json
{
  "mcpServers": {
    "openalex": {
      "type": "stdio",
      "command": "python",
      "args": ["/absolute/path/to/openalex-mcp/openalex_server.py"],
      "env": { "OPENALEX_MAILTO": "you@example.com" }
    }
  }
}
```

### Claude Desktop

Add the same entry to your `claude_desktop_config.json`:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "openalex": {
      "command": "python",
      "args": ["/absolute/path/to/openalex-mcp/openalex_server.py"],
      "env": { "OPENALEX_MAILTO": "you@example.com" }
    }
  }
}
```

Restart Claude Desktop. The OpenAlex tools will appear in the tools menu.

## Example

> **You:** What are the most-cited papers on graph neural networks?
>
> **Claude** *(calls `search_works` with `sort_by_citations=true`)* returns
> titles, authors, venues, citation counts, and open-access PDF links.

## How it works

Each tool maps to an OpenAlex REST endpoint (`/works`, `/authors`) and trims the
response down to the fields worth reading (title, authors, venue, year, citation
count, DOI, and open-access PDF URL). `get_work` additionally reconstructs the
abstract from OpenAlex's inverted index.

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgements

Data from [OpenAlex](https://openalex.org), an open and free catalog of the
global research system by [OurResearch](https://ourresearch.org).
