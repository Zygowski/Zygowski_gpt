import streamlit as st
from openai import OpenAI
from dotenv import dotenv_values
import json
from pathlib import Path
import os

st.set_page_config(page_title="Zygowski GPT", layout="centered")

#
# ZMIENNE
#
model_pricings = {
    "gpt-4o": {
        "input_tokens": 5.00 / 1_000_000,  # per token
        "output_tokens": 15.00 / 1_000_000,  # per token
    },
    "gpt-4o-mini": {
        "input_tokens": 0.150 / 1_000_000,  # per token
        "output_tokens": 0.600 / 1_000_000,  # per token
    }
}
MODEL = "gpt-4o"
USD_TO_PLN = 3.82
PRICING = model_pricings[MODEL]
env = dotenv_values(".env")  # wczytanie zmiennych środowiskowych z pliku .env


if "OPENAI_API_KEY" in st.secrets:
    openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

else:
    # Jeśli nie ma klucza w secrets, sprawdź sesję
    if "api_key" not in st.session_state:
        st.session_state.api_key = ""

    # Jeśli użytkownik jeszcze nie podał klucza, pokaż formularz
    if not st.session_state.api_key:
        st.title("🔐 Wprowadź swój OpenAI API Key")

        with st.form("key_form"):
            api_input = st.text_input("Klucz API:", type="password", placeholder="sk-...")
            submitted = st.form_submit_button("Zatwierdź")

            if submitted:
                if api_input:
                    st.session_state.api_key = api_input
                    st.experimental_rerun()
                else:
                    st.warning("⚠️ Klucz nie może być pusty.")

        st.stop()

    # Użyj klucza od użytkownika
    openai_client = OpenAI(api_key=st.session_state.api_key)

#
# CHATBOT
#
def get_chatbot_reply(user_prompt, memory):
    # dodaj system message
    messages = [
        {
            "role": "system",
            "content": st.session_state["chatbot_personality"],
        },
    ]
    # dodaj wszystkie wiadomości z pamięci
    for message in memory:
        messages.append({"role": message["role"], 
                         "content": message["content"]
                    })

    # dodaj wiadomość użytkownika
    messages.append({"role": "user", 
                     "content": user_prompt
                })

    response = openai_client.chat.completions.create( # respond wała chata  do myślenia
        model=MODEL,
        messages=messages
    )
    usage = {}
    if response.usage: # funkcja responda "usage" zwraca informacje o tokenach
        usage = {
            #input
            "prompt_tokens": response.usage.prompt_tokens,
            #output
            "completion_tokens": response.usage.completion_tokens,
            #input + output
            "total_tokens": response.usage.total_tokens,
        }
    return {
        "role": "assistant",
        "content": response.choices[0].message.content,
        "usage": usage,
    }
#
# HISTORIA KONWERSACJI
#
DEFAULT_PERSONALITY = """
Jesteś pomocnikiem, który odpowiada na wszystkie pytania użytkownika.
Odpowiadaj na pytania w sposób zwięzły i zrozumiały.
""".strip()

DB_PATH = Path("db")
DB_CONVERSATIONS_PATH = DB_PATH / "conversations"
# db/
# ├── current.json
# ├── conversations/
# │   ├── 1.json
# │   ├── 2.json
# │   └── ...
def load_conversation_to_state(conversation):
    st.session_state["id"] = conversation["id"]
    st.session_state["name"] = conversation["name"]
    st.session_state["messages"] = conversation["messages"]
    st.session_state["chatbot_personality"] = conversation["chatbot_personality"]


def load_current_conversation():
    if not DB_PATH.exists():
        DB_PATH.mkdir()
        DB_CONVERSATIONS_PATH.mkdir()
        conversation_id = 1
        conversation = {
            "id": conversation_id,
            "name": "Konwersacja 1",
            "chatbot_personality": DEFAULT_PERSONALITY,
            "messages": [],
        }

        # tworzymy nową konwersację
        with open(DB_CONVERSATIONS_PATH / f"{conversation_id}.json", "w") as f:
            f.write(json.dumps(conversation))

        # która od razu staje się aktualną
        with open(DB_PATH / "current.json", "w") as f:
            f.write(json.dumps({
                "current_conversation_id": conversation_id,
            }))

    else:
        # sprawdzamy, która konwersacja jest aktualna
        with open(DB_PATH / "current.json", "r") as f:
            data = json.loads(f.read())
            conversation_id = data["current_conversation_id"]

        # wczytujemy konwersację
        with open(DB_CONVERSATIONS_PATH / f"{conversation_id}.json", "r") as f:
            conversation = json.loads(f.read())

    load_conversation_to_state(conversation)

