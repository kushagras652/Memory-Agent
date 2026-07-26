import json
import re 
import sys
import uuid

from langchain_core.messages import HumanMessage,SystemMessage
from core.llm import extraction_llm
from core.storage import metadata_store,vector_store
from core.pattern_detection import detect_and_store_patterns
from core.forgetting import resolve_contradictions

EXTRACTION_SYSTEM_PROMPT="""You analyze a single conversation turn (one\
user message + one assistant reply) and extract two things.

1."memories":durable facts/preferences/events worth remembering across\
future sessions - but ONLY things the user explicitly stated.Do NOT \
extract the assistant's answer itself,generic chit-chat, or anything \
inferred rather than stated.A technical question("how do i do X in JAVA")\
is NOT itself a stated preference - do not extract one from it.

2."topics":a short list of lowercase keywords for any specific \
programming language, framework, or technology this turn involved(e.g. \
["java"],["python","pandas"] - include this even when no preference \
was stated,since it's just a topic tag,not a memory claim.Empty list \
if no specific technology was involved.

Respond with ONLY a json object - no markdown fences,no commentary:
{"memories":[{"type":"preference"|"fact"|"event"|"correction", \
    "content":"<one self-contained sentence>","importance":<float 1-10>, \
        "confidence":<float 0-1>}],"topics":["..."]}

If nothing is worth remembering, "memories" should be an empty array.
"""

CONFIDENCE_THRESHOLD=0.5

def _strip_json_fences(text:str)->str:
    match=re.search(r"```(?:json)?\s*(.*?)\s*```",text,re.DOTALL)
    return match.group(1) if match else text.strip()


def extract_and_store(user_text:str,assistant_text:str,user_id:str)->list[dict]:
    turn_text=f"User said:{user_text}\n Assistant  said:{assistant_text}"

    memory_candidates=[]
    topics=[]


    try:
        result=extraction_llm.invoke(
            [SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),HumanMessage(content=turn_text)]
        )
        parsed=json.loads(_strip_json_fences(result.content))
        memory_candidates=parsed.get("memories",[])
        topics=parsed.get("topics",[])
    except json.JSONDecodeError as e:
        print(f"[extractor] could not parse extraction output {e }",file=sys.stderr)

    accepted=[]
    for item in memory_candidates:
        try:
            if item.get("confidence",0) < CONFIDENCE_THRESHOLD:
                continue
            memory_id=str(uuid.uuid4())
            metadata_store.insert_memory(
                memory_id=memory_id,
                user_id=user_id,
                type_=item["type"],
                content=item['content'],
                importance=float(item['importance']),
                source="explicit",
            )
            vector_store.add_memory(
                memory_id=memory_id,
                content=item['content'],
                user_id=user_id,
                type_=item['type'],
            )
            superseded_id=resolve_contradictions(
                user_id,memory_id,item['content'],item['type']
            )
            accepted.append({"type":item['type'],"content":item['content'],"source":"explicit","superseded":superseded_id})
        except (KeyError,TypeError,ValueError) as e:
            print(f"[extractor] skipped malformed candidates {item}:{e}",file=sys.stderr)

    metadata_store.log_topics(user_id,topics)
    inferred=detect_and_store_patterns(user_id)

    return accepted+inferred

            

