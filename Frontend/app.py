import streamlit as st
import requests
import uuid

API_BASE_URL = "http://localhost:8002/api"

st.set_page_config(page_title="Quest AI Agent Chat", page_icon="🤖", layout="wide")

if "token" not in st.session_state:
    st.session_state.token = None

if "user" not in st.session_state:
    st.session_state.user = None

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []


def save_token(token: str, user: dict):
    st.session_state.token = token
    st.session_state.user = user
    st.session_state.conversation_id = None
    st.session_state.messages = []


def clear_session():
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.conversation_id = None
    st.session_state.messages = []


def get_headers():
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}


def login(email: str, password: str):
    try:
        resp = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            save_token(data["access_token"], data["user"])
            return True, "Login successful"
        else:
            try:
                error_data = resp.json()
                return False, error_data.get("detail", "Login failed")
            except:
                return False, f"Login failed (status {resp.status_code})"
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to server. Is the backend running on port 8002?"
    except Exception as e:
        return False, f"Error: {str(e)}"


def register(email: str, password: str, full_name: str = None, role: str = "candidate"):
    try:
        resp = requests.post(
            f"{API_BASE_URL}/auth/register",
            json={"email": email, "password": password, "full_name": full_name, "role": role},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            save_token(data["access_token"], data["user"])
            return True, "Registration successful"
        else:
            try:
                error_data = resp.json()
                return False, error_data.get("detail", "Registration failed")
            except:
                return False, f"Registration failed (status {resp.status_code})"
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to server. Is the backend running on port 8002?"
    except Exception as e:
        return False, f"Error: {str(e)}"


def create_conversation(title: str = None):
    try:
        resp = requests.post(
            f"{API_BASE_URL}/conversations",
            json={"title": title} if title else {},
            headers=get_headers(),
            timeout=10,
        )
        if resp.status_code == 200:
            return True, resp.json()
        else:
            return False, resp.json().get("detail", "Failed to create conversation")
    except Exception as e:
        return False, f"Connection error: {e}"


def list_conversations():
    try:
        resp = requests.get(
            f"{API_BASE_URL}/conversations",
            headers=get_headers(),
            timeout=10,
        )
        if resp.status_code == 200:
            return True, resp.json()
        else:
            return False, resp.json().get("detail", "Failed to list conversations")
    except Exception as e:
        return False, f"Connection error: {e}"


def fetch_messages(conversation_id: str, user_id: str):
    try:
        resp = requests.get(
            f"{API_BASE_URL}/chat/{conversation_id}/messages?user_id={user_id}",
            headers=get_headers(),
            timeout=10,
        )
        if resp.status_code == 200:
            return True, resp.json().get("messages", [])
        else:
            return False, resp.json().get("detail", "Failed to fetch messages")
    except Exception as e:
        return False, f"Connection error: {e}"


def send_message(conversation_id: str, user_id: str, message: str):
    try:
        resp = requests.post(
            f"{API_BASE_URL}/chat",
            json={"conversation_id": conversation_id, "user_id": user_id, "message": message},
            headers=get_headers(),
            timeout=60,
        )
        if resp.status_code == 200:
            return True, resp.json()
        else:
            return False, resp.json().get("detail", "Failed to send message")
    except Exception as e:
        return False, f"Connection error: {e}"


def end_conversation(conversation_id: str, user_id: str):
    try:
        resp = requests.post(
            f"{API_BASE_URL}/chat/{conversation_id}/end?user_id={user_id}",
            headers=get_headers(),
            timeout=10,
        )
        return resp.status_code in (200, 404)
    except Exception:
        return False


if not st.session_state.token:
    st.title(" Quest Copilot - Login")

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="your@email.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                if not email or not password:
                    st.error("Please fill in all fields")
                else:
                    success, msg = login(email, password)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    with tab2:
        with st.form("register_form"):
            email = st.text_input("Email", placeholder="your@email.com")
            full_name = st.text_input("Full Name", placeholder="John Doe")
            role = st.selectbox("Role", ["candidate", "poster"], help="Candidate: looking for jobs. Poster: posting jobs/quests.")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign Up")

            if submitted:
                if not email or not password:
                    st.error("Please fill in all fields")
                else:
                    success, msg = register(email, password, full_name, role)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

else:
    st.title(f" Quest Copilot")

    with st.sidebar:
        st.header(f"Welcome, {st.session_state.user.get('email', 'User')}")
        st.caption(f"Role: {st.session_state.user.get('role', 'candidate')}")
        st.markdown("---")

        if st.button("🚪 Logout"):
            clear_session()
            st.rerun()

        st.markdown("---")
        st.subheader("Conversations")

        success, result = list_conversations()
        if success and result:
            for conv in result:
                btn_label = conv.get("title", conv["id"][:8])[:25]
                if st.button(btn_label, key=f"conv_{conv['id']}"):
                    st.session_state.conversation_id = conv["id"]
                    success_msgs, messages = fetch_messages(conv["id"], st.session_state.user["id"])
                    
                    if success_msgs:
                        # Format messages for Streamlit state
                        formatted_msgs = []
                        for m in messages:
                            meta = {}
                            if m.get("intent"): meta["intent"] = m["intent"]
                            if m.get("confidence"): meta["confidence"] = m["confidence"]
                            if m.get("sources"): meta["sources"] = m["sources"]
                            
                            formatted_msgs.append({
                                "role": m["role"],
                                "content": m["content"],
                                "meta": meta if meta else None
                            })
                        st.session_state.messages = formatted_msgs
                    else:
                        st.session_state.messages = []
                        st.error(f"Could not load messages: {messages}")
                        
                    st.rerun()
        elif success:
            st.info("No conversations yet")
        else:
            st.error("Failed to load conversations")

        st.markdown("---")

        if st.button("➕ New Conversation"):
            success, result = create_conversation()
            if success:
                st.session_state.conversation_id = result["id"]
                st.session_state.messages = []
                st.success("Conversation created!")
                st.rerun()
            else:
                st.error(result)

    if not st.session_state.conversation_id:
        st.info("👈 Select a conversation from the sidebar or create a new one to start chatting!")
    else:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("meta"):
                    with st.expander("Details"):
                        st.json(msg["meta"])

        if prompt := st.chat_input("Ask about quests, share your skills, or request insights…"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                placeholder = st.empty()
                placeholder.markdown("⏳ Thinking…")

                success, result = send_message(st.session_state.conversation_id, st.session_state.user["id"], prompt)

                if success:
                    answer = result.get("answer", "No answer received.")
                    intent = result.get("intent", "unknown")
                    confidence = result.get("confidence")
                    sources = result.get("sources", [])

                    placeholder.markdown(answer)

                    meta = {
                        "intent": intent,
                        "confidence": confidence,
                        "sources": sources,
                    }

                    st.session_state.messages.append(
                        {"role": "assistant", "content": answer, "meta": meta}
                    )

                    with st.expander("Details"):
                        st.json(meta)

                else:
                    placeholder.error(f"Error: {result}")

        if st.session_state.messages and st.button("🛑 End Conversation"):
            if end_conversation(st.session_state.conversation_id, st.session_state.user["id"]):
                st.success("Conversation ended & memory flushed!")
            else:
                st.error("Failed to end conversation")

            st.session_state.conversation_id = None
            st.session_state.messages = []
            st.rerun()