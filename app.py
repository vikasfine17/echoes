import streamlit as st
import sqlite3
import requests
from datetime import datetime
from PIL import Image
from io import BytesIO

# -----------------------------
# CONFIGURATION
# -----------------------------

st.set_page_config(
    page_title="ECHOES - Memories Never Die",
    page_icon="🕯️",
    layout="wide"
)

DB_NAME = "echoes.db"
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "gemma4:e2b"

# -----------------------------
# DATABASE
# -----------------------------

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def create_database():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person TEXT NOT NULL,
            title TEXT NOT NULL,
            story TEXT NOT NULL,
            image BLOB,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def save_memory(person, title, story, image):
    conn = get_connection()

    image_data = image.getvalue() if image else None

    conn.execute("""
        INSERT INTO memories
        (person, title, story, image, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        person,
        title,
        story,
        image_data,
        datetime.now().strftime("%d %B %Y, %I:%M %p")
    ))

    conn.commit()
    conn.close()


def get_memories(search=""):
    conn = get_connection()

    if search:
        search_term = f"%{search}%"
        memories = conn.execute("""
            SELECT * FROM memories
            WHERE person LIKE ?
               OR title LIKE ?
               OR story LIKE ?
            ORDER BY id DESC
        """, (search_term, search_term, search_term)).fetchall()
    else:
        memories = conn.execute("""
            SELECT * FROM memories
            ORDER BY id DESC
        """).fetchall()

    conn.close()
    return memories


def delete_memory(memory_id):
    conn = get_connection()
    conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    conn.commit()
    conn.close()


# -----------------------------
# GEMMA AI
# -----------------------------

def ask_echo(question):
    memories = get_memories()

    if not memories:
        return "I don't have any saved memories yet. Please preserve a memory first."

    memory_context = ""

    for memory in memories:
        memory_context += f"""
        Person: {memory['person']}
        Title: {memory['title']}
        Story: {memory['story']}
        Date saved: {memory['created_at']}

        ----------------------
        """

    prompt = f"""
You are ECHOES, a gentle and thoughtful personal memory assistant.

Your job is to help the user recall memories they have saved.

IMPORTANT RULES:
1. Answer using ONLY the memories provided below.
2. Never invent events, names, dates, or details.
3. If the answer is not in the saved memories, say that you do not know.
4. Be warm, respectful, and concise.
5. Do not pretend to be a deceased person or claim to communicate with them.

SAVED MEMORIES:

{memory_context}

USER QUESTION:
{question}
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False
            },
            timeout=180
        )

        response.raise_for_status()
        data = response.json()

        return data["message"]["content"]

    except requests.exceptions.ConnectionError:
        return "I cannot connect to Ollama. Please make sure Ollama is running."

    except requests.exceptions.Timeout:
        return "Gemma is taking too long to respond. Please try again."

    except (requests.exceptions.RequestException, ValueError, KeyError):
        return "Something went wrong while contacting Gemma. Check that your model is available."


# -----------------------------
# DESIGN
# -----------------------------

st.markdown("""
<style>
.stApp {
    background: #0b0912;
    color: #f5f0e8;
}

section[data-testid="stSidebar"] {
    background: #15111f;
    border-right: 1px solid #30243d;
}

h1, h2, h3 {
    color: #e8c77b !important;
}

p, label {
    color: #e5dfea;
}

div.stButton > button {
    background: #8b5cf6;
    color: white;
    border: none;
    border-radius: 9px;
    padding: 10px 18px;
}

div.stButton > button:hover {
    background: #a78bfa;
    color: white;
}

div[data-testid="stMetric"] {
    background: #171321;
    border: 1px solid #30243d;
    padding: 15px;
    border-radius: 12px;
}

textarea, input {
    background-color: #171321 !important;
}

.echo-card {
    background: #171321;
    border: 1px solid #30243d;
    padding: 18px;
    border-radius: 12px;
    margin-bottom: 12px;
}
</style>
""", unsafe_allow_html=True)


# -----------------------------
# APP START
# -----------------------------

create_database()

if "page" not in st.session_state:
    st.session_state.page = "Home"

# Sidebar

st.sidebar.title("🕯️ ECHOES")
st.sidebar.caption("Memories Never Die")
st.sidebar.divider()

