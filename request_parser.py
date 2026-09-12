import requests
import json


def parse_request(user_request):

    prompt = f"""
You are the planning component of a YouTube Shorts search agent.

The user will describe the kind of YouTube Shorts they want.

USER REQUEST:
{user_request}

Convert the request into a structured search plan.

Identify:

1. search_query
   - A concise YouTube search query.
   - Include the important topic, people, characters, games, shows,
     activities, or other subjects explicitly requested by the user.
   - Do NOT add qualities or styles that the user did not request.

2. topic
   - The main topic explicitly requested by the user.

3. subjects
   - Important people, characters, objects, or specific subjects
     explicitly requested by the user.
   - Use [] if none were specified.

4. style
   - Only include styles explicitly requested by the user.
   - Examples: funny, educational, scary, emotional, highlights.
   - Use [] if no style was requested.
   - NEVER assume a style from the topic.

Return ONLY valid JSON.

Use exactly this format:

{{
    "search_query": "...",
    "topic": "...",
    "subjects": [],
    "style": []
}}

Do not include explanations.
Do not include markdown.
Return JSON only.
"""

    try:

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "gemma3:12b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0,
                    "num_predict": 200
                }
            },
            timeout=180
        )

        response.raise_for_status()

    except requests.RequestException as e:

        print("Could not connect to Ollama.")
        print("Error:", e)

        return None


    raw_answer = response.json().get(
        "response",
        ""
    ).strip()


    print()
    print("Gemma request analysis:")
    print(raw_answer)
    print()


    # -----------------------------
    # REMOVE MARKDOWN CODE FENCES
    # -----------------------------

    if raw_answer.startswith("```"):

        lines = raw_answer.splitlines()

        # Remove opening ``` or ```json
        if lines:
            lines = lines[1:]

        # Remove closing ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        raw_answer = "\n".join(lines).strip()


    # -----------------------------
    # PARSE JSON
    # -----------------------------

    try:

        plan = json.loads(raw_answer)

    except json.JSONDecodeError:

        print("Gemma did not return valid JSON.")
        print(
            "Cleaned response:",
            repr(raw_answer)
        )

        return None


    return plan