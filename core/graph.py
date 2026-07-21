from langchain_core.messages import AIMessage,HumanMessage,SystemMessage
from langgraph.graph import StateGraph,MessagesState,START,END
from core.extraction import extract_and_store
from core.llm import chat_llm
from core.retrieval import format_memories,retrieve_relevant_memories

SYSTEM_PROMPT=(
    "You are a helpful assistent with long-term memory of this user."
    "If relevant memories are provided below, use them naturally to"
    "personalize your response - don't announce that you're recalling"
    "something, just act on it.If no memories are relevant to the"
    "current message, ignore the memory section entirely."
)

class AgentState(MessagesState):
    user_id:str
    last_extracted:list
    retrieved_context:str

def retrieval_node(state:AgentState):
    messages=state['messages']
    last_human=next(m for m in reversed(messages) if isinstance(m,HumanMessage))
    user_id=state.get("user_id","default_user")

    memories=retrieve_relevant_memories(last_human.content,user_id)
    return {"retrieved_context":format_memories(memories)}

def call_model(state:AgentState):
    retrieved_context=state.get("retrieved_context","")
    messages=state['messages']

    if retrieved_context:
        sys_msgs=[m for m in messages if isinstance(m,SystemMessage)]
        other_msgs=[m for m in messages if not isinstance(m,SystemMessage)]
        memory_msg=SystemMessage(
            content=f"Relevant memories about this user:\n{retrieved_context}"
        )
        final_messages=sys_msgs + [memory_msg] + other_msgs
    else:
        final_messages=messages

    
    response=chat_llm.invoke(final_messages)
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
    graph.add_node("retrieval",retrieval_node)
    graph.add_node("agent",call_model)
    graph.add_node("memory_extractor",memory_extractor_node)
    graph.add_edge(START,'retrieval')
    graph.add_edge("retrieval","agent")
    graph.add_edge("agent","memory_extractor")
    graph.add_edge("memory_extractor",END)
    return graph.compile()