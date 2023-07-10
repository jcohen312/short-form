import moviepy.editor as mp
import math
from PIL import Image
import numpy
import sys
import pysrt
import requests
import config
import time


def create_srt_file(script_list, output_file):
    with open(output_file, "w") as file:
        count = 1
        for index, word_dict in enumerate(script_list):
            start_time = format_time(word_dict["start_time"])
            stop_time = format_time(word_dict["end_time"])
            subtitle = f"{count}\n{start_time} --> {stop_time}\n{word_dict['word']}\n\n"
            file.write(subtitle)
            count += 1


def format_time(time):
    seconds = int(time)
    milliseconds = int((time - seconds) * 1000)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return "{:02d}:{:02d}:{:02d},{:03d}".format(hours, minutes, seconds, milliseconds)


def time_to_seconds(time_obj):
    return (
        time_obj.hours * 3600
        + time_obj.minutes * 60
        + time_obj.seconds
        + time_obj.milliseconds / 1000
    )


def create_subtitle_clips(
    subtitles, videosize, fontsize=90, font="Rockwell-Bold", color="white", debug=False
):
    subtitle_clips = []

    for subtitle in subtitles:
        start_time = time_to_seconds(subtitle.start)
        end_time = time_to_seconds(subtitle.end)
        duration = end_time - start_time

        video_width, video_height = videosize

        text_clip = (
            mp.TextClip(
                subtitle.text,
                fontsize=fontsize,
                font=font,
                color=color,
                stroke_color="black",
                stroke_width=3,
                size=(video_width * 3 / 4, None),
                method="caption",
            )
            .set_start(start_time)
            .set_duration(duration)
        )
        subtitle_x_position = "center"
        subtitle_y_position = video_height * 2 / 5

        text_position = (subtitle_x_position, subtitle_y_position)
        subtitle_clips.append(text_clip.set_position(text_position))

    return subtitle_clips


def zoom_in_effect(clip, zoom_ratio=0.04):
    def effect(get_frame, t):
        img = Image.fromarray(get_frame(t))
        base_size = img.size

        new_size = [
            math.ceil(img.size[0] * (1 + (zoom_ratio * t))),
            math.ceil(img.size[1] * (1 + (zoom_ratio * t))),
        ]

        # The new dimensions must be even.
        new_size[0] = new_size[0] + (new_size[0] % 2)
        new_size[1] = new_size[1] + (new_size[1] % 2)

        img = img.resize(new_size, Image.LANCZOS)

        x = math.ceil((new_size[0] - base_size[0]) / 2)
        y = math.ceil((new_size[1] - base_size[1]) / 2)

        img = img.crop([x, y, new_size[0] - x, new_size[1] - y]).resize(
            base_size, Image.LANCZOS
        )

        result = numpy.array(img)
        img.close()

        return result

    return clip.fl(effect)


def stitch_video(
    scenes, audio_file, srt_file, output_file_name, final_size=(1080, 1920)
):
    slides = []
    for n, scene in enumerate(scenes):
        slides.append(
            mp.ImageClip(scene["image_path"])
            .set_fps(30)
            .set_duration(scene["end_time"] - scene["start_time"])
            .resize(final_size)
        )

        slides[n] = zoom_in_effect(slides[n], 0.04)

    final_clip = mp.concatenate_videoclips(slides)

    subtitles = pysrt.open(srt_file)
    subtitle_clips = create_subtitle_clips(subtitles, final_clip.size)

    # Add subtitles to the video
    final_video = mp.CompositeVideoClip([final_clip] + subtitle_clips)

    # Load audio file
    audio = mp.AudioFileClip(audio_file)

    # Set the audio of the final clip
    final_video.audio = audio

    # Write the result to a file (remember to adjust the fps as per your requirement)
    final_video.write_videofile(output_file_name, codec="libx264", audio_codec="aac")


def download_file(url, save_path):
    response = requests.get(url)
    response.raise_for_status()  # Raise an exception if the request was unsuccessful

    with open(save_path, "wb") as file:
        file.write(response.content)

    print(f"File downloaded successfully and saved at {save_path}")

    return save_path


