
import json
import logging 
from src.application.services.integration.disambiguation import build_full_conflict, write_to_results_file, build_chat_messages_with_disconnected, load_templates_from_folder, make_inference_and_wait, parse_result
PROMPT_TEMPLATES = load_templates_from_folder("src/application/services/integration/benchmarking")

# --------------------------------
# Preparing messages for inference
# --------------------------------

def build_prompt_benchmarking(disconnected, remaining):
    """
    Build the prompt for benchmarking. The prompt for the benchmarking is slightly different
    from the one used in the disambiguation process. The benchmarking prompt asks for more details
    about the disambiguation process, such as the key features behind the decision.
    """
    template = PROMPT_TEMPLATES["prompt_benchmarking"]

    instruction_prompt = template.render()

    data_dict = {
        "disconnected": disconnected,
        "remaining": remaining
    }

    messages = build_chat_messages_with_disconnected(instruction_prompt, data_dict)

    return messages

def prepare_messages_file(disconnected_entries, instances_dict, messages_file_path):
    '''
    For benchmarking of the disambiguation process.
    '''
    count = 0
    for key in disconnected_entries:
        count += 1
        logging.info(f"Building messsages for conflict {count} - {key}")
        try:
            full_conflict = build_full_conflict(disconnected_entries[key], instances_dict)
            messages = build_prompt_benchmarking(full_conflict["disconnected"], full_conflict["remaining"])
            logging.info(f"Number of messages: {len(messages)}")
            result = {
                "key": messages
            }
            write_to_results_file(result, messages_file_path)
            logging.info(f"Messages for conflict {key} written to file.")
        
        except Exception as e:
            logging.error(f"Error processing conflict {key}: {e}")

# ---------------------------------------------------------------
# MAKE INFERENCES: with a given model for a given set of messages 
# -------------------------------------------------------------
def parse_messages_file(messages_file_path):
    messages = {}
    with open(messages_file_path, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    entry = json.loads(line)
                    key = next(iter(entry))
                    message = entry[key]
                    messages[key] = message
                    
                except Exception as e:
                    logging.warning(f"Could not parse line: {line[:100]}...\n{e}")

    return messages


def make_inferences(messages,model, output_file_path):
    '''
    For benchmarking of the disambiguation process.
    This maybe can be moved to a use_case
    '''
    logging.info(f"Number of cases to process: {len(messages)}")

    for key in messages:
        logging.info(f"Making inference for conflict {key}")
        try:
            logging.info(f"Making inference for conflict {key}")
            result = make_inference_and_wait(messages[key], model)
            logging.info(f"Parsing result for conflict {key}")
            parsed_result  = parse_result(result)

            with open(output_file_path, 'a') as f:
                json.dump({key: parsed_result}, f)
                f.write('\n')

            logging.info(f"Results for conflict {key} written to file.")
            logging.info("----------------------------")
            
        
        except Exception as e:
            logging.error(f"Error processing conflict {key}: {e}")
    
    logging.info("All inferences completed.")
    



if __name__ == "__main__":
    disconnected_entries_file = 'data/disconnected_entries.json'
    messages_file = 'scripts/data/messages.json'
    grouped_entries_file = 'data/grouped.json'

    # ---------- SCRIPT 1 - MESSAGES PREP -----------------------
    # create instances dict from grouped entries 
    instances_dict = {}

    # Create messages for each inference
    prepare_messages_file(disconnected_entries_file, instances_dict, messages_file)



    # ---------- SCRIPT 2 - INFERENCE  ----------------------

    # 🤔 Measure time for each inference??
    # 🤔 Have different and parallel bash script for each model??

    # Make inferences for each message
    messages = parse_messages_file(messages_file)

    output_file_path_root = 'scripts/data/benchmarking_results.json'

    models = [

    ]

    results_paths = {}
    for model in models:
        output_file_path = f"{output_file_path_root}_{model}.json"
        results_paths[model] = output_file_path

    for model in models:
        logging.info(f"Making inferences with model {model}")
        make_inferences(messages, model, results_paths[model])
    
    # ---------- JUPYTER NOTEBOOK 1 - METRICS CALCULATION ----------------------

    # Compare with human results and compute metrics
    human_results = "scripts/data/human_results.json"
    for model in models:
        logging.info(f"Comparing results for model {model}")
        # Load the results
        with open(results_paths[model], 'r') as f:
            results = [json.loads(line) for line in f]
        
        # Load the human results
        with open(human_results, 'r') as f:
            human_results = [json.loads(line) for line in f]

        # Compare the results with human results
        # Compute metrics such as accuracy, precision, recall, F1-score, etc.
        # Put in dataframe
        # Plot the results
        
        pass

    # 4. Save results to file

