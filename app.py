import streamlit as st
from openai import OpenAI
from dotenv import dotenv_values
import os

st.set_page_config(page_title="Zygowski GPT", layout="centered")
# Styl dla przewijalnej listy konwersacji


if "started" not in st.session_state:
    st.session_state.started = False

if not st.session_state.started:
    st.title("🤖 Zygowski GPT")
    st.subheader("Cześć! 👋")
    st.write("To moja aplikacja do pisania z AI. Możesz prowadzić rozmowy z inteligentnym asystentem.")
    st.write("Kliknij poniżej, aby rozpocząć.")
    
    if st.button("Rozpocznij rozmowę"):
        st.session_state.started = True
        st.rerun()
    
    st.stop()

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
USD_TO_PLN = 3.74
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
                    st.rerun()
                else:
                    st.warning("⚠️ Klucz nie może być pusty.")

        st.stop()

    # Użyj klucza od użytkownika
    openai_client = OpenAI(api_key=st.session_state.api_key)
def create_new_conversation():
    # (treść funkcji bez zmian – ta którą masz)

# TERAZ ten kod będzie działał poprawnie:
    if "conversations" not in st.session_state:
        st.session_state["conversations"] = {}

    if "current_conversation_id" not in st.session_state:
        create_new_conversation()
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


def load_conversation_to_state(conversation):
    st.session_state["id"] = conversation["id"]
    st.session_state["name"] = conversation["name"]
    st.session_state["messages"] = conversation["messages"]
    st.session_state["chatbot_personality"] = conversation["chatbot_personality"]


def load_current_conversation():

    if "conversations" not in st.session_state:
        st.session_state["conversations"] = {}

    if "current_conversation_id" not in st.session_state:
        # tworzymy pierwszą konwersację
        conversation_id = 1
        conversation = {
            "id": conversation_id,
            "name": "Nowa konwersacja",
            "chatbot_personality": DEFAULT_PERSONALITY,
            "messages": [],
        }
        st.session_state["conversations"][conversation_id] = conversation
        st.session_state["current_conversation_id"] = conversation_id
    else:
        conversation_id = st.session_state["current_conversation_id"]

    conversation = st.session_state["conversations"][conversation_id]


    load_conversation_to_state(conversation)
    if 'editing' not in st.session_state:  # Inicjalizacja stanu edycji
        st.session_state.editing = {}

# ZAPISYWANIE KONWERSACJI

def save_current_conversation_messages():
    conversation_id = st.session_state["id"]
    st.session_state["conversations"][conversation_id]["messages"] = st.session_state["messages"]


def save_current_conversation_name():
    conversation_id = st.session_state["id"]
    st.session_state["conversations"][conversation_id]["name"] = st.session_state["name"]

def save_current_conversation_personality():
    conversation_id = st.session_state["id"]
    st.session_state["conversations"][conversation_id]["chatbot_personality"] = st.session_state["chatbot_personality"]


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
    if "conversations" not in st.session_state:
        st.session_state["conversations"] = {}

    if st.session_state["conversations"]:
        conversation_id = max(st.session_state["conversations"].keys()) + 1
    else:
        conversation_id = 1
    


    conversation = {
        "id": conversation_id,
        "name": "Nowa konwersacja",
        "chatbot_personality": DEFAULT_PERSONALITY,
        "messages": [],
    }

    st.session_state["conversations"][conversation_id] = conversation
    st.session_state["current_conversation_id"] = conversation_id

    load_conversation_to_state(conversation)# załadowanie nowej konwersacji do sesji
    st.rerun()


# funkcja ta pozwala zmienić aktualną konwersacje (ZAŁADOWANIE INNEJ KONWERSACJI)
def switch_conversation(conversation_id: int):
    st.session_state["current_conversation_id"] = conversation_id
    conversation = st.session_state["conversations"][conversation_id]
    
    load_conversation_to_state(conversation) # załadować tą konwersacje do sesji 
    
    
