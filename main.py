import os
import sqlite3
from typing import Annotated, TypedDict, List
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
import jwt

# LangGraph & LangChain Imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# --- CONFIGURATION ---
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-default-key")
ALGORITHM = "HS256"
DB_FILE = "app.db"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# Password Hashing Setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# --- LANGGRAPH AGENT SETUP ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

def build_langgraph_agent():
    # Initialize OpenAI Model
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        api_key=OPENAI_API_KEY
    )

    # Define Agent Node
    def chatbot_node(state: AgentState):
        system_instruction = SystemMessage(
            content="You are a helpful, precise AI assistant integrated into a FastAPI backend application."
        )
        response = llm.invoke([system_instruction] + state["messages"])
        return {"messages": [response]}

    # Build Graph
    graph_builder = StateGraph(AgentState)
    graph_builder.add_node("chatbot", chatbot_node)
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_edge("chatbot", END)

    return graph_builder.compile()

# Compile the graph on startup
langgraph_agent = build_langgraph_agent()


# --- DATABASE SETUP ---
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            hashed_password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()


# --- HELPER FUNCTIONS ---
def hash_password(password: str) -> str:
    return pwd_context.hash(password[:72])

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password[:72], hashed_password)

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# --- REQUEST / RESPONSE MODELS ---
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    password: str

class AgentQuery(BaseModel):
    prompt: str


# --- ENDPOINTS ---

# 1. REGISTER
@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserRegister, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    
    cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (user.username, user.email))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Username or Email already registered")

    hashed_pwd = hash_password(user.password)
    cursor.execute(
        "INSERT INTO users (username, email, full_name, hashed_password) VALUES (?, ?, ?, ?)",
        (user.username, user.email, user.full_name, hashed_pwd)
    )
    db.commit()
    return {"status": "success", "message": "User registered successfully!"}

# 2. LOGIN (/token)
@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (form_data.username,))
    db_user = cursor.fetchone()

    if not db_user or not verify_password(form_data.password, db_user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    now = datetime.now(timezone.utc)

    id_token = jwt.encode({
        "sub": db_user["username"],
        "name": db_user["full_name"],
        "email": db_user["email"],
        "exp": now + timedelta(hours=1)
    }, SECRET_KEY, algorithm=ALGORITHM)

    access_token = jwt.encode({
        "sub": db_user["username"],
        "scopes": ["read:agent"],
        "exp": now + timedelta(hours=1)
    }, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "id_token": id_token,
        "access_token": access_token,
        "token_type": "bearer"
    }

# 3. PROTECTED LANGGRAPH AGENT ENDPOINT
@app.post("/api/agent")
def run_agent(query: AgentQuery, user: dict = Depends(verify_token)):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is missing in .env file")

    try:
        # Run prompt through LangGraph
        initial_state = {"messages": [HumanMessage(content=query.prompt)]}
        result = langgraph_agent.invoke(initial_state)
        
        # Extract response message content
        agent_reply = result["messages"][-1].content

        return {
            "status": "success",
            "user": user.get("sub"),
            "prompt": query.prompt,
            "response": agent_reply
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LangGraph Agent execution error: {str(e)}")

# --- STATIC FILES ---
app.mount("/", StaticFiles(directory="static", html=True), name="static")
