from langchain_deepseek import ChatDeepSeek

from core.config import DEEPSEEK_API_KEY,DEEPSEEK_MODEL

chat_llm=ChatDeepSeek(
    model=DEEPSEEK_MODEL,
    api_key=DEEPSEEK_API_KEY,
    temperature=0.7
)

extraction_llm=ChatDeepSeek(
    model=DEEPSEEK_MODEL,
    api_key=DEEPSEEK_API_KEY,
    temperature=0
)