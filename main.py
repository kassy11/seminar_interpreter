import os
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from src.audio import download_audio, read
from src.gpt import generate, create_prompt
from logzero import logger
from src.utils import load_env
from src.bot import add_mention, read_format_prompt
import datetime

load_env()
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")

app = App(token=SLACK_BOT_TOKEN)


@app.event("message")
@app.event("app_mention")
def respond_to_mention(event, say):
    user_text = re.sub(r"<[^>]*>", "", event["text"]).strip()
    thread_id = event["ts"]
    user_id = event["user"]
    channel_id = event["channel"]

    # read user input and upload audio files
    format_prompt = ""
    audio_list = []
    exist_audio = False
    if "files" in event and len(event["files"]) > 0:
        for file in event["files"]:
            mimetype = file["mimetype"]
            logger.info(f"User send file. mimetype={mimetype}.")
            if mimetype == "text/plain" or mimetype == "text/markdown":
                logger.info("User send format prompt from file.")
                format_prompt = read_format_prompt(
                    file["url_private_download"], SLACK_BOT_TOKEN
                )
                logger.info("User send format prompt by file.")
            elif mimetype == "audio/mpeg":
                # TODO: audio/mpeg以外にも許可する
                audio_list.append(file["url_private_download"])
                exist_audio = True

    if not exist_audio:
        logger.warning("User does'nt send any audio files.")
        say(
            text=add_mention(user_id, "音声ファイルを指定してください。"),
            thread_ts=thread_id,
            channel=channel_id,
        )
        return

    # format prompt prefers user input over file
    if user_text:
        format_prompt = user_text
        logger.info("User send format prompt from input.")

    response = ""
    for audio in audio_list:
        prefix = str(datetime.datetime.now()).strip()
        tmp_file_name = f"tmp_{prefix}_{os.path.basename(audio)}"
        say(
            text=add_mention(user_id, f"{audio} から音声テキストを取得しています。"),
            thread_ts=thread_id,
            channel=channel_id,
        )

        is_success = download_audio(audio, tmp_file_name, SLACK_BOT_TOKEN)

        if is_success:
            audio_text = read(tmp_file_name)
            print(audio_text)
            prompt = create_prompt(format_prompt, audio_text)
            say(
                text=add_mention(
                    user_id, "議事録を生成中です。\n1~5分ほどかかります。\n"
                ),
                thread_ts=thread_id,
                channel=channel_id,
            )
            answer = generate(prompt)
            response += add_mention(user_id, f"{audio} の議事録です。\n{answer}\n\n")
            logger.info(f"Successfully generate summary from {audio}.")
        else:
            response += add_mention(
                user_id,
                f"{audio} から音声テキストを取得できませんでした。",
            )
    say(text=response, channel=channel_id)


if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
