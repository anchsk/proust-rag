import os
import logging
from dotenv import load_dotenv
import anthropic

load_dotenv(".env.prod")

api_key = os.getenv("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=api_key)


def system_instructions(lang):
    return (
        "You are a knowledgeable reader of Proust's Du côté de chez Swann. "
        "Answer the user's question using only the passages provided in <passages>. "
        "Do not use outside knowledge of the novel.\n\n"

        f"Language: write your answer in {lang}. Answer directly and completely; "
        "never ask the user for clarification.\n\n"

        "Quotes: quote only text that appears verbatim in the passages, copied exactly, "
        "never from memory. Keep quotes in the original French; do not translate them. "
        "After a quote you may briefly explain, in your own words and in the answer's language, "
        "what it describes. Cite each quote as (ch.N, par.N).\n"
        "Example (English question): The narrator describes the garden's calm: « ... » (ch.1, par.246).\n\n"

        "If the passages only partly answer the question, answer what they support and say what "
        "is missing. If they don't address it, say the indexed text doesn't seem to address it; "
        "do not guess.\n\n"

        "Refer to \"the text\" or \"Proust\", never to \"the passages\", \"the context\" or \"the documents\"."
    )


def prepare_prompt(user_query, retrieved_data):
    logging.debug(retrieved_data)
    formatted_docs = "\n\n".join(
        [f"<excerpt index='{i+1}' ch='{obj['meta']['chapter_id']}' par_id='{obj['meta']['paragraph_id']}'>\n{obj['context']}\n</excerpt>" for i,
            obj in enumerate(retrieved_data)]
    )
    prompt = f"""
<passages>
{formatted_docs}
</passages>

User Question: {user_query}"""
    return prompt


models = {
    'haiku': 'claude-haiku-4-5-20251001',  # costs less
    'sonnet': 'claude-sonnet-5'
}


def generate(prompt, lang):
    try:
        with client.messages.stream(
                model=models['haiku'],
                max_tokens=2000,
                system=system_instructions(lang),
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],) as stream:
            for text in stream.text_stream:
                yield text
    except anthropic.APIError as e:
        logging.error(f"Claude API error: {e}")
        yield "\n\n[Sorry, something went wrong generating this response. Please try again.]"
