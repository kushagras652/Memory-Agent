import uuid

from core.storage import metadata_store,vector_store

TOPIC_THRESHOLD=3
WINDOW_DAYS=7
INFERRED_IMPORTANCE=5.0

def _has_existing_preference(user_id:str,topic:str)->bool:
    for row in metadata_store.list_memories(user_id,status='active'):
        if row['type']=="preference" and topic in row['content'].lower():
            return True
    return False

def detect_and_store_patterns(user_id:str)->list[dict]:
    counts=metadata_store.get_recent_topic_count(user_id,window_days=WINDOW_DAYS)

    newly_created=[]

    for topic,count in counts.items():
        if count<TOPIC_THRESHOLD:
            continue
        if _has_existing_preference(user_id,topic):
            continue
        content=(
            f"Frequently asks about {topic} ({count} times in  the last"
            f"{WINDOW_DAYS} days) - likely prefers coding in {topic}"
        )

        memory_id=str(uuid.uuid4())
        metadata_store.insert_memory(
            memory_id=memory_id,
            user_id=user_id,
            type_="preference",
            content=content,
            importance=INFERRED_IMPORTANCE,
            source='inferred',
        )
        vector_store.add_memory(
            memory_id=memory_id,content=content,user_id=user_id,type_='preference'
        )
        newly_created.append({"type":"preference","content":content,"source":"inferred"})

    return newly_created