def create_did_video(audio_url, source_image_url):
    url = "https://api.d-id.com/talks"

    payload = {
        "script": {
            "type": "audio",
            "subtitles": "false",
            "provider": {"type": "microsoft", "voice_id": "en-US-JennyNeural"},
            "ssml": "false",
            "reduce_noise": "false",
            "audio_url": audio_url,
        },
        "config": {"fluent": "false", "pad_audio": "0.0"},
        "source_url": source_image_url,
        #          "face": { "size": 1920 }
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Basic {config.did_key}",
    }

    response = requests.post(url, json=payload, headers=headers)

    return response.json()


def get_did_talk(talk_id):
    url = f"https://api.d-id.com/talks/{talk_id}"

    headers = {"accept": "application/json", "authorization": f"Basic {config.did_key}"}
    response = requests.get(url, headers=headers)

    return response.json()


def upload_audio_to_did(audio_file_path):
    url = "https://api.d-id.com/audios"

    files = {"audio": (audio_file_path, open(audio_file_path, "rb"), "audio/mpeg")}
    headers = {"accept": "application/json", "authorization": f"Basic {config.did_key}"}

    response = requests.post(url, files=files, headers=headers)

    return response.json()


def process_did_video(audio_file_path, source_image_url, save_path):
    audio_upload_response = upload_audio_to_did(audio_file_path)

    print(audio_upload_response)

    video_create_response = create_did_video(
        audio_upload_response["url"], source_image_url
    )

    print(video_create_response)

    time.sleep(30)

    retrieve_talk_response = get_did_talk(video_create_response["id"])

    print(retrieve_talk_response)

    video_path = download_file(retrieve_talk_response["result_url"], save_path)

    print(video_path)

    return (
        audio_upload_response,
        video_create_response,
        retrieve_talk_response,
        video_path,
    )


def resize_clip(file_path, size=(1080, 1920), subtitle_clips=None):
    clip = mp.VideoFileClip(file_path)

    new_clip = clip.resize(size)

    if subtitle_clips:
        final_video = mp.CompositeVideoClip([new_clip] + subtitle_clips)

    else:
        final_video = new_clip

    audio = mp.AudioFileClip(file_path)

    final_video.audio = audio

    # # Write the result to a file (remember to adjust the fps as per your requirement)
    if file_path.endswith(".mp4"):
        new_path = file_path[:-4] + "_resized.mp4"
    else:
        new_path = file_path

    final_video.write_videofile(new_path, audio_codec="aac")

    return new_path


def stitch_speaker_video(video_path, final_size=(1080, 1920), srt_file=""):
    if srt_file:
        subtitles = pysrt.open(srt_file)

        subtitle_clips = create_subtitle_clips(subtitles, final_size)

        final_video = resize_clip(
            video_path, size=final_size, subtitle_clips=subtitle_clips
        )

    else:
        final_video = resize_clip(video_path, size=final_size)

    return final_video


def create_video_from_scene_styles(
    scenes_with_styles,
    audio_file,
    output_file_name,
    srt_file="",
    final_size=(1080, 1920),
    speaker_image="https://create-images-results.d-id.com/google-oauth2%7C103445322921472417399/drm_U1K7sfMZejIwm6ndz8u1c/image.png",
):
    if all(d.get("scene_style") == "speaker" for d in scenes_with_styles):
        print("All scene_style values are 'speaker'")
        # NO NEED TO GENERATE SCENE DESCRIPTIONS OR IMAGES. SIMPLY GENERATE VIDEO FROM DID AND ADD SUBTITLES

        (
            audio_upload_response,
            video_create_response,
            retrieve_talk_response,
            video_path,
        ) = process_did_video(audio_file, speaker_image, output_file_name)

        final_path = stitch_speaker_video(
            video_path, final_size=final_size, srt_file=srt_file
        )

        print("video created!")
        print(f"video save here --> {final_path}")

    #        RENAME VARIABLES ABOVE, SAVE THEM AND RESIZE CLIP

    # Your code here
    elif all(d.get("scene_style") == "image" for d in scenes_with_styles):
        print("All scene_style values are 'speaker'")


#       JUMP INTO NORMAL PROCESS THAT EXISTS
