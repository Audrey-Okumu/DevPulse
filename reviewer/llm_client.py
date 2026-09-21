from django.conf import settings
from google import genai


def get_ai_review(filename, patch):
    client = genai.Client(api_key=settings.LLM_API_KEY)

    prompt = f"""You are a senior Python code reviewer. Review the following diff from the file `{filename}`.

Focus on:
- Bugs or correctness issues
- Style issues (PEP 8, naming, readability)
- Risks (security, performance, edge cases)

Be concise. If there's nothing significant to flag, say so briefly rather than inventing issues.

Diff:
{patch}
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )

    return response.text