# --- TU dodajemy automatyczne nadawanie nazwy ---
# Upewnij się, że załadowałeś wiadomości przed generowaniem nazwy
    if (
        st.session_state.get("name") == "Nowa konwersacja"
        and st.session_state.get("messages")  # sprawdzamy czy są jakiekolwiek wiadomości
):
        new_name = generate_conversation_name(st.session_state["messages"])
        st.session_state["name"] = new_name
        st.session_state["new_conversation_name"] = new_name
        save_current_conversation_name()

    st.rerun()


def list_conversations(): # wczytywanie i zwracanie list rozmów
    result = []
    if "conversations" not in st.session_state:
        return result

    for conversation_id in sorted(st.session_state["conversations"].keys()):
        conversation = st.session_state["conversations"][conversation_id]
        result.append((conversation["id"], conversation["name"]))

    return result


                                                             
def delete_conversation(conversation_id: int):
    if "conversations" not in st.session_state:
        return

    if conversation_id in st.session_state["conversations"]:
        del st.session_state["conversations"][conversation_id]

        if st.session_state.get("current_conversation_id") == conversation_id:
            remaining = list(st.session_state["conversations"].keys())
            if remaining:
                new_current_id = min(remaining)
                st.session_state["current_conversation_id"] = new_current_id
                load_conversation_to_state(st.session_state["conversations"][new_current_id])
            else:
                create_new_conversation()

    st.rerun()                                      


#
# MAIN PROGRAM
#

load_current_conversation()

st.title(":classical_building: MójGPT")

for idx, message in enumerate(st.session_state["messages"]):
    #st.write(f"Processing message {idx}: {message['role']} - {message['content']}")

    if st.session_state.editing.get(idx, False):
        edited_content = st.text_area(f"Edytuj wiadomość #{idx}", message["content"], key=f"edit_{idx}")


        if st.button("Zapisz", key=f"save_{idx}"):
            # Zaktualizuj istniejącą wiadomość
            st.session_state["messages"][idx]["content"] = edited_content
            st.session_state.editing[idx] = False
            save_current_conversation_messages()

            # (Bezpośrednio reagować na zmienioną wiadomość)
            memory = st.session_state["messages"][-20:]
            bot_response = get_chatbot_reply(edited_content, memory)

            # Zaktualizuj odpowiedź bota tylko wtedy, gdy występuje zaraz po zmienionej wiadomości użytkownika
            if idx + 1 < len(st.session_state["messages"]) and st.session_state["messages"][idx + 1]["role"] == "assistant":
                st.session_state["messages"][idx + 1]["content"] = bot_response['content']
            else:
                # Tylko dodaj, jeśli nie istnieje odpowiedź bota
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": bot_response['content']
                })

            save_current_conversation_messages()
            st.rerun()

        if st.button("Anuluj", key=f"cancel_{idx}"):
            st.session_state.editing[idx] = False
            st.rerun()

    else:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

        # Logika dla przycisku edycji
        if message["role"] == "user":
            #st.write(f"Adding edit button for message {idx}")
            if st.button("Edytuj", key=f"edit_btn_{idx}"):
                st.session_state.editing[idx] = True
                st.rerun()

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
    
    st.subheader("🗂️ Konwersacje")
   

    if st.button("➕ Nowa konwersacja"):
        create_new_conversation()
    
    

    
    conversations = list_conversations()
    sorted_conversations = sorted(conversations, key=lambda x: x["id"], reverse=True)

    
    for conversation in sorted_conversations:                                                        
        #with st.container():
        c0, c1, c2 = st.columns([4, 1, 1])

        with c0:
            st.write(conversation["name"])

        with c1:
            if st.button("📂", key=f"load_{conversation['id']}", disabled=conversation["id"] == st.session_state["id"]):
                switch_conversation(conversation["id"])

        with c2:
            if st.button("🗑️", key=f"delete_{conversation['id']}"):
                delete_conversation(conversation["id"])
    
