import os
import logging
from dotenv import load_dotenv
import anthropic

load_dotenv(".env.prod")

api_key = os.getenv("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=api_key)


def system_instructions(lang):
    return ("You are a helpful assistant analyzing literary text. Answer the user's question using ONLY "
            "the provided context. If the context does not contain enough information, state that you do not know.\n\n"
            f"Write your entire answer in {lang}. Keep direct quotes from the source text in "
            "original French, un-translated, each followed by (ch_id, par_id).\n\n"
            "Example: if the user asks in English, write your answer in English, but any quoted sentence "
            "stays in French, like: The narrator describes the garden's calm — « ... » (ch.1, par.246).\n\n"
            "Never ask the user for clarification about language — always answer directly, "
            "in one complete response, in the language you determine the question is written in.\n\n")


def prepare_prompt(user_query, retrieved_data):
    logging.debug(retrieved_data)
    formatted_docs = "\n\n".join(
        [f"<document index='{i+1}' ch='{obj['meta']['chapter_id']}' par_id='{obj['meta']['paragraph_id']}'>\n{obj['context']}\n</document>" for i,
            obj in enumerate(retrieved_data)]
    )
    prompt = f""" Here's the retrieved context to help answer the question:
    <documents>
    {formatted_docs}
    </documents>
    
    User Question: {user_query}"""
    return prompt


models = {
    'haiku': 'claude-haiku-4-5-20251001',  # costs less
    'sonnet': 'claude-sonnet-5'
}

def generate(prompt, lang):
    if not prompt:
        return ''

    try:
        with client.messages.stream(
                model=models['haiku'],
                max_tokens=1000,
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
        logging.error(f"Clause API error: {e}")
        yield "\n\n[Sorry, something went wrong generating this response. Please try again.]"