# ZAPISYWANIE KONWERSACJI

def save_current_conversation_messages():
    conversation_id = st.session_state["id"]
    new_messages = st.session_state["messages"]

    with open(DB_CONVERSATIONS_PATH / f"{conversation_id}.json", "r") as f:
        conversation = json.loads(f.read())

    with open(DB_CONVERSATIONS_PATH / f"{conversation_id}.json", "w") as f:
        f.write(json.dumps({
            **conversation,
            "messages": new_messages,
        }))



def save_current_conversation_name():
    conversation_id = st.session_state["id"]
    conversation_id = st.session_state.get("id", "id_1")

    new_conversation_name = st.session_state["new_conversation_name"]

    with open(DB_CONVERSATIONS_PATH / f"{conversation_id}.json", "r") as f:
        conversation = json.loads(f.read())

    with open(DB_CONVERSATIONS_PATH / f"{conversation_id}.json", "w") as f:
        f.write(json.dumps({
            **conversation,
            "name": new_conversation_name,
        }))


def save_current_conversation_personality():
    conversation_id = st.session_state["id"]
    new_chatbot_personality = st.session_state["new_chatbot_personality"]

    with open(DB_CONVERSATIONS_PATH / f"{conversation_id}.json", "r") as f:
        conversation = json.loads(f.read())

    with open(DB_CONVERSATIONS_PATH / f"{conversation_id}.json", "w") as f:
        f.write(json.dumps({
            **conversation,
            "chatbot_personality": new_chatbot_personality,
        }))

def generate_conversation_name(messages):
    # Tylko pierwsze 1–2 wiadomości wystarczą
    short_history = "\n".join([f"{m['role']}: {m['content']}" for m in messages[:2]])

    prompt = [
        {"role": "system",
        "content": "Jesteś asystentem, który nadaje krótkie, trafne tytuły konwersacjom."},
        {"role": "user",
        "content": f"Oto początek rozmowy:\n\n{short_history}\n\nNadaj krótki tytuł (maks 5 słów)."}
    ]

    response = openai_client.chat.completions.create(
        model=MODEL,
        messages=prompt,
        max_tokens=20,
    )

    return response.choices[0].message.content.strip()


def create_new_conversation():
    # Szukamy nowego ID
    conversation_ids = [int(p.stem) for p in DB_CONVERSATIONS_PATH.glob("*.json")] # zaczytywanie wszystkich plików z rozszerzeniem json i pobieranie ich ID
    conversation_id = max(conversation_ids, default=0) + 1 # zwiększamy ID o 1

    personality = st.session_state.get("chatbot_personality", DEFAULT_PERSONALITY) # pobieramy osobowość chatbota z sesji lub ustawiamy domyślną
    


    conversation = {
        "id": conversation_id,
        "name": "Nowa konwersacja",
        "chatbot_personality": personality,
        "messages": [],
    }

    with open(DB_CONVERSATIONS_PATH / f"{conversation_id}.json", "w") as f: # zapisywanie nowej konwersacji do pliku
        f.write(json.dumps(conversation))

    with open(DB_PATH / "current.json", "w") as f:
        f.write(json.dumps({"current_conversation_id": conversation_id})) # zapisywanie ID nowej konwersacji jako aktualnej

    load_conversation_to_state(conversation) # załadowanie nowej konwersacji do sesji
    st.rerun()


# funkcja ta pozwala zmienić aktualną konwersacje (ZAŁADOWANIE INNEJ KONWERSACJI)
def switch_conversation(conversation_id):
    with open(DB_CONVERSATIONS_PATH / f"{conversation_id}.json", "r") as f:
        conversation = json.loads(f.read()) # Wczytujemy konwersację

    with open(DB_PATH / "current.json", "w") as f:
        f.write(json.dumps({
            "current_conversation_id": conversation_id, # USTAWIANIE CURRENT CNV NA TĄ KONWERSACJE
        }))

    load_conversation_to_state(conversation) # załadować tą konwersacje do sesji 
    
    
    # --- TU dodajemy automatyczne nadawanie nazwy ---
    if st.session_state["name"] == "Nowa konwersacja":
        new_name = generate_conversation_name(st.session_state["messages"])
        st.session_state["name"] = new_name
        st.session_state.update({"new_conversation_name": new_name})

        save_current_conversation_name()

    st.rerun()


