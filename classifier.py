import requests


def classify_short(user_request, title):
    prompt = f"""
You are a strict relevance classifier.

USER REQUEST:
{user_request}

SHORT TITLE:
{title}

Decide whether this YouTube Short is relevant to the user's request.

The Short should be YES only when the title clearly matches the
topic and subjects requested by the user.

Do not assume an unrelated subject is relevant.
Do not make guesses when there is no evidence in the title.

Examples:

User request:
Find funny Young Sheldon Shorts about Sheldon and Missy

Short title:
Sheldon and Missy have the funniest fight | Young Sheldon
Answer: YES

Short title:
Missy and Sheldon meet Mandy for the first time | Young Sheldon
Answer: YES

Short title:
How to Make Perfect Chocolate Cake
Answer: NO

Return ONLY:
YES
or
NO
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "gemma3:12b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": 10
            }
        },
        timeout=120
    )

    data = response.json()

    answer = data.get("response", "").strip().upper()

    print("AI ANSWER:", repr(answer))

    if "YES" in answer:
        return True
    elif "NO" in answer:
        return False

    return False


# Test
user_request = "Find funny Young Sheldon Shorts about Sheldon and Missy"

titles = [
    "Sheldon and Missy have the funniest fight 😂 | Young Sheldon",
    "Missy and Sheldon meet Mandy for the first time 😂 | Young Sheldon",
    "How to Make Perfect Chocolate Cake",
]

for title in titles:
    result = classify_short(user_request, title)

    print("TITLE:", title)
    print("MATCH:", result)
    print("-" * 50)