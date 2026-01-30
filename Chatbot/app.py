import gradio as gr
import traceback
from Chatbot.bot import answer_query

def chat_fn(message, history):
    try:
        answer = answer_query(message)
        if not answer:
            answer = "I couldn’t process that. Please try rephrasing your question."
    except Exception:
        traceback.print_exc()
        answer = "Something went wrong while processing your request."
    history.append((message, answer))
    return "", history

with gr.Blocks(
    theme=gr.themes.Soft(),
    title="Railway Intelligence Assistant"
) as demo:
    gr.Markdown("""
    # 🚆 Railway Intelligence Assistant  
    **LLM-powered RAG system using FAISS, live APIs, and ChatGPT**
    """)
    chatbot = gr.Chatbot(height=420)
    msg = gr.Textbox(
        placeholder="Ask about railway rules, safety, or live train information…",
        show_label=False
    )
    msg.submit(chat_fn, [msg, chatbot], [msg, chatbot])
demo.launch()
