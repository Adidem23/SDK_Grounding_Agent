import asyncio
from typing import List, Optional, Any

from opik.evaluation.metrics.llm_judges.answer_relevance.metric import AnswerRelevance
from opik.evaluation.metrics.score_result import ScoreResult


def main():
    """
    Demonstrates how to use the AnswerRelevance metric with Opik.
    """

    # Initialize the AnswerRelevance metric
    answer_relevance_metric = AnswerRelevance()

    # Define example input, output, and context
    input_text = "What is the capital of France?"

    output_text_relevant = "Paris is the capital and most populous city of France."
    output_text_irrelevant = "The Eiffel Tower is a famous landmark in France."

    context = [
        "France is a country located in Western Europe.",
        "Paris is known for its art, fashion, gastronomy, and culture.",
    ]

    print("--- Evaluating Answer Relevance (synchronous) ---")

    # Example 1: Relevant answer with context
    print("\nEvaluating a relevant answer with context:")

    score_result_relevant = answer_relevance_metric.score(
        input=input_text,
        output=output_text_relevant,
        context=context,
    )

    print(f"Input: {input_text}")
    print(f"Output: {output_text_relevant}")
    print(f"Context: {context}")
    print(f"Score: {score_result_relevant.score}")
    print(f"Reason: {score_result_relevant.reason}")

    # Example 2: Irrelevant answer with context
    print("\nEvaluating an irrelevant answer with context:")

    score_result_irrelevant = answer_relevance_metric.score(
        input=input_text,
        output=output_text_irrelevant,
        context=context,
    )

    print(f"Input: {input_text}")
    print(f"Output: {output_text_irrelevant}")
    print(f"Context: {context}")
    print(f"Score: {score_result_irrelevant.score}")
    print(f"Reason: {score_result_irrelevant.reason}")

    # Example 3: Relevant answer without context
    print("\nEvaluating a relevant answer without context:")

    score_result_no_context = answer_relevance_metric.score(
        input=input_text,
        output=output_text_relevant,
        context=None,  # context can be omitted as well
    )

    print(f"Input: {input_text}")
    print(f"Output: {output_text_relevant}")
    print("Context: None")
    print(f"Score: {score_result_no_context.score}")
    print(f"Reason: {score_result_no_context.reason}")


async def async_main():
    """
    Demonstrates how to use the asynchronous AnswerRelevance metric with Opik.
    """

    # Initialize the AnswerRelevance metric
    answer_relevance_metric = AnswerRelevance()

    # Define example input, output, and context
    input_text = "Who wrote 'Romeo and Juliet'?"

    output_text_relevant = (
        "William Shakespeare wrote the tragic play 'Romeo and Juliet'."
    )

    output_text_irrelevant = "The Globe Theatre was a famous venue for plays."

    context = [
        "William Shakespeare was an English playwright, poet, and actor.",
        "His plays are among the most famous in the English language.",
    ]

    print("\n--- Evaluating Answer Relevance (asynchronous) ---")

    # Example 1: Relevant answer with context
    print("\nEvaluating a relevant answer with context (async):")

    score_result_async_relevant = await answer_relevance_metric.ascore(
        input=input_text,
        output=output_text_relevant,
        context=context,
    )

    print(f"Input: {input_text}")
    print(f"Output: {output_text_relevant}")
    print(f"Context: {context}")
    print(f"Score: {score_result_async_relevant.score}")
    print(f"Reason: {score_result_async_relevant.reason}")

    # Example 2: Irrelevant answer without context
    print("\nEvaluating an irrelevant answer without context (async):")

    score_result_async_no_context = await answer_relevance_metric.ascore(
        input=input_text,
        output=output_text_irrelevant,
    )

    print(f"Input: {input_text}")
    print(f"Output: {output_text_irrelevant}")
    print("Context: None")
    print(f"Score: {score_result_async_no_context.score}")
    print(f"Reason: {score_result_async_no_context.reason}")


if __name__ == "__main__":
    main()

    # Run the asynchronous example
    asyncio.run(async_main())