# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.

---

## Tool Inventory

### Tool 1: `search_listings(description, size, max_price)`

| | |
|---|---|
| **Purpose** | Searches the mock listings dataset for items matching a text description, with optional size and price filters. Returns results sorted by keyword relevance. |
| **Inputs** | `description` (str): keywords describing the item; `size` (str or None) is the size string to filter by, case-insensitive substring match; `max_price` (float or None) is the maximum price inclusive |
| **Output** | `list[dict]`:  matching listing dicts sorted best-match first; empty list if nothing matches. Each dict contains: `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand`, `platform` |

### Tool 2: `suggest_outfit(new_item, wardrobe)`

| | |
|---|---|
| **Purpose** | Uses an LLM to suggest 1–2 complete outfits pairing the thrifted item with pieces from the user's wardrobe. Falls back to general styling advice if the wardrobe is empty. |
| **Inputs** | `new_item` (dict): a listing dict for the item being considered; `wardrobe` (dict): a wardrobe dict with an `items` key containing a list of wardrobe item dicts |
| **Output** | `str`: non-empty outfit suggestion from the LLM (either specific outfit combos referencing named wardrobe pieces, or general styling advice) |

### Tool 3: `create_fit_card(outfit, new_item)`

| | |
|---|---|
| **Purpose** | Uses an LLM to write a 2–4 sentence Instagram/TikTok caption for the thrifted find. Casual and authentic tone, mentions item name, price, and platform once each. |
| **Inputs** | `outfit` (str): the outfit suggestion string from `suggest_outfit`; `new_item` (dict): the listing dict for the thrifted item |
| **Output** | `str`: a caption string, or an error message string if `outfit` is empty/whitespace (does not raise) |

---

## Planning Loop

`run_agent(query, wardrobe)` in `agent.py` executes a fixed linear sequence with one early-exit branch. There is no dynamic tool selection.

1. **Initialize**: `_new_session(query, wardrobe)` creates a session dict with all output fields set to `None` or `[]`.

2. **Parse the query**: regex extracts three values from the raw query string:
   - `description`: the query with `size <token>`, `$<amount>`, and `under` stripped out (e.g. `"vintage graphic tee under $30"` → `"vintage graphic tee"`)
   - `size`: first match of `size \S+`, case-insensitive; `None` if not found
   - `max_price`: first `$<number>` found, cast to float; `None` if not found

   All three are stored in `session["parsed"]`.

3. **Search and branch**: `search_listings` is called with the parsed values. If it returns an empty list, `session["error"]` is set to a helpful retry message and `run_agent` returns immediately , `suggest_outfit` and `create_fit_card` are never called. If results exist, `session["selected_item"]` is set to `results[0]` (highest relevance) and execution continues.

4. **Suggest outfit**: `suggest_outfit(session["selected_item"], session["wardrobe"])` is called unconditionally at this point. The result is stored in `session["outfit_suggestion"]`. No branch here , the tool handles empty wardrobes internally.

5. **Generate fit card**: `create_fit_card(session["outfit_suggestion"], session["selected_item"])` is called. The result is stored in `session["fit_card"]`. No branch here, the tool handles empty outfit strings internally.

6. **Return session**: the completed session dict is returned. The caller (`app.py`) checks `session["error"]` first.

---

## State Management

All state lives in a single `session` dict for the duration of one `run_agent()` call. No tool communicates with another directly,  each writes its output into `session`, and the next step reads from `session`.

| Field | Written by | Read by |
|---|---|---|
| `session["parsed"]` | regex parser  | `search_listings()` call |
| `session["search_results"]` | `search_listings()` | empty-check branch |
| `session["selected_item"]` | planning loop `results[0]` | `suggest_outfit()`, `create_fit_card()` |
| `session["wardrobe"]` | `_new_session()` (from caller) | `suggest_outfit()` |
| `session["outfit_suggestion"]` | `suggest_outfit()` | `create_fit_card()` |
| `session["fit_card"]` | `create_fit_card()` | `app.py` |
| `session["error"]` | planning loop on empty results | `app.py` |

The session dict is the return value of `run_agent()`. State was verified to flow correctly: `session["selected_item"] is session["search_results"][0]` evaluates to `True` (same object, not a copy), and the fit card produced during testing referenced the exact price and platform from `session["selected_item"]` without any re-fetching.

---

## Error Handling

| Tool | Failure mode | Handling | Concrete example |
|---|---|---|---|
| `search_listings` | No listings match the query | Returns `[]`; planning loop sets `session["error"]` and returns early before calling any LLM tools | Query `"designer ballgown size XXS under $5"` -> `[]` -> error: `"No listings matched your search. Try broader keywords, remove the size filter, or raise your price limit."` |
| `suggest_outfit` | `wardrobe["items"]` is empty | Sends a different prompt asking for general styling advice instead of specific outfit combos; always returns a non-empty string | Query with `get_empty_wardrobe()` -> LLM returned general advice about silhouettes and color pairings for the item, no crash |
| `create_fit_card` | `outfit` is `""` or whitespace-only | Guard at top of function returns an error message string immediately, never calls the LLM | `create_fit_card("", item)` -> `"Could not generate a fit card: outfit suggestion is missing or empty."` |

---

## Spec Reflection

**One way the spec helped:** Establishing the planning loop, state management table, tools, and architecture prior to writing any code was helpful in understanding the big picture of the system. It helped me better understand how the agent was going to work. I think it also made the implementation step easier, because I had already described the entire structure of the project beforehand

**One way implementation diverged from the spec:** 


## AI Usage
**Instance 1:** I 
**Instance 2:**
