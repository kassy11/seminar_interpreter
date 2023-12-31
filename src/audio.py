import urllib.request
from logzero import logger
from .utils import load_env
import openai
import os

load_env()


# TODO: read_format_promptと統一できそう
def download_audio(audio, tmp_file_name, slack_bot_token):
    req = urllib.request.Request(audio)
    req.add_header("Authorization", f"Bearer {slack_bot_token}")

    logger.info(f"Downloading audio file from {audio}...")
    try:
        with urllib.request.urlopen(req) as web_file:
            with open(tmp_file_name, "wb") as local_file:
                local_file.write(web_file.read())
    except Exception as e:
        logger.warning(f"Failed to download audio from {audio}.")
        logger.warning(f"Exception: {str(e)}")
        return False

    return True


def read(tmp_file_name):
    # TODO: whisperでテキストを読み取り
    # TODO: 音声ファイルが重いとき
    audio_file = open(tmp_file_name, "rb")
    # File uploads are currently limited to 25 MB and
    # following input file types are supported: mp3, mp4, mpeg, mpga, m4a, wav, and webm.
    # https://platform.openai.com/docs/guides/speech-to-text
    transcript = openai.Audio.transcribe(
        model="whisper-1", file=audio_file, response_format="text"
    )
    os.remove(tmp_file_name)
    return transcript
