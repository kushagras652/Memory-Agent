import sys

from langchain_core.messages import HumanMessage,SystemMessage
from core.graph import SYSTEM_PROMPT,build_graph
from core.storage import metadata_store

def chat_loop():
    metadata_store.init_db()
    app=build_graph()

    user_id=input("User id (for this session):").strip() or "default_user"
    history=[SystemMessage(content=SYSTEM_PROMPT)]

    print(f"\n Memory Agent- user id:{user_id}")
    print("Type 'exit' to quit.\n")

    while True:
        try:
            user_input=input("You: ").strip()
        except (EOFError,KeyboardInterrupt):
            print("\nExiting")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit","quit"):
            print("Exiting")
            break

        history.append(HumanMessage(content=user_input))

        try:
            result=app.invoke({"messages":history,"user_id":user_id})
        except Exception as e:
            print(f"[error calling model: {e}]",file=sys.stderr)
            history.pop()
            continue


        if result.get('retrieved_context'):
            print("   [memories recalled]")
            for line in result['retrieved_context'].splitlines():
                print(f"   {line}")

        ai_message=result['messages'][-1]
        history.append(ai_message)
        print(f"Agent: {ai_message.content}\n")


        for mem in result.get("last_extracted",[]):
            tag="inferred from pattern" if mem.get('source')=='inferred' else "stated"
            print(f"[memory saved -{tag}] ({mem['type']}) {mem['content']}")
        if result.get("last_extracted"):
            print()


if __name__=="__main__":
    chat_loop()
