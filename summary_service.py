import os

import cohere

co = cohere.Client(os.environ["COHERE_API_KEY"])


def summarize(string):
    response = co.summarize(
        text=string
    )
    return response.summary
