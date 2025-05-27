import os
import re
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from langchain.schema import SystemMessage
from langchain.chains import LLMChain
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage
import mysql.connector
import os

load_dotenv()

print(f"DB_HOST: {os.getenv('DB_HOST')}")
print(f"DB_USER: {os.getenv('DB_USER')}")
print(f"DB_PASSWORD: {os.getenv('DB_PASSWORD')}")
print(f"DB_NAME: {os.getenv('DB_NAME')}")

# Connect to MySQL
db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    unix_socket=None,  # Prevents named pipe issues
    use_pure=True  # Forces use of Python connector
)
cursor = db.cursor()


# Load environment variables

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Get API key for Groq
groq_api_key = os.getenv("GROQ_API_KEY")
model = "llama3-8b-8192"
client = ChatGroq(groq_api_key=groq_api_key, model_name=model)

# Define system prompt for patient behavior
system_prompt = """You are a medical training bot helping a newly graduated doctor practice patient interactions.  

### **Customization Phase – Strictly Ask One Question at a Time:**  
1. **"What age group are you treating today?"** (Child, Teen, Adult, Middle-aged, Elderly)  
2. **"What severity should the condition be?"** (1. Low 2. Medium 3. High)  
3. **"Shall we start?"** (Wait for "Yes" before proceeding)  

---

### **Instant Roleplay Begins**  
Once the doctor says **"Yes"**, immediately act as the patient.  
- **No more setup explanations.**  
- **No reminding the doctor how to respond.**  

#### **Example Interactions:**  
👴 **Elderly (High Severity):** *"My chest hurts so bad… it's sharp and stabbing. I can’t catch my breath."*  
🧒 **Child (Low Severity):** *"My tummy hurts when I eat sweets."*  

- Keep responses **short and natural**.  
- If the doctor **pauses or responds incorrectly**, **stay in character** instead of correcting them.  

**Example (Wrong Response by Doctor)**  
❌ Doctor: *"OK."*  
✅ Bot: *"Doctor… I feel like something is really wrong. Should I be worried?"*  

- If the doctor **misses key questions**, **hint subtly**:  
  - *"Is this serious, doctor?"*  
  - *"Do I need tests?"*  

---

### **Ending & Feedback**  
- Stop when the doctor says **"End chat."**  
- Provide a **brief score (out of 10) with one sentence of feedback.**  

**Example Feedback:**  
- *"Score: 9/10 – You responded quickly and asked the right questions!"*  
- *"Score: 5/10 – You didn't ask about my pain location or history."*  

This keeps the experience **realistic, immersive, and efficient.** 🚑💡  
"""

# Memory for conversation history
memory = ConversationBufferWindowMemory(k=5, memory_key="chat_history", return_messages=True)

# Function to get chatbot response

def get_response(text):
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        HumanMessagePromptTemplate.from_template("{human_input}"),
    ])
    conversation = LLMChain(llm=client, prompt=prompt, verbose=False, memory=memory)
    
    bot_response = conversation.predict(human_input=text)
    
    # ✅ Save chat history in MySQL
    save_chat(text, bot_response)
    
    return bot_response

# Function to save chat history in MySQL
def save_chat(user_message, bot_response):
    try:
        sql = "INSERT INTO chat_history (user_query, bot_response, timestamp) VALUES (%s, %s, NOW())"
        cursor.execute(sql, (user_message, bot_response))
        db.commit()
    except Exception as e:
        print(f"Error saving chat to database: {e}")
def save_evaluation(conversation, score, feedback):
    try:
        sql = "INSERT INTO evaluations (conversation_summary, score, feedback, timestamp) VALUES (%s, %s, %s, NOW())"
        cursor.execute(sql, (conversation, score, feedback))
        db.commit()
        print("✅ Evaluation saved successfully.")
    except Exception as e:
        print(f"❌ Error saving evaluation to database: {e}")



# Function to evaluate doctor interaction and provide feedback


