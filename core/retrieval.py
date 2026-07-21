import math
from datetime import datetime,timezone
from core.storage import metadata_store,vector_store

SIMILARITY_WEIGHT=0.5
RECENCY_WEIGHT=0.2
IMPORTANCE_WEIGHT=0.3

RECENCY_HALF_LIFE_DAYS=7
CANDIDATE_POOL_SIZE=10
TOP_N_RESULTS=4

def _recency_score(last_accessed_iso:str)->float:
    last=datetime.fromisoformat(last_accessed_iso)
    if last.tzinfo is None:
        last=last.replace(tzinfo=timezone.utc)
    age_days=(datetime.now(timezone.utc)-last).total_seconds()/86400
    return math.exp(-age_days/RECENCY_HALF_LIFE_DAYS)

def retrieve_relevant_memories(query:str,user_id:str,top_n:int = TOP_N_RESULTS)-> list[dict]:
    hits=vector_store.query_similar(query,user_id=user_id,k=CANDIDATE_POOL_SIZE)

    scored=[]
    for hit in hits:
        row=metadata_store.get_memory(hit['id'])
        if row is None or row['status'] != "active":
            continue

        similarity=1/(1+hit['distance'])
        recency=_recency_score(row['last_accessed'])
        importance_norm=row['importance']/10

        combined_score=(
            SIMILARITY_WEIGHT*similarity
            +RECENCY_WEIGHT*recency
            +IMPORTANCE_WEIGHT*importance_norm
        )
        scored.append(
            {
                "id":hit['id'],
                "content":hit['content'],
                "type":row['type'],
                "importance":row['importance'],
                "score":combined_score,
            }
        )

    scored.sort(key=lambda x:x['score'],reverse=True)
    top=scored[:top_n]

    for item in top:
        metadata_store.touch_memory(item['id'])

    return top

def format_memories(memories: list[dict])->str:
    if not memories:
        return ""
    
    return "\n".join(f"- ({m['type']}) {m['content']}" for m in memories)
    
