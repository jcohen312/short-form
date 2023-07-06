import yt_dlp
from google.cloud import speech
from pydub import AudioSegment
import whisper_timestamped as whisper
import json


def download_audio_from_youtube(url, output_path):
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
        "outtmpl": output_path,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def download_audio_from_tiktok(url, output_path):
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
        "outtmpl": output_path,
        "extractor_args": {
            "youtube": {
                "skip": "dash",
            },
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def download_audio(url, output_path):
    if "youtube.com" in url:
        print("youtube source detected")

        download_audio_from_youtube(url, output_path)

        print("video audio downloaded")

    elif "www.tiktok.com" in url:
        print("tiktok source detected")

        download_audio_from_tiktok(url, output_path)

        print("video audio downloaded")


def transcribe_audio(audio_file_path):
    audio = whisper.load_audio(audio_file_path)

    model = whisper.load_model("openai/whisper-large-v2", device="cpu")

    result = whisper.transcribe(model, audio, language="en")

    raw = json.dumps(result, indent=2, ensure_ascii=False)

    audio_json = json.loads(raw)

    return audio_json


def get_word_timings(full_audio_json):
    words_raw = [
        word
        for chunk in [x["words"] for x in full_audio_json["segments"]]
        for word in chunk
    ]

    key_mapping = {"start": "start_time", "end": "end_time", "text": "word"}

    # Rename the keys in each dictionary
    words = []
    for dictionary in words_raw:
        renamed_dict = {
            key_mapping.get(key, key): value for key, value in dictionary.items()
        }
        words.append(renamed_dict)

    return words


def create_scene_chunks_by_time(timings, max_length: float = 4.5):
    chunks = []
    current_chunk = []
    current_chunk_length = 0
    current_chunk_start = 0

    for index, timing in enumerate(timings):
        word_start = timing["start_time"]
        word_stop = timing["end_time"]
        word = timing["word"]
        word_length = word_stop - word_start

        if index != (len(timings) - 1):
            additional_time = timings[index + 1]["start_time"] - word_stop

            total_time = word_length + additional_time

            #             print(timing)

            if current_chunk_length < 4.5:
                current_chunk.append(word)

                current_chunk_length += word_length + additional_time

            elif current_chunk_length >= max_length:
                chunks.append(
                    {
                        "start_time": current_chunk_start,
                        "end_time": current_chunk_start + current_chunk_length,
                        "scene_script": " ".join(current_chunk),
                        "scene_length": current_chunk_length,
                    }
                )

                current_chunk_start = word_start

                current_chunk_length = total_time

                current_chunk = [word]
        else:
            #             print(timing)

            current_chunk.append(word)

            current_chunk_length += word_length + additional_time

            chunks.append(
                {
                    "start_time": current_chunk_start,
                    "end_time": current_chunk_start + current_chunk_length,
                    "scene_script": " ".join(current_chunk),
                    "scene_length": current_chunk_length,
                }
            )

    return chunks


def create_scenes_by_segments(full_audio_json):
    scene_timings = []

    for index, segment in enumerate(full_audio_json["segments"]):
        start_time = segment["start"]
        end_time = segment["end"]
        scene_script = segment["text"]

        if index != (len(full_audio_json["segments"]) - 1):
            additional_time = full_audio_json["segments"][index + 1]["start"] - end_time
        else:
            additional_time = 0

        scene_timings.append(
            {
                "start_time": start_time,
                "end_time": end_time + additional_time,
                "scene_script": scene_script,
                "scene_length": end_time + additional_time - start_time,
            }
        )

    return scene_timings


def process_audio(audio_file, scene_method: str = "time", max_length: float = 4.5):
    aj = transcribe_audio(audio_file)

    print("Audio Transcribed!")

    word_timings = get_word_timings(aj)

    if scene_method == "time":
        scenes = create_scene_chunks_by_time(word_timings, max_length=max_length)

    elif scene_method == "segment":
        scenes = create_scenes_by_segments(aj)

    full_script = aj["text"].strip()

    return aj, word_timings, scenes, full_script