def evaluate_response(doctor_conversation):
    """
    Evaluates the doctor's conversation based on empathy, clarity, and professionalism,
    assigning a score from 0-10 with proper feedback.
    """
    try:
        if not doctor_conversation.strip():
            return 0, "No conversation detected for evaluation. Please ensure the interaction is recorded."

        evaluation_prompt = f"""
        You are an AI medical evaluator. Assess the following conversation between a doctor and a patient.
        Provide:
        - A score (0-10) based on empathy, clarity, and professionalism.
        - A short feedback summary highlighting strengths and areas for improvement.

        Scoring Guide:
        - 0-3: Poor (dismissive, unclear, lacking empathy)
        - 4-6: Average (some clarity but lacks depth)
        - 7-9: Good (empathetic and professional)
        - 10: Excellent (clear, empathetic, medically sound)

        -----
        Conversation:
        {doctor_conversation}
        -----

        Response Format:
        Score: <number>
        Feedback: <brief feedback>
        """

        # Invoke AI model for evaluation
        result = client.invoke([HumanMessage(content=evaluation_prompt)]).content.strip()

        # Try extracting score and feedback using regex
        match = re.search(r"Score:\s*(\d+)[^\d]*Feedback:\s*(.+)", result, re.DOTALL)
        if match:
            score = int(match.group(1))
            feedback = match.group(2).strip()
        else:
            # Fallback: Extract first number as score if present
            score_match = re.search(r"(\d+)", result)
            score = int(score_match.group(1)) if score_match else 2
            feedback = result if "Feedback" in result else "Evaluation feedback could not be extracted."

        return score, feedback

    except Exception as e:
        print(f"Error in evaluation: {e}")
        return 2, "An error occurred during evaluation. Default score assigned."


# API Route for chatbot response with evaluation
@app.route("/response", methods=["POST"])
def response():
    try:
        data = request.get_json()
        query = data.get("query", "").strip()

        if not query:
            return jsonify({"error": "Query parameter is missing."}), 400

        # ✅ Handle "end chat" case
        if query.lower() == "end chat":
            print("End chat detected. Processing evaluation...")

            # ✅ Fetch entire conversation
            conversation_history = "\n".join(
                [msg.content for msg in memory.load_memory_variables({})["chat_history"]]
            )
            if not conversation_history.strip():
                return jsonify({"response": "No conversation found for evaluation."})

            # ✅ Get score and feedback
            score, feedback = evaluate_response(conversation_history)

            # ✅ Store the evaluation in MySQL
            save_evaluation(conversation_history, score, feedback)

            return jsonify({
                "response": "Chat ended. Here is your evaluation score and feedback.",
                "score": score,
                "feedback": feedback
            })

        # ✅ Otherwise, normal chatbot response
        response = get_response(query)
        return jsonify({"response": response})

    except Exception as e:
        print(f"Full Error: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

# Serve frontend files
frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "FRONTEND")

@app.route("/")
def index():
    return send_from_directory(frontend_path, "index.html")

@app.route("/<path:filename>")
def serve_file(filename):
    return send_from_directory(frontend_path, filename)
@app.route('/evaluation-history', methods=['GET'])
def get_evaluation_history():
    try:
        cursor.execute("SELECT conversation_summary, score, feedback, timestamp FROM evaluations ORDER BY timestamp DESC LIMIT 10")
        evaluations = cursor.fetchall()
        
        evaluation_data = [{"conversation": row[0], "score": row[1], "feedback": row[2], "timestamp": str(row[3])} for row in evaluations]
        
        return jsonify({"evaluations": evaluation_data})
    
    except Exception as e:
        return jsonify({"error": f"Failed to fetch evaluation history: {e}"})


# Run Flask app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
    
@app.route('/chat-history', methods=['GET'])
def get_chat_history():
    try:
        cursor.execute("SELECT user_query, bot_response, timestamp FROM chat_history ORDER BY timestamp DESC LIMIT 10")
        chats = cursor.fetchall()
        
        chat_data = [{"user": row[0], "bot": row[1], "timestamp": str(row[2])} for row in chats]
        
        return jsonify({"chat_history": chat_data})
    
    except Exception as e:
        return jsonify({"error": f"Failed to fetch chat history: {e}"})
