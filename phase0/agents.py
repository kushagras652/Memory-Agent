import os
import sys

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage,SystemMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import StateGraph,START,END,MessagesState

load_dotenv()


MODEL=os.environ.get("DEEPSEEK_MODEL","deepseek-v4-flash")

SYSTEM_PROMPT=(
    "You are a helpfull assistant."
)

llm=ChatDeepSeek(
    model=MODEL,
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    temperature=0.7
)

def call_model(state:MessagesState):
    response=llm.invoke(state['messages'])
    return {'messages':[response]}


def build_graph():
    graph=StateGraph(MessagesState)
    graph.add_node("agent",call_model)
    graph.add_edge(START,"agent")
    graph.add_edge("agent",END)

    return graph.compile()


def chat_loop():
    app=build_graph()
    history=[SystemMessage(content=SYSTEM_PROMPT)]

    print(f"MEMORY AGENT -Phase 0(no memory)-model:{MODEL}")
    print("Type exit to quit.\n")

    while(True):
        try:
            user_input=input("You: ").strip()
        except(EOFError,KeyboardInterrupt):
            print("\nEXITING")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit"):
            print("EXITING")
            break

        history.append(HumanMessage(content=user_input))

        try:
            result=app.invoke({"messages":history})
        except Exception as e:
            print(f"[error calling model: {e}]",file=sys.stderr)
            history.pop()
            continue

        ai_message=result["messages"][-1]
        history.append(ai_message)

        print(f"Agent : {ai_message.content}\n")


if __name__=="__main__":
    chat_loop()