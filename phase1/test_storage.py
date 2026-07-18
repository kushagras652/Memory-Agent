import uuid

from core.storage import metadata_store,vector_store

USER_ID="demo_user"

SAMPLE_MEMORIES=[
    ("preference","Prefers concise,to-the-point answers without filler.",7.0),
    ("fact","Works as a backend engineer,mostly in Python and Go.",6.0),
    ("preference","Is vegetrain.",8.0),
    ("event","Mentioned they're travelling to Lisbon next week.",4.0),
]

def seed():
    print("Seeding sample memories...\n")
    ids=[]
    for type_,content,importance in SAMPLE_MEMORIES:
        memory_id=str(uuid.uuid4())
        metadata_store.insert_memory(
            memory_id=memory_id,
            user_id=USER_ID,
            type_=type_,
            content=content,
            importance=importance,
        )
        vector_store.add_memory(
            memory_id=memory_id,content=content,user_id=USER_ID,type_=type_
        )
        ids.append(memory_id)
        print(f"[{type_:10s}] {content}")
        print()
    return ids
    
def query(text:str):
    print(f"QUERY : {text}\n")
    hits=vector_store.query_similar(text,user_id=USER_ID,k=3)

    if not hits:
        print("no hits-----vector store is empty")
        return 
    
    for hit in hits:
        row=metadata_store.get_memory(hit['id'])
        metadata_store.touch_memory(hit["id"])
        print(f"diatnce={hit['distance']:.4f} content =\"{hit['content']}\"")
        if row:
            print(
                f"   -> metadata:type={row['type']} importance ={row['importance']}"
                f"access_count={row['access_count']+1} status={row['status']}"
            )
        else:
            print("   -> no matching rows in the metadata store")
        print()


if __name__=="__main__":
    metadata_store.init_db()
    seed()

    query("what food does this person eat")
    query("what does this person do for work")

    print("if each query above returned a relevant memory with matching")
    print("metadata (type/importance/status),phase 1 exit criteria are met")