page = st.sidebar.radio(
    "NAVIGATION",
    [
        "Home",
        "Preserve Memory",
        "Memory Vault",
        "Ask ECHOES"
    ]
)

st.sidebar.divider()
st.sidebar.caption("Powered by local Gemma 4")
st.sidebar.caption("Your memories stay on this device.")


# -----------------------------
# HOME
# -----------------------------

if page == "Home":

    memories = get_memories()

    st.title("ECHOES")
    st.subheader("Memories Never Die.")

    st.write(
        "A private space to preserve your memories "
        "and revisit the moments that matter."
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Memories Preserved", len(memories))

    with col2:
        st.metric("AI Model", "Gemma 4")

    st.divider()

    st.markdown("### Every memory deserves to live on.")

    st.write(
        "Save your stories, photographs, and meaningful moments. "
        "Later, ask ECHOES questions and let your saved memories "
        "help you remember."
    )

    st.info(
        "ECHOES uses a locally running AI model. "
        "It does not need a cloud AI API."
    )


# -----------------------------
# PRESERVE MEMORY
# -----------------------------

elif page == "Preserve Memory":

    st.title("Preserve a Memory")
    st.write("Save a moment that you never want to forget.")

    with st.form("memory_form"):

        person = st.text_input(
            "Who is this memory about?",
            placeholder="Example: My grandfather"
        )

        title = st.text_input(
            "Memory title",
            placeholder="Example: Our first trip together"
        )

        story = st.text_area(
            "Tell your story",
            placeholder="Write everything you want to remember...",
            height=180
        )

        image = st.file_uploader(
            "Add a photograph (optional)",
            type=["jpg", "jpeg", "png", "webp"]
        )

        submitted = st.form_submit_button(
            "🕯️ Preserve Memory",
            use_container_width=True
        )

        if submitted:

            if not person.strip() or not title.strip() or not story.strip():
                st.error("Please fill in the person, title, and story.")

            else:
                if image:
                    try:
                        with Image.open(image) as uploaded_image:
                            uploaded_image.verify()
                    except Exception:
                        st.error("Please upload a valid image.")
                        st.stop()

                save_memory(person.strip(), title.strip(), story.strip(), image)

                st.success("Your memory has been preserved!")
                st.balloons()


# -----------------------------
# MEMORY VAULT
# -----------------------------

elif page == "Memory Vault":

    st.title("Memory Vault")
    st.write("Explore the moments you have preserved.")

    search = st.text_input(
        "Search memories",
        placeholder="Search by person, title, or story..."
    )

    memories = get_memories(search.strip())

    if not memories:
        st.info("No memories found. Start by preserving one!")

    for memory in memories:

        with st.expander(
            f"🕯️ {memory['title']} — {memory['person']}"
        ):

            st.caption(f"Saved on: {memory['created_at']}")

            st.write(memory["story"])

            if memory["image"]:
                st.image(
                    memory["image"],
                    caption=memory["title"],
                    use_container_width=True
                )

            if st.button(
                "Delete this memory",
                key=f"delete_{memory['id']}"
            ):
                delete_memory(memory["id"])
                st.success("Memory deleted.")
                st.rerun()


# -----------------------------
# ASK ECHOES
# -----------------------------

elif page == "Ask ECHOES":

    st.title("Ask ECHOES")
    st.write(
        "Ask questions about the memories you have saved. "
        "Gemma will answer using your local memory collection."
    )

    memories = get_memories()

    if not memories:
        st.warning("You need to preserve some memories first.")

    else:

        st.markdown("### What would you like to remember?")

        question = st.text_area(
            "Your question",
            placeholder=(
                "Example: What did I write about my grandfather?"
            ),
            height=100
        )

        if st.button("Ask ECHOES", use_container_width=True):

            if not question.strip():
                st.warning("Please enter a question.")

            else:
                with st.spinner("ECHOES is remembering..."):

                    answer = ask_echo(question.strip())

                st.markdown("### 🕯️ ECHOES says")
                st.markdown(
                    f'<div class="echo-card">{answer}</div>',
                    unsafe_allow_html=True
                )

                st.caption("Response generated by your local Gemma 4 model.")

