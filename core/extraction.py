import json
import re 
import sys
import uuid

from langchain_core.messages import HumanMessage,SystemMessage
from core.llm import extraction_llm
from core.storage import metadata_store,vector_store

EXTRACTION_SYSTEM_PROMPT="""You extract long-term memories from a single\
converstaion turn(one user message + one assitent reply).

Only extract things that are durable and worth remembering across future\
sessions - e.g. explicit preferences,stated facts about the user,\
corrections to prevoiously stated info, or notable events/plans they\
mentioned.Do NOT extract the assistant's answer itself,generic\
chit-chat,or anything trivial\obvoius.

Respond with only JSON Array-no markdown fences,no commentry. \
Each item must look like:
{"type":"preference" | "fact" | "event" | "correction",\
"content":"<one self-contained sentence, understanble without the \
original conversation>", "importance":<float 1-10>,\
"confidence":<float 0-1>}

If nothing is worth remembering ,respond with exactly []
"""

CONFIDENCE_THRESHOLD=0.5

def _strip_json_fences(text:str)->str:
    match=re.search(r"```(?:json)?\s*(.*?)\s*```",text,re.DOTALL)
    return match.group(1) if match else text.strip()


def extract_and_store(user_text:str,assitant_text:str,user_id:str)->list[dict]:
    turn_text=f"User said:{user_text}\n Assistant  said:{assitant_text}"

    try:
        result=extraction_llm.invoke(
            [SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),HumanMessage(content=turn_text)]
        )
        candidates=json.loads(_strip_json_fences(result.content))
    except json.JSONDecodeError as e:
        print(f"[extractor] could not parse extraction output: {e}",file=sys.stderr)
        candidates=[]

    accepted=[]
    for item in candidates:
        try:
            if item.get("confidence",0)<CONFIDENCE_THRESHOLD:
                continue
            memory_id=str(uuid.uuid4())
            metadata_store.insert_memory(
            memory_id=memory_id,
            user_id=user_id,
            type_=item["type"],
            content=item['content'],
            importance=float(item['importance']),
          )
            vector_store.add_memory(
            memory_id=memory_id,
            user_id=user_id,
            content=item['content'],
            type_=item['type'],
            )
            accepted.append(item)
        except (KeyError,TypeError,ValueError) as e:
            print(f"[extractor] skipped malformed candidate {item}:{e}",file=sys.stderr)

    return accepted

