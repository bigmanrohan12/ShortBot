import subprocess
import json
import requests
import tempfile
import os
import time

from request_parser import parse_request


# ============================================================
# SETTINGS
# ============================================================

# Maximum number of searches if we need more results.
MAX_SEARCHES = 3

# No artificial delay between searches.
WAIT_BETWEEN_SEARCHES = 0

# How long to wait after YouTube search results load.
YOUTUBE_WAIT = 1000

WEBCMD_SESSION = "short-bot-nf"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:12b"


# ============================================================
# FIND SHORTS
# ============================================================

def find_shorts(user_request, quantity):

    # --------------------------------------------------------
    # VALIDATE INPUT
    # --------------------------------------------------------

    if not isinstance(user_request, str) or not user_request.strip():
        raise ValueError("user_request must be a non-empty string.")

    if not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("quantity must be an integer greater than 0.")

    user_request = user_request.strip()


    # ========================================================
    # UNDERSTAND USER REQUEST
    # ========================================================

    print()
    print("Understanding your request...")
    print()

    plan = parse_request(user_request)

    if not plan:
        print("Could not understand the request.")
        return []

    base_search_query = plan.get(
        "search_query",
        ""
    ).strip()

    if not base_search_query:
        print("Gemma did not generate a search query.")
        return []

    print("Search query:", base_search_query)
    print()


    # ========================================================
    # SEARCH QUERY VARIATIONS
    # ========================================================

    # We start with the plain search.
    # Extra searches are only used if we still need results.

    search_queries = [
        base_search_query,
        base_search_query + " funny moments",
        base_search_query + " clips",
    ]


    # ========================================================
    # STORAGE
    # ========================================================

    # All Shorts we've ever seen.
    seen_urls = set()

    # Shorts that Gemma classified as relevant.
    relevant_shorts = []


    # ========================================================
    # SEARCH LOOP
    # ========================================================

    for search_number in range(1, MAX_SEARCHES + 1):

        # ----------------------------------------------------
        # STOP AS SOON AS WE HAVE ENOUGH
        # ----------------------------------------------------

        if len(relevant_shorts) >= quantity:
            break


        # ----------------------------------------------------
        # SELECT SEARCH QUERY
        # ----------------------------------------------------

        query_index = search_number - 1

        if query_index < len(search_queries):

            search_query = search_queries[query_index]

        else:

            search_query = (
                base_search_query
                + f" {search_number}"
            )


        print()
        print("=" * 60)
        print(
            f"SEARCH {search_number}/{MAX_SEARCHES}"
        )
        print("=" * 60)
        print()

        print("Query:", search_query)
        print()


        # ====================================================
        # CREATE DYNAMIC BROWSER SCRIPT
        # ====================================================

        js_query = json.dumps(search_query)

        browser_script = f"""
await page.goto('https://www.youtube.com');

const searchBox = page.getByRole('combobox');

await searchBox.fill({js_query});

const searchButton = page.getByRole('button', {{
    name: 'Search',
    description: 'Search'
}});

await searchButton.click();

await page.waitForTimeout({YOUTUBE_WAIT});

const shortsLinks = await page.locator('a[href*="/shorts/"]').all();

const results = [];
const seen = new Set();

for (const link of shortsLinks) {{

    const url = await link.getAttribute('href');
    const title = await link.getAttribute('title');

    if (!url || url === '/shorts/' || !title) {{
        continue;
    }}

    if (seen.has(url)) {{
        continue;
    }}

    seen.add(url);

    results.push({{
        title: title,
        url: 'https://www.youtube.com' + url
    }});
}}

return results;
"""


        # ====================================================
        # SAVE TEMPORARY BROWSER SCRIPT
        # ====================================================

        browser_file = None

        try:

            temp_file = tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".js",
                delete=False,
                encoding="utf-8"
            )

            temp_file.write(browser_script)
            temp_file.close()

            browser_file = temp_file.name


            # =================================================
            # RUN WEBCMD
            # =================================================

            print("Searching YouTube...")
            print()

            command = [
                "webcmd.cmd",
                "--session",
                WEBCMD_SESSION,
                "browser",
                "run",
                "--file",
                browser_file
            ]

            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )


        finally:

            if browser_file and os.path.exists(browser_file):
                os.remove(browser_file)


        # ====================================================
        # CHECK WEBCMD
        # ====================================================

        if process.returncode != 0:

            print("Webcmd error:")
            print(process.stderr)
            continue


        # ====================================================
        # PARSE WEBCMD OUTPUT
        # ====================================================

        output = process.stdout.strip()

        try:

            data = json.loads(output)

        except json.JSONDecodeError as e:

            print(
                "Could not parse Webcmd output as JSON."
            )

            print("Error:", e)
            print()
            print("Raw output:")
            print(output)

            continue


        shorts = data.get(
            "result",
            []
        )

        if not isinstance(shorts, list):
            shorts = []


        print(
            "Found",
            len(shorts),
            "Shorts."
        )

        print()


        # ====================================================
        # REMOVE DUPLICATES
        # ====================================================

        new_shorts = []

        for short in shorts:

            if not isinstance(short, dict):
                continue

            url = short.get("url")

            if not url:
                continue

            if url in seen_urls:
                continue

            seen_urls.add(url)

            new_shorts.append(short)


        print(
            "New Shorts:",
            len(new_shorts)
        )

        print()


        # If YouTube returned nothing new,
        # continue to next query.
        if not new_shorts:

            print(
                "No new Shorts from this search."
            )

            continue


        # ====================================================
        # SHOW NEW SHORTS
        # ====================================================

        for i, short in enumerate(
            new_shorts,
            start=1
        ):

            print(
                f"{i}. {short.get('title', 'Untitled')}"
            )

        print()


        # ====================================================
        # BATCH GEMMA CLASSIFIER
        # ====================================================

        print(
            "Sending new Shorts to Gemma..."
        )

        print()


        numbered_titles = []

        for i, short in enumerate(
            new_shorts,
            start=1
        ):

            title = short.get(
                "title",
                ""
            )

            numbered_titles.append(
                f"{i}. {title}"
            )


        titles_text = "\n".join(
            numbered_titles
        )


        classifier_prompt = f"""
You are a strict relevance classifier.

USER REQUEST:
{user_request}

SEARCH PLAN:
Topic: {plan.get("topic", "")}
Subjects: {plan.get("subjects", [])}
Style: {plan.get("style", [])}

YouTube Shorts found:

{titles_text}

Determine which Shorts are relevant to the user's request.

Important rules:

- For broad requests, accept Shorts clearly belonging to
  the requested topic.
- If the user specifies particular people, characters,
  subjects, or styles, those requirements matter.
- Do not invent requirements that the user did not ask for.
- Do not reject a Short simply because its title uses
  different wording.
- Do not assume an unrelated subject is relevant.

Return ONLY valid JSON.

Use exactly:

{{
    "relevant": [1, 2, 5]
}}

The numbers must correspond to the Shorts above.

If none are relevant:

{{
    "relevant": []
}}

Do not include explanations.
Do not include markdown.
Return JSON only.
"""


        # ====================================================
        # SEND TO OLLAMA
        # ====================================================

        try:

            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": classifier_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0,
                        "num_predict": 100
                    }
                },
                timeout=180
            )

            response.raise_for_status()

        except requests.RequestException as e:

            print(
                "Could not connect to Ollama."
            )

            print("Error:", e)

            continue


        # ====================================================
        # PARSE GEMMA RESPONSE
        # ====================================================

        try:

            raw_answer = response.json().get(
                "response",
                ""
            ).strip()

        except (ValueError, AttributeError):

            print(
                "Ollama returned an invalid response."
            )

            continue


        print("Gemma response:")
        print(raw_answer)
        print()


        # ====================================================
        # REMOVE MARKDOWN FENCES
        # ====================================================

        if raw_answer.startswith("```"):

            lines = raw_answer.splitlines()

            if lines:
                lines = lines[1:]

            if (
                lines
                and lines[-1].strip() == "```"
            ):

                lines = lines[:-1]

            raw_answer = "\n".join(
                lines
            ).strip()


        # ====================================================
        # PARSE JSON
        # ====================================================

        try:

            classifier_result = json.loads(
                raw_answer
            )

        except json.JSONDecodeError:

            print(
                "Gemma did not return valid JSON."
            )

            print(
                "Cleaned response:",
                repr(raw_answer)
            )

            continue


        relevant_numbers = classifier_result.get(
            "relevant",
            []
        )

        if not isinstance(relevant_numbers, list):
            relevant_numbers = []


        # ====================================================
        # ADD RELEVANT SHORTS
        # ====================================================

        added_this_search = 0

        existing_urls = {
            item.get("url")
            for item in relevant_shorts
        }


        for number in relevant_numbers:

            if not isinstance(number, int):
                continue

            if number < 1 or number > len(new_shorts):
                continue


            short = new_shorts[number - 1]

            url = short.get("url")

            if not url:
                continue


            if url in existing_urls:
                continue


            relevant_shorts.append(
                short
            )

            existing_urls.add(url)

            added_this_search += 1


            # Stop adding once we have enough.
            if len(relevant_shorts) >= quantity:
                break


        print(
            "Relevant added:",
            added_this_search
        )

        print(
            "Total relevant:",
            len(relevant_shorts),
            "/",
            quantity
        )

        print()


        # ====================================================
        # CHECK WHETHER WE ARE DONE
        # ====================================================

        if len(relevant_shorts) >= quantity:

            print(
                "Required number of Shorts reached!"
            )

            break


        # ====================================================
        # PREPARE FOR NEXT SEARCH
        # ====================================================

        remaining = quantity - len(
            relevant_shorts
        )

        print(
            "Still need",
            remaining,
            "more relevant Shorts."
        )


        if search_number < MAX_SEARCHES:

            print(
                "Searching again..."
            )

            if WAIT_BETWEEN_SEARCHES > 0:

                time.sleep(
                    WAIT_BETWEEN_SEARCHES
                )


    # ========================================================
    # FINAL RESULTS
    # ========================================================

    final_results = relevant_shorts[:quantity]


    print()
    print("=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print()


    if not final_results:

        print(
            "No relevant Shorts were found."
        )

    else:

        for i, short in enumerate(
            final_results,
            start=1
        ):

            print(
                f"{i}. {short.get('title', 'Untitled')}"
            )

            print(
                f"   {short.get('url', '')}"
            )

            print()


    print(
        "Total relevant:",
        len(final_results)
    )

    print(
        "Requested:",
        quantity
    )


    # ========================================================
    # INCOMPLETE SEARCH WARNING
    # ========================================================

    if len(final_results) < quantity:

        print()
        print(
            "Could not find enough relevant Shorts "
            "within the search limit."
        )


    # ========================================================
    # RETURN RESULTS TO CALLER
    # ========================================================

    return final_results


# ============================================================
# COMMAND-LINE TEST
# ============================================================

if __name__ == "__main__":

    user_request = input(
        "What Shorts are you looking for?\n> "
    )


    while True:

        try:

            quantity = int(
                input(
                    "How many Shorts do you want?\n> "
                )
            )

            if quantity > 0:
                break

            print(
                "Please enter a number greater than 0."
            )

        except ValueError:

            print(
                "Please enter a valid number."
            )


    results = find_shorts(
        user_request,
        quantity
    )