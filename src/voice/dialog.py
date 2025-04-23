import datetime
from db import SessionLocal
from models import VoiceSession, VoicePrompt, VoiceResponse
from .tts import tts_play
from .stt import listen

def run_voice_dialog(schedule_id: int, prompt_texts: list[str], timeout: int = 5) -> dict[str, str]:
    """
    Run a voice dialog session:
    1. Create a VoiceSession row with ACTIVE status.
    2. For each prompt text:
       - Play via TTS
       - Insert VoicePrompt
       - Listen for response via STT
       - Insert VoiceResponse
    3. Update session status to SUCCESS and set ended_at.
    Returns a mapping of prompt_text to recognized response.
    """
    session = SessionLocal()
    vs = VoiceSession(schedule_id=schedule_id)
    session.add(vs)
    session.commit()
    session.refresh(vs)

    responses = {}
    for text in prompt_texts:
        # play prompt
        tts_play(text)
        # record prompt
        vp = VoicePrompt(session_id=vs.id, prompt_text=text)
        session.add(vp)
        session.commit()
        session.refresh(vp)
        # listen for response
        resp_text = listen(duration=timeout)
        # record response
        vr = VoiceResponse(prompt_id=vp.id, recognized_text=resp_text)
        session.add(vr)
        session.commit()
        session.refresh(vr)
        responses[text] = resp_text

    # finalize session
    vs.ended_at = datetime.datetime.utcnow()
    vs.session_status = "SUCCESS"
    session.commit()
    session.close()

    return responses