def list_conversations(): # wczytywanie i zwracanie list rozmów
    conversations = []
    for p in DB_CONVERSATIONS_PATH.glob("*.json"):
        with open(p, "r") as f: # otwieranie wszystkich plików o rozszerzeniu json
            conversation = json.loads(f.read())
            conversations.append({
                "id": conversation["id"],
                "name": conversation["name"],
            })# z każdego pliku zwraza id i name

    return conversations # jest to uproszczenie rozmowy 
def delete_conversation(conversation_id):                                                               
    # Usuń plik konwersacji
    file_path = DB_CONVERSATIONS_PATH / f"{conversation_id}.json"
    if file_path.exists():
        file_path.unlink()

    # Jeżeli usunięto aktualnie aktywną konwersację
    if st.session_state["id"] == conversation_id:
        # znajdź nową konwersację do załadowania
        remaining_conversations = list_conversations()
        if remaining_conversations:
            switch_conversation(remaining_conversations[0]["id"])
        else:
            # jeśli nie ma żadnej, utwórz nową
            create_new_conversation()

    st.rerun()                                      


#
# MAIN PROGRAM
#

load_current_conversation()

st.title(":classical_building: MójGPT")

for message in st.session_state["messages"]: # instrukcje dla funkcji messages
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("O co chcesz spytać?")
if prompt:
    user_message = {"role": "user", 
                    "content": prompt}
    
    with st.chat_message("user"):
        st.markdown(user_message["content"])

    st.session_state["messages"].append(user_message)

    with st.chat_message("assistant"):
        chatbot_message = get_chatbot_reply( # odpowiada to za generowanie odpowiedzi
            prompt, 
            memory=st.session_state["messages"][-20:] # nasz chat zapamietuje ostatnie 10 wiadomości
        )
        st.markdown(chatbot_message["content"])

    st.session_state["messages"].append(chatbot_message)

    save_current_conversation_messages()
    # === AUTOMATYCZNA ZMIANA NAZWY PO PIERWSZEJ ODPOWIEDZI ===
    if st.session_state["name"] == "Nowa konwersacja" and len(st.session_state["messages"]) >= 2:
        new_name = generate_conversation_name(st.session_state["messages"])
        st.session_state["name"] = new_name
        st.session_state["new_conversation_name"] = new_name
        save_current_conversation_name()

with st.sidebar:
    st.write("Aktualny model", MODEL)

    total_cost = 0
    for message in st.session_state["messages"]:
        if "usage" in message:
            total_cost += message["usage"]["prompt_tokens"] * PRICING["input_tokens"]
            total_cost += message["usage"]["completion_tokens"] * PRICING["output_tokens"]

    c0, c1 = st.columns(2)
    with c0: 
        st.metric("Koszt rozmowy (USD)", f"{total_cost:.4f}") # koszt rozmowy w USD zaokrąglony do 4 miejsc po przecinku

    with c1:
        st.metric("Koszt rozmowy (PLN)", f"{total_cost * USD_TO_PLN:.4f}") # koszt rozmowy w PLN zaokrąglony do 4 miejsc po przecinku
    
    if "new_conversation_name" not in st.session_state:
        st.session_state["new_conversation_name"] = ""

    
    st.session_state["name"] = st.text_input(
        "Nazwa konwersacji",
        value=st.session_state["new_conversation_name"],
        key="new_conversation_name",
        on_change=save_current_conversation_name,
    )
    st.session_state["chatbot_personality"] = st.text_area(
        "Osobowość chatbota",
        max_chars=1000,
        height=200,
        value=st.session_state["chatbot_personality"],
        key="new_chatbot_personality",
        on_change=save_current_conversation_personality,
    )
    
    st.subheader("Konwersacje")
    if st.button("Nowa konwersacja"):
        create_new_conversation()
    
    # pokazujemy tylko top 5 konwersacji
    conversations = list_conversations()
    sorted_conversations = sorted(conversations, key=lambda x: x["id"], reverse=True)
    
    
    for conversation in sorted_conversations[:5]:                                                        
        c0, c1, c2 = st.columns([6, 3, 1])

        with c0:
            st.write(conversation["name"])

        with c1:
            if st.button("📂", key=f"load_{conversation['id']}", disabled=conversation["id"] == st.session_state["id"]):
                switch_conversation(conversation["id"])

        with c2:
            if st.button("🗑️", key=f"delete_{conversation['id']}"):
                delete_conversation(conversation["id"])

