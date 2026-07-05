import os
import json
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).parent
CALENDAR_TOKEN = BASE_DIR / "token_calendar.json"
CALENDAR_CREDS = BASE_DIR / "credentials_calendar.json"


def _obtener_credenciales():
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow

        SCOPES = ['https://www.googleapis.com/auth/calendar']
        creds = None

        if CALENDAR_TOKEN.exists():
            creds = Credentials.from_authorized_user_file(str(CALENDAR_TOKEN), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not CALENDAR_CREDS.exists():
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CALENDAR_CREDS), SCOPES)
                creds = flow.run_local_server(port=0)

            with open(CALENDAR_TOKEN, 'w') as token:
                token.write(creds.to_json())

        return creds
    except Exception:
        return None


def listar_eventos(dias=7):
    creds = _obtener_credenciales()
    if not creds:
        return "No hay credenciales de Google Calendar."

    try:
        from googleapiclient.discovery import build

        service = build('calendar', 'v3', credentials=creds)
        ahora = datetime.utcnow()
        futuro = ahora + timedelta(days=dias)
        events_result = service.events().list(
            calendarId='primary',
            timeMin=ahora.isoformat() + 'Z',
            timeMax=futuro.isoformat() + 'Z',
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        eventos = events_result.get('items', [])
        if not eventos:
            return "No hay eventos proximos."

        respuesta = "Proximos eventos:\n"
        for ev in eventos[:5]:
            start = ev['start'].get('dateTime', ev['start'].get('date', '?'))
            summary = ev.get('summary', 'Sin titulo')
            respuesta += f"• {start}: {summary}\n"

        return respuesta.strip()
    except Exception as e:
        return f"Error consultando calendario: {e}"


def crear_evento(titulo, fecha, hora=None):
    creds = _obtener_credenciales()
    if not creds:
        return "No hay credenciales de Google Calendar."

    try:
        from googleapiclient.discovery import build

        service = build('calendar', 'v3', credentials=creds)

        start_dt = f"{fecha}T{hora or '10:00:00'}"
        end_dt = f"{fecha}T{hora and str(int(hora.split(':')[0]) + 1).zfill(2) + ':00:00' or '11:00:00'}"

        event = {
            'summary': titulo,
            'start': {'dateTime': start_dt, 'timeZone': 'America/Asuncion'},
            'end': {'dateTime': end_dt, 'timeZone': 'America/Asuncion'},
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Evento creado: {titulo} el {fecha} a las {hora or '10:00'}"
    except Exception as e:
        return f"Error creando evento: {e}"


def resumen_hoy():
    creds = _obtener_credenciales()
    if not creds:
        return "Sin credenciales de calendario."

    try:
        from googleapiclient.discovery import build

        service = build('calendar', 'v3', credentials=creds)
        hoy = datetime.utcnow()
        manana = hoy + timedelta(days=1)
        events_result = service.events().list(
            calendarId='primary',
            timeMin=hoy.isoformat() + 'Z',
            timeMax=manana.isoformat() + 'Z',
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        eventos = events_result.get('items', [])
        if not eventos:
            return "No tienes eventos para hoy."

        respuesta = "Tus eventos de hoy:\n"
        for ev in eventos[:5]:
            start = ev['start'].get('dateTime', ev['start'].get('date', '?'))
            summary = ev.get('summary', 'Sin titulo')
            respuesta += f"• {start}: {summary}\n"

        return respuesta.strip()
    except Exception as e:
        return f"Error: {e}"
