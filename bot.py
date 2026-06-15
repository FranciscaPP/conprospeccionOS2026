import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import anthropic
from supabase import create_client
from datetime import datetime

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GHL_BASE_URL = "https://services.leadconnectorhq.com"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SUBCUENTAS = {
    "ecosmart": {"location_id": os.getenv("ECOSMART_ID"), "token": os.getenv("ECOSMART_TOKEN")},
    "clickie": {"location_id": os.getenv("CLICKIE_ID"), "token": os.getenv("CLICKIE_TOKEN")},
    "just4u": {"location_id": os.getenv("JUST4U_ID"), "token": os.getenv("JUST4U_TOKEN")},
    "tiresias": {"location_id": os.getenv("TIRESIAS_ID"), "token": os.getenv("TIRESIAS_TOKEN")},
    "bambutech": {"location_id": os.getenv("BAMBUTECH_ID"), "token": os.getenv("BAMBUTECH_TOKEN")},
    "gbs": {"location_id": os.getenv("GBS_ID"), "token": os.getenv("GBS_TOKEN")},
}

ALIAS_CLIENTES = {
    "ecosmart": ["ecosmart", "eco smart"],
    "clickie": ["clickie", "clicky"],
    "just4u": ["just4u", "just 4u", "just for you", "jazz for you"],
    "tiresias": ["tiresias", "tiresia"],
    "bambutech": ["bambutech", "bambu tech", "bambu"],
    "gbs": ["gbs", "gbs logistics"],
}

def detectar_cliente(texto):
    texto_lower = texto.lower()
    for cliente, aliases in ALIAS_CLIENTES.items():
        for alias in aliases:
            if alias in texto_lower:
                return cliente
    return None

def get_ranking_sdr_hoy():
    try:
        r = supabase.from_("vw_ranking_sdr_hoy").select("*").execute()
        return r.data
    except Exception as e:
        return f"Error: {str(e)}"

def get_llamadas_hoy(cliente=None):
    try:
        query = supabase.from_("vw_llamadas_dashboard").select("*")
        if cliente:
            query = query.ilike("cliente", f"%{cliente}%")
        r = query.execute()
        return r.data
    except Exception as e:
        return f"Error: {str(e)}"

def get_performance_sdr(cliente=None):
    try:
        query = supabase.from_("vw_performance_sdr_diario").select("*")
        if cliente:
            query = query.ilike("cliente", f"%{cliente}%")
        r = query.execute()
        return r.data
    except Exception as e:
        return f"Error: {str(e)}"

def get_reuniones_hoy(cliente=None):
    try:
        query = supabase.from_("vw_reuniones_del_dia").select("*")
        if cliente:
            query = query.ilike("cliente", f"%{cliente}%")
        r = query.execute()
        return r.data
    except Exception as e:
        return f"Error: {str(e)}"

def get_dashboard_general():
    try:
        r = supabase.from_("vw_dashboard_general").select("*").execute()
        return r.data
    except Exception as e:
        return f"Error: {str(e)}"

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pregunta = update.message.text
    await update.message.reply_text("🔍 Consultando datos...")

    cliente = detectar_cliente(pregunta)
    pregunta_lower = pregunta.lower()

    datos = {}

    if any(p in pregunta_lower for p in ["ranking", "quien llamó", "quién llamó", "más llamadas", "trabajó"]):
        datos["ranking_sdr"] = get_ranking_sdr_hoy()

    if any(p in pregunta_lower for p in ["llamada", "llamadas", "llamó", "minutos"]):
        datos["llamadas"] = get_llamadas_hoy(cliente)

    if any(p in pregunta_lower for p in ["reunion", "reunión", "cita", "agendó", "agenda"]):
        datos["reuniones"] = get_reuniones_hoy(cliente)

    if any(p in pregunta_lower for p in ["performance", "rendimiento", "sdr", "actividad"]):
        datos["performance"] = get_performance_sdr(cliente)

    if any(p in pregunta_lower for p in ["general", "resumen", "hoy", "día"]):
        datos["general"] = get_dashboard_general()

    if not datos:
        datos["general"] = get_dashboard_general()
        datos["ranking"] = get_ranking_sdr_hoy()

    system_prompt = f"""Eres Alicia, asistente operacional de ConProspección.
Tienes acceso a datos reales de la agencia desde Supabase.
Responde SIEMPRE en español, clara y concisamente.
NO muestres código ni texto técnico.
Usa los datos para responder directamente la pregunta.
Si los datos están vacíos dilo claramente.

SDRs: Eugenia, Florencia, Mariana, Zoe, Julia, Sandra, Mariela, Yanina
Clientes: Ecosmart, Clickie, Just4U, Tiresias, Bambutech, GBS Logistics
Cliente detectado en pregunta: {cliente if cliente else 'ninguno específico'}

DATOS ACTUALES:
{datos}
"""

    try:
        mensaje = claude.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": pregunta}]
        )
        respuesta = mensaje.content[0].text
    except Exception as e:
        respuesta = f"❌ Error: {str(e)}"

    await update.message.reply_text(respuesta)

def main():
    print("Alicia bot iniciando...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
    print("Bot activo. Esperando mensajes en Telegram...")
    app.run_polling()

if __name__ == "__main__":
    main()
