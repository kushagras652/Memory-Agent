from langchain_core.messages import AIMessage,HumanMessage
from langgraph.graph import StateGraph,MessagesState,START,END
from core.extraction import extract_and_store
from core.llm import chat_llm

SYSTEM_PROMPT=(
    "You are a helpful assistent.Memory retrieval is not wered in yet -"
    "facts are being saved in the background,but you can't recall them"
    "in your response yet."
)

class AgentState(MessagesState):
    user_id:str
    last_extracted:list

def call_model(state:AgentState):
    response=chat_llm.invoke(state['messages'])
    return {"messages":[response]}

def memory_extractor_node(state:AgentState):
    messages=state['messages']
    last_ai=next(m for m in reversed(messages) if isinstance(m,AIMessage))
    last_human=next(m for m in reversed(messages) if isinstance(m,HumanMessage))
    user_id=state.get("user_id","default_user")

    accepted=extract_and_store(last_human.content,last_ai.content,user_id)
    return {"last_extracted":accepted}

def build_graph():
    graph=StateGraph(AgentState)
    graph.add_node("agent",call_model)
    graph.add_node("memory_extractor",memory_extractor_node)
    graph.add_edge(START,'agent')
    graph.add_edge("agent","memory_extractor")
    graph.add_edge("memory_extractor",END)
    return graph.compile()