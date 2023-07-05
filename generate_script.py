import yt_dlp
from google.cloud import speech
from pydub import AudioSegment


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
        "extractor_args": {"youtube": {"skip": "dash",},},
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


def transcribe_gcs_with_word_time_offsets(file):
    """Transcribe the given audio file asynchronously and output the word time
    offsets."""
    #     from google.cloud import speech

    with open(file, "rb") as f:
        data = f.read()

    client = speech.SpeechClient()

    audio = speech.RecognitionAudio(content=data)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        #         sample_rate_hertz=16000,
        language_code="en-US",
        audio_channel_count=2,
        enable_word_time_offsets=True,
    )

    operation = client.long_running_recognize(config=config, audio=audio)

    print("Waiting for operation to complete...")
    response = operation.result(timeout=90)

    #     for result in result.results:
    #         alternative = result.alternatives[0]
    #         print(f"Transcript: {alternative.transcript}")
    #         print(f"Confidence: {alternative.confidence}")

    #         for word_info in alternative.words:
    #             word = word_info.word
    #             start_time = word_info.start_time
    #             end_time = word_info.end_time

    #             print(
    #                 f"Word: {word}, start_time: {start_time.total_seconds()}, end_time: {end_time.total_seconds()}"
    #             )

    # Process the response and extract word-level information
    word_timings = []
    for result in response.results:
        for word in result.alternatives[0].words:
            start_time = word.start_time.total_seconds()
            end_time = word.end_time.total_seconds()
            word_text = word.word
            word_timings.append((start_time, end_time, word_text))

    return word_timings


def combine_words(timings, min_chunk_length=4.5, max_chunk_length=5.9):
    chunks = []
    current_chunk = []
    current_chunk_length = 0
    current_chunk_start = None
    last_word_end = None

    for index, timing in enumerate(timings):
        word_start = timing[0]
        word_stop = timing[1]
        word = timing[2]
        word_length = word_stop - word_start

        # If adding the current word exceeds the maximum chunk length, start a new chunk
        if current_chunk_length + word_length > max_chunk_length:
            if current_chunk:
                chunk_start = current_chunk_start
                chunk_end = (
                    timings[index + 1][0]
                    if last_word_end != timings[index + 1][0]
                    else word_stop
                )
                chunk_text = " ".join(current_chunk)
                chunks.append(
                    {
                        "start_time": chunk_start,
                        "end_time": chunk_end,
                        "scene_script": chunk_text,
                    }
                )
            current_chunk = []
            current_chunk_length = 0
            current_chunk_start = word_start

        if current_chunk_start is None:
            current_chunk_start = word_start

        current_chunk.append(word)
        current_chunk_length += word_length
        last_word_end = word_stop

        # If the current chunk length reaches the minimum chunk length, start a new chunk
        if current_chunk_length >= min_chunk_length:
            chunk_start = current_chunk_start
            chunk_end = (
                timings[index + 1][0]
                if last_word_end != timings[index + 1][0]
                else word_stop
            )
            chunk_text = " ".join(current_chunk)
            chunks.append(
                {
                    "start_time": chunk_start,
                    "end_time": chunk_end,
                    "scene_script": chunk_text,
                }
            )
            current_chunk = []
            current_chunk_length = 0
            current_chunk_start = None  # Reset for the new chunk start to be set

    # If there are any remaining words, add them as the last chunk
    if current_chunk:
        chunk_start = current_chunk_start
        chunk_end = last_word_end
        chunk_text = " ".join(current_chunk)
        chunks.append(
            {
                "start_time": chunk_start,
                "end_time": chunk_end,
                "scene_script": chunk_text,
            }
        )

    full_script = ""

    for x in timings:
        full_script += x[2] + " "

    return chunks, full_script

