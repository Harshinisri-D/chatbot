import os
from dotenv import load_dotenv
from langchain.chains import LLMChain
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.messages import SystemMessage
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq

# Load environment variables
load_dotenv()
groq_api_key = os.environ.get("GROQ_API_KEY")
model = "llama3-8b-8192"

# Initialize Groq client
client = ChatGroq(groq_api_key=groq_api_key, model_name=model)

# Memory storage for doctor-patient chat sessions
conversation_memory = {}

def get_chatbot_response(doctor_email, user_input):
    """
    Stores conversation history and gets chatbot response.
    Each doctor has a separate conversation memory.
    """
    if doctor_email not in conversation_memory:
        conversation_memory[doctor_email] = ConversationBufferWindowMemory(
            k=5, memory_key="chat_history", return_messages=True
        )

    memory = conversation_memory[doctor_email]

    system_prompt = (
        "You are a 45-year-old patient named John visiting a medical clinic for a consultation. "
        "Your goal is to simulate real patient experiences and help doctors practice patient interactions."
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessagePromptTemplate.from_template("{human_input}"),
        ]
    )

    conversation = LLMChain(
        llm=client,
        prompt=prompt,
        verbose=False,
        memory=memory,
    )

    response = conversation.predict(human_input=user_input)
    return response

