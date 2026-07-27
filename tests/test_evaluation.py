import sys
from pathlib import Path

# Allow running this script from the tests/ directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import HumanMessage, SystemMessage
from core.graph import build_graph, SYSTEM_PROMPT
from core.storage import metadata_store

SCENERIOS= [
    {
        "name":"explicit_preference_recall",
        "user_id":"eval_explicit_pref",
        "seed_turns":[
            "I prefer writing my scripts in python rather than Javascript."
        ],
        "query":"Can you help me write a quick script to parse a CSV file?",
        "expect_keywords":['python'],
        "forbidden_keywords":[],
    },
    {
        "name":"implicit_pattern_recall",
        "user_id":"eval_implicit_pattern",
        "seed_turns":[
            "How don i reverse a string in java?",
            "What's the best way to handle exceptions in java?",
            "how do i read a file line by line in java?"
        ],
        "query":"write me a  function to check whether the number is prime",
        "expect_keywords":['java'],
        "forbidden_keywords":[],
    },
    {
        "name":"contradiction_resolution",
        "user_id":"eval_contradiction",
        "seed_turns":[
            "I prefer coding in python",
            "Actually,I've completely switched to Go and do not use python."
        ],
        "query":"Write me a hello world program",
        "expect_keywords":['go'],
        "forbidden_keywords":['python'],
    },
    {
        "name":"retrieval_precision_no_false_recall",
        "user_id":"eval_precision",
        "seed_turns":["I am  a vegetarian and do not eat meat."],
        "query":"What's a good way to structure a rest api?",
        "expect_keywords":[],
        "forbidden_keywords":['vegetarian','meat'],
    },
]

def run_scenario(scenario:dict)->dict:
    user_id=scenario['user_id']

    seed_app=build_graph()
    history=[SystemMessage(content=SYSTEM_PROMPT)]
    for seed_msg in scenario['seed_turns']:
        history.append(HumanMessage(content=seed_msg))
        result=seed_app.invoke({"messages":history,"user_id":user_id})
        history.append(result['messages'][-1])

    eval_app=build_graph()
    eval_history=[SystemMessage(content=SYSTEM_PROMPT),HumanMessage(content=scenario['query'])]
    eval_result = eval_app.invoke({"messages": eval_history, "user_id": user_id})

    response_text = eval_result['messages'][-1].content.lower()
    retrieved=(eval_result.get("retrieved_context")or "").lower()


    expected = scenario['expect_keywords']
    forbidden=scenario['forbidden_keywords']

    keyword_hit=any(k.lower() in response_text for k in expected) if expected else None
    forbidden_hit=any(k.lower() in response_text for k in forbidden) if forbidden else None

    if expected:
        passed= bool(keyword_hit) and not forbidden_hit
    else:
        passed= not forbidden_hit

    return {
        "name":scenario['name'],
        "passed":passed,
        "keyword_hit":keyword_hit,
        "forbidden_hit":forbidden_hit,
        "retrieved":retrieved,
        "response_snippet": eval_result['messages'][-1].content[:150],
    }

def main():
    metadata_store.init_db()

    print("Running evaluation suite - this makes real llm calls,may take a minute. \n")

    results=[]
    for scenario in SCENERIOS:
        print(f"---{scenario['name']}---")
        result=run_scenario(scenario)
        results.append(result)

        status="PASS" if result['passed'] else "FAIL"
        print(f"    [{status}]")
        print(f"   retrived:{result['retrieved'] or '(nothing)'}")
        print(f"   response snippet:{result['response_snippet']!r}")
        print()

    passed_count=sum(1 for r in results if r['passed'])
    total=len(results)
    print(f"Score: {passed_count}/{total} scenarios passed ({passed_count/total *100:.0f}%)")


    if passed_count < total:
        print("\nFailed scenarios - check whether this is a threshold/prompt")
        print("tuning issue (e.g. CONFIDENCE_THRESHOLD, CONTRADICTION_DISTANCE_THRESHOLD)")
        print("or an actual bug,before assumning the system is broken.")


if __name__=="__main__":
    main()

    

