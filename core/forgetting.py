import math
import uuid
from collections import defaultdict
from datetime import datetime,timezone
from typing import Optional

from langchain_core.messages import HumanMessage,SystemMessage

from core.llm import extraction_llm
from core.storage import metadata_store,vector_store

DECAY_HALF_LIFE_DAYS=14
EXPIRE_IMPORTANCE_THRESHOLD=1.0

CONTRADICTION_DISTANCE_THRESHOLD=0.5

CONSOLIDATION_MIN_AGE_DAY=14
CONSOLIDATION_IMPORTANCE_THRESHOLD=3.0
CONSOLIDATION_MIN_GROUP_SIZE=3
CONSOLIDATED_IMPORTANCE=4.0

def _age_days(iso_timestamp:str)->float:
    ts=datetime.fromisoformat(iso_timestamp)
    if ts.tzinfo is None:
        ts=ts.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc)- ts).total_seconds()/86400

def decay_and_expire(user_id:str)->dict:
    decayed,expired=0,0
    now_iso=datetime.now(timezone.utc).isoformat()

    for row in metadata_store.list_memories(user_id,status="active"):
        elapsed_days= _age_days(row['last_decayed_at'])
        if elapsed_days <=0:
            continue

        factor=math.exp(-elapsed_days/DECAY_HALF_LIFE_DAYS)
        new_importance=row['importance']*factor
        metadata_store.update_importance(row['id'],new_importance,now_iso)
        decayed+=1

        if new_importance < EXPIRE_IMPORTANCE_THRESHOLD:
            metadata_store.set_status(row['id'],"expired")
            expired+=1

    return {'decayed':decayed,"expired":expired}

def _llm_says_contradicts(old_content:str,new_content:str)->bool:
    prompt=(
        f'OLD memory: "{old_content}"\n'
        f'NEW memory: "{new_content}"\n'
        "Does the new memory update,correct, or replace the OLD one"
        "(i.e. they're about the same specific thing, and the old one is "
        "now outdated) ? Answer with exactly one word:YES OR NO."
    )

    try:
        result=extraction_llm.invoke(
            [SystemMessage(content="Answer with exactly one word:yes or no"),
             HumanMessage(content=prompt)]
        )
        return result.content.strip().lower().startswith("y")
    except Exception:
        return False

def resolve_contradictions(user_id:str,new_memory_id:str,new_content:str,type_:str)->Optional[str]:
    hits=vector_store.query_similar(new_content,user_id=user_id,k=5)
    for hit in hits:
        if hit['id']== new_memory_id:
            continue
        if hit['distance']> CONTRADICTION_DISTANCE_THRESHOLD:
            continue

        row=metadata_store.get_memory(hit['id'])
        if row is None or row['status'] != "active" or row['type']!=type_:
            continue

        if _llm_says_contradicts(row['content'],new_content):
            metadata_store.set_status(row['id'],"superseded")
            return row['id']

        break

    return None

def consolidate_old_memories(user_id:str)->list[dict]:
    candidates=[
    row
    for row in  metadata_store.list_memories(user_id,status="active")
    if row['importance'] < CONSOLIDATION_IMPORTANCE_THRESHOLD 
    and _age_days(row['created_at']) >= CONSOLIDATION_MIN_AGE_DAY
    ]

    groups=defaultdict(list)
    for row in candidates:
        groups[row['type']].append(row)

    created=[]
    for type_,group in groups.items():
        if len(group) < CONSOLIDATION_MIN_GROUP_SIZE:
            continue

        bullet_list="\n".join(f"-{r['content']}" for r in group)
        prompt=(
            f"Combine these {len(group)} old,low-importance memories about"
            f"a user into ONE summary sentence that preserves the"
            f"useful information:\n{bullet_list}\n\n Respond with only the"
            "summary sentence,nothing else,"
        )

        try:
            result=extraction_llm.invoke(
                [SystemMessage(content="Respond with only the summary sentence."),
                 HumanMessage(content=prompt)]

            )
            summary=result.content.strip()
        except Exception:
            continue

        memory_id=str(uuid.uuid4())
        metadata_store.insert_memory(
            memory_id=memory_id,
            user_id=user_id,
            type_=type_,
            content=summary,
            importance=CONSOLIDATED_IMPORTANCE,
            source="consolidated",
        )
        vector_store.add_memory(
            memory_id=memory_id,content=summary,user_id=user_id,type_=type_
        )
        for row in group:
            metadata_store.set_status(row['id'],"superseded")

        created.append({"type":type_,"content":summary,"source":"consolidated"})

    return created

def prune_stale_tags(retention_days:int=14)->int:
    return metadata_store.delete_old_tags(retention_days)

def run_forgetting_job(user_id:str)->dict:
    decay_result=decay_and_expire(user_id)
    consolidated=consolidate_old_memories(user_id)
    pruned_tags=prune_stale_tags()
    return {
        "decayed":decay_result['decayed'],
        "expired":decay_result['expired'],
        "consolidated":consolidated,
        "pruned_tags":pruned_tags
}
