import pyttsx3

_engine = None

def tts_play(text: str, rate: int = None, volume: float = None):
    """
    Play text-to-speech for given text using pyttsx3.
    """
    global _engine
    if _engine is None:
        _engine = pyttsx3.init()
    if rate is not None:
        _engine.setProperty('rate', rate)
    if volume is not None:
        _engine.setProperty('volume', volume)
    _engine.say(text)
    _engine.runAndWait()
