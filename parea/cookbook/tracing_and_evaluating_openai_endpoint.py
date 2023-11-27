from typing import Dict, List

import json
import os
import time

import openai
from dotenv import load_dotenv

from parea import RedisCache, init
from parea.helpers import write_trace_logs_to_csv
from parea.utils.trace_utils import get_current_trace_id, trace

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")


use_cache = True
cache = RedisCache() if use_cache else None
init(api_key=os.getenv("PAREA_API_KEY"), cache=cache)


def call_llm(data: list[dict], model: str = "gpt-3.5-turbo", temperature: float = 0.0) -> str:
    return openai.ChatCompletion.create(model=model, temperature=temperature, messages=data).choices[0].message["content"]


def goal_success_ratio(inputs: Dict, output: str, target: str = None) -> float:
    """Returns the average amount of turns the user had to converse with the AI to reach their goals."""
    output = json.loads(output)
    # need to determine where does a new goal start
    conversation_segments = []
    start_index = 0
    end_index = 3
    while end_index < len(output):
        user_follows_same_goal = call_llm(
            [
                {
                    "role": "system",
                    "content": "Look at the conversation and to determine if the user is still following the same goal "
                    "or if they are following a new goal. If they are following the same goal, respond "
                    "SAME_GOAL. Otherwise, respond NEW_GOAL. In any case do not answer the user request!",
                }
            ]
            + output[start_index:end_index],
            model="gpt-4",
        )

        if user_follows_same_goal == "SAME_GOAL":
            end_index += 2
        else:
            conversation_segments.append(output[start_index : end_index - 1])
            start_index = end_index - 1
            end_index += 2

    if start_index < len(output):
        conversation_segments.append(output[start_index:])

    # for now assume that the user reached their goal in every segment
    # so we can return the average amount of turns the user had to converse with the AI to reach their goals
    return sum([2 / len(segment) for segment in conversation_segments]) / len(conversation_segments)


def friendliness(inputs: Dict, output: str, target: str = None) -> float:
    response = call_llm(
        [
            {"role": "system", "content": "You evaluate the friendliness of the following response on a scale of 0 to 10. You must only return a number."},
            {"role": "assistant", "content": output},
        ],
        model="gpt-4",
    )
    try:
        return float(response) / 10.0
    except TypeError:
        return 0.0


def usefulness(inputs: Dict, output: str, target: str = None) -> float:
    user_input = inputs["messages"][-1]["content"]
    response = call_llm(
        [
            {"role": "system", "content": "You evaluate the usefulness of the response given the user input on a scale of 0 to 10. You must only return a number."},
            {"role": "assistant", "content": f'''User input: "{user_input}"\nAssistant response: "{output}"'''},
        ],
        model="gpt-4",
    )
    try:
        return float(response) / 10.0
    except TypeError:
        return 0.0


@trace(eval_funcs=[friendliness, usefulness])
def helpful_the_second_time(messages: List[Dict[str, str]]) -> str:
    helpful_response = call_llm(
        [
            {"role": "system", "content": "You are a friendly, and helpful assistant that helps people with their homework."},
        ]
        + messages,
        model="gpt-4",
    )

    has_user_asked_before_raw = call_llm(
        [
            {
                "role": "system",
                "content": "Assess if the user has asked the last question before or is asking again for more \
information on a previous topic. If so, respond ASKED_BEFORE. Otherwise, respond NOT_ASKED_BEFORE.",
            }
        ]
        + messages,
        model="gpt-4",
    )
    has_user_asked_before = has_user_asked_before_raw == "ASKED_BEFORE"

    if has_user_asked_before:
        messages.append({"role": "assistant", "content": helpful_response})
        return helpful_response
    else:
        unhelfpul_response = call_llm(
            [
                {
                    "role": "system",
                    "content": "Given the helpful response to the user input below, please provide a slightly unhelpful \
    response which makes the user ask again in case they didn't ask already again because of a previous unhelpful answer. \
    In case the user asked again, please provide a last response",
                },
            ]
            + messages
            + [{"role": "assistant", "content": helpful_response}],
            model="gpt-4",
        )
        messages.append({"role": "assistant", "content": unhelfpul_response})
        return unhelfpul_response


@trace(eval_funcs=[goal_success_ratio], access_output_of_func=lambda x: x[0])
def unhelpful_chat():
    print("Welcome to the chat! Type 'exit' to end the session.")

    trace_id = get_current_trace_id()

    messages = []
    while True:
        user_input = input("\nYou: ")

        if user_input.lower() == "exit":
            print("Goodbye!")
            break

        messages.append({"role": "user", "content": user_input})
        print("Bot:", helpful_the_second_time(messages))

    return messages, trace_id


def main():
    _, trace_id = unhelpful_chat()

    if os.getenv("PAREA_API_KEY"):
        print(f"You can view the logs at: https://app.parea.ai/logs/detailed/{trace_id}")
    if use_cache:
        time.sleep(5)  # wait for local eval function to finish
        path_csv = f"trace_logs-{int(time.time())}.csv"
        trace_logs = cache.read_logs()
        write_trace_logs_to_csv(path_csv, trace_logs)
        print(f"CSV-file of results: {path_csv}")
        parent_trace = None
        for trace_log in trace_logs:
            if trace_log.trace_id == trace_id:
                parent_trace = trace_log
                break
        if parent_trace:
            print(f"Overall score(s):\n{json.dumps(parent_trace.scores)}")


if __name__ == "__main__":
    main()
