import httpx
import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# Configurar SDK de Gemini al iniciar
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


class AIService:
    @staticmethod
    async def analyze_market(context: dict):
        # 1. Intentar con DeepSeek primero
        result = await AIService._call_deepseek(context)

        # 2. Si DeepSeek falla, usar Gemini como respaldo
        if "error" in result:
            logging.info(f"DeepSeek falló ({result['error']}), usando Gemini 2.5 Flash como respaldo...")
            gemini_result = await AIService._call_gemini(context)
            if "error" not in gemini_result:
                return gemini_result
            return {"error": f"Ambos servicios fallaron. DeepSeek: {result['error']} | Gemini: {gemini_result['error']}"}

        return result

    @staticmethod
    async def _call_deepseek(context: dict):
        if not DEEPSEEK_API_KEY:
            return {"error": "DeepSeek API Key no configurada."}

        prompt = AIService._get_prompt(context)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{DEEPSEEK_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": "Eres un motor de análisis probabilístico para un bot de trading algorítmico."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.5
                    }
                )
                if response.status_code != 200:
                    return {"error": f"DeepSeek Error: {response.status_code}"}

                result = response.json()
                return {"analysis": result['choices'][0]['message']['content']}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    async def _call_gemini(context: dict):
        if not GEMINI_API_KEY:
            return {"error": "Gemini API Key no configurada."}

        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            prompt = AIService._get_prompt(context)
            response = model.generate_content(prompt)
            analysis_text = response.text
            return {"analysis": f"**[ANÁLISIS - GEMINI 2.5 FLASH]**\n\n{analysis_text}"}
        except Exception as e:
            logging.error(f"Gemini SDK Error: {e}")
            return {"error": str(e)}

    @staticmethod
    def _get_prompt(context: dict):
        tp = context.get('tp', 0)
        sl = context.get('sl', 0)
        price = context.get('price', 0)

        tp_dist_pct = abs((tp - price) / price * 100) if price else 0
        sl_dist_pct = abs((price - sl) / price * 100) if price else 0

        return f"""
Actúa como un Analista de Trading Algorítmico Senior especializado en criptomonedas con apalancamiento.

CONTEXTO DE LA OPERACIÓN ACTUAL:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Símbolo:          {context.get('symbol', 'N/A')}
• Dirección:        {context.get('trade_type', 'N/A')} (posición activa)
• Precio Actual:    ${price}
• RSI (14):         {context.get('rsi', 0):.1f}

NIVELES TÉCNICOS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Take Profit (TP): ${tp}  →  distancia {tp_dist_pct:.2f}% del precio actual
• Stop Loss (SL):   ${sl}  →  distancia {sl_dist_pct:.2f}% del precio actual

CONFIGURACIÓN DEL BOT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Temporalidad:     {context.get('timeframe', '1h')}
• Apalancamiento:   {context.get('leverage', 5)}x (margen ISOLADO)
• Multiplicador ATR: {context.get('atr_multiplier', 2.0)}

ANÁLISIS REQUERIDO (responde en español):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. **Probabilidades estimadas:**
   - % de probabilidad de alcanzar el TP
   - % de probabilidad de alcanzar el SL antes del TP
   - Justifica basándote en la posición del RSI, distancias y dirección

2. **Análisis técnico:**
   - Estado del RSI y qué implica para esta posición (¿momentum a favor o en contra?)
   - Riesgo de reversión basado en el RSI
   - Ratio Riesgo/Recompensa implícito

3. **Veredicto:**
   - Nivel de confianza: Alta / Media / Baja
   - Razón principal del veredicto

IMPORTANTE: Sé directo y objetivo. Usa lenguaje técnico experto. No des consejos financieros, solo análisis probabilístico basado en los datos.
"""
