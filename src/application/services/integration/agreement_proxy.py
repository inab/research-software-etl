from src.application.services.integration.disambiguation import load_solved_conflict_keys, parse_result, query_openrouter, query_huggingface_new

# function that given a message, returns the agreemnt of the models 
def decision_agreement_proxy(messages: str) -> str:
    """
    This function takes a message as input and returns the agreement of the models.
    It uses the `decision_agreement` function from the `decision_agreement` module.
    """
    # model 1: Llama 4 Scout
    model = "meta-llama/Llama-4-Scout-17B-16E-Instruct"
    provider = "together"
    result_llama_4, meta_llama_4 = query_huggingface_new(messages, model=model, provider=provider)
    try:
        result_llama_4 = parse_result(result_llama_4)
    except Exception as e:
        result_llama_4 = {}

    # model 2: Mixtral 8x7B
    model = "mistralai/mixtral-8x7b-instruct"
    result_mixtral, meta_mixtral = query_openrouter(messages, model=model)
    try:
        result_mixtral = parse_result(result_mixtral)
    except Exception as e:
        result_mixtral = {}
    
    # agreement
    result_llama_4_verdict = result_llama_4.get("verdict", None)
    result_mixtral_verdict = result_mixtral.get("verdict", None)
    # if both models agree, return the result
    if result_llama_4_verdict == result_mixtral_verdict:
        return result_llama_4
    
    else:
        return {
            "verdict": "disagreement",
            "llama_4": result_llama_4,
            "mixtral": result_mixtral,
        }

# function that prepares a github issue with the metadata of entries