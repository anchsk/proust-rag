import anthropic
import os
from dotenv import load_dotenv

load_dotenv(".env.prod")
api_key = os.getenv("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=api_key)

system_instructions = (
    "You are a helpful assistant analyzing literary text. Answer the user's question using ONLY "
    "the provided context. If the context does not contain enough information, state that you do not know.\n\n"
    "Rules for language and quotes:\n"
    "1. Respond in the primary language of the user's question.\n"
    "2. Keep all direct quotes from the source text in their original French without translating them.\n"
    "3. Provide the ch_id and par_id of the quote.\n"
)

#  "3. Provide your own explanations and summaries in the user's language."


def prepare_prompt(user_query, retrieved_data):
    # get the passages from retrieved data
    print(retrieved_data)
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
    'haiku': 'claude-haiku-4-5-20251001', # costs less
    'sonnet': 'claude-sonnet-5'
}


def send_prompt(prompt):

    if not prompt:
        return ''

    message = client.messages.create(
        model=models['haiku'],
        max_tokens=1000,
        system=system_instructions,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )
    return message.content


def generate(prompt):
    if not prompt:
            return ''

    with client.messages.stream(
            model=models['haiku'],
            max_tokens=1000,
            system=system_instructions,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],) as stream:
        for text in stream.text_stream:
            yield text
