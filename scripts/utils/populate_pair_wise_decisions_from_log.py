"Puts human decisions in pair_decisions.jsonl"

# Open human logs 

# For line in human logs
#   - create record
#   - open pair_decisions file
#   - add line

import json

HUMAN_LOG_PATH = "/Users/evabsc/projects/software-observatory/research-software-etl/human_annotations/human_conflicts_log.jsonl"
PAIR_WISE_PATH = "/Users/evabsc/projects/software-observatory/research-software-etl/src/application/services/integration/disambiguation/pair_decisions.jsonl"


def same(label):
    return label=='same'

def populate_pair_decisions():
    total = 0
    error = 0

    with open(HUMAN_LOG_PATH, "r", encoding="utf-8") as fin, \
         open(PAIR_WISE_PATH, "a", encoding="utf-8") as fout:

        for lineno, line in enumerate(fin, start=1):
            line = line.strip()
            if not line:
                continue

            # ------- loading original entry --------

            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"[human] Invalid JSON on line {lineno}: {e}") from e

            # -------- creating new entry ----------
            
            try:
                payload = {
                    "pair_id": obj['pair_id'],
                    "kind": obj['kind'],
                    "same_as_remainging": same(obj["decision"]),
                    "confidence": obj["confidence"],
                    "source": obj["source"],
                    "ts": obj["ts"]
                }
            except:
                error +=1
            else:
                json.dump(payload, fout, ensure_ascii=False, default=str)
                fout.write("\n")
                total += 1

    print(f"Done. Wrote {total} entries to {PAIR_WISE_PATH}. Missing information for {error} entries (skipped).")

# ---------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------

if __name__ == "__main__":
    populate_pair_decisions